import os
import zlib
import math
import json
import shutil
import importlib
from typing import Tuple, List, Dict

import bpy
import bpy.types
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import blender_parser as bpa
from . import datastruct as dat
from . import byteutils as byt
from . import rawdata as rwd
from . import smalltype as smt
from . import modify_data as mfd
from . import model_exporter as mex

MAX_JOINT_NUM = 130

bl_info = {
    "name": "Dalbaragi Model Exporter",
    "author": "Sungmin Woo",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Export > Dalbaragi Model (.dmd)",
    "description": "Export a model file for Dalbargi engine.",
    "warning": "Under development.",
    "wiki_url": "",
    "category": "Import-Export",
    "tracker_url": ""
}


def _fixVecRotations(x: float, y: float, z: float) -> Tuple[float, float, float]:
    return float(x), float(z), -float(y)


def _normalizeVec3(x: float, y: float, z: float):
    length = math.sqrt(x * x + y * y + z * z)
    return x / length, y / length, z / length


def _copyImage(image: bpy.types.Image, dstpath: str) -> None:
    if image.packed_file is None:  # Not packed
        srcpath = bpy.path.abspath(image.filepath)
        if os.path.isfile(srcpath):
            shutil.copyfile(srcpath, dstpath)
            print("[DAL] Image copied: {}".format(dstpath))
        else:
            raise FileNotFoundError("[DAL] Image not found: {}".format(srcpath))
    else:  # Packed
        packed = image.packed_files[0]
        original_path = packed.filepath
        packed.filepath = dstpath
        packed.save()
        packed.filepath = original_path
        print("[DAL] Image exported from packed: {}".format(dstpath))


