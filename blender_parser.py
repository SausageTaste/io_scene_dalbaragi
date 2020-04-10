import math
from typing import Dict, List, Tuple, Iterable

import bpy

from . import rawdata as rwd
from . import smalltype as smt


BLENDER_OBJ_TYPE_MESH        = "MESH"
BLENDER_OBJ_TYPE_CURVE       = "CURVE"
BLENDER_OBJ_TYPE_SURFACE     = "SURFACE"
BLENDER_OBJ_TYPE_META        = "META"
BLENDER_OBJ_TYPE_FONT        = "FONT"
BLENDER_OBJ_TYPE_ARMATURE    = "ARMATURE"
BLENDER_OBJ_TYPE_LATTICE     = "LATTICE"
BLENDER_OBJ_TYPE_EMPTY       = "EMPTY"
BLENDER_OBJ_TYPE_GPENCIL     = "GPENCIL"
BLENDER_OBJ_TYPE_CAMERA      = "CAMERA"
BLENDER_OBJ_TYPE_LIGHT       = "LIGHT"
BLENDER_OBJ_TYPE_SPEAKER     = "SPEAKER"
BLENDER_OBJ_TYPE_LIGHT_PROBE = "LIGHT_PROBE"

BLENDER_MATERIAL_BLEND_OPAQUE = "OPAQUE"
BLENDER_MATERIAL_BLEND_CLIP   = "CLIP"
BLENDER_MATERIAL_BLEND_HASHED = "HASHED"
BLENDER_MATERIAL_BLEND_BLEND  = "BLEND"


# In blender's coordinate system, -z is down.
# But in Dalbaragi engine, -y is down and -z is far direction.
def _fix_rotation(v: smt.Vec3) -> smt.Vec3:
    return smt.Vec3(v.x, v.z, -v.y)

def _to_degree(radian: float) -> float:
    return float(radian) * 180.0 / math.pi

def _get_objects():
    for obj in bpy.context.scene.objects:
        yield obj


class _MaterialParser:
    @classmethod
    def parse(cls, blender_material):
        assert blender_material is not None

        bsdf = cls.__findPrincipledBSDFNode(blender_material.node_tree.nodes)
        if bsdf is None:
            raise RuntimeError("[DAL] Only Principled BSDF node is supported.")

        material = rwd.Scene.Material()

        node_base_color = bsdf.inputs["Base Color"]
        node_metallic   = bsdf.inputs["Metallic"]
        node_roughness  = bsdf.inputs["Roughness"]
        node_normal     = bsdf.inputs["Normal"]

        material.m_alphaBlend = True if blender_material.blend_method != BLENDER_MATERIAL_BLEND_OPAQUE else False
        material.m_roughness = node_roughness.default_value
        material.m_metallic = node_metallic.default_value

        image_node = cls.__findImageNodeRecur(node_base_color)
        if image_node is not None:
            material.m_albedoMap = image_node.image.name

        image_node = cls.__findImageNodeRecur(node_metallic)
        if image_node is not None:
            material.m_metallicMap = image_node.image.name

        image_node = cls.__findImageNodeRecur(node_roughness)
        if image_node is not None:
            material.m_roughnessMap = image_node.image.name

        image_node = cls.__findImageNodeRecur(node_normal)
        if image_node is not None:
            material.m_normalMap = image_node.image.name

        return material

    @staticmethod
    def __findPrincipledBSDFNode(nodes):
        for node in nodes:
            if "ShaderNodeBsdfPrincipled" == node.bl_idname:
                return node
        return None

    @classmethod
    def __findImageNodeRecur(cls, parent_node):
        if hasattr(parent_node, "links"):
            for linked in parent_node.links:
                node = linked.from_node
                if "ShaderNodeTexImage" == node.bl_idname:
                    return node
                else:
                    res = cls.__findImageNodeRecur(node)
                    if res is not None:
                        return res
        if hasattr(parent_node, "inputs"):
            for nodeinput in parent_node.inputs:
                res = cls.__findImageNodeRecur(nodeinput)
                if res is not None:
                    return res
            
        return None

