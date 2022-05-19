import enum
import array
from typing import List, Dict, Union, Set, Tuple

from . import byteutils as byt
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
        output["transform"] = self.__transform.make_json()
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


class Vertex:
    def __init__(self):
        self.__pos = smt.Vec3()
        self.__uv_coord = smt.Vec2()
        self.__normal = smt.Vec3()
        self.__joints: List[Tuple[float, int]] = []

    def add_joint(self, joint_index: int, weight: float) -> None:
        joint_index = int(joint_index)
        weight = float(weight)

        if 0.0 == weight:
            return
        if self.__has_joint_index(joint_index):
            raise RuntimeError()

        self.__joints.append((weight, joint_index))
        self.__joints.sort(reverse=True)

    @property
    def position(self):
        return self.__pos

    @position.setter
    def position(self, value):
        assert isinstance(value, smt.Vec3)
        self.__pos = value

    @property
    def uv_coord(self):
        return self.__uv_coord

    @uv_coord.setter
    def uv_coord(self, value):
        assert isinstance(value, smt.Vec2)
        self.__uv_coord = value

    @property
    def normal(self):
        return self.__normal

    @normal.setter
    def normal(self, value):
        assert isinstance(value, smt.Vec3)
        self.__normal = value

    @property
    def joints(self):
        return self.__joints

    def __has_joint_index(self, joint_index: int):
        for j_weight, j_index in self.__joints:
            if j_index == joint_index:
                return True
        return False


class VertexBuffer:
    def __init__(self):
        self.__vertices: List[Vertex] = []

    def make_json(self, output: Dict, bin_arr: BinaryArrayBuilder):
        positions, uv_coordinates, normals = self.__make_arrays()
        joints = self.__make_joints_binary_array()

        binary_arrays = [
            (positions.tobytes(), "vertices binary data"),
            (uv_coordinates.tobytes(), "uv coordinates binary data"),
            (normals.tobytes(), "normals binary data"),
            (joints, "joints binary data"),
        ]

        output["vertex count"] = len(self.__vertices)
        for binary_data, field_name in binary_arrays:
            pos, size = bin_arr.add_bin_array(binary_data)
            output[field_name] = {
                "position": pos,
                "size": size,
            }

    def add_vertex(self, position: smt.Vec3, uv_coord: smt.Vec2, normal: smt.Vec3):
        vertex = Vertex()
        vertex.position = position
        vertex.uv_coord = uv_coord
        vertex.normal = normal
        self.__vertices.append(vertex)
        return vertex

    def __make_arrays(self):
        positions = array.array("f")
        uv_coordinates = array.array("f")
        normals = array.array("f")

        for v in self.__vertices:
            positions.append(v.position.x)
            positions.append(v.position.y)
            positions.append(v.position.z)

            uv_coordinates.append(v.uv_coord.x)
            uv_coordinates.append(v.uv_coord.y)

            normals.append(v.normal.x)
            normals.append(v.normal.y)
            normals.append(v.normal.z)

        return positions, uv_coordinates, normals

    def __make_joints_binary_array(self) -> bytearray:
        output = bytearray()
        for v in self.__vertices:
            output += byt.to_int32(len(v.joints))
            for j_weight, j_index in v.joints:
                output += byt.to_int32(j_index)
                output += byt.to_float32(j_weight)
        return output


def _make_mangled_mesh_name(mesh_name: str, material_name: str):
    return f"{mesh_name}+{material_name}"


class Mesh:
    def __init__(self):
        self.__name = ""
        self.__skeleton_name = ""
        self.__vertices: Dict[str, VertexBuffer] = {}

    def make_json(self, output: List[Dict], bin_arr: BinaryArrayBuilder):
        for material_name, vertex_buffer in self.__vertices.items():
            output.append({
                "name": _make_mangled_mesh_name(self.name, material_name),
                "skeleton name": self.skeleton_name,
            })
            vertex_buffer.make_json(output[-1], bin_arr)

    def add_vertex(self, material_name: str, position: smt.Vec3, uv_coord: smt.Vec2, normal: smt.Vec3):
        if material_name not in self.__vertices.keys():
            self.__vertices[material_name] = VertexBuffer()

        return self.__vertices[material_name].add_vertex(position, uv_coord, normal)

    @property
    def vertex_buffers(self):
        return self.__vertices.items()

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = str(value)

    @property
    def skeleton_name(self):
        return self.__skeleton_name

    @skeleton_name.setter
    def skeleton_name(self, value: str):
        self.__skeleton_name = str(value)


