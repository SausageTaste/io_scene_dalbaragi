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
    mesh = "MESH"
    camera = "CAMERA"
    armature = "ARMATURE"

    directional_light = "DLIGHT"
    point_light = "PLIGHT"
    spotlight = "SLIGHT"


# In blender's coordinate system, -z is down.
# But in Dalbaragi engine, -y is down and -z is far direction.
def __fix_vec3_orientation(v: smt.Vec3) -> smt.Vec3:
    return smt.Vec3(v.x, v.z, -v.y)


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
    type_str = str(obj.type)

    if "LIGHT" == type_str:
        if isinstance(obj.data, bpy.types.SunLight):
            return ObjType.directional_light
        elif isinstance(obj.data, bpy.types.PointLight):
            return ObjType.point_light
        elif isinstance(obj.data, bpy.types.SpotLight):
            return ObjType.spotlight

    for x in ObjType:
        if x.value == type_str:
            return x

    return ObjType.unknown


def __parse_scene(bpy_scene, configs: ParseConfigs) -> dst.Scene:
    scene = dst.Scene()

    for obj in bpy_scene.objects:
        obj_type = __classify_object_type(obj)

        if obj_type == ObjType.directional_light:
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
