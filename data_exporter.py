import enum
import math
from typing import Optional, Tuple, List, Dict

import bpy

from . import byteutils as byt
from . import smalltype as smt
from . import mesh_manager as mes
from . import data_struct as dst


_TO_DEGREE = 180.0 / math.pi


class ParseConfigs:
    def __init__(
        self,
        exclude_hidden_meshes: bool = False,
        exclude_hidden_objects: bool = False,
    ):
        self.__exclude_hidden_meshes = bool(exclude_hidden_meshes)
        self.__exclude_hidden_objects = bool(exclude_hidden_objects)

    @property
    def exclude_hidden_meshes(self):
        return self.__exclude_hidden_meshes

    @property
    def exclude_hidden_objects(self):
        return self.__exclude_hidden_objects


class ObjType(enum.Enum):
    unknown = "UNKNOWN"
    camera = "CAMERA"
    armature = "ARMATURE"
    emtpy = "EMPTY"

    mesh = "MESH"
    env_map = "ENVMAP"
    water_plane = "WATERPLANE"

    directional_light = "DLIGHT"
    point_light = "PLIGHT"
    spotlight = "SLIGHT"


class _MaterialParser:
    __NODE_BSDF = "ShaderNodeBsdfPrincipled"
    __NODE_HOLDOUT = "ShaderNodeHoldout"
    __NODE_MATERIAL_OUTPUT = "ShaderNodeOutputMaterial"
    __NODE_TEX_IMAGE = "ShaderNodeTexImage"
    __NODE_GROUP = "ShaderNodeGroup"

    __BLEND_OPAQUE = "OPAQUE"
    __BLEND_CLIP = "CLIP"
    __BLEND_HASHED = "HASHED"
    __BLEND_BLEND = "BLEND"

    @classmethod
    def parse(cls, blender_material) -> Optional[dst.Material]:
        assert blender_material is not None

        shader_output = cls.__find_node_named(cls.__NODE_MATERIAL_OUTPUT, blender_material.node_tree.nodes)

        try:
            linked_shader = shader_output.inputs["Surface"].links[0].from_node
        except IndexError:
            return None

        alpha_blend_enabled = True if blender_material.blend_method != cls.__BLEND_OPAQUE else False

        if cls.__NODE_BSDF == linked_shader.bl_idname:
            return cls.__parse_principled_bsdf(linked_shader, alpha_blend_enabled)
        elif cls.__NODE_HOLDOUT == linked_shader.bl_idname:
            return None
        elif cls.__NODE_GROUP == linked_shader.bl_idname:
            if "XPS Shader" == linked_shader.node_tree.name_full:
                return cls.__parse_xps_shader(linked_shader, alpha_blend_enabled)
            else:
                print("Not supported shader type: {}".format(linked_shader.node_tree.name_full))
                return None
        else:
            print("Not supported shader type: {}".format(linked_shader.bl_idname))
            return None

    @staticmethod
    def __find_node_named(name: str, nodes):
        for node in nodes:
            if name == node.bl_idname:
                return node
        return None

    @classmethod
    def __find_node_recur_named(cls, name, parent_node):
        if hasattr(parent_node, "links"):
            for linked in parent_node.links:
                node = linked.from_node
                if name == node.bl_idname:
                    return node
                else:
                    res = cls.__find_node_recur_named(name, node)
                    if res is not None:
                        return res
        if hasattr(parent_node, "inputs"):
            for node_input in parent_node.inputs:
                res = cls.__find_node_recur_named(name, node_input)
                if res is not None:
                    return res

        return None

    @classmethod
    def __parse_principled_bsdf(cls, bsdf, alpha_blend: bool) -> dst.Material:
        material = dst.Material()

        node_roughness = bsdf.inputs["Roughness"]
        node_metallic = bsdf.inputs["Metallic"]

        material.transparency = alpha_blend
        material.roughness = node_roughness.default_value
        material.metallic = node_metallic.default_value

        image_node = cls.__find_node_recur_named(cls.__NODE_TEX_IMAGE, bsdf.inputs["Base Color"])
        if image_node is not None:
            material.albedo_map = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.__NODE_TEX_IMAGE, node_roughness)
        if image_node is not None:
            material.roughness_map = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.__NODE_TEX_IMAGE, node_roughness)
        if image_node is not None:
            material.metallic_map = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.__NODE_TEX_IMAGE, bsdf.inputs["Normal"])
        if image_node is not None:
            material.normal_map = image_node.image.name

        return material

    @classmethod
    def __parse_xps_shader(cls, linked_shader, alpha_blend: bool) -> dst.Material:
        material = dst.Material()

        material.transparency = alpha_blend

        image_node = cls.__find_node_recur_named(cls.__NODE_TEX_IMAGE, linked_shader.inputs["Diffuse"])
        if image_node is not None:
            material.albedo_map = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.__NODE_TEX_IMAGE, linked_shader.inputs["Bump Map"])
        if image_node is not None:
            material.normal_map = image_node.image.name

        return material