class Material:
    def __init__(self):
        self.__name = ""

        self.__roughness = 0.5
        self.__metallic = 0.0
        self.__transparency = False

        self.__albedo_map = ""
        self.__roughness_map = ""
        self.__metallic_map = ""
        self.__normal_map = ""

    def is_same(self, other: "Material") -> bool:
        return (
            self.roughness == other.roughness
            and self.metallic == other.metallic
            and self.transparency == other.transparency
            and self.albedo_map == other.albedo_map
            and self.roughness_map == other.roughness_map
            and self.metallic_map == other.metallic_map
            and self.normal_map == other.normal_map
        )

    def make_json(self):
        return {
            "name": self.name,
            "roughness": self.roughness,
            "metallic": self.metallic,
            "transparency": self.transparency,
            "albedo map": self.albedo_map,
            "roughness map": self.roughness_map,
            "metallic map": self.metallic_map,
            "normal map": self.normal_map,
        }

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = str(value)

    @property
    def roughness(self):
        return self.__roughness

    @roughness.setter
    def roughness(self, value):
        self.__roughness = float(value)

    @property
    def metallic(self):
        return self.__metallic

    @metallic.setter
    def metallic(self, value):
        self.__metallic = float(value)

    @property
    def transparency(self):
        return self.__transparency

    @transparency.setter
    def transparency(self, value):
        self.__transparency = bool(value)

    @property
    def albedo_map(self):
        return self.__albedo_map

    @albedo_map.setter
    def albedo_map(self, value):
        self.__albedo_map = str(value)

    @property
    def roughness_map(self):
        return self.__roughness_map

    @roughness_map.setter
    def roughness_map(self, value):
        self.__roughness_map = str(value)

    @property
    def metallic_map(self):
        return self.__metallic_map

    @metallic_map.setter
    def metallic_map(self, value):
        self.__metallic_map = str(value)

    @property
    def normal_map(self):
        return self.__normal_map

    @normal_map.setter
    def normal_map(self, value):
        self.__normal_map = str(value)


class JointType(enum.Enum):
    basic = "basic"
    hair_root = "dal_phy_hairRoot"
    skirt_root = "dal_phy_skirtRoot"


class SkelJoint:
    def __init__(self, name: str):
        self.__name = str(name)
        self.__parent_name = ""
        self.__type = JointType.basic
        self.__offset_mat = smt.Mat4x4()

    def make_json(self):
        return {
            "name": self.name,
            "parent name": self.parent_name,
            "joint type": self.joint_type.name,
            "offset matrix": self.offset_mat.make_json(),
        }

    @property
    def name(self):
        return self.__name

    @property
    def parent_name(self):
        return self.__parent_name

    @parent_name.setter
    def parent_name(self, value):
        self.__parent_name = str(value)

    @property
    def joint_type(self):
        return self.__type

    @joint_type.setter
    def joint_type(self, value):
        assert isinstance(value, JointType)
        self.__type = value

    @property
    def offset_mat(self):
        return self.__offset_mat


class Skeleton:
    def __init__(self, name: str):
        self.__name = str(name)
        self.__joints: List[SkelJoint] = []

    def make_json(self):
        return {
            "name": self.name,
            "joints": [xx.make_json() for xx in self.__joints],
        }

    def new_joint(self, name: str) -> SkelJoint:
        if self.__does_joint_name_exist(name):
            raise RuntimeError(f'Trying to add a joint "{name}", which already exists in skeleton "{self.name}"')

        self.__joints.append(SkelJoint(name))
        return self.__joints[-1]

    def make_name_index_map(self):
        output = dict()
        for i, joint in enumerate(self.__joints):
            output[joint.name] = i
        return output

    @property
    def name(self):
        return self.__name

    def __does_joint_name_exist(self, name: str):
        name = str(name)
        for joint in self.__joints:
            if joint.name == name:
                return True
        return False


