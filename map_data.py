from typing import Dict

from . import smalltype as smt
from . import rawdata as rwd


class Level:
    class MapChunk:
        def __init__(self, scene: rwd.Scene):
            assert isinstance(scene, rwd.Scene)
            self.__data: rwd.Scene = scene

            self.__aabb = smt.AABB3()
            self.__offsetPos = smt.Vec3()

            self.__updateAABB()

        @property
        def m_data(self):
            return self.__data

        @property
        def m_offset(self):
            return self.__offsetPos

        @property
        def m_aabb(self):
            return self.__aabb

        def __updateAABB(self) -> None:
            for actor in self.__data.m_static_actors:
                unit = self.__data.m_render_units[actor.m_renderUnitID]
                mesh_aabb = unit.m_mesh.makeAABB()
                p0 = actor.m_transform.transform(mesh_aabb.m_min)
                p1 = actor.m_transform.transform(mesh_aabb.m_max)
                self.__aabb.resizeToContain(p0.x, p0.y, p0.z)
                self.__aabb.resizeToContain(p1.x, p1.y, p1.z)


    def __init__(self, scenes: Dict[str, rwd.Scene]):
        self.__data: Dict[str, Level.MapChunk] = {}

        self.__fetch(scenes)

    def __len__(self):
        return len(self.__data)

    def items(self):
        return self.__data.items()

    def __fetch(self, scenes: Dict[str, rwd.Scene]) -> None:
        for name, scene in scenes.items():
            self.__data[name] = Level.MapChunk(scene)