class AnimationParser:
    @classmethod
    def parseSkeleton(cls):
        numArma = len(bpy.data.armatures)
        if 0 == numArma:
            return dat.SkeletonInterface()
        elif numArma > 1:
            raise RuntimeError("[DAL] Multiple armatures.")

        skeleton = dat.SkeletonInterface()

        armature: bpy.types.Armature = bpy.data.armatures[0]
        rootBone = cls.__findRootBone(armature.bones)

        index = skeleton.makeIndexOf(rootBone.name)
        boneInfo = skeleton[index]
        boneInfo.m_parentName = ""

        boneInfo.m_offsetMat.set(rootBone.matrix_local)

        cls.__parseSkelRecur(rootBone, skeleton)
        return skeleton

    @classmethod
    def __parseSkelRecur(cls, bone: bpy.types.Bone, skeleton: dat.SkeletonInterface) -> None:
        for child in bone.children:
            index = skeleton.makeIndexOf(child.name)
            boneInfo = skeleton[index]
            boneInfo.m_parentName = bone.name

            if (child.get("dal_phy_hairRoot", None) is not None):
                boneInfo.setHairRoot();
            elif (child.get("dal_phy_skirtRoot", None) is not None):
                boneInfo.setSkirtRoot();

            # rot = mathutils.Matrix.Rotation(math.radians(-90.0), 4, 'X')
            boneInfo.m_offsetMat.set(child.matrix_local)

            cls.__parseSkelRecur(child, skeleton)

    @classmethod
    def __findRootBone(cls, bones):
        root = None

        for bone in bones:
            if bone.parent is None:
                if root is None:
                    root = bone
                else:
                    raise ValueError("[DAL] There are two root bone: {}, {}".format(root.name, bone.name))

        if root is None:
            raise ValueError("[DAL] Failed to find a root bone")

        return root

    class AnimInfoVar:
        def __init__(self):
            self.__data = {}

        def add(self, channel: int, timepoint: float, value: float) -> None:
            assert isinstance(channel, int)
            assert isinstance(timepoint, float)

            if timepoint not in self.__data.keys():
                self.__data[timepoint] = {}
            self.__data[timepoint][channel] = float(value)

        def get(self, timepoint: float, channel: int) -> float:
            assert isinstance(channel, int)
            assert isinstance(timepoint, float)

            return self.__data[timepoint][channel]

        def getExtended(self, timepoint: float, channel: int) -> float:
            assert isinstance(channel, int)
            assert isinstance(timepoint, float)

            try:
                return self.__data[timepoint][channel]
            except KeyError:
                requestedOrder = self.__timepointToOrder(timepoint)
                prevOrder = requestedOrder - 1
                if prevOrder < 0:
                    raise RuntimeError("[DAL] First keyframe need all its channels with a value.")
                prevTimepoint = self.__orderToTimepoint(prevOrder)
                return self.get(prevTimepoint, channel)

        def iterTimepoints(self) -> iter:
            return iter(self.__getSortedTimepoints())

        def __getSortedTimepoints(self) -> List[float]:
            timepoints = list(self.__data.keys())
            timepoints.sort()
            return timepoints

        def __orderToTimepoint(self, order: int) -> float:
            assert isinstance(order, int)
            assert order >= 0
            return self.__getSortedTimepoints()[order]

        def __timepointToOrder(self, timepoint: float) -> int:
            assert isinstance(timepoint, float)
            return self.__getSortedTimepoints().index(timepoint)

    class BoneAnimInfo:
        def __init__(self):
            self.__data = {}  # dict< var name, dict< time, dict<channel, value> > >

        def __getitem__(self, key) -> "AnimationParser.AnimInfoVar":
            return self.__data[key]

        def add(self, varName: str, channel: int, timepoint: float, value: float) -> None:
            assert isinstance(channel, int)
            assert isinstance(timepoint, float)
            assert isinstance(varName, str)

            if varName not in self.__data.keys():
                self.__data[varName] = AnimationParser.AnimInfoVar()
            self.__data[varName].add(channel, timepoint, value)

        def items(self):
            return self.__data.items()

    class BoneDict:
        def __init__(self):
            self.__bones: Dict[str, AnimationParser.BoneAnimInfo] = {}

        def __str__(self):
            return str(self.__bones)

        def __getitem__(self, boneName: str) -> "AnimationParser.BoneAnimInfo":
            try:
                return self.__bones[boneName]
            except KeyError:
                self.__bones[boneName] = AnimationParser.BoneAnimInfo()
                return self.__bones[boneName]

        def items(self):
            return self.__bones.items()

        def print(self):
            for name, info in self.__bones.items():
                print(name)
                for varName, data in info.items():
                    print("\t", varName)
                    for x in data.items():
                        print("\t\t", x)

    @classmethod
    def parseActions(cls, skeleton: dat.SkeletonInterface) -> List[dat.Animation]:
        animations = []

        for action in bpy.data.actions:
            action: bpy.types.Action
            anim = dat.Animation(action.name, skeleton)
            anim.m_tickPerSec = bpy.context.scene.render.fps

            bonedict: AnimationParser.BoneDict = cls.__makeBoneDict(action)

            for joint in anim.m_joints:
                joint: dat.JointAnim

                boneInfo: AnimationParser.BoneAnimInfo = bonedict[joint.m_name]

                try:
                    poses: AnimationParser.AnimInfoVar = boneInfo["location"]
                except KeyError:
                    pass
                else:
                    for tp in poses.iterTimepoints():
                        x = poses.get(tp, 0)
                        y = poses.get(tp, 1)
                        z = poses.get(tp, 2)
                        joint.addPos(tp, x, y, z)

                try:
                    rotations: AnimationParser.AnimInfoVar = boneInfo["rotation_quaternion"]
                except KeyError:
                    pass
                else:
                    for tp in rotations.iterTimepoints():
                        # It always confuses me.
                        w = rotations.get(tp, 0)
                        x = rotations.get(tp, 1)
                        y = rotations.get(tp, 2)
                        z = rotations.get(tp, 3)
                        joint.addRotation(tp, x, y, z, w)

                try:
                    scales: AnimationParser.AnimInfoVar = boneInfo["scale"]
                except KeyError:
                    pass
                else:
                    for tp in scales.iterTimepoints():
                        x = scales.get(tp, 0)
                        y = scales.get(tp, 1)
                        z = scales.get(tp, 2)
                        averageScale = (x + y + z) / 3
                        joint.addScale(tp, averageScale)

            animations.append(anim)

        return animations

    @classmethod
    def __makeBoneDict(cls, action) -> BoneDict:
        bones = cls.BoneDict()

        for fcu in action.fcurves:
            boneName, varName = cls.__splitFcuDataPath(fcu.data_path)
            channel = fcu.array_index
            bone: AnimationParser.BoneAnimInfo = bones[boneName]
            for keyframe in fcu.keyframe_points:
                bone.add(varName, channel, keyframe.co[0], keyframe.co[1])

        return bones

    @staticmethod
    def __splitFcuDataPath(path: str):
        pass1 = path.split('"')
        boneName = pass1[1]

        pass2 = pass1[2].split(".")
        varName = pass2[-1]

        return boneName, varName


