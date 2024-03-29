from typing import List, Dict, Iterable

import numpy as np

from . import byteutils as byt
from . import map_data as mpd
from . import rawdata as rwd
from . import smalltype as smt


MAX_DLIGHT_COUNT = 3


def __find_envmap_index(name: str, envmaps: Iterable[rwd.EnvMap]) -> int:
    if not name:
        return -1

    for i, m in enumerate(envmaps):
        if m.m_name == name:
            return i
    else:
        raise RuntimeError("envmap named \"{}\" does not exist".format(name))


def __build_bin_vec3(v: smt.Vec3) -> bytearray:
    result = bytearray()

    result += byt.to_float32(v.x)
    result += byt.to_float32(v.y)
    result += byt.to_float32(v.z)

    return result


def __build_bin_aabb(aabb: smt.AABB3) -> bytearray:
    result = bytearray()

    result += __build_bin_vec3(aabb.m_min)
    result += __build_bin_vec3(aabb.m_max)

    return result


def __build_bin_transform(trans: smt.Transform) -> bytearray:
    assert isinstance(trans, smt.Transform)

    result = bytearray()

    result += __build_bin_vec3(trans.m_pos)

    result += byt.to_float32(trans.m_rotate.w)
    result += byt.to_float32(trans.m_rotate.x)
    result += byt.to_float32(trans.m_rotate.y)
    result += byt.to_float32(trans.m_rotate.z)

    result += byt.to_float32(trans.m_scale)

    return result


# id_map is None if skeleton doesn't exist.
def __build_bin_mesh(mesh: rwd.Mesh) -> bytearray:
    assert isinstance(mesh, rwd.Mesh)

    data = bytearray()

    raw_vertices: List[float] = []
    raw_uv_coords: List[float] = []
    raw_normals: List[float] = []

    for v in mesh.vertices():
        raw_vertices.extend(v.m_vertex.xyz)
        raw_uv_coords.extend(v.m_uvCoord.xy)
        raw_normals.extend(v.m_normal.xyz)

    num_vertices = mesh.size()
    v = np.array(raw_vertices, dtype=np.float32)
    t = np.array(raw_uv_coords, dtype=np.float32)
    n = np.array(raw_normals, dtype=np.float32)

    data += byt.to_int32(num_vertices)
    data += v.tobytes()
    data += t.tobytes()
    data += n.tobytes()

    return data


def __build_bin_render_unit(unit: rwd.RenderUnit):
    assert isinstance(unit, rwd.RenderUnit)

    data = bytearray()

    # Material
    material: rwd.Material = unit.m_material
    data += byt.to_float32(material.m_roughness)
    data += byt.to_float32(material.m_metallic)

    textures = (
        material.m_albedoMap,
        material.m_roughnessMap,
        material.m_metallicMap,
        material.m_normalMap,
    )

    for tex in textures:
        if tex:
            data += byt.to_nullTerminated("::" + tex)
        else:
            data += b'\0'

    # Mesh
    data += __build_bin_mesh(unit.m_mesh)

    return data


def __build_bin_model(model: rwd.Model) -> bytearray:
    assert isinstance(model, rwd.Model)

    data = bytearray()

    # Render units
    data += byt.to_int32(len(model.m_renderUnits))
    for unit in model.m_renderUnits:
        data += __build_bin_render_unit(unit)

    # AABB
    data += __build_bin_aabb(model.m_aabb)

    # Info
    data += byt.to_bool1(model.m_hasRotate)
    data += byt.to_bool1(model.m_hasMeshCollider)

    return data


def __build_bin_static_actor(actor: rwd.StaticActor):
    assert isinstance(actor, rwd.StaticActor)

    result = bytearray()

    result += byt.to_nullTerminated(actor.m_name)
    result += __build_bin_transform(actor.m_transform)
    result += byt.to_int32(actor.m_collider.value)

    return result


def __build_bin_water_plane(water: rwd.WaterPlane) -> bytearray:
    assert isinstance(water, rwd.WaterPlane)

    result = bytearray()

    result += __build_bin_vec3(water.m_centerPos)
    result += __build_bin_vec3(water.m_deepColor)

    result += byt.to_float32(water.m_width)
    result += byt.to_float32(water.m_height)

    result += byt.to_float32(water.m_flowSpeed)
    result += byt.to_float32(water.m_waveStreng)
    result += byt.to_float32(water.m_darkestDepth)
    result += byt.to_float32(water.m_reflectance)

    return result


