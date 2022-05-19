import enum
import math
from typing import Optional, Tuple, List, Dict

import bpy

from . import smalltype as smt
from . import data_struct as dst


_TO_DEGREE = 180.0 / math.pi


class ParseConfigs:
    def __init__(
        self,
        exclude_hidden_objects: bool = False,
    ):
        self.__exclude_hidden_objects = bool(exclude_hidden_objects)


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
        linked_shader = shader_output.inputs["Surface"].links[0].from_node
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


def __parse_mesh(obj, mesh: dst.Mesh):
    obj_mesh = obj.data
    assert isinstance(obj_mesh, bpy.types.Mesh)
    obj_mesh.calc_loop_triangles()

    mesh.name = obj_mesh.name

    for tri in obj_mesh.loop_triangles:
        try:
            material_name = obj.data.materials[tri.material_index].name
        except IndexError:
            material_name = ""

        for i in range(3):
            # Vertex
            vertex_index: int = tri.vertices[i]
            vertex_data = obj_mesh.vertices[vertex_index].co
            vertex = smt.Vec3(vertex_data[0], vertex_data[1], vertex_data[2])

            # UV coord
            if obj_mesh.uv_layers.active is not None:
                uv_data = obj_mesh.uv_layers.active.data[tri.loops[i]].uv
            else:
                uv_data = (0.0, 0.0)
            uv_coord = smt.Vec2(uv_data[0], uv_data[1])

            # Normal
            if tri.use_smooth:
                normal_data = obj_mesh.vertices[vertex_index].normal
            else:
                normal_data = tri.normal
            normal = smt.Vec3(normal_data[0], normal_data[1], normal_data[2])
            normal.normalize()

            mesh.add_vertex(material_name, vertex, uv_coord, normal)


def __parse_actor(obj, actor: dst.IActor):
    actor.name = obj.name

    if obj.parent is not None:
        actor.parent_name = obj.parent.name
    else:
        actor.parent_name = ""

    for c in obj.users_collection:
        actor.collections.append(c.name)

    actor.pos.x = obj.location.x
    actor.pos.y = obj.location.y
    actor.pos.z = obj.location.z

    actor.quat.w = obj.rotation_quaternion[0]
    actor.quat.x = obj.rotation_quaternion[1]
    actor.quat.y = obj.rotation_quaternion[2]
    actor.quat.z = obj.rotation_quaternion[3]

    actor.hidden = obj.visible_get()


def __parse_armature(obj, skeleton: dst.Skeleton):
    assert isinstance(obj, bpy.types.Armature)

    for bone in obj.bones:
        joint = skeleton.new_joint(bone.name)

        if bone.parent is not None:
            joint.parent_name = bone.parent.name

        for x in dst.JointType:
            if bone.get(x.value, None) is not None:
                joint.joint_type = x

        joint.offset_mat.set_blender_mat(bone.matrix_local)


def __parse_mesh_actor(obj, scene: dst.Scene):
    actor = scene.new_mesh_actor()
    __parse_actor(obj, actor)
    actor.mesh_name = obj.data.name

    armature = obj.find_armature()
    if (armature is not None) and (not scene.has_skeleton(armature.name)):
        __parse_armature(armature.data, scene.new_skeleton(armature.name))

    for bpy_mat in obj.data.materials:
        if scene.has_material(bpy_mat.name):
            continue
        material = _MaterialParser.parse(bpy_mat)
        if material is not None:
            material.name = bpy_mat.name
            scene.add_material(material)

    try:
        scene.find_mesh_by_name(actor.mesh_name)
    except KeyError:
        mesh = scene.new_mesh()
        __parse_mesh(obj, mesh)


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

    for obj in bpy_scene.objects:
        obj_type = __classify_object_type(obj)

        if obj_type == ObjType.mesh:
            __parse_mesh_actor(obj, scene)
        elif obj_type == ObjType.emtpy:
            __parse_actor(obj, scene.new_mesh_actor())

        elif obj_type == ObjType.directional_light:
            __parse_light_directional(obj, scene.new_dlight())
        elif obj_type == ObjType.point_light:
            __parse_light_point(obj, scene.new_plight())
        elif obj_type == ObjType.spotlight:
            __parse_light_spot(obj, scene.new_slight())

    return scene


def parse_scenes(configs: ParseConfigs) -> Tuple[List[dst.Scene], dst.BinaryArrayBuilder]:
    output = []
    bin_arr = dst.BinaryArrayBuilder()

    for bpy_scene in bpy.data.scenes:
        scene = __parse_scene(bpy_scene, configs)
        output.append(scene)

    return output, bin_arr


def build_json(scenes: List[dst.Scene], bin_arr: dst.BinaryArrayBuilder, configs: ParseConfigs) -> Tuple[Dict, bytes]:
    output = {
        "scenes": [xx.make_json(bin_arr) for xx in scenes],
    }

    return output, bin_arr.data
