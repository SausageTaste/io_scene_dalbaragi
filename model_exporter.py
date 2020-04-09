from typing import Iterable, Dict, Optional, List

import numpy as np

from . import rawdata as rwd
from . import smalltype as smt
from . import byteutils as byt


MAX_JOINT_NUM = 130

def _make_joints_id_map(skeleton: rwd.Scene.Skeleton) -> Dict[str, int]:
    result = dict()

    for i, joint in enumerate(skeleton.m_joints):
        assert joint.m_name not in result.keys()
        result[joint.m_name] = i

    return result

def _make_aabb_of_meshes(meshes: Iterable[rwd.Scene.Mesh]) -> rwd.smt.AABB3:
    aabb = rwd.smt.AABB3()

    for mesh in meshes:
        for v in mesh.vertices():
            aabb.resizeToContain(v.m_vertex.x, v.m_vertex.y, v.m_vertex.z)

    return aabb


def _build_bin_mat4(mat: smt.Mat4) -> bytearray:
    assert isinstance(mat, smt.Mat4)

    floatlist = []
    for row in range(4):
        for col in range(4):
            floatlist.append(mat.get(row, col))

    return bytearray(np.array(floatlist, dtype=np.float32).tobytes())

def _build_bin_aabb(aabb: smt.AABB3) -> bytearray:
    assert isinstance(aabb, smt.AABB3)

    data = bytearray()

    data += byt.to_float32(aabb.m_min[0])
    data += byt.to_float32(aabb.m_min[1])
    data += byt.to_float32(aabb.m_min[2])
    data += byt.to_float32(aabb.m_max[0])
    data += byt.to_float32(aabb.m_max[1])
    data += byt.to_float32(aabb.m_max[2])

    return data

def _build_bin_skeleton(skeleton: rwd.Scene.Skeleton, id_map: Dict[str, int]) -> bytearray:
    assert isinstance(skeleton, rwd.Scene.Skeleton)

    if len(skeleton) > MAX_JOINT_NUM:
        raise RuntimeError("the number of joints in \"{}\" exceeds capacity {}".format(len(skeleton), MAX_JOINT_NUM))

    data = bytearray()

    data += byt.to_int32(len(skeleton))
    for joint in skeleton.m_joints:
        parent_id = id_map[joint.m_parentName] if ("" != joint.m_parentName) else -1

        data += byt.to_nullTerminated(joint.m_name)
        data += byt.to_int32(parent_id)
        data += byt.to_int32(joint.m_jointType.value)
        data += _build_bin_mat4(joint.m_offsetMat)

    return data

def _build_bin_joint_keyframes(keyframes: rwd.Scene.JointKeyframes) -> bytearray:
    assert isinstance(keyframes, rwd.Scene.JointKeyframes)

    data = bytearray()

    data += _build_bin_mat4(keyframes.m_transform)

    poses = list(keyframes.iterPoses())
    rotations = list(keyframes.iterRotates())
    scales = list(keyframes.iterScales())

    data += byt.to_int32(len(poses))
    for timepoint, value in poses:
        data += byt.to_float32(timepoint)
        data += byt.to_float32(value.x)
        data += byt.to_float32(value.y)
        data += byt.to_float32(value.z)

    data += byt.to_int32(len(rotations))
    for timepoint, value in rotations:
        data += byt.to_float32(timepoint)
        data += byt.to_float32(value.x)
        data += byt.to_float32(value.y)
        data += byt.to_float32(value.z)
        data += byt.to_float32(value.w)

    data += byt.to_int32(len(scales))
    for timepoint, value in scales:
        data += byt.to_float32(timepoint)
        data += byt.to_float32(value)

    return data

def _build_bin_animation(anim: rwd.Scene.Animation, id_map: Dict[str, int]) -> bytearray:
    assert isinstance(anim, rwd.Scene.Animation)
    assert 0.0 != anim.m_tickPerSec

    data = bytearray()

    data += byt.to_nullTerminated(anim.m_name)
    data += byt.to_float32(anim.calcDurationTick())
    data += byt.to_float32(anim.m_tickPerSec)

    # Joints
    data += byt.to_int32(len(id_map))

    dummy_joint_data = _build_bin_joint_keyframes(rwd.Scene.JointKeyframes("dummy"))
    data_list: List[Optional[bytearray]] = [dummy_joint_data for _ in range(len(id_map))]

    for joint in anim.m_joints:
        index = id_map[joint.m_name]
        data_list[index] = _build_bin_joint_keyframes(joint)

    for x in data_list:
        data += x

    return data