class _AnimationParser:
    class _ActionAssembler:
        class _JointData:
            class _TimepointDict:
                def __init__(self):
                    self.__data: Dict[float, Dict[int, float]] = {}

                def add(self, timepoint: float, channel: int, value: float):
                    assert isinstance(timepoint, float)
                    assert isinstance(channel, int)
                    assert isinstance(value, float)

                    if timepoint not in self.__data.keys():
                        self.__data[timepoint] = {}
                    self.__data[timepoint][channel] = value

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
                        requested_order = self.__timepointToOrder(timepoint)
                        prev_order = requested_order - 1
                        if prev_order < 0:
                            raise RuntimeError("[DAL] First keyframe need all its channels with a value.")
                        prev_timepoint = self.__orderToTimepoint(prev_order)
                        return self.get(prev_timepoint, channel)

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

            def __init__(self):
                # For a pos and scale, x=0, y=1, z=2
                # For a quat, w=0, x=1, y=2, z=3
                self.__poses = self._TimepointDict()
                self.__quats = self._TimepointDict()
                self.__scales = self._TimepointDict()

            @property
            def m_poses(self):
                return self.__poses
            @property
            def m_quats(self):
                return self.__quats
            @property
            def m_scales(self):
                return self.__scales

        def __init__(self):
            self.__jointsData: Dict[str, _AnimationParser._ActionAssembler._JointData] = {}

        def add(self, joint_name: str, var_name: str, timepoint: float, channel: int, value: float):
            joint_name = str(joint_name)
            var_name = str(var_name)

            if joint_name not in self.__jointsData.keys():
                self.__jointsData[joint_name] = self._JointData()

            if "location" == var_name:
                self.__jointsData[joint_name].m_poses.add(timepoint, channel, value)
            elif "rotation_quaternion" == var_name:
                self.__jointsData[joint_name].m_quats.add(timepoint, channel, value)
            elif "scale" == var_name:
                self.__jointsData[joint_name].m_scales.add(timepoint, channel, value)
            else:
                print('[DAL] WARN::Unkown variable for a joint: "{}"'.format(var_name))

        @property
        def m_jointsData(self):
            return self.__jointsData

    @classmethod
    def parse(cls, blender_action: bpy.types.Action):
        assert isinstance(blender_action, bpy.types.Action)

        anim = rwd.Scene.Animation(blender_action.name, bpy.context.scene.render.fps)

        assembler = cls._ActionAssembler()
        for fcu in blender_action.fcurves:
            # var_name is either location, rotation_quaternion or scale
            # channel stands for x, y, z for locations, w, x, y, z for quat, x, y, z for scale.
            joint_name, var_name = cls.__splitFcuDataPath(fcu.data_path)
            channel = fcu.array_index

            for keyframe in fcu.keyframe_points:
                timepoint = keyframe.co[0]
                value = keyframe.co[1]
                assembler.add(joint_name, var_name, timepoint, channel, value)

        for joint_name, joint_data in assembler.m_jointsData.items():
            joint_keyframes = anim.newJoint(joint_name)

            poses = joint_data.m_poses
            for tp in poses.iterTimepoints():
                x = poses.get(tp, 0)
                y = poses.get(tp, 1)
                z = poses.get(tp, 2)
                joint_keyframes.addPos(tp, x, y, z)

            rots = joint_data.m_quats
            for tp in rots.iterTimepoints():
                w = rots.get(tp, 0)
                x = rots.get(tp, 1)
                y = rots.get(tp, 2)
                z = rots.get(tp, 3)
                joint_keyframes.addRotate(tp, w, x, y, z)

            scales = joint_data.m_scales
            for tp in scales.iterTimepoints():
                x = scales.get(tp, 0)
                y = scales.get(tp, 1)
                z = scales.get(tp, 2)
                average_scale = (x + y + z) / 3
                joint_keyframes.addScale(tp, average_scale)

        return anim

    @staticmethod
    def __splitFcuDataPath(path: str) -> Tuple[str, str]:
        pass1 = path.split('"')
        bone_name = pass1[1]

        pass2 = pass1[2].split(".")
        var_name = pass2[-1]

        return bone_name, var_name