def __parse_transform(obj, output: smt.Transform):
    output.m_pos.x = obj.location.x
    output.m_pos.y = obj.location.y
    output.m_pos.z = obj.location.z

    initial_rotate_mode = obj.rotation_mode
    obj.rotation_mode = "QUATERNION"
    output.m_rotate.w = obj.rotation_quaternion[0]
    output.m_rotate.x = obj.rotation_quaternion[1]
    output.m_rotate.y = obj.rotation_quaternion[2]
    output.m_rotate.z = obj.rotation_quaternion[3]
    obj.rotation_mode = initial_rotate_mode

    output.m_scale.x = obj.scale[0]
    output.m_scale.y = obj.scale[1]
    output.m_scale.z = obj.scale[2]


def __parse_actor(obj, actor: dst.IActor):
    actor.name = obj.name

    if obj.parent is not None:
        actor.parent_name = obj.parent.name
    else:
        actor.parent_name = ""

    for c in obj.users_collection:
        actor.add_collection_name(c.name)

    __parse_transform(obj, actor.transform)
    actor.hidden = not obj.visible_get()


def __parse_armature(obj, skeleton: dst.Skeleton):
    assert isinstance(obj.data, bpy.types.Armature)

    __parse_transform(obj, skeleton.transform)

    for bone in obj.data.bones:
        joint = skeleton.new_joint(bone.name)

        if bone.parent is not None:
            joint.parent_name = bone.parent.name

        for type_enum, type_specifier in dst.JOINT_TYPE_MAP.items():
            if bone.get(type_specifier, None) is not None:
                joint.joint_type = type_enum

        joint.offset_mat.set_blender_mat(bone.matrix_local)


class _TimePointDict:
    def __init__(self):
        self.__data: Dict[float, Dict[int, float]] = {}

    def add(self, time_point: float, channel: int, value: float):
        assert isinstance(time_point, float)
        assert isinstance(channel, int)
        assert isinstance(value, float)

        if time_point not in self.__data.keys():
            self.__data[time_point] = {}
        self.__data[time_point][channel] = value

    def get(self, time_point: float, channel: int) -> float:
        assert isinstance(channel, int)
        assert isinstance(time_point, float)

        return self.__data[time_point][channel]

    def get_extended(self, time_point: float, channel: int) -> float:
        assert isinstance(channel, int)
        assert isinstance(time_point, float)

        try:
            return self.__data[time_point][channel]
        except KeyError:
            requested_index = self.__convert_time_point_to_index(time_point)
            prev_index = requested_index - 1
            if prev_index < 0:
                raise RuntimeError("[DAL] First keyframe need all its channels with a value.")
            prev_time_point = self.__convert_index_to_time_point(prev_index)
            return self.get(prev_time_point, channel)

    def iter_timepoints(self) -> iter:
        return iter(self.__make_sorted_timepoints())

    def __make_sorted_timepoints(self) -> List[float]:
        timepoints = list(self.__data.keys())
        timepoints.sort()
        return timepoints

    def __convert_index_to_time_point(self, order: int) -> float:
        assert isinstance(order, int)
        assert order >= 0
        return self.__make_sorted_timepoints()[order]

    def __convert_time_point_to_index(self, time_point: float) -> int:
        assert isinstance(time_point, float)
        return self.__make_sorted_timepoints().index(time_point)


class _JointData:
    def __init__(self):
        # Channels for a pos and scale are x=0, y=1, z=2
        # For a quat, w=0, x=1, y=2, z=3
        self.__positions = _TimePointDict()
        self.__rotations = _TimePointDict()
        self.__scales = _TimePointDict()

    @property
    def positions(self):
        return self.__positions

    @property
    def rotations(self):
        return self.__rotations

    @property
    def scales(self):
        return self.__scales