# id_map is None if skeleton doesn't exist.
def _build_bin_mesh(mesh: rwd.Scene.Mesh, id_map: Optional[Dict[str, int]]) -> bytearray:
    assert isinstance(mesh, rwd.Scene.Mesh)

    data = bytearray()

    raw_vertices: List[float] = []
    raw_uv_coords: List[float] = []
    raw_normals: List[float] = []

    for v in mesh.vertices():
        raw_vertices.extend(v.m_vertex.xyz)
        raw_uv_coords.extend(v.m_uvCoord.xy)
        raw_normals.extend(v.m_normal.xyz)

    has_skeleton = mesh.hasJoint() and (id_map is not None)
    num_vertices = mesh.size()
    v = np.array(raw_vertices, dtype=np.float32)
    t = np.array(raw_uv_coords, dtype=np.float32)
    n = np.array(raw_normals, dtype=np.float32)

    data += byt.to_int32(num_vertices)
    data += byt.to_bool1(has_skeleton)

    data += v.tobytes()
    data += t.tobytes()
    data += n.tobytes()

    if has_skeleton:
        raw_weights: List[float] = []
        raw_jids: List[int] = []

        for v in mesh.vertices():
            weights_n_ids = [(0, -1), (0, -1), (0, -1)]
            for j_weight, j_name in v.m_joints:
                try:
                    joint_id = id_map[j_name]
                except KeyError:
                    continue
                else:
                    weights_n_ids.append((j_weight, joint_id))
            weights_n_ids.sort(reverse=True)

            w0 = weights_n_ids[0][0]
            w1 = weights_n_ids[1][0]
            w2 = weights_n_ids[2][0]
            weight_sum = w0 + w1 + w2
            weight_normalizer = (1.0 / weight_sum) if (0.0 != weight_sum) else 1.0

            raw_weights.append(w0 * weight_normalizer)
            raw_weights.append(w1 * weight_normalizer)
            raw_weights.append(w2 * weight_normalizer)

            raw_jids.append(weights_n_ids[0][1])
            raw_jids.append(weights_n_ids[1][1])
            raw_jids.append(weights_n_ids[2][1])

            # print(smt.Vec3(w0, w1, w2), weights_n_ids[0][1], weights_n_ids[1][1], weights_n_ids[2][1])

        bw = np.array(raw_weights, dtype=np.float32)
        bi = np.array(raw_jids, dtype=np.int32)
        assert len(bw) == len(bi) == 3 * num_vertices

        data += bw.tobytes()
        data += bi.tobytes()

    return data

def _build_bin_render_unit(actor: rwd.Scene.StaticActor, unit: rwd.Scene.RenderUnit, id_map: Optional[Dict[str, int]]):
    assert isinstance(actor, rwd.Scene.StaticActor)
    assert isinstance(unit, rwd.Scene.RenderUnit)

    data = bytearray()

    data += byt.to_nullTerminated(actor.m_name)

    # Material
    material: rwd.Scene.Material = unit.m_material
    data += byt.to_float32(material.m_roughness)
    data += byt.to_float32(material.m_metallic)
    data += byt.to_nullTerminated(material.m_albedoMap)
    data += byt.to_nullTerminated(material.m_roughnessMap)
    data += byt.to_nullTerminated(material.m_metallicMap)
    data += byt.to_nullTerminated(material.m_normalMap)

    # Mesh
    data += _build_bin_mesh(unit.m_mesh, id_map)

    return data


def make_binary_dmd(scene: rwd.Scene):
    assert isinstance(scene, rwd.Scene)

    data = bytearray()

    # AABB
    aabb = _make_aabb_of_meshes(xx.m_mesh for xx in scene.m_render_units.values())
    data += _build_bin_aabb(aabb)

    joint_id_map = None
    if 0 == len(scene.m_skeletons):
        data += byt.to_int32(0)  # 0 joints
        data += byt.to_int32(0)  # 0 animations
    elif 1 == len(scene.m_skeletons):
        # Skeleton
        joint_id_map = _make_joints_id_map(scene.m_skeletons[0])
        data += _build_bin_skeleton(scene.m_skeletons[0], joint_id_map)

        # Animations
        data += byt.to_int32(len(scene.m_animations))
        for anim in scene.m_animations:
            data += _build_bin_animation(anim, joint_id_map)
    else:
        raise RuntimeError("multiple armatures are not supported!")

    # Render units
    data += byt.to_int32(len(scene.m_static_actors))
    for actor in scene.m_static_actors:
        unit = scene.m_render_units[actor.m_renderUnitID]
        data += _build_bin_render_unit(actor, unit, joint_id_map)

    return data
