from typing import Dict, List, Tuple, Callable, Iterator, Any
import enum

from . import smalltype as smt


MAX_JOINT_COUNT = 130


class Scene:
    class Material:
        def __init__(self):
            self.m_roughness = 0.5
            self.m_metallic = 0.0
            self.m_albedoMap = ""
            self.m_roughnessMap = ""
            self.m_metallicMap = ""

    class VertexData:
        def __init__(self):
            self.m_vertex = smt.Vec3()
            self.m_uvCoord = smt.Vec2()
            self.m_normal = smt.Vec3()
            self.m_joints: List[Tuple[float, str]] = []

        def addJoint(self, name: str, weight: float) -> None:
            self.m_joints.append((weight, name))
            self.m_joints.sort(reverse=True)

    class Mesh:
        def __init__(self):
            self.__vertices: List[Scene.VertexData] = []
            self.__skeletonName = ""

        def addVertex(self, data: "Scene.VertexData") -> None:
            self.__vertices.append(data)

        def vertices(self) -> Iterator["Scene.VertexData"]:
            return iter(self.__vertices)

        def size(self) -> int:
            return len(self.__vertices)

        @property
        def m_skeletonName(self):
            return self.__skeletonName

        @m_skeletonName.setter
        def m_skeletonName(self, name: str):
            self.__skeletonName = str(name)

    class RenderUnit:
        def __init__(self):
            self.__ref_count = 0
            self.__material = Scene.Material()
            self.__mesh = Scene.Mesh()

        @property
        def m_refCount(self):
            return self.__ref_count

        @m_refCount.setter
        def m_refCount(self, value: int):
            self.__ref_count = int(value)

        @property
        def m_material(self):
            return self.__material

        @m_material.setter
        def m_material(self, value: "Scene.Material"):
            assert isinstance(value, Scene.Material)
            self.__material = value

        @property
        def m_mesh(self):
            return self.__mesh

    class JointType(enum.Enum):
        basic = 0
        hair_root = 1
        skirt_root = 2

    class Joint:
        def __init__(self, name: str, parent_name: str):
            self.__name = str(name)
            self.__parentName = str(parent_name)
            self.__offsetMat = smt.Mat4()
            self.__jointType = Scene.JointType.basic

        def __str__(self):
            if Scene.JointType.basic != self.m_jointType:
                return 'Joint{{ name="{}", parent="{}", type={} }}'.format(
                    self.m_name, self.m_parentName, self.m_jointType)
            else:
                return 'Joint{{ name="{}", parent="{}" }}'.format(self.m_name, self.m_parentName)

        @property
        def m_name(self):
            return self.__name

        @property
        def m_parentName(self):
            return self.__parentName

        @property
        def m_offsetMat(self):
            return self.__offsetMat

        @property
        def m_jointType(self):
            return self.__jointType

        @m_jointType.setter
        def m_jointType(self, v: "Scene.JointType"):
            assert isinstance(v, Scene.JointType)

            if Scene.JointType.basic != self.__jointType:
                print('[DAL] WARN::Joint type set twice for "{}", from "{}" to "{}".'.format(
                    self.__name, self.__jointType, v
                ))

            self.__jointType = v

    class Skeleton:
        def __init__(self, name: str):
            self.__name = str(name)
            self.__joints: List[Scene.Joint] = []

        def __iter__(self):
            return iter(self.__joints)

        def __len__(self):
            return len(self.__joints)

        def newJoint(self, name: str, parent_name: str) -> "Scene.Joint":
            if len(self.__joints) > MAX_JOINT_COUNT:
                raise RuntimeError("the number of joints cannot exceed {}.".format(MAX_JOINT_COUNT))

            joint = Scene.Joint(name, parent_name)
            self.__joints.append(joint)
            return joint

        @property
        def m_name(self):
            return self.__name

    class JointKeyframes:
        def __init__(self, joint_name: str):
            self.__name = str(joint_name)

            self.__poses: List[Tuple[float, smt.Vec3]] = []
            self.__rotates: List[Tuple[float, smt.Quat]] = []
            self.__scales: List[Tuple[float, float]] = []

        def addPos(self, timepoint: float, x, y, z) -> None:
            data = (float(timepoint), smt.Vec3(x, y, z))
            self.__poses.append(data)

        def addRotate(self, timepoint: float, w, x, y, z) -> None:
            data = (float(timepoint), smt.Quat(w, x, y, z))
            self.__rotates.append(data)

        def addScale(self, timepoint: float, v: float):
            data = (float(timepoint), float(v))
            self.__scales.append(data)

        def iterPoses(self):
            return iter(self.__poses)

        def iterRotates(self):
            return iter(self.__rotates)

        def iterScales(self):
            return iter(self.__scales)

        def getMaxTimepoint(self) -> float:
            max_value = 0.0

            for x in self.__poses:
                max_value = max(max_value, x[0])
            for x in self.__rotates:
                max_value = max(max_value, x[0])
            for x in self.__scales:
                max_value = max(max_value, x[0])

            return max_value

        def cleanUp(self) -> None:
            # Poses

            poses_new = self.__poses[:]

            poses_new.sort()
            poses_new: List[Tuple[float, smt.Vec3]] = self.__removeDuplicateKeyframes(poses_new)
            if 1 == len(poses_new) and poses_new[0][1].isDefault():
                poses_new.clear()

            # Rotations

            rotates_new = self.__rotates[:]

            rotates_new.sort()
            rotates_new: List[Tuple[float, smt.Quat]] = self.__removeDuplicateKeyframes(rotates_new)
            if 1 == len(rotates_new) and rotates_new[0][1].isDefault():
                rotates_new.clear()

            # Scales

            scales_new = self.__scales[:]

            scales_new.sort()
            scales_new: List[Tuple[float, float]] = self.__removeDuplicateKeyframes(scales_new)
            if 1 == len(scales_new) and smt.isFloatNear(scales_new[0][1], 1):
                scales_new.clear()

            # Apply changes

            self.__poses = poses_new
            self.__rotates = rotates_new
            self.__scales = scales_new

        # Must call self.cleanUp first
        def isUseless(self) -> bool:
            if len(self.__poses):
                return False
            elif len(self.__rotates):
                return False
            elif len(self.__scales):
                return False
            else:
                return True

        @property
        def m_name(self):
            return self.__name

        @staticmethod
        def __removeDuplicateKeyframes(arr: List[Tuple[float, Any]]):
            arr_size = len(arr)
            if 0 == arr_size:
                return []

            new_arr = [arr[0]]
            for i in range(1, arr_size):
                if arr[i][1] != new_arr[-1][1]:
                    new_arr.append(arr[i])
            return new_arr

    class Animation:
        def __init__(self, name: str, tick_per_sec: float):
            self.__name = str(name)
            self.__tickPerSec = float(tick_per_sec)
            self.__keyframes: List[Scene.JointKeyframes] = []

        def newJoint(self, joint_name: str) -> "Scene.JointKeyframes":
            keyframes = Scene.JointKeyframes(joint_name)
            self.__keyframes.append(keyframes)
            return keyframes

        def cleanUp(self) -> None:
            for joint in self.m_joints:
                joint.cleanUp()

        @property
        def m_name(self):
            return self.__name

        @property
        def m_tickPerSec(self):
            return self.__tickPerSec

        @property
        def m_joints(self):
            return self.__keyframes

    class StaticActor:
        def __init__(self):
            self.m_name = ""
            self.m_renderUnitID = 0

    def __init__(self):
        self.m_render_units: Dict[int, Scene.RenderUnit] = {}
        self.m_static_actors: List[Scene.StaticActor] = []
        self.m_skeletons: List[Scene.Skeleton] = []
        self.m_animations: List[Scene.Animation] = []

        # Tuple(name, reason)
        self.m_skipped_objs: List[Tuple[str, str]] = []

    def printInfo(self, println: Callable) -> None:
        for uid, unit in self.m_render_units.items():
            println('[DAL] Render unit{{ id={}, ref_count={}, verts={}, skeleton="{}" }}'.format(
                uid, unit.m_refCount, unit.m_mesh.size(), unit.m_mesh.m_skeletonName))
        for actor in self.m_static_actors:
            println('[DAL] Static actor{{ name="{}", uid={} }}'.format(actor.m_name, actor.m_renderUnitID))
        for skeleton in self.m_skeletons:
            println('[DAL] Skeleton{{ name="{}", joints={} }}'.format(skeleton.m_name, len(skeleton)))
            for joint in skeleton:
                println('[DAL]    {}'.format(joint))
        for anim in self.m_animations:
            println('[DAL] Animation{{ name="{}", joints={} }}'.format(anim.m_name, len(anim.m_joints)))
            for joint in anim.m_joints:
                println('[DAL]    Joint{{ name="{}" }}'.format(joint.m_name))
                for tp, pos in joint.iterPoses():
                    println('[DAL]        Pos   at {} : {{ {}, {}, {} }}'.format(tp, pos.x, pos.y, pos.z))
                for tp, quat in joint.iterRotates():
                    println(
                        '[DAL]        rot   at {} : {{ {}, {}, {}, {} }}'.format(tp, quat.w, quat.x, quat.y, quat.z))
                for tp, scale in joint.iterScales():
                    println('[DAL]        scale at {} : {}'.format(tp, scale))
        for name, reason in self.m_skipped_objs:
            println('[DAL] Skipped {{ name="{}", reason="{}" }}'.format(name, reason))