class _ActionAssembler:
    def __init__(self):
        self.__joints: Dict[str, _JointData] = {}

    def items(self):
        return self.__joints.items()

    def add(self, joint_name: str, var_name: str, time_point: float, channel: int, value: float):
        joint_name = str(joint_name)
        var_name = str(var_name)

        if joint_name not in self.__joints.keys():
            self.__joints[joint_name] = _JointData()

        if "location" == var_name:
            self.__joints[joint_name].positions.add(time_point, channel, value)
        elif "rotation_quaternion" == var_name:
            self.__joints[joint_name].rotations.add(time_point, channel, value)
        elif "scale" == var_name:
            self.__joints[joint_name].scales.add(time_point, channel, value)
        else:
            raise RuntimeError(f'[DAL] WARN::Unknown variable for a joint: "{var_name}"')


# var_name is either location, rotation_quaternion or scale
def __split_fcu_data_path(path: str) -> Tuple[str, str]:
    pass1 = path.split('"')
    bone_name = pass1[1]

    pass2 = pass1[2].split(".")
    var_name = pass2[-1]

    return bone_name, var_name


def __parse_animation(bpy_action, anim: dst.Animation):
    assert isinstance(bpy_action, bpy.types.Action)
    assembler = _ActionAssembler()

    for fcu in bpy_action.fcurves:
        joint_name, var_name = __split_fcu_data_path(fcu.data_path)
        # channel stands for x, y, z for locations, w, x, y, z for quat, x, y, z for scale.
        channel = fcu.array_index

        for keyframe in fcu.keyframe_points:
            time_point = keyframe.co[0]
            value = keyframe.co[1]
            assembler.add(joint_name, var_name, time_point, channel, value)

    for j_name, j_data in assembler.items():
        joint_keyframes = anim.new_joint(j_name)

        for tp in j_data.positions.iter_timepoints():
            joint_keyframes.add_position(
                tp,
                j_data.positions.get(tp, 0),
                j_data.positions.get(tp, 1),
                j_data.positions.get(tp, 2),
            )

        for tp in j_data.rotations.iter_timepoints():
            joint_keyframes.add_rotation(
                tp,
                j_data.rotations.get(tp, 0),
                j_data.rotations.get(tp, 1),
                j_data.rotations.get(tp, 2),
                j_data.rotations.get(tp, 3),
            )

        for tp in j_data.scales.iter_timepoints():
            average_scale = (j_data.scales.get(tp, 0) + j_data.scales.get(tp, 1) + j_data.scales.get(tp, 2)) / 3
            joint_keyframes.add_scale(tp, average_scale)

    return anim


def __parse_mesh_actor(obj, scene: dst.Scene):
    actor = scene.new_mesh_actor()
    __parse_actor(obj, actor)
    actor.mesh_name = obj.data.name

    # Skeleton
    # ------------------------------------------------------------------------------------------------------------------

    armature = obj.find_armature()
    if (armature is not None) and isinstance(armature.data, bpy.types.Armature):
        if scene.has_skeleton(armature.name):
            skeleton = scene.find_skeleton_by_name(armature.name)
        else:
            skeleton = scene.new_skeleton(armature.name)
            __parse_armature(armature, skeleton)
    else:
        skeleton = None

    # Material
    # ------------------------------------------------------------------------------------------------------------------

    for bpy_mat in obj.data.materials:
        if scene.has_material(bpy_mat.name):
            continue
        material = _MaterialParser.parse(bpy_mat)
        if material is not None:
            material.name = bpy_mat.name
            scene.add_material(material)
        else:
            print(f"Failed to parse a material: {bpy_mat.name}")

    # Mesh
    # ------------------------------------------------------------------------------------------------------------------

    if skeleton is not None:
        joint_name_index_map = skeleton.make_name_index_map()
        skeleton_name = skeleton.name
    else:
        joint_name_index_map = {}
        skeleton_name = ""

    scene.mesh_manager.add_bpy_mesh(obj, skeleton_name, joint_name_index_map)


def __parse_light_base(obj, light: dst.ILight) -> None:
    light.color.x = obj.data.color.r
    light.color.y = obj.data.color.g
    light.color.z = obj.data.color.b

    light.has_shadow = obj.data.use_shadow
    light.intensity = obj.data.energy


def __parse_light_directional(obj, dlight: dst.DirectionalLight):
    assert isinstance(obj.data, bpy.types.SunLight)

    __parse_actor(obj, dlight)
    __parse_light_base(obj, dlight)

    return dlight


def __parse_light_point(obj, plight: dst.PointLight):
    assert isinstance(obj.data, bpy.types.PointLight) or isinstance(obj.data, bpy.types.SpotLight)

    __parse_actor(obj, plight)
    __parse_light_base(obj, plight)

    if not obj.data.use_custom_distance:
        # print("[DAL] WARN::custom distance is not enabled for light \"{}\"".format(plight.name))
        pass

    plight.max_distance = float(obj.data.cutoff_distance)
    plight.half_intense_distance = float(obj.data.distance)

    return plight


