from typing import List

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

def _build_bin_render_unit(actor: rwd.Scene.StaticActor, unit: rwd.Scene.RenderUnit):
    assert isinstance(actor, rwd.Scene.StaticActor)
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


def make_binary_dmc(scene: rwd.Scene):
    assert isinstance(scene, rwd.Scene)

    data = bytearray()

    # Render units
    data += byt.to_int32(len(scene.m_static_actors))
    for actor in scene.m_static_actors:
        unit = scene.m_render_units[actor.m_renderUnitID]
        data += _build_bin_render_unit(actor, unit)

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