def _parse_skeleton(blender_armature) -> rwd.Scene.Skeleton:
    assert isinstance(blender_armature, bpy.types.Armature)

    skeleton = rwd.Scene.Skeleton(blender_armature.name)

    for bone in blender_armature.bones:
        parent_name = ""
        if bone.parent is not None:
            parent_name = bone.parent.name

        joint_data = skeleton.newJoint(bone.name, parent_name)

        if bone.get("dal_phy_hairRoot", None) is not None:
            joint_data.m_jointType = rwd.Scene.JointType.hair_root
        elif bone.get("dal_phy_skirtRoot", None) is not None:
            joint_data.m_jointType = rwd.Scene.JointType.skirt_root

        joint_data.m_offsetMat.set(bone.matrix_local)

    return skeleton

def _parse_render_unit(obj, data_id: int) -> rwd.Scene.RenderUnit:
    assert isinstance(obj.data, bpy.types.Mesh)

    unit = rwd.Scene.RenderUnit(data_id)

    if obj.data.materials[0] is not None:
        unit.m_material = _MaterialParser.parse(obj.data.materials[0])

    armature = obj.find_armature()
    if armature is not None:
        unit.m_mesh.m_skeletonName = armature.name

    for face in obj.data.polygons:
        verts_per_face = len(face.vertices)
        assert len(face.loop_indices) == verts_per_face
        if 3 == verts_per_face:
            vert_indices = (0, 1, 2)
        elif 4 == verts_per_face:
            vert_indices = (0, 1, 2, 0, 2, 3)
        else:
            print("[DAL] WARNING:: Loop with {} vertices is not supported, thus omitted".format(verts_per_face))
            continue

        for i in vert_indices:
            # Vertex
            vert_index: int = face.vertices[i]
            vertex_data = obj.data.vertices[vert_index].co
            vertex = smt.Vec3(vertex_data[0], vertex_data[1], vertex_data[2])
            vertex = _fix_rotation(vertex)

            # UV coord
            loop: int = face.loop_indices[i]
            uv_data = (obj.data.uv_layers.active.data[loop].uv if obj.data.uv_layers.active is not None else (0.0, 0.0))
            uv_coord = smt.Vec2(uv_data[0], uv_data[1])

            # Normal
            if face.use_smooth:
                normal_data = obj.data.vertices[vert_index].normal
            else:
                normal_data = face.normal
            normal = smt.Vec3(normal_data[0], normal_data[1], normal_data[2])
            normal = _fix_rotation(normal)
            normal.normalize()

            # Rest
            vdata = rwd.Scene.VertexData()
            vdata.m_vertex = vertex
            vdata.m_uvCoord = uv_coord
            vdata.m_normal = normal

            for g in obj.data.vertices[vert_index].groups:
                group_name = str(obj.vertex_groups[g.group].name)
                vdata.addJoint(group_name, g.weight)

            unit.m_mesh.addVertex(vdata)

    return unit

def _parse_light_base(obj, light: rwd.Scene.ILight) -> None:
    light.m_name = obj.name

    light.m_color.x = obj.data.color.r
    light.m_color.y = obj.data.color.g
    light.m_color.z = obj.data.color.b

    light.m_useShadow = obj.data.use_shadow
    light.m_intensity = obj.data.energy

def _parse_light_point(obj):
    assert isinstance(obj.data, bpy.types.PointLight)

    plight = rwd.Scene.PointLight()

    _parse_light_base(obj, plight)

    plight.m_pos.x = obj.location.x
    plight.m_pos.y = obj.location.y
    plight.m_pos.z = obj.location.z

    if not obj.data.use_custom_distance:
        print("[DAL] WARN::custom distance is not enabled for light \"{}\"".format(plight.m_name))
    plight.m_maxDistance = float(obj.data.cutoff_distance)
    plight.m_halfIntenseDist = float(obj.data.distance)

    return plight

