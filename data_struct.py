import enum
import array
import struct
from typing import List, Dict, Union, Tuple, Any, Set

from . import byteutils as byt
from . import smalltype as smt


class NameRegistry:
    def __init__(self):
        self.__registry: Dict[str, Any] = {}

    def register(self, obj: Any, name: str):
        if name in self.__registry.keys():
            if obj != self.__registry[name]:
                raise RuntimeError(f'Name collision: "{name}" between {self.__registry[name]}, {obj}')
            else:
                return
        else:
            self.__registry[name] = obj


class BinaryArrayBuilder:
    def __init__(self):
        self.__data = bytearray()

    @property
    def data(self):
        return bytes(self.__data)

    @property
    def size(self):
        return len(self.__data)

    def add_int16(self, value: int):
        self.__data += struct.pack("<h", int(value))

    def add_int32(self, value: int):
        self.__data += struct.pack("<i", int(value))

    def add_float32(self, value: float):
        self.__data += struct.pack("<f", float(value))

    # Null terminated string
    def add_str(self, value: str):
        self.__data += value.encode("utf-8")
        self.__data += b"\0"

    def add_bin_array(self, arr: Union[bytes, bytearray]):
        start_index = len(self.__data)
        self.__data += arr
        end_index = len(self.__data)
        return start_index, end_index - start_index


class IActor:
    def __init__(self, name_reg: NameRegistry):
        self.__name = ""
        self.__parent_name = ""
        self.__collections: List[str] = []
        self.__transform = smt.Transform()
        self.__hidden = False

        self.__name_reg = name_reg

    def insert_json(self, output: Dict) -> None:
        output["name"] = self.name
        output["parent name"] = self.parent_name
        output["collections"] = self.__collections
        output["transform"] = self.__transform.make_json()
        output["hidden"] = self.hidden

    def add_collection_name(self, collection_name: str):
        self.__collections.append(str(collection_name))

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name_reg.register(self, value)
        self.__name = str(value)

    @property
    def parent_name(self):
        return self.__parent_name

    @parent_name.setter
    def parent_name(self, value: str):
        self.__parent_name = str(value)

    @property
    def transform(self):
        return self.__transform

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
    def scale(self):
        return self.__transform.m_scale

    @scale.setter
    def scale(self, value):
        self.__transform.m_scale = value

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
        self.__tangent = smt.Vec3()
        self.__bitangent_sign = 1.0
        self.__joints: List[Tuple[float, int]] = []

    def add_joint(self, joint_index: int, weight: float) -> None:
        self.__joints.append((float(weight), int(joint_index)))

    def sort_joints(self):
        self.__joints.sort(reverse=True)

    @property
    def position(self):
        return self.__pos

    @property
    def uv_coord(self):
        return self.__uv_coord

    @property
    def normal(self):
        return self.__normal

    @property
    def tangent(self):
        return self.__tangent

    @property
    def bitangent_sign(self):
        return self.__bitangent_sign

    @bitangent_sign.setter
    def bitangent_sign(self, value: float):
        self.__bitangent_sign = float(value)

    @property
    def joints(self):
        return iter(self.__joints)

    @property
    def joint_count(self):
        return len(self.__joints)


