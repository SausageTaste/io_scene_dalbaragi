import os
import sys
import zlib
import math
import json
import collections
from typing import Tuple, List, Dict

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import datastruct as dat
from . import byteutils as byt


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
    return ( float(x), float(z), -float(y) )

def _normalizeVec3(x: float, y: float, z: float):
    length = math.sqrt( x*x + y*y + z*z )
    return ( x/length, y/length, z/length )


class AnimationParser:
    @classmethod
    def parseSkeleton(cls):
        skeleton = dat.SkeletonInterface()
        assert 1 == len(bpy.data.armatures)
        armature = bpy.data.armatures[0]
        rootBone = cls.__findRootBone(armature.bones)

        index = skeleton.makeIndexOf(rootBone.name)
        boneInfo = skeleton[index]
        boneInfo.m_parentIndex = -1

        cls.__parseSkelRecur(rootBone, skeleton)
        return skeleton

    @classmethod
    def __parseSkelRecur(cls, bone, skeleton: dat.SkeletonInterface) -> None:
        for child in bone.children:
            index = skeleton.makeIndexOf(child.name)
            boneInfo = skeleton[index]
            boneInfo.m_parentIndex = skeleton.getIndexOf(bone.name)

            cls.__parseSkelRecur(child, skeleton)

    @classmethod
    def __findRootBone(cls, bones):
        root = None

        for bone in bones:
            if bone.parent is None:
                if root is None:
                    root = bone
                else:
                    raise ValueError("There are two root bone: {}, {}".format(root.name, bone.name))

        if root is None:
            raise ValueError("Failed to find a root bone")

        return root


    class BoneAnimInfo:
        def __init__(self):
            self.__data = {}
            # dict< var name, dict< time, dict<channel, value> > >

        def __getitem__(self, key):
            return self.__data[key]

        def add(self, varName: str, channel: int, timepoint: float, value: float) -> None:
            assert isinstance(channel, int)
            assert isinstance(timepoint, float)
            assert isinstance(varName, str)

            if varName not in self.__data.keys():
                self.__data[varName] = dict()
            keyframes = self.__data[varName]

            if timepoint not in keyframes.keys():
                keyframes[timepoint] = {}

            keyframes[timepoint][channel] = float(value)

        def items(self):
            return self.__data.items()

    class BoneDict:
        def __init__(self):
            self.__bones: Dict[ str, "BoneAnimInfo" ] = {}

        def __str__(self):
            return str(self.__bones)

        def __getitem__(self, boneName: str) -> "BoneAnimInfo":
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
            anim = dat.Animation(action.name, skeleton)
            bonedict: BoneDict = cls.__makeBoneDict(action)

            for joint in anim.m_joints:
                boneInfo: BoneAnimInfo = bonedict[joint.m_name]
                poses = boneInfo["location"]
                rotations = boneInfo["rotation_quaternion"]
                scales = boneInfo["scale"]

            animations.append(anim)

        return animations

    @classmethod
    def __makeBoneDict(cls, action) -> BoneDict:
        bones = cls.BoneDict()

        for fcu in action.fcurves:
            boneName, varName = cls.__splitFcuDataPath(fcu.data_path)
            channel = fcu.array_index
            bone: BoneAnimInfo = bones[boneName]
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
        bsdf = cls.__findPrincipledBSDFNode(blenderMat.node_tree.nodes)
        if bsdf is None:
            raise ValueError("Only Principled BSDF node is supported.")

        material = dat.Material()

        node_baseColor = bsdf.inputs["Base Color"]
        node_metallic  = bsdf.inputs["Metallic"]
        node_roughness = bsdf.inputs["Roughness"]

        material.m_roughness = node_roughness.default_value
        material.m_metallic = node_metallic.default_value

        imageNode = cls.__findImageNodeRecur(node_baseColor)
        if imageNode is not None:
            material.m_diffuseMap = imageNode.image.name
        else:
            raise ValueError("Diffuse map must be defined.")

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
            for input in parentNode.inputs:
                res = cls.__findImageNodeRecur(input)
                if res is not None:
                    return res
            
        return None


