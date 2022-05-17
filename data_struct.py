import array
from typing import List, Dict, Union

import numpy as np

from . import smalltype as smt


class BinaryArrayBuilder:
    def __init__(self):
        self.__data = bytearray()

    @property
    def data(self):
        return bytes(self.__data)

    def add_bin_array(self, arr: Union[bytes, bytearray]):
        start_index = len(self.__data)
        self.__data += arr
        end_index = len(self.__data)
        return start_index, end_index - start_index


class IActor:
    def __init__(self):
        self.__name = ""
        self.__parent_name = ""
        self.__collections: List[str] = []
        self.__transform = smt.Transform()
        self.__hidden = False

    def insert_json(self, output: Dict) -> None:
        output["name"] = self.name
        output["parent name"] = self.parent_name
        output["collections"] = self.collections
        output["transform"] = self.__transform.makeJson()
        output["hidden"] = self.hidden

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = str(value)

    @property
    def parent_name(self):
        return self.__parent_name

    @parent_name.setter
    def parent_name(self, value: str):
        self.__parent_name = str(value)

    @property
    def collections(self):
        return self.__collections

    @property
    def pos(self):
        return self.__transform.m_pos

    @pos.setter
    def pos(self, value: smt.Vec3):
        self.__transform.m_pos = value

    @property
    def quat(self):
        return self.__transform.m_rotate

    @quat.setter
    def quat(self, value: smt.Quat):
        self.__transform.m_rotate = value

    @property
    def hidden(self):
        return self.__hidden

    @hidden.setter
    def hidden(self, value: bool):
        self.__hidden = bool(value)


class VertexBuffer:
    def __init__(self):
        self.__positions = array.array("f")
        self.__uv_coordinates = array.array("f")
        self.__normals = array.array("f")

    def make_json(self, bin_arr: BinaryArrayBuilder):
        v = np.array(self.__positions, dtype=np.float32).tobytes()
        t = np.array(self.__uv_coordinates, dtype=np.float32).tobytes()
        n = np.array(self.__normals, dtype=np.float32).tobytes()

        v_pos, v_size = bin_arr.add_bin_array(v)
        t_pos, t_size = bin_arr.add_bin_array(t)
        n_pos, n_size = bin_arr.add_bin_array(n)

        return {
            "vertices binary data": {
                "position": v_pos,
                "size": v_size,
            },
            "uv coordinates binary data": {
                "position": t_pos,
                "size": t_size,
            },
            "normals binary data": {
                "position": n_pos,
                "size": n_size,
            },
        }

    def add_vertex(self, position: smt.Vec3, uv_coord: smt.Vec2, normal: smt.Vec3):
        self.__positions.append(position.x)
        self.__positions.append(position.y)
        self.__positions.append(position.z)

        self.__uv_coordinates.append(uv_coord.x)
        self.__uv_coordinates.append(uv_coord.y)

        self.__normals.append(normal.x)
        self.__normals.append(normal.y)
        self.__normals.append(normal.z)


class Mesh:
    def __init__(self):
        self.__name = ""
        self.__vertices: Dict[str, VertexBuffer] = {}

    def make_json(self, bin_arr: BinaryArrayBuilder):
        output = {
            "name": self.name,
            "vertices": [],
        }

        for k, v in self.__vertices.items():
            output["vertices"].append(v.make_json(bin_arr))
            output["vertices"][-1]["material name"] = k

        return output

    def add_vertex(self, material_name: str, position: smt.Vec3, uv_coord: smt.Vec2, normal: smt.Vec3):
        if material_name not in self.__vertices.keys():
            self.__vertices[material_name] = VertexBuffer()
        self.__vertices[material_name].add_vertex(position, uv_coord, normal)

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = str(value)


class Material:
    def __init__(self):
        pass


class MeshActor(IActor):
    def __init__(self):
        super().__init__()

        self.__mesh_name = ""

    def make_json(self):
        output = {
            "mesh name": self.mesh_name,
        }

        IActor.insert_json(self, output)
        return output

    @property
    def mesh_name(self):
        return self.__mesh_name

    @mesh_name.setter
    def mesh_name(self, value):
        self.__mesh_name = str(value)


