from typing import Dict

from . import byteutils as byt
from . import smalltype as smt
from . import rawdata as rwd


class _WorldInfo:
    class MapChunkData:
        def __init__(self, scene: rwd.Scene):
            self.__aabb = smt.AABB3()

            self.__fetch(scene)

        def makeBinary(self) -> bytearray:
            result = bytearray()

            result += byt.to_float32(self.__aabb.m_min.x)
            result += byt.to_float32(self.__aabb.m_min.y)
            result += byt.to_float32(self.__aabb.m_min.z)
            result += byt.to_float32(self.__aabb.m_max.x)
            result += byt.to_float32(self.__aabb.m_max.y)
            result += byt.to_float32(self.__aabb.m_max.z)

            return result

        def __fetch(self, scene: rwd.Scene) -> None:
            for actor in scene.m_static_actors:
                unit = scene.m_render_units[actor.m_renderUnitID]
                mesh_aabb = unit.m_mesh.makeAABB()
                p0 = actor.m_transform.transform(mesh_aabb.m_min)
                p1 = actor.m_transform.transform(mesh_aabb.m_max)
                self.__aabb.resizeToContain(p0.x, p0.y, p0.z)
                self.__aabb.resizeToContain(p1.x, p1.y, p1.z)


    def __init__(self, scenes: Dict[str, rwd.Scene]):
        self.__data: Dict[str, _WorldInfo.MapChunkData] = {}

        self.__fetch(scenes)

    def buildBinary(self) -> bytearray:
        result = bytearray()

        result += byt.to_int32(len(self.__data))

        for name, scene in self.__data.items():
            result += byt.to_nullTerminated(name)
            result += scene.makeBinary()

        return result

    def __fetch(self, scenes: Dict[str, rwd.Scene]) -> None:
        for name, scene in scenes.items():
            self.__data[name] = self.MapChunkData(scene)


def make_binary_dlb(scenes: Dict[str, rwd.Scene]) -> bytearray:
    world_info = _WorldInfo(scenes)
    return world_info.buildBinary()