class MaterialParser:
    @classmethod
    def parse(cls, blenderMat):
        assert blenderMat is not None

        bsdf = cls.__findPrincipledBSDFNode(blenderMat.node_tree.nodes)
        if bsdf is None:
            raise ValueError("[DAL] Only Principled BSDF node is supported.")

        material = dat.Material()

        node_baseColor = bsdf.inputs["Base Color"]
        node_metallic = bsdf.inputs["Metallic"]
        node_roughness = bsdf.inputs["Roughness"]

        material.m_roughness = node_roughness.default_value
        material.m_metallic = node_metallic.default_value

        imageNode = cls.__findImageNodeRecur(node_baseColor)
        if imageNode is not None:
            material.m_diffuseMap = imageNode.image.name
        # else:
        #    raise ValueError("[DAL] Diffuse map must be defined.")

        imageNode = cls.__findImageNodeRecur(node_metallic)
        if imageNode is not None:
            material.m_metallicMap = imageNode.image.name

        imageNode = cls.__findImageNodeRecur(node_roughness)
        if imageNode is not None:
            material.m_roughnessMap = imageNode.image.name

        return material

    @staticmethod
    def __findPrincipledBSDFNode(nodes):
        for node in nodes:
            if "ShaderNodeBsdfPrincipled" == node.bl_idname:
                return node
        return None

    @classmethod
    def __findImageNodeRecur(cls, parentNode):
        if hasattr(parentNode, "links"):
            for linked in parentNode.links:
                node = linked.from_node
                if "ShaderNodeTexImage" == node.bl_idname:
                    return node
                else:
                    res = cls.__findImageNodeRecur(node)
                    if res is not None:
                        return res
        if hasattr(parentNode, "inputs"):
            for nodeinput in parentNode.inputs:
                res = cls.__findImageNodeRecur(nodeinput)
                if res is not None:
                    return res

        return None


class ModelBuilder:
    def __init__(self, removeUselessJoints: bool):
        self.__skeleton = AnimationParser.parseSkeleton()
        self.__animations = AnimationParser.parseActions(self.__skeleton)

        if removeUselessJoints:
            uselesses = None
            for anim in self.__animations:
                anim.cleanUp()
                animUselesses = anim.getSetOfNamesOfUselesses()
                if uselesses is None:
                    uselesses = animUselesses
                else:
                    uselesses = uselesses.intersection(animUselesses)

            jointIndexMap = self.__skeleton.removeJoints(uselesses)

            for anim in self.__animations:
                anim.removeJoints(uselesses)
                assert anim.isMatchWith(self.__skeleton)

            print("[DAL] Removed joints are {}".format(uselesses))
        else:
            jointIndexMap = self.__skeleton.makeIndexMap()

        self.__units, self.__aabb = self.__parseRenderUnits(jointIndexMap)

    def makeBinary(self) -> bytearray:
        if len(self.__skeleton) > MAX_JOINT_NUM:
            raise RuntimeError(
                "[DAL] The number of joints ({}) cannot exceed {}.".format(len(self.__skeleton), MAX_JOINT_NUM))

        data = bytearray()

        data += self.__aabb.makeBinary()
        data += self.__skeleton.makeBinary()

        data += byt.to_int32(len(self.__animations))
        for anim in self.__animations:
            data += anim.makeBinary()

        data += byt.to_int32(len(self.__units))
        for unit in self.__units:
            unit: dat.RenderUnit
            data += unit.makeBinary()

        return data

    def makeJson(self) -> dict:
        return {
            "aabb": self.__aabb.makeJson(),
            "render units size": len(self.__units),
            "render units": [x.makeJson() for x in self.__units],
            "skeleton interface": self.__skeleton.makeJson(),
            "animations": [x.makeJson() for x in self.__animations],
        }

    def getImgNames(self):
        imgNames = set()

        for unit in self.__units:
            imgNames.add(unit.m_material.m_diffuseMap)
            imgNames.add(unit.m_material.m_roughnessMap)
            imgNames.add(unit.m_material.m_metallicMap)

        try:
            imgNames.remove("")
        except KeyError:
            pass

        return imgNames

    @staticmethod
    def __parseRenderUnits(skeleton: Dict[str, int]):
        units = []
        aabb = dat.AABB()

        for obj in bpa.get_objects():
            if not hasattr(obj.data, "polygons"): continue
            if not obj.visible_get():
                print("Skipped obj: {}".format(obj.name))
                continue

            assert 1 == len(obj.data.materials)

            unit = dat.RenderUnit(obj.name)
            if obj.data.materials[0] is None:
                raise RuntimeError("Object '{}' does not have a material.".format(obj.name))
            unit.m_material = MaterialParser.parse(obj.data.materials[0])

            for face in obj.data.polygons:
                lenVert = len(face.vertices)
                assert len(face.loop_indices) == lenVert
                if 3 == lenVert:
                    vertIndices = (0, 1, 2)
                elif 4 == lenVert:
                    vertIndices = (0, 1, 2, 0, 2, 3)
                else:
                    raise NotImplementedError("[DAL] Loop with {} vertices is not supported!".format(lenVert))
                for i in vertIndices:
                    vert: int = face.vertices[i]
                    loop: int = face.loop_indices[i]
                    vertex = obj.data.vertices[vert].co
                    texcoord = (obj.data.uv_layers.active.data[loop].uv if obj.data.uv_layers.active is not None else (
                    0.0, 0.0))
                    if face.use_smooth:
                        normal = obj.data.vertices[vert].normal
                    else:
                        normal = face.normal

                    vertex: Tuple[float, float, float] = _fixVecRotations(vertex[0], vertex[1], vertex[2])
                    normal: Tuple[float, float, float] = _fixVecRotations(normal[0], normal[1], normal[2])
                    normal: Tuple[float, float, float] = _normalizeVec3(normal[0], normal[1], normal[2])

                    boneWeightAndID = [(0, -1), (0, -1), (0, -1)]
                    for g in obj.data.vertices[vert].groups:
                        groupName = str(obj.vertex_groups[g.group].name)
                        try:
                            boneIndex = skeleton[groupName]
                        except (RuntimeError, KeyError):
                            continue
                        else:
                            boneWeightAndID.append((float(g.weight), boneIndex))
                    boneWeightAndID.sort(reverse=True)

                    unit.m_mesh.addVertex(
                        vertex[0], vertex[1], vertex[2],
                        texcoord[0], texcoord[1],
                        normal[0], normal[1], normal[2],
                        boneWeightAndID[0][1], boneWeightAndID[1][1], boneWeightAndID[2][1],
                        boneWeightAndID[0][0], boneWeightAndID[1][0], boneWeightAndID[2][0],
                    )

                    aabb.resizeToContain(vertex[0], vertex[1], vertex[2])

            units.append(unit)

        return units, aabb