def __build_bin_envmap(envmap: rwd.EnvMap) -> bytearray:
    data = bytearray()

    data += __build_bin_vec3(envmap.m_pos)
    data += byt.to_int32(len(envmap.m_volume))

    for plane in envmap.m_volume:
        coeff = plane.coef()

        data += byt.to_float32(coeff[0])
        data += byt.to_float32(coeff[1])
        data += byt.to_float32(coeff[2])
        data += byt.to_float32(coeff[3])

    return data


def __build_bin_light(light: rwd.ILight) -> bytearray:
    result = bytearray()

    result += byt.to_nullTerminated(light.m_name)
    result += byt.to_bool1(light.m_hasShadow)
    result += __build_bin_vec3(light.m_color)
    result += byt.to_float32(light.m_intensity)

    return result


def __build_bin_plight(plight: rwd.PointLight) -> bytearray:
    result = __build_bin_light(plight)

    result += __build_bin_vec3(plight.m_pos)
    result += byt.to_float32(plight.m_maxDistance)
    result += byt.to_float32(plight.m_halfIntenseDist)

    return result


def __build_bin_slight(slight: rwd.SpotLight) -> bytearray:
    result = __build_bin_light(slight)

    result += __build_bin_vec3(slight.m_pos)
    result += byt.to_float32(slight.m_maxDistance)
    result += byt.to_float32(slight.m_halfIntenseDist)

    result += __build_bin_vec3(slight.m_direction)
    result += byt.to_float32(slight.m_spotDegree)
    result += byt.to_float32(slight.m_spotBlend)

    return result


def make_binary_dmc(scene: rwd.Scene):
    assert isinstance(scene, rwd.Scene)

    data = bytearray()

    uid_index_map: Dict[int, int] = {}

    # Models
    data += byt.to_int32(len(scene.m_models))
    for i, mid_n_model in enumerate(scene.m_models.items()):
        model_id, model = mid_n_model
        model: rwd.Model

        data += __build_bin_model(model)

        assert model_id not in uid_index_map.keys()
        uid_index_map[model_id] = i

    # Static actors
    data += byt.to_int32(len(scene.m_static_actors))
    for actor in scene.m_static_actors:
        data += __build_bin_static_actor(actor)
        data += byt.to_int32(uid_index_map[actor.m_renderUnitID])

        num_units = len(scene.m_models[actor.m_renderUnitID].m_renderUnits)
        data += byt.to_int32(num_units)
        for i in range(num_units):
            envmap_name = actor.envmapOf(i)
            envmap_index = __find_envmap_index(envmap_name, scene.m_envmaps)
            data += byt.to_int32(envmap_index)

    # Waters
    data += byt.to_int32(len(scene.m_waters))
    for water in scene.m_waters:
        data += __build_bin_water_plane(water)

    # Env maps
    data += byt.to_int32(len(scene.m_envmaps))
    for envmap in scene.m_envmaps:
        data += __build_bin_envmap(envmap)

    # Point lights
    data += byt.to_int32(len(scene.m_plights))
    for plight in scene.m_plights:
        data += __build_bin_plight(plight)

    # Spotlights
    data += byt.to_int32(len(scene.m_slights))
    for slight in scene.m_slights:
        data += __build_bin_slight(slight)

    return data


def __build_bin_chunk_info(chunk: mpd.Level.MapChunk) -> bytearray:
    result = bytearray()

    result += __build_bin_aabb(chunk.m_aabb)

    result += byt.to_float32(chunk.m_offset.x)
    result += byt.to_float32(chunk.m_offset.y)
    result += byt.to_float32(chunk.m_offset.z)

    return result


def __build_bin_dlight(dlight: rwd.DirectionalLight) -> bytearray:
    result = __build_bin_light(dlight)

    result += __build_bin_vec3(dlight.m_direction)

    return result


def make_binary_dlb(level: mpd.Level) -> bytearray:
    dlights: List[rwd.DirectionalLight] = []
    for name, chunk in level.items():
        dlights += chunk.m_data.m_dlights
    if len(dlights) > MAX_DLIGHT_COUNT:
        raise RuntimeError("the number of directional lights cannot exceed {}".format(MAX_DLIGHT_COUNT))

    result = bytearray()

    result += byt.to_int32(len(dlights))
    for dlight in dlights:
        result += __build_bin_dlight(dlight)

    result += byt.to_int32(len(level))
    for name, chunk in level.items():
        result += byt.to_nullTerminated(name)
        result += __build_bin_chunk_info(chunk)

    return result
