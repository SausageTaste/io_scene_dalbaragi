import array
from typing import List, Dict, Tuple

from . import byteutils as byt
from . import smalltype as smt


class _Vertex:
    def __init__(self):
        self.__pos = smt.Vec3()
        self.__uv_coord = smt.Vec2()
        self.__normal = smt.Vec3()
        self.__joints: List[Tuple[float, int]] = []

    def add_joint(self, joint_index: int, weight: float) -> None:
        self.__joints.append((float(weight), int(joint_index)))

    def sort_joints(self):
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
        return iter(self.__joints)

    @property
    def joint_count(self):
        return len(self.__joints)


class _VertexBuffer:
    def __init__(self):
        self.__vertices: List[_Vertex] = []

    def make_json(self, output: Dict, bin_arr: byt.BinaryArrayBuilder):
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
        vertex = _Vertex()
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
            v.sort_joints()
            output += byt.to_int32(v.joint_count)
            for j_weight, j_index in v.joints:
                output += byt.to_int32(j_index)
                output += byt.to_float32(j_weight)
        return output


class _Mesh:
    def __init__(self):
        self.__name = ""
        self.__skeleton_name = ""
        self.__vertices: Dict[str, _VertexBuffer] = {}

    def make_json(self, output: List[Dict], bin_arr: byt.BinaryArrayBuilder):
        for material_name, vertex_buffer in self.__vertices.items():
            output.append({
                "name": self.get_mangled_name(material_name),
                "skeleton name": self.skeleton_name,
            })
            vertex_buffer.make_json(output[-1], bin_arr)

    def add_vertex(self, material_name: str, position: smt.Vec3, uv_coord: smt.Vec2, normal: smt.Vec3):
        if material_name not in self.__vertices.keys():
            self.__vertices[material_name] = _VertexBuffer()

        return self.__vertices[material_name].add_vertex(position, uv_coord, normal)

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


class MeshManager:
    def __init__(self) -> None:
        self.__meshes = []

    def get_mesh_mat_pairs(self, mesh_name: str) -> List[Tuple[str, str]]:
        mesh = self.__find_by_name(mesh_name)
        output: List[Tuple[str, str]] = []

        for mat_name, vert_buf in mesh.vertex_buffers:
            output.append((
                mesh.get_mangled_name(mat_name),
                mat_name,
            ))

        return output

    # Returns mesh name
    def add_bpy_mesh(self, bpy_mesh, skeleton_name: str, joint_name_index_map: Dict[str, int]) -> str:
        mesh_name = str(bpy_mesh.data.name)

        try:
            self.__find_by_name(mesh_name)
        except KeyError:
            mesh = self.__new_mesh(mesh_name)
            self.__parse_mesh(bpy_mesh, mesh, skeleton_name, joint_name_index_map)

        return mesh_name

    def make_json(self, bin_arr: byt.BinaryArrayBuilder):
        output = []
        for mesh in self.__meshes:
            mesh.make_json(output, bin_arr)
        return output

    def __new_mesh(self, name: str):
        mesh = _Mesh()
        mesh.name = name
        self.__meshes.append(mesh)
        return mesh

    def __find_by_name(self, name: str):
        for x in self.__meshes:
            if x.name == name:
                return x

        raise KeyError(f'Failed to find a mesh named "{name}"')

    @staticmethod
    def __parse_mesh(obj, mesh: _Mesh, skeleton_name: str, joint_name_index_map: Dict[str, int]):
        obj_mesh = obj.data
        # assert isinstance(obj_mesh, bpy.types.Mesh)

        obj_mesh.calc_loop_triangles()
        mesh.name = obj_mesh.name
        mesh.skeleton_name = skeleton_name

        for tri in obj_mesh.loop_triangles:
            try:
                material_name = obj.data.materials[tri.material_index].name
            except IndexError:
                material_name = ""

            for i in range(3):
                # Vertex
                vertex_index: int = tri.vertices[i]
                vertex_data = obj_mesh.vertices[vertex_index].co
                vertex = smt.Vec3(vertex_data[0], vertex_data[1], vertex_data[2])

                # UV coord
                if obj_mesh.uv_layers.active is not None:
                    uv_data = obj_mesh.uv_layers.active.data[tri.loops[i]].uv
                else:
                    uv_data = (0.0, 0.0)
                uv_coord = smt.Vec2(uv_data[0], uv_data[1])

                # Normal
                if tri.use_smooth:
                    normal_data = obj_mesh.vertices[vertex_index].normal
                else:
                    normal_data = tri.normal
                normal = smt.Vec3(normal_data[0], normal_data[1], normal_data[2])
                normal.normalize()

                dst_vertex = mesh.add_vertex(material_name, vertex, uv_coord, normal)

                for g in obj.data.vertices[vertex_index].groups:
                    joint_name = str(obj.vertex_groups[g.group].name)
                    try:
                        joint_index = joint_name_index_map[joint_name]
                    except KeyError:
                        pass
                    else:
                        dst_vertex.add_joint(joint_index, g.weight)


def create_mesh_manager():
    return MeshManager()
