from typing import Dict, List, Tuple, Callable, Iterator
import enum

from . import smalltype as smt


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
            joint = Scene.Joint(name, parent_name)
            self.__joints.append(joint)
            return joint

        @property
        def m_name(self):
            return self.__name

    class StaticActor:
        def __init__(self):
            self.m_name = ""
            self.m_renderUnitID = 0


    def __init__(self):
        self.m_render_units: Dict[int, Scene.RenderUnit] = {}
        self.m_static_actors: List[Scene.StaticActor] = []
        self.m_skeletons: List[Scene.Skeleton] = []

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
                println('\t{}'.format(joint))
        for name, reason in self.m_skipped_objs:
            println('[DAL] Skipped {{ name="{}", reason="{}" }}'.format(name, reason))
