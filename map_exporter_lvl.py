from typing import List, Dict

import numpy as np

from . import byteutils as byt
from . import map_data as mpd
from . import rawdata as rwd
from . import smalltype as smt


def _build_bin_aabb(aabb: smt.AABB3) -> bytearray:
    result = bytearray()

    result += byt.to_float32(aabb.m_min.x)
    result += byt.to_float32(aabb.m_min.y)
    result += byt.to_float32(aabb.m_min.z)
    result += byt.to_float32(aabb.m_max.x)
    result += byt.to_float32(aabb.m_max.y)
    result += byt.to_float32(aabb.m_max.z)

    return result

def _build_bin_transform(trans: smt.Transform) -> bytearray:
    assert isinstance(trans, smt.Transform)

    result = bytearray()

    result += byt.to_float32(trans.m_pos.x)
    result += byt.to_float32(trans.m_pos.y)
    result += byt.to_float32(trans.m_pos.z)

    result += byt.to_float32(trans.m_rotate.w)
    result += byt.to_float32(trans.m_rotate.x)
    result += byt.to_float32(trans.m_rotate.y)
    result += byt.to_float32(trans.m_rotate.z)

    result += byt.to_float32(trans.m_scale)

    return result


# id_map is None if skeleton doesn't exist.
def _build_bin_mesh(mesh: rwd.Scene.Mesh) -> bytearray:
    assert isinstance(mesh, rwd.Scene.Mesh)

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

def _build_bin_render_unit(unit: rwd.Scene.RenderUnit):
    assert isinstance(unit, rwd.Scene.RenderUnit)

    data = bytearray()

    # Material
    material: rwd.Scene.Material = unit.m_material
    data += byt.to_float32(material.m_roughness)
    data += byt.to_float32(material.m_metallic)
    data += byt.to_nullTerminated(material.m_albedoMap)
    data += byt.to_nullTerminated(material.m_roughnessMap)
    data += byt.to_nullTerminated(material.m_metallicMap)
    data += byt.to_nullTerminated(material.m_normalMap)

    # Mesh
    data += _build_bin_mesh(unit.m_mesh)

    # AABB
    aabb = unit.m_mesh.makeAABB()
    data += _build_bin_aabb(aabb)

    return data

def _build_bin_static_actor(actor: rwd.Scene.StaticActor):
    assert isinstance(actor, rwd.Scene.StaticActor)

    result = bytearray()

    result += byt.to_nullTerminated(actor.m_name)
    result += _build_bin_transform(actor.m_transform)

    return result


def make_binary_dmc(scene: rwd.Scene):
    assert isinstance(scene, rwd.Scene)

    data = bytearray()

    uid_index_map: Dict[int, int] = {}

    # Render units
    data += byt.to_int32(len(scene.m_render_units))
    for i, uid_n_unit in enumerate(scene.m_render_units.items()):
        uid, unit = uid_n_unit
        data += _build_bin_render_unit(unit)

        assert uid not in uid_index_map.keys()
        uid_index_map[uid] = i

    # Static actors
    data += byt.to_int32(len(scene.m_static_actors))
    for actor in scene.m_static_actors:
        data += _build_bin_static_actor(actor)
        data += byt.to_int32(uid_index_map[actor.m_renderUnitID])

    return data


def __build_bin_chunk_info(chunk: mpd.Level.MapChunk) -> bytearray:
    result = bytearray()

    result += _build_bin_aabb(chunk.m_aabb)

    result += byt.to_float32(chunk.m_offset.x)
    result += byt.to_float32(chunk.m_offset.y)
    result += byt.to_float32(chunk.m_offset.z)

    return result

def make_binary_dlb(level: mpd.Level) -> bytearray:
    result = bytearray()

    result += byt.to_int32(len(level))

    for name, chunk in level.items():
        result += byt.to_nullTerminated(name)
        result += __build_bin_chunk_info(chunk)

    return result