def __parse_light_spot(obj, slight: dst.Spotlight):
    assert isinstance(obj.data, bpy.types.SpotLight)

    __parse_light_point(obj, slight)

    slight.spot_degree = _TO_DEGREE * float(obj.data.spot_size)
    slight.spot_blend = float(obj.data.spot_blend)

    return slight


def __parse_water_plane(obj, water_plane: dst.WaterPlane, meshes: mes.MeshManager):
    __parse_actor(obj, water_plane)
    water_plane.mesh_name = meshes.add_bpy_mesh(obj, "", {})


def __parse_env_map(obj, env_map: dst.EnvironmentMap):
    __parse_actor(obj, env_map)

    name_start_index = str(obj.name).index("%", 1) + 1
    env_map.name = str(obj.name)[name_start_index:]

    if "pcorrect" in obj and "true" == obj["pcorrect"]:
        for face in obj.data.polygons:
            point = smt.Vec3(face.center.x, face.center.y, face.center.z)
            normal = smt.Vec3(face.normal.x, face.normal.y, face.normal.z)
            normal.normalize()

            plane = env_map.new_plane()
            plane.setPointNormal(point, normal)


def __classify_object_type(obj):
    obj_name = str(obj.name)
    type_str = str(obj.type)

    if "LIGHT" == type_str:
        if isinstance(obj.data, bpy.types.SunLight):
            return ObjType.directional_light
        elif isinstance(obj.data, bpy.types.PointLight):
            return ObjType.point_light
        elif isinstance(obj.data, bpy.types.SpotLight):
            return ObjType.spotlight

    if "MESH" == type_str:
        if "%" != obj_name[0]:
            return ObjType.mesh
        else:
            tail = obj_name.find("%", 1)
            if -1 == tail:
                tail = len(obj_name)
            special_mesh_type = obj_name[1:tail]

            if "envmap" == special_mesh_type:
                return ObjType.env_map
            elif "water" == special_mesh_type:
                return ObjType.water_plane
            else:
                raise RuntimeError(f"invalid special mesh type '{special_mesh_type}' for object '{obj_name}'")

    for x in ObjType:
        if x.value == type_str:
            return x

    return ObjType.unknown


def __parse_scene(bpy_scene, configs: ParseConfigs) -> dst.Scene:
    scene = dst.Scene()

    scene.name = bpy_scene.name

    for action in bpy.data.actions:
        animation = __parse_animation(action, scene.new_animation(action.name, bpy.context.scene.render.fps))
        animation.clean_up()

    for obj in bpy_scene.objects:
        if not obj.visible_get() and configs.exclude_hidden_objects:
            scene.ignored_objects.new(obj.name, 'Hidden object')
            continue
        obj_type = __classify_object_type(obj)

        if obj_type == ObjType.mesh:
            if not obj.visible_get() and configs.exclude_hidden_meshes:
                scene.ignored_objects.new(obj.name, 'Hidden mesh')
            else:
                __parse_mesh_actor(obj, scene)
        elif obj_type == ObjType.emtpy:
            __parse_actor(obj, scene.new_mesh_actor())

        elif obj_type == ObjType.directional_light:
            __parse_light_directional(obj, scene.new_dlight())
        elif obj_type == ObjType.point_light:
            __parse_light_point(obj, scene.new_plight())
        elif obj_type == ObjType.spotlight:
            __parse_light_spot(obj, scene.new_slight())
        elif obj_type == ObjType.water_plane:
            __parse_water_plane(obj, scene.new_water_plane(), scene.mesh_manager)
        elif obj_type == ObjType.env_map:
            __parse_env_map(obj, scene.new_env_map())

        else:
            scene.ignored_objects.new(obj.name, f'Not supported object type: {obj_type}, {obj.type}')

    return scene


def parse_scenes(configs: ParseConfigs) -> Tuple[List[dst.Scene], mes.BinaryArrayBuilder]:
    output = []
    bin_arr = mes.create_binary_builder()

    for bpy_scene in bpy.data.scenes:
        scene = __parse_scene(bpy_scene, configs)
        output.append(scene)

    return output, bin_arr


def build_json(scenes: List[dst.Scene], bin_arr: mes.BinaryArrayBuilder, configs: ParseConfigs) -> Tuple[Dict, bytes]:
    output = {
        "scenes": [xx.make_json(bin_arr) for xx in scenes],
    }

    return output, bin_arr.data