class MeshActor(IActor):
    def __init__(self):
        super().__init__()

        self.__mesh_name = ""

    def make_json(self, meshes: List[Mesh]):
        output = {}
        IActor.insert_json(self, output)
        output["render pairs"] = self.__make_render_pairs(meshes)
        return output

    @property
    def mesh_name(self):
        return self.__mesh_name

    @mesh_name.setter
    def mesh_name(self, value):
        self.__mesh_name = str(value)

    def __make_render_pairs(self, meshes: List[Mesh]) -> List[Dict]:
        for x in meshes:
            if x.name == self.mesh_name:
                selected_mesh = x
                break
        else:
            raise RuntimeError()

        output: List[Dict] = []
        for mat_name, vert_buf in selected_mesh.vertex_buffers:
            output.append({
                "mesh name": _make_mangled_mesh_name(selected_mesh.name, mat_name),
                "material name": mat_name,
            })
        return output


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
        self.__name = ""

        self.__meshes: List[Mesh] = []
        self.__materials: List[Material] = []
        self.__skeletons: List[Skeleton] = []

        self.__mesh_actors: List[MeshActor] = []
        self.__dlights: List[DirectionalLight] = []
        self.__plights: List[PointLight] = []
        self.__slights: List[Spotlight] = []

    def make_json(self, bin_arr: BinaryArrayBuilder) -> Dict:
        return {
            "name": self.name,
            "meshes": self.__make_json_for_meshes(bin_arr),
            "materials": [xx.make_json() for xx in self.__materials],
            "skeletons": [xx.make_json() for xx in self.__skeletons],
            "mesh actors": [xx.make_json(self.__meshes) for xx in self.__mesh_actors],
            "directional lights": [xx.make_json() for xx in self.__dlights],
            "point lights": [xx.make_json() for xx in self.__plights],
            "spotlights": [xx.make_json() for xx in self.__slights],
        }

    def get_texture_names(self) -> Set[str]:
        output = set()

        for material in self.__materials:
            output.add(material.albedo_map)
            output.add(material.roughness_map)
            output.add(material.metallic_map)
            output.add(material.normal_map)

        try:
            output.remove("")
        except KeyError:
            pass

        return output

    def find_mesh_by_name(self, name: str):
        for mesh in self.__meshes:
            if str(name) == mesh.name:
                return mesh

        raise KeyError(f"Mesh named '{name}' does not exist")

    def find_material_by_name(self, name: str):
        for material in self.__materials:
            if str(name) == material.name:
                return material

        raise KeyError(f"Material named '{name}' does not exist")

    def find_skeleton_by_name(self, name: str):
        if not name:
            raise ValueError(f"Invalid skeleton name: {name}")

        for x in self.__skeletons:
            if str(name) == x.name:
                return x

        raise KeyError(f"Skeleton named '{name}' does not exist")

    def has_material(self, name: str):
        try:
            self.find_material_by_name(name)
        except KeyError:
            return False
        else:
            return True

    def has_skeleton(self, name: str):
        try:
            self.find_skeleton_by_name(name)
        except KeyError:
            return False
        else:
            return True

    def add_material(self, material: Material):
        try:
            found_mat = self.find_material_by_name(material.name)
        except KeyError:
            self.__materials.append(material)
        else:
            if not found_mat.is_same(material):
                raise RuntimeError()

    def new_skeleton(self, name):
        if self.has_skeleton(name):
            raise RuntimeError()

        x = Skeleton(name)
        self.__skeletons.append(x)
        return x

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

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = str(value)

    def __make_json_for_meshes(self, bin_arr: BinaryArrayBuilder):
        output = []
        for mesh in self.__meshes:
            mesh.make_json(output, bin_arr)
        return output

    def __find_mesh_actor_by_name(self, name: str):
        for x in self.__mesh_actors:
            if x.name == str(name):
                return x

        raise KeyError(f"Mesh actor named '{name}' does not exist")