def _parse_light_directional(obj):
    assert isinstance(obj.data, bpy.types.SunLight)

    dlight = rwd.Scene.DirectionalLight()

    _parse_light_base(obj, dlight)

    quat = smt.Quat()
    quat.w = obj.rotation_quaternion[0]
    quat.x = obj.rotation_quaternion[1]
    quat.y = obj.rotation_quaternion[2]
    quat.z = obj.rotation_quaternion[3]
    down = smt.Vec3(0, 0, -1)  # Take a look at the comment near "_fix_rotation" function
    dlight.m_direction = _fix_rotation(quat.rotateVec(down))

    return dlight

def _parse_light_spot(obj):
    assert isinstance(obj.data, bpy.types.SpotLight)

    slight = rwd.Scene.SpotLight()

    _parse_light_base(obj, slight)

    slight.m_pos.x = obj.location.x
    slight.m_pos.y = obj.location.y
    slight.m_pos.z = obj.location.z

    if not obj.data.use_custom_distance:
        print("[DAL] WARN::custom distance is not enabled for light \"{}\"".format(slight.m_name))
    slight.m_maxDistance = float(obj.data.cutoff_distance)
    slight.m_halfIntenseDist = float(obj.data.distance)

    quat = smt.Quat()
    quat.w = obj.rotation_quaternion[0]
    quat.x = obj.rotation_quaternion[1]
    quat.y = obj.rotation_quaternion[2]
    quat.z = obj.rotation_quaternion[3]
    down = smt.Vec3(0, 0, -1)  # Take a look at the comment near "_fix_rotation" function
    slight.m_direction = _fix_rotation(quat.rotateVec(down))

    slight.m_spotDegree = _to_degree(obj.data.spot_size)
    slight.m_spotBlend = float(obj.data.spot_blend)

    return slight


def _parse_objects(objects: iter, scene: rwd.Scene, ignore_hidden: bool) -> None:
    for obj in objects:
        type_str = str(obj.type)

        if (not obj.visible_get()) and ignore_hidden:
            scene.m_skipped_objs.append((obj.name, "Hiddel object"))
            continue

        if BLENDER_OBJ_TYPE_MESH == type_str:
            data_id = id(obj.data)
            if data_id not in scene.m_render_units.keys():
                scene.m_render_units[data_id] = _parse_render_unit(obj, data_id)
            scene.m_render_units[data_id].m_refCount += 1

            actor = rwd.Scene.StaticActor()
            actor.m_name = obj.name
            actor.m_renderUnitID = data_id
            scene.m_static_actors.append(actor)
        elif BLENDER_OBJ_TYPE_ARMATURE == type_str:
            skeleton = _parse_skeleton(obj.data)
            scene.m_skeletons.append(skeleton)
        elif BLENDER_OBJ_TYPE_LIGHT == type_str:
            if isinstance(obj.data, bpy.types.PointLight):
                plight = _parse_light_point(obj)
                scene.m_plights.append(plight)
            elif isinstance(obj.data, bpy.types.SunLight):
                dlight = _parse_light_directional(obj)
                scene.m_dlights.append(dlight)
            elif isinstance(obj.data, bpy.types.SpotLight):
                slight = _parse_light_spot(obj)
                scene.m_slights.append(slight)
            else:
                raise RuntimeError("Unkown type of light: {}".format(type(obj.data)))
        else:
            scene.m_skipped_objs.append((obj.name, "Not supported object type: {}".format(type_str)))



def parse_raw_data() -> rwd.Scene:
    scene = rwd.Scene()

    _parse_objects(_get_objects(), scene, True)

    for action in bpy.data.actions:
        animation = _AnimationParser.parse(action)
        animation.cleanUp()
        scene.m_animations.append(animation)

    return scene

def parse_raw_data_map() -> Dict[str, rwd.Scene]:
    scenes: Dict[str, rwd.Scene] = {}

    for collection in bpy.data.collections:
        scene = rwd.Scene()
        _parse_objects(collection.all_objects, scene, False)
        scenes[collection.name] = scene

    return scenes