class EmportDalModel(Operator, ExportHelper):
    """Export binary map file for Dalbargi engine."""

    bl_idname = "export_model.dmd"
    bl_label = "Export DMD"

    filename_ext = ".dmd"

    filter_glob = StringProperty(
        default="*.dmd",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    optionBool_copyImages = BoolProperty(
        name="Copy textures",
        description="Copy textures to same path as exported model file.",
        default=False,
    )

    optionBool_createReadable = BoolProperty(
        name="Create readable file",
        description="Create a txt file that contains model info.",
        default=True,
    )

    optionBool_removeUselessJoints = BoolProperty(
        name="Remove useless joints",
        description="Remove all the joints without keyframes.",
        default=False,
    )

    """
    enum_example = EnumProperty(
        name        = "Example Enum",
        description = "Choose between two items",
        items       = (
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default     = 'OPT_A',
    )
    """

    def execute(self, context):
        #model = ModelBuilder(self.optionBool_removeUselessJoints)

        scene = bpa.parse_raw_data()
        assert 1 == len(scene.m_skeletons)
        if self.optionBool_removeUselessJoints:
            mfd.JointRemover.process(scene.m_skeletons[0], scene.m_animations, scene.m_render_units.values())
        print("[DAL] Building done")

        if self.optionBool_createReadable:
            readable_path = os.path.splitext(self.filepath)[0] + ".txt"
            readable_content = scene.makeJson()
            with open(readable_path, "w", encoding="utf8") as file:
                json.dump(readable_content, file, indent=4, sort_keys=False)
            print("[DAL] Readable file created")

        bin_data = mex.make_binary_dmd(scene)
        full_size = len(bin_data)
        final_bin = bytearray() + b"dalmdl" + byt.to_int32(full_size) + zlib.compress(bin_data, zlib.Z_BEST_COMPRESSION)
        with open(self.filepath, "wb") as file:
            file.write(final_bin)
        print("[DAL] Model exported")

        if self.optionBool_copyImages:
            img_names = scene.imageNames()
            save_fol = os.path.split(self.filepath)[0].replace("\\", "/")
            for name in img_names:
                image: bpy.types.Image = bpy.data.images[name]
                dst_path = save_fol + "/" + name
                _copyImage(image, dst_path)
            print("[DAL] Image copied")

        print("[DAL] Finished")
        return {'FINISHED'}


def menu_func_export(self, context):
    # Only needed if you want to add into a dynamic menu
    self.layout.operator(EmportDalModel.bl_idname, text="Dalbaragi Model (.dmd)")


def register():
    importlib.reload(byt)
    importlib.reload(smt)
    importlib.reload(rwd)
    importlib.reload(mex)

    importlib.reload(bpa)
    importlib.reload(dat)
    importlib.reload(mfd)

    bpy.utils.register_class(EmportDalModel)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(EmportDalModel)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export_model.dmd('INVOKE_DEFAULT')
