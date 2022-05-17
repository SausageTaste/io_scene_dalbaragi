import enum
import math
from typing import Dict

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

    mesh = "MESH"
    env_map = "ENVMAP"
    water_plane = "WATERPLANE"

    directional_light = "DLIGHT"
    point_light = "PLIGHT"
    spotlight = "SLIGHT"


# In blender's coordinate system, -z is down.
# But in Dalbaragi engine, -y is down and -z is far direction.
def __fix_vec3_orientation(v: smt.Vec3) -> smt.Vec3:
    return smt.Vec3(v.x, v.z, -v.y)


def __parse_mesh(obj, mesh: dst.Mesh):
    obj_mesh = obj.data
    assert isinstance(obj_mesh, bpy.types.Mesh)
    obj_mesh.calc_loop_triangles()

    mesh.name = obj_mesh.name

    armature = obj.find_armature()

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


def __parse_mesh_actor(obj, scene: dst.Scene):
    actor = scene.new_mesh_actor()
    __parse_actor(obj, actor)
    actor.mesh_name = obj.data.name

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
        print("[DAL] WARN::custom distance is not enabled for light \"{}\"".format(plight.name))

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

    for obj in bpy_scene.objects:
        obj_type = __classify_object_type(obj)

        if obj_type == ObjType.mesh:
            __parse_mesh_actor(obj, scene)

        elif obj_type == ObjType.directional_light:
            __parse_light_directional(obj, scene.new_dlight())
        elif obj_type == ObjType.point_light:
            __parse_light_point(obj, scene.new_plight())
        elif obj_type == ObjType.spotlight:
            __parse_light_spot(obj, scene.new_slight())

    return scene


def parse_scene_json(configs: ParseConfigs) -> Dict:
    output = {}

    for bpy_scene in bpy.data.scenes:
        output[bpy_scene.name] = __parse_scene(bpy_scene, configs).make_json()

    return output
