from typing import Dict, List, Tuple, Callable, Iterator, Any, Set
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
            self.m_normalMap = ""
            self.m_alphaBlend = False

        def makeJson(self):
            return {
                "roughness": self.m_roughness,
                "metallic": self.m_metallic,
                "albedo map": self.m_albedoMap,
                "roughness map": self.m_roughnessMap,
                "metallic map": self.m_metallicMap,
                "normal map": self.m_normalMap,
                "alpha blend": self.m_alphaBlend,
            }

    class VertexData:
        def __init__(self):
            self.m_vertex = smt.Vec3()
            self.m_uvCoord = smt.Vec2()
            self.m_normal = smt.Vec3()
            self.m_joints: List[Tuple[float, str]] = []

        def addJoint(self, name: str, weight: float) -> None:
            if 0.0 == weight: return

            self.m_joints.append((weight, name))
            self.m_joints.sort(reverse=True)

    class Mesh:
        def __init__(self):
            self.__vertices: List[Scene.VertexData] = []
            self.__skeletonName = ""

        def makeJson(self):
            return {
                "vertices size": len(self.__vertices),
                "skeleton name": self.__skeletonName,
                "has joints": self.hasJoint(),
            }

        def addVertex(self, data: "Scene.VertexData") -> None:
            self.__vertices.append(data)

        def vertices(self) -> Iterator["Scene.VertexData"]:
            return iter(self.__vertices)

        def size(self) -> int:
            return len(self.__vertices)

        def hasJoint(self) -> bool:
            for v in self.vertices():
                if len(v.m_joints):
                    return True

            return False

        @property
        def m_skeletonName(self):
            return self.__skeletonName

        @m_skeletonName.setter
        def m_skeletonName(self, name: str):
            self.__skeletonName = str(name)

    class RenderUnit:
        def __init__(self, uid: int):
            self.__id = int(uid)
            self.__ref_count = 0
            self.__material = Scene.Material()
            self.__mesh = Scene.Mesh()

        def makeJson(self):
            return {
                "id": self.__id,
                "ref count": self.__ref_count,
                "material": self.__material.makeJson(),
                "mesh": self.__mesh.makeJson(),
            }

        @property
        def m_id(self):
            return self.__id

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

        def makeJson(self):
            return {
                "name": self.__name,
                "parent name": self.__parentName,
                "joint type": self.__jointType.name,
            }

        @property
        def m_name(self):
            return self.__name

        @property
        def m_parentName(self):
            return self.__parentName

        @m_parentName.setter
        def m_parentName(self, v: str):
            self.__parentName = str(v)

        @property
        def m_offsetMat(self) -> smt.Mat4:
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

        def makeJson(self):
            return {
                "name": self.__name,
                "joints size": len(self.__joints),
                "joints": [xx.makeJson() for xx in self.__joints],
            }

        def newJoint(self, name: str, parent_name: str) -> "Scene.Joint":
            if len(self.__joints) > MAX_JOINT_COUNT:
                raise RuntimeError("the number of joints cannot exceed {}.".format(MAX_JOINT_COUNT))
            if self.__doesNameExist(name):
                raise RuntimeError('tried to add joint "{}" which already exists'.format(name))

            joint = Scene.Joint(name, parent_name)
            self.__joints.append(joint)
            return joint

        def findByName(self, name: str):
            for joint in self.__joints:
                if joint.m_name == name:
                    return joint
            else:
                raise RuntimeError('joint "{}" not found in skeleton "{}"'.format(name, self.__name))

        def assertJointOrder(self) -> None:
            for i, joint in enumerate(self.__joints):
                parent_name = joint.m_parentName
                if "" == parent_name:
                    continue

                for j, parent in enumerate(self.__joints):
                    if parent.m_name == parent_name:
                        if i <= j:
                            raise AssertionError('child joint "{}" is on left of its parent "{}"'.format(
                                joint.m_name, parent_name
                            ))
                        else:
                            break
                else:
                    raise RuntimeError('a joint "{}" has "{}" as its parent, which does not exist'.format(
                        joint.m_name, parent_name
                    ))

        def getVitalJoints(self) -> Set[str]:
            super_parents: Set[str] = set()
            result: Set[str] = set()

            for joint in self.__joints:
                jname = joint.m_name

                if "" == joint.m_parentName:
                    result.add(jname)
                elif joint.m_parentName in super_parents:
                    super_parents.add(jname)
                    result.add(jname)

                #if joint.m_jointType in (Scene.JointType.skirt_root, Scene.JointType.hair_root):
                #    super_parents.add(jname)
                #    result.add(jname)

            return result

        @property
        def m_name(self):
            return self.__name

        @property
        def m_joints(self):
            return self.__joints

        @m_joints.setter
        def m_joints(self, v: List["Scene.Joint"]):
            assert isinstance(v, list)
            for x in v:
                assert isinstance(x, Scene.Joint)

            self.__joints = v

        def __doesNameExist(self, name: str) -> bool:
            for joint in self.__joints:
                if name == joint.m_name:
                    return True

            return False

    class JointKeyframes:
        def __init__(self, joint_name: str):
            self.__name = str(joint_name)
            self.__transform = smt.Mat4()

            self.__poses: List[Tuple[float, smt.Vec3]] = []
            self.__rotates: List[Tuple[float, smt.Quat]] = []
            self.__scales: List[Tuple[float, float]] = []

        def makeJson(self):
            return {
                "name": self.__name,
                "poses size": len(self.__poses),
                "rotates size": len(self.__rotates),
                "scales size": len(self.__scales)
            }

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

        @property
        def m_transform(self):
            return self.__transform

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

        def makeJson(self):
            return {
                "name": self.__name,
                "tick per sec": self.__tickPerSec,
                "joint keyframes size": len(self.__keyframes),
                "joint keyframes": [xx.makeJson() for xx in self.__keyframes],
            }

        def newJoint(self, joint_name: str) -> "Scene.JointKeyframes":
            keyframes = Scene.JointKeyframes(joint_name)
            self.__keyframes.append(keyframes)
            return keyframes

        def cleanUp(self) -> None:
            for joint in self.m_joints:
                joint.cleanUp()

        def removeJoints(self, to_remove_names: Set[str]):
            new_list: List[Scene.JointKeyframes] = []

            for joint in self.__keyframes:
                if joint.m_name not in to_remove_names:
                    new_list.append(joint)

            self.__keyframes = new_list

        def calcDurationTick(self) -> float:
            max_value = 0.0

            for joint in self.m_joints:
                max_value = max(joint.getMaxTimepoint(), max_value)

            return max_value if 0.0 != max_value else 1.0

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

        def makeJson(self):
            return {
                "name": self.m_name,
                "render unit id": self.m_renderUnitID,
            }

    class ILight:
        def __init__(self):
            self.__name = ""
            self.__color = smt.Vec3()
            self.__intensity = 1000.0
            self.__hasShadow = False

        def makeJson(self):
            return {
                "name": self.m_name,
                "color": str(self.m_color),
                "intensity": self.m_intensity,
                "has shadow": self.m_hasShadow,
            }

        @property
        def m_name(self):
            return self.__name

        @m_name.setter
        def m_name(self, value: str):
            self.__name = str(value)

        @property
        def m_color(self):
            return self.__color

        @m_color.setter
        def m_color(self, value: smt.Vec3):
            assert isinstance(value, smt.Vec3)
            self.__color = value

        @property
        def m_intensity(self):
            return self.__intensity

        @m_intensity.setter
        def m_intensity(self, value: float):
            self.__intensity = float(value)

        @property
        def m_hasShadow(self):
            return self.__hasShadow

        @m_hasShadow.setter
        def m_hasShadow(self, value: bool):
            self.__hasShadow = bool(value)

    class PointLight(ILight):
        def __init__(self):
            super().__init__()

            self.__pos = smt.Vec3()
            self.m_maxDistance = 0.0
            self.m_halfIntenseDist = 0.0

        def makeJson(self):
            data = super().makeJson()

            data["pos"] = str(self.m_pos)
            data["max distance"] = self.m_maxDistance
            data["half intensity distance"] = self.m_halfIntenseDist

            return data

        @property
        def m_pos(self):
            return self.__pos

        @m_pos.setter
        def m_pos(self, value: smt.Vec3):
            assert isinstance(value, smt.Vec3)
            self.__pos = value

    class DirectionalLight(ILight):
        def __init__(self):
            super().__init__()

            self.__direction = smt.Vec3()

        def makeJson(self):
            data = super().makeJson()

            data["direction"] = str(self.m_direction)

            return data

        @property
        def m_direction(self):
            return self.__direction

        @m_direction.setter
        def m_direction(self, value: smt.Vec3):
            assert isinstance(value, smt.Vec3)
            self.__direction = value

    class SpotLight(ILight):
        def __init__(self):
            super().__init__()

            self.__pos = smt.Vec3()
            self.m_maxDistance = 0.0
            self.m_halfIntenseDist = 0.0

            self.__direction = smt.Vec3()
            self.m_spotDegree = 0.0
            self.m_spotBlend = 0.0

        def makeJson(self):
            data = super().makeJson()

            data["pos"] = str(self.m_pos)
            data["max distance"] = self.m_maxDistance
            data["half intensity distance"] = self.m_halfIntenseDist

            data["direction"] = str(self.m_direction)
            data["spot degree"] = self.m_spotDegree
            data["spot blend"] = self.m_spotBlend

            return data

        @property
        def m_pos(self):
            return self.__pos

        @m_pos.setter
        def m_pos(self, value: smt.Vec3):
            assert isinstance(value, smt.Vec3)
            self.__pos = value

        @property
        def m_direction(self):
            return self.__direction

        @m_direction.setter
        def m_direction(self, value: smt.Vec3):
            assert isinstance(value, smt.Vec3)
            self.__direction = value


    def __init__(self):
        self.m_render_units: Dict[int, Scene.RenderUnit] = {}
        self.m_static_actors: List[Scene.StaticActor] = []
        self.m_skeletons: List[Scene.Skeleton] = []
        self.m_animations: List[Scene.Animation] = []

        self.m_plights: List[Scene.PointLight] = []
        self.m_dlights: List[Scene.DirectionalLight] = []
        self.m_slights: List[Scene.SpotLight] = []

        # Tuple(name, reason)
        self.m_skipped_objs: List[Tuple[str, str]] = []

    def makeJson(self):
        data = {
            "render units size": len(self.m_render_units),
            "render units": [xx.makeJson() for xx in self.m_render_units.values()],

            "static actors size": len(self.m_static_actors),
            "static actors": [xx.makeJson() for xx in self.m_static_actors],

            "skeletons size": len(self.m_skeletons),
            "skeletons": [xx.makeJson() for xx in self.m_skeletons],

            "animations size": len(self.m_animations),
            "animations": [xx.makeJson() for xx in self.m_animations],

            "point lights size": len(self.m_plights),
            "point lights": [xx.makeJson() for xx in self.m_plights],

            "directional lights size": len(self.m_dlights),
            "directional lights": [xx.makeJson() for xx in self.m_dlights],

            "spot lights size": len(self.m_slights),
            "spot lights": [xx.makeJson() for xx in self.m_slights],
        }

        skipped_list = {}
        for obj_name, reason in self.m_skipped_objs:
            skipped_list[obj_name] = reason
        data["skipped"] = skipped_list

        return data

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

    def imageNames(self) -> Set[str]:
        img_names = set()

        for unit in self.m_render_units.values():
            img_names.add(unit.m_material.m_albedoMap)
            img_names.add(unit.m_material.m_roughnessMap)
            img_names.add(unit.m_material.m_metallicMap)
            img_names.add(unit.m_material.m_normalMap)

        try:
            img_names.remove("")
        except KeyError:
            pass

        return img_names