class ModelBuilder:
    def __init__(self):
        self.__units = []

        self.__parseRenderUnits()

        skeleton = AnimationParser.parseSkeleton()
        for k in (skeleton):
            print(k)

        animations = AnimationParser.parseActions(skeleton)
        for anim in (animations):
            print(anim.m_joints)

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_int32(len(self.__units))

        for unit in self.__units:
            unit: dat.RenderUnit
            data += unit.makeBinary()

        return data

    def makeJson(self) -> dict:
        return {
            "render units[{}]".format(len(self.__units)) : [x.makeJson() for x in self.__units],
        }

    def getImgNames(self):
        imgNames = set()

        for unit in self.__units:
            imgNames.add(unit.m_material.m_diffuseMap)
            imgNames.add(unit.m_material.m_roughnessMap)
            imgNames.add(unit.m_material.m_metallicMap)

        imgNames.remove("")

        return imgNames

    def __parseRenderUnits(self):
        for obj in bpy.context.scene.objects:
            if not hasattr(obj.data, "polygons"): continue
            assert 1 == len(obj.data.materials)

            unit = dat.RenderUnit(obj.name)
            unit.m_material = MaterialParser.parse(obj.data.materials[0])

            for face in obj.data.polygons:
                lenVert = len(face.vertices)
                assert len(face.loop_indices) == lenVert
                if 3 == lenVert:
                    vertIndices = (0, 1, 2)
                elif 4 == lenVert:
                    vertIndices = (0, 1, 2, 0, 2, 3)
                else:
                    raise NotImplementedError("Loop with {} vertices is not supported!".format(lenVert))

                for i in vertIndices:
                    vert = face.vertices[i]
                    loop = face.loop_indices[i]

                    vertex = obj.data.vertices[vert].co
                    texcoord = (obj.data.uv_layers.active.data[loop].uv if obj.data.uv_layers.active is not None else (0.0, 0.0))
                    if face.use_smooth:
                        normal = obj.data.vertices[vert].normal
                    else:
                        normal = face.normal

                    vertex = _fixVecRotations(vertex[0], vertex[1], vertex[2])
                    normal = _fixVecRotations(normal[0], normal[1], normal[2])
                    normal = _normalizeVec3(normal[0], normal[1], normal[2])

                    unit.m_mesh.addVertex(
                        vertex[0], vertex[1], vertex[2],
                        texcoord[0], texcoord[1],
                        normal[0], normal[1], normal[2]
                    )

            self.__units.append(unit)


class EmportDalModel(Operator, ExportHelper):
    """Export binary map file for Dalbargi engine."""

    bl_idname = "export_model.dmd"
    bl_label = "Export DMD"

    filename_ext = ".dmd"

    filter_glob: StringProperty(
        default="*.dmd",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    optionBool_copyImages: BoolProperty(
        name = "Copy textures",
        description = "Copy textures to same path as exported model file.",
        default = False,
    )

    optionBool_createReadable: BoolProperty(
        name = "Create readable file.",
        description = "",
        default = False,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        model = ModelBuilder()

        binData = model.makeBinary()
        fullSize = len(binData)
        finalBin = byt.to_int32(fullSize) + zlib.compress(binData, zlib.Z_BEST_COMPRESSION)
        with open(self.filepath, "wb") as file:
            file.write(finalBin)

        if self.optionBool_copyImages:
            imgNames = model.getImgNames()
            saveFol = os.path.split(self.filepath)[0].replace("\\", "/")
            for name in imgNames:
                image = bpy.data.images[name]
                dstPath = saveFol + "/" + name
                image.save_render(dstPath)

        if self.optionBool_createReadable:
            readablePath = os.path.splitext(self.filepath)[0] + ".txt"
            readableContent = model.makeJson()
            with open(readablePath, "w", encoding="utf8") as file:
                json.dump(readableContent, file, indent=4, sort_keys=False)

        return {'FINISHED'}


def menu_func_export(self, context):
    # Only needed if you want to add into a dynamic menu
    self.layout.operator(EmportDalModel.bl_idname, text="Dalbaragi Model (.dmd)")

def register():
    bpy.utils.register_class(EmportDalModel)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(EmportDalModel)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export_model.dmd('INVOKE_DEFAULT')