class VertexBuffer:
    def __init__(self):
        self.__vertices: List[Vertex] = []

    def make_json(self, output: Dict, bin_arr: BinaryArrayBuilder):
        positions, uv_coordinates, normals, tangents = self.__make_arrays()
        joints = self.__make_joints_binary_array()

        binary_arrays = [
            (positions.tobytes(), "vertices binary data"),
            (uv_coordinates.tobytes(), "uv coordinates binary data"),
            (normals.tobytes(), "normals binary data"),
            (tangents.tobytes(), "tangents binary data"),
            (joints, "joints binary data"),
        ]

        output["vertex count"] = len(self.__vertices)
        for binary_data, field_name in binary_arrays:
            pos, size = bin_arr.add_bin_array(binary_data)
            output[field_name] = {
                "position": pos,
                "size": size,
            }

    def new_vertex(self):
        vertex = Vertex()
        self.__vertices.append(vertex)
        return vertex

    def __make_arrays(self):
        positions = array.array("f")
        uv_coordinates = array.array("f")
        normals = array.array("f")
        tangents = array.array("f")

        for v in self.__vertices:
            positions.append(v.position.x)
            positions.append(v.position.y)
            positions.append(v.position.z)

            uv_coordinates.append(v.uv_coord.x)
            uv_coordinates.append(v.uv_coord.y)

            normals.append(v.normal.x)
            normals.append(v.normal.y)
            normals.append(v.normal.z)

            tangents.append(v.tangent.x)
            tangents.append(v.tangent.y)
            tangents.append(v.tangent.z)
            tangents.append(v.bitangent_sign)

        return positions, uv_coordinates, normals, tangents

    def __make_joints_binary_array(self) -> bytearray:
        output = bytearray()
        for v in self.__vertices:
            v.sort_joints()
            output += byt.to_int32(v.joint_count)
            for j_weight, j_index in v.joints:
                output += byt.to_int32(j_index)
                output += byt.to_float32(j_weight)
        return output


class Mesh:
    def __init__(self):
        self.__name = ""
        self.__skeleton_name = ""
        self.__vertices: Dict[str, VertexBuffer] = {}

    def make_json(self, output: List[Dict], bin_arr: BinaryArrayBuilder):
        for material_name, vertex_buffer in self.__vertices.items():
            output.append({
                "name": self.get_mangled_name(material_name),
                "skeleton name": self.skeleton_name,
            })
            vertex_buffer.make_json(output[-1], bin_arr)

    def new_vertex(self, material_name: str):
        if material_name not in self.__vertices.keys():
            self.__vertices[material_name] = VertexBuffer()

        return self.__vertices[material_name].new_vertex()

    def get_mangled_name(self, material_name: str):
        if 1 == len(self.__vertices.keys()):
            return self.name
        else:
            return self.__make_mangled_mesh_name(material_name)

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

    def __make_mangled_mesh_name(self, material_name: str):
        return f"{self.name}+{material_name}"


class Material:
    def __init__(self):
        self.__name = ""

        self.__roughness = 0.5
        self.__metallic = 0.0

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
        return False

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
    basic = 0
    hair_root = 1
    skirt_root = 2


