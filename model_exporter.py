from typing import Iterable, Dict, Optional, List, Tuple

import numpy as np

from . import rawdata as rwd
from . import smalltype as smt
from . import byteutils as byt


NUM_JOINTS_PER_VERTEX = 4


def _make_joints_id_map(skeleton: rwd.Skeleton) -> Dict[str, int]:
    result = dict()

    for i, joint in enumerate(skeleton.m_joints):
        assert joint.m_name not in result.keys()
        result[joint.m_name] = i

    return result


def _make_aabb_of_models(models: Iterable[rwd.Model]) -> rwd.smt.AABB3:
    aabb = rwd.smt.AABB3()

    for model in models:
        aabb = aabb + model.m_aabb

    return aabb


def _divide_meshes_with_joints(scene: rwd.Scene, joint_id_map: Dict[str, int]):
    units_with_joints: List[Tuple[str, rwd.RenderUnit]] = []
    units_without_joints: List[Tuple[str, rwd.RenderUnit]] = []

    for actor in scene.m_static_actors:
        for unit in scene.m_models[actor.m_renderUnitID].m_renderUnits:
            if 0 == unit.m_mesh.size():
                continue

            if unit.m_mesh.hasJoint() and (joint_id_map is not None):
                units_with_joints.append((actor.m_name, unit))
            else:
                units_without_joints.append((actor.m_name, unit))

    return units_with_joints, units_without_joints


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


def _build_bin_skeleton(skeleton: rwd.Skeleton, id_map: Dict[str, int]) -> bytearray:
    assert isinstance(skeleton, rwd.Skeleton)

    if len(skeleton) > rwd.MAX_JOINT_COUNT:
        raise RuntimeError("the number of joints in \"{}\" exceeds capacity {}".format(len(skeleton), rwd.MAX_JOINT_COUNT))

    data = bytearray()

    data += byt.to_int32(len(skeleton))
    for joint in skeleton.m_joints:
        parent_id = id_map[joint.m_parentName] if ("" != joint.m_parentName) else -1

        data += byt.to_nullTerminated(joint.m_name)
        data += byt.to_int32(parent_id)
        data += byt.to_int32(joint.m_jointType.value)
        data += _build_bin_mat4(joint.m_offsetMat)

    return data


def _build_bin_joint_keyframes(keyframes: rwd.JointKeyframes) -> bytearray:
    assert isinstance(keyframes, rwd.JointKeyframes)

    data = bytearray()

    data += byt.to_nullTerminated(keyframes.m_name)
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


def _build_bin_animation(anim: rwd.Animation, id_map: Dict[str, int]) -> bytearray:
    assert isinstance(anim, rwd.Animation)
    assert 0.0 != anim.m_tickPerSec

    data = bytearray()

    data += byt.to_nullTerminated(anim.m_name)
    data += byt.to_float32(anim.calcDurationTick())
    data += byt.to_float32(anim.m_tickPerSec)

    # Joints
    data += byt.to_int32(len(anim.m_joints))
    for joint in anim.m_joints:
        data += _build_bin_joint_keyframes(joint)

    return data


# id_map is None if skeleton doesn't exist.
def _build_bin_mesh_without_joint(mesh: rwd.Mesh) -> Tuple[int, bytearray]:
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

    return num_vertices, data


def _build_bin_mesh_with_joint(mesh: rwd.Mesh, id_map: Optional[Dict[str, int]]) -> bytearray:
    assert isinstance(mesh, rwd.Mesh)
    assert mesh.hasJoint() and (id_map is not None)

    num_vertices, data = _build_bin_mesh_without_joint(mesh)

    if True:
        raw_weights: List[float] = []
        raw_jids: List[int] = []

        for v in mesh.vertices():
            weights_n_ids: List[Tuple[float, int]] = [(0.0, -1) for _ in range(NUM_JOINTS_PER_VERTEX)]
            for j_weight, j_name in v.m_joints:
                try:
                    joint_id = id_map[j_name]
                except KeyError:
                    continue
                else:
                    weights_n_ids.append((j_weight, joint_id))
            weights_n_ids.sort(reverse=True)
            weight_sum = float(sum(xx[0] for xx in weights_n_ids[0:NUM_JOINTS_PER_VERTEX]))

            if 0.0 == weight_sum:
                for weight, jid in range(NUM_JOINTS_PER_VERTEX):
                    raw_weights.append(weight)
                    raw_jids.append(jid)
            else:
                weight_normalizer = 1.0 / weight_sum
                for weight, jid in weights_n_ids[:NUM_JOINTS_PER_VERTEX]:
                    raw_weights.append(weight * weight_normalizer)
                    raw_jids.append(jid)

        bw = np.array(raw_weights, dtype=np.float32)
        bi = np.array(raw_jids, dtype=np.int32)
        assert len(bw) == len(bi) == NUM_JOINTS_PER_VERTEX * num_vertices

        data += bw.tobytes()
        data += bi.tobytes()

    return data


def _build_bin_material(material: rwd.Material) -> bytearray:
    data = bytearray()

    data += byt.to_float32(material.m_roughness)
    data += byt.to_float32(material.m_metallic)
    data += byt.to_bool1(material.m_alphaBlend)
    data += byt.to_nullTerminated(material.m_albedoMap)
    data += byt.to_nullTerminated(material.m_roughnessMap)
    data += byt.to_nullTerminated(material.m_metallicMap)
    data += byt.to_nullTerminated(material.m_normalMap)

    return data


def make_binary_dmd(scene: rwd.Scene):
    assert isinstance(scene, rwd.Scene)

    data = bytearray()

    # AABB
    aabb = _make_aabb_of_models(xx for xx in scene.m_models.values())
    data += _build_bin_aabb(aabb)

    joint_id_map: Optional[Dict[str, int]] = None
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

    # Models
    units_with_joints, units_without_joints = _divide_meshes_with_joints(scene, joint_id_map)

    data += byt.to_int32(len(units_without_joints))
    for name, unit in units_without_joints:
        data += byt.to_nullTerminated(name)
        data += _build_bin_material(unit.m_material)
        data += _build_bin_mesh_without_joint(unit.m_mesh)[1]

    data += byt.to_int32(len(units_with_joints))
    for name, unit in units_with_joints:
        data += byt.to_nullTerminated(name)
        data += _build_bin_material(unit.m_material)
        data += _build_bin_mesh_with_joint(unit.m_mesh, joint_id_map)

    # Placeholders for indexed mesh list
    data += byt.to_int32(0)
    data += byt.to_int32(0)

    # Signature
    data += byt.to_nullTerminated("")

    return data