class ILight:
    def __init__(self):
        self.__color = smt.Vec3(1, 1, 1)
        self.__intensity = 1000.0
        self.__has_shadow = False

    def insert_json(self, output: Dict) -> None:
        output["color"] = self.color.xyz
        output["intensity"] = self.intensity
        output["has shadow"] = self.has_shadow

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, value: smt.Vec3):
        assert isinstance(value, smt.Vec3)
        self.__color = value

    @property
    def intensity(self):
        return self.__intensity

    @intensity.setter
    def intensity(self, value: float):
        self.__intensity = float(value)

    @property
    def has_shadow(self):
        return self.__has_shadow

    @has_shadow.setter
    def has_shadow(self, value: bool):
        self.__has_shadow = bool(value)


class DirectionalLight(IActor, ILight):
    def __init__(self):
        IActor.__init__(self)
        ILight.__init__(self)

    def make_json(self) -> Dict:
        output = {}

        IActor.insert_json(self, output)
        ILight.insert_json(self, output)
        return output


class PointLight(IActor, ILight):
    def __init__(self):
        IActor.__init__(self)
        ILight.__init__(self)

        self.__max_distance = 0.0
        self.__half_intense_distance = 0.0

    def make_json(self) -> Dict:
        output = {
           "max distance": self.max_distance,
           "half intense distance": self.half_intense_distance,
        }

        IActor.insert_json(self, output)
        ILight.insert_json(self, output)
        return output

    @property
    def max_distance(self):
        return self.__max_distance

    @max_distance.setter
    def max_distance(self, value: float):
        self.__max_distance = float(value)

    @property
    def half_intense_distance(self):
        return self.__half_intense_distance

    @half_intense_distance.setter
    def half_intense_distance(self, value: float):
        self.__half_intense_distance = float(value)


class Spotlight(PointLight):
    def __init__(self):
        super().__init__()

        self.__spot_degree = 0.0
        self.__spot_blend = 0.0

    def make_json(self) -> Dict:
        output = PointLight.make_json(self)

        output["spot degree"] = self.__spot_degree
        output["spot blend"] = self.__spot_blend

        return output

    @property
    def spot_degree(self):
        return self.__spot_degree

    @spot_degree.setter
    def spot_degree(self, value: float):
        self.__spot_degree = float(value)

    @property
    def spot_blend(self):
        return self.__spot_blend

    @spot_blend.setter
    def spot_blend(self, value: float):
        self.__spot_blend = float(value)


class Scene:
    def __init__(self):
        self.__meshes: List[Mesh] = []
        self.__materials: List[Material] = []

        self.__mesh_actors: List[MeshActor] = []
        self.__dlights: List[DirectionalLight] = []
        self.__plights: List[PointLight] = []
        self.__slights: List[Spotlight] = []

    def make_json(self, bin_arr: BinaryArrayBuilder) -> Dict:
        return {
            "meshes": [xx.make_json(bin_arr) for xx in self.__meshes],
            "mesh actors": [xx.make_json() for xx in self.__mesh_actors],
            "directional lights": [xx.make_json() for xx in self.__dlights],
            "point lights": [xx.make_json() for xx in self.__plights],
            "spotlights": [xx.make_json() for xx in self.__slights],
        }

    def find_mesh_by_name(self, name: str):
        for mesh in self.__meshes:
            if name == mesh.name:
                return mesh

        raise KeyError(f"Mesh named '{name}' does not exist")

    def new_mesh(self):
        mesh = Mesh()
        self.__meshes.append(mesh)
        return mesh

    def new_mesh_actor(self):
        mesh = MeshActor()
        self.__mesh_actors.append(mesh)
        return mesh

    def new_dlight(self):
        light = DirectionalLight()
        self.__dlights.append(light)
        return light

    def new_plight(self):
        light = PointLight()
        self.__plights.append(light)
        return light

    def new_slight(self):
        light = Spotlight()
        self.__slights.append(light)
        return light

    def check_validity(self):
        if not self.__do_all_parents_exist():
            return False

        return True

    def __find_mesh_actor_by_name(self, name: str):
        for x in self.__mesh_actors:
            if x.name == name:
                return x

        raise KeyError(f"Mesh actor named '{name}' does not exist")

    def __do_all_parents_exist(self):
        for x in self.__mesh_actors:
            try:
                self.__find_mesh_actor_by_name(x.parent_name)
            except KeyError:
                return False

        return True