JOINT_TYPE_MAP: Dict[JointType, str] = {
    JointType.hair_root: "dal_phy_hairRoot",
    JointType.skirt_root: "dal_phy_skirtRoot",
}


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
            "joint type": self.joint_type.value,
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
        self.__transform = smt.Transform()
        self.__joints: List[SkelJoint] = []

    def make_json(self):
        return {
            "name": self.name,
            "transform": self.transform.make_json(),
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

    @property
    def transform(self):
        return self.__transform

    def __does_joint_name_exist(self, name: str):
        name = str(name)
        for joint in self.__joints:
            if joint.name == name:
                return True
        return False


class _TimePointDict:
    def __init__(self):
        self.__data: Dict[float, Dict[int, float]] = {}

    def get_triplet_count(self):
        count = 0
        for time_point, channels in self.__data.items():
            count += len(channels)
        return count

    # (time_point, channel, value)
    def iter_triplets(self):
        for time_point, channels in self.__data.items():
            for ch, v in channels.items():
                yield time_point, ch, v

    def add(self, time_point: float, channel: int, value: float):
        assert isinstance(time_point, float)
        assert isinstance(channel, int)
        assert isinstance(value, float)

        if time_point not in self.__data.keys():
            self.__data[time_point] = {}
        self.__data[time_point][channel] = value


class AnimJoint:
    def __init__(self):
        # Channels for a pos and scale are x=0, y=1, z=2
        # For a quat, w=0, x=1, y=2, z=3
        self.__positions = _TimePointDict()
        self.__rotations = _TimePointDict()
        self.__scales = _TimePointDict()

    @property
    def positions(self):
        return self.__positions

    @property
    def rotations(self):
        return self.__rotations

    @property
    def scales(self):
        return self.__scales


class Animation:
    def __init__(self, name: str, ticks_per_sec: float):
        self.__name = str(name)
        self.__ticks_per_sec = float(ticks_per_sec)
        self.__joints: Dict[str, AnimJoint] = {}

    def make_json(self, bin_arr: BinaryArrayBuilder):
        begin = bin_arr.size

        bin_arr.add_int32(len(self.__joints))
        for joint_name, joint in self.__joints.items():
            bin_arr.add_str(joint_name)

            bin_arr.add_int32(joint.positions.get_triplet_count())
            for time_point, channel, value in joint.positions.iter_triplets():
                bin_arr.add_float32(time_point)
                bin_arr.add_int16(channel)
                bin_arr.add_float32(value)

            bin_arr.add_int32(joint.rotations.get_triplet_count())
            for time_point, channel, value in joint.rotations.iter_triplets():
                bin_arr.add_float32(time_point)
                bin_arr.add_int16(channel)
                bin_arr.add_float32(value)

            bin_arr.add_int32(joint.scales.get_triplet_count())
            for time_point, channel, value in joint.scales.iter_triplets():
                bin_arr.add_float32(time_point)
                bin_arr.add_int16(channel)
                bin_arr.add_float32(value)

        end = bin_arr.size

        return {
            "name": self.name,
            "ticks per seconds": self.__ticks_per_sec,
            "joints data loc": begin,
            "joints data size": end - begin,
        }

    def add(self, joint_name: str, var_name: str, time_point: float, channel: int, value: float):
        joint_name = str(joint_name)
        var_name = str(var_name)

        if joint_name not in self.__joints.keys():
            self.__joints[joint_name] = AnimJoint()

        if "location" == var_name:
            self.__joints[joint_name].positions.add(time_point, channel, value)
        elif "rotation_quaternion" == var_name:
            self.__joints[joint_name].rotations.add(time_point, channel, value)
        elif "scale" == var_name:
            self.__joints[joint_name].scales.add(time_point, channel, value)
        else:
            raise RuntimeError(f'[DAL] WARN::Unknown variable for a joint: "{var_name}"')

    @property
    def name(self):
        return self.__name


class MeshActor(IActor):
    def __init__(self, name_reg: NameRegistry):
        super().__init__(name_reg)

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
        if "" == self.mesh_name:
            return []

        for x in meshes:
            if x.name == self.mesh_name:
                selected_mesh = x
                break
        else:
            raise RuntimeError(f'A mesh actor "{self.name}" failed to find a mesh named "{self.mesh_name}"')

        output: List[Dict] = []
        for mat_name, vert_buf in selected_mesh.vertex_buffers:
            output.append({
                "mesh name": selected_mesh.get_mangled_name(mat_name),
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
    def __init__(self, name_reg: NameRegistry):
        IActor.__init__(self, name_reg)
        ILight.__init__(self)

    def make_json(self) -> Dict:
        output = {}

        IActor.insert_json(self, output)
        ILight.insert_json(self, output)
        return output


class PointLight(IActor, ILight):
    def __init__(self, name_reg: NameRegistry):
        IActor.__init__(self, name_reg)
        ILight.__init__(self)

        self.__max_distance = 0.0

    def make_json(self) -> Dict:
        output = {
           "max distance": self.max_distance,
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


class Spotlight(PointLight):
    def __init__(self, name_reg: NameRegistry):
        super().__init__(name_reg)

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


class WaterPlane(IActor):
    def __init__(self, name_reg: NameRegistry):
        super().__init__(name_reg)

        self.__mesh = Mesh()

    def make_json(self, bin_arr: BinaryArrayBuilder):
        output = {
            "mesh": []
        }

        IActor.insert_json(self, output)
        self.__mesh.make_json(output["mesh"], bin_arr)
        return output

    @property
    def mesh(self):
        return self.__mesh


class EnvironmentMap(IActor):
    def __init__(self, name_reg: NameRegistry):
        super().__init__(name_reg)

        self.m_volume: List[smt.Plane] = []

    def make_json(self):
        output = {}
        IActor.insert_json(self, output)

        output["volume"] = []
        for plane in self.m_volume:
            output["volume"].append(plane.coef())

        return output

    def new_plane(self):
        plane = smt.Plane()
        self.m_volume.append(plane)
        return plane


class IgnoredObject:
    def __init__(self, name: str = "", description: str = ""):
        self.__name = str(name)
        self.__description = str(description)

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value):
        self.__name = str(value)

    @property
    def description(self):
        return self.__description

    @description.setter
    def description(self, value):
        self.__description = str(value)


class IgnoredObjectList:
    def __init__(self):
        self.__data: List[IgnoredObject] = []

    def new(self, name: str = "", description: str = ""):
        output = IgnoredObject(name, description)
        self.__data.append(output)
        return output

    def make_json(self):
        output = {}
        for x in self.__data:
            output[x.name] = x.description
        return output


class Scene:
    def __init__(self):
        self.__name = ""

        self.__meshes: List[Mesh] = []
        self.__materials: List[Material] = []
        self.__skeletons: List[Skeleton] = []
        self.__animations: List[Animation] = []

        self.__mesh_actors: List[MeshActor] = []
        self.__dlights: List[DirectionalLight] = []
        self.__plights: List[PointLight] = []
        self.__slights: List[Spotlight] = []
        self.__water_planes: List[WaterPlane] = []
        self.__env_maps: List[EnvironmentMap] = []

        self.__ignored = IgnoredObjectList()

        self.__actor_name_reg = NameRegistry()

    @property
    def ignored_objects(self):
        return self.__ignored

    def make_json(self, bin_arr: BinaryArrayBuilder) -> Dict:
        return {
            "name": self.name,
            "root transform": [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1],

            "meshes": self.__make_json_for_meshes(bin_arr),
            "materials": [xx.make_json() for xx in self.__materials],
            "skeletons": [xx.make_json() for xx in self.__skeletons],
            "animations": [xx.make_json(bin_arr) for xx in self.__animations],
            "mesh actors": [xx.make_json(self.__meshes) for xx in self.__mesh_actors],
            "directional lights": [xx.make_json() for xx in self.__dlights],
            "point lights": [xx.make_json() for xx in self.__plights],
            "spotlights": [xx.make_json() for xx in self.__slights],
            "water planes": [xx.make_json(bin_arr) for xx in self.__water_planes],
            "environment maps": [xx.make_json() for xx in self.__env_maps],

            "ignored objects": self.ignored_objects.make_json(),
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

    def new_animation(self, name: str, ticks_per_sec: float):
        x = Animation(name, ticks_per_sec)
        self.__animations.append(x)
        return x

    def new_mesh_actor(self):
        mesh = MeshActor(self.__actor_name_reg)
        self.__mesh_actors.append(mesh)
        return mesh

    def new_dlight(self):
        light = DirectionalLight(self.__actor_name_reg)
        self.__dlights.append(light)
        return light

    def new_plight(self):
        light = PointLight(self.__actor_name_reg)
        self.__plights.append(light)
        return light

    def new_slight(self):
        light = Spotlight(self.__actor_name_reg)
        self.__slights.append(light)
        return light

    def new_water_plane(self):
        water = WaterPlane(self.__actor_name_reg)
        self.__water_planes.append(water)
        return water

    def new_env_map(self):
        env_map = EnvironmentMap(self.__actor_name_reg)
        self.__env_maps.append(env_map)
        return env_map

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
