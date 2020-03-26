from typing import Dict, List, Tuple, Callable

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

        def addVertex(self, data: "Scene.VertexData") -> None:
            self.__vertices.append(data)

        def vertices(self):
            return iter(self.__vertices)

        def size(self) -> int:
            return len(self.__vertices)

    class RenderUnit:
        def __init__(self):
            self.m_ref_count = 0
            self.m_material = Scene.Material()
            self.m_mesh = Scene.Mesh()

    class StaticActor:
        def __init__(self):
            self.m_name = ""
            self.m_renderUnitID = 0


    def __init__(self):
        self.m_render_units: Dict[int, Scene.RenderUnit] = {}
        self.m_static_actors: List[Scene.StaticActor] = []

        # Tuple(name, reason)
        self.m_skipped_objs: List[Tuple[str, str]] = []

    def printInfo(self, println: Callable) -> None:
        for uid, unit in self.m_render_units.items():
            println('[DAL] Render unit{{ id={}, ref_count={}, verts={} }}'.format(
                uid, unit.m_ref_count, unit.m_mesh.size()))
        for actor in self.m_static_actors:
            println('[DAL] Static actor{{ name="{}", uid={} }}'.format(actor.m_name, actor.m_renderUnitID))
        for name, reason in self.m_skipped_objs:
            println('[DAL] Skipped {{ name="{}", reason="{}" }}'.format(name, reason))
