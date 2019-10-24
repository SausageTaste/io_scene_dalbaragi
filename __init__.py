import json
import base64

import zlib
import numpy as np

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


bl_info = {
    "name": "Dalbaragi Model Exporter",
    "author": "Sungmin Woo",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Export > Dalbaragi Model (.dmd)",
    "description": "Export a model file for Dalbargi engine.",
    "warning": "Under development.",
    "wiki_url": "",
    "category": "Import-Export",
    "tracker_url": ""
}


class Material:
    def __init__(self):
        self.__roughness = 0.5
        self.__metallic = 0.0

        self.__diffuseMap = ""
        self.__roughnessMap = ""
        self.__metallicMap = ""

    def __str__(self):
        return "Material{{ roughness={}, metallic={} }}".format(self.__roughness, self.__metallic)

    def makeJson(self):
        return {
            "roughness" : self.__roughness,
            "metallic" : self.__metallic,
            "diffuse_map" : self.__diffuseMap,
            "roughness_map" : self.__roughnessMap,
            "metallic_map" : self.__metallicMap,
        }

    @property
    def m_roughness(self):
        return self.__roughness
    @m_roughness.setter
    def m_roughness(self, v: float):
        self.__roughness = float(v)

    @property
    def m_metallic(self):
        return self.__metallic
    @m_metallic.setter
    def m_metallic(self, v: float):
        self.__metallic = float(v)

    @property
    def m_diffuseMap(self):
        return self.__diffuseMap
    @m_diffuseMap.setter
    def m_diffuseMap(self, v: str):
        self.__diffuseMap = str(v)

    @property
    def m_roughnessMap(self):
        return self.__roughnessMap
    @m_roughnessMap.setter
    def m_roughnessMap(self, v: str):
        self.__roughnessMap = str(v)

    @property
    def m_metallicMap(self):
        return self.__metallicMap
    @m_metallicMap.setter
    def m_metallicMap(self, v: str):
        self.__metallicMap = str(v)


class RenderUnit:
    def __init__(self, name: str):
        self.__name = str(name)

        self.__vertices = []
        self.__texcoords = []
        self.__normals = []

        self.__material = Material()

    def addVertex(self, xVert, yVert, zVert, xTex, yTex, xNorm, yNorm, zNorm):
        self.__vertices +=  [ float(xVert), float(yVert), float(zVert) ]
        self.__texcoords += [ float(xTex ), float(yTex )               ]
        self.__normals +=   [ float(xNorm), float(yNorm), float(zNorm) ]

    def getVertexArrays(self):
        v = np.array(self.__vertices, dtype=np.float32)
        t = np.array(self.__texcoords, dtype=np.float32)
        n = np.array(self.__normals, dtype=np.float32)
        return v, t, n

    @property
    def m_name(self):
        return self.__name

    @property
    def m_material(self):
        return self.__material
    @m_material.setter
    def m_material(self, m: Material):
        if not isinstance(m, Material):
            raise TypeError()
        else:
            self.__material = m


class MaterialParser:
    @classmethod
    def parse(cls, blenderMat):
        bsdf = cls.__findPrincipledBSDFNode(blenderMat.node_tree.nodes)
        if bsdf is None:
            raise ValueError("Only Principled BSDF node is supported.")

        material = Material()

        node_baseColor = bsdf.inputs["Base Color"]
        node_metallic  = bsdf.inputs["Metallic"]
        node_roughness = bsdf.inputs["Roughness"]

        material.m_roughness = node_roughness.default_value
        material.m_metallic = node_metallic.default_value

        imageNode = cls.__findImageNodeRecur(node_baseColor)
        if imageNode is not None:
            material.m_diffuseMap = imageNode.image.name
        else:
            raise ValueError("Diffuse map must be defined.")

        imageNode = cls.__findImageNodeRecur(node_metallic)
        if imageNode is not None:
            material.m_metallicMap = imageNode.image.name

        imageNode = cls.__findImageNodeRecur(node_roughness)
        if imageNode is not None:
            material.m_roughnessMap = imageNode.image.name

        return material

    @staticmethod
    def __findPrincipledBSDFNode(nodes):
        for node in nodes:
            if "ShaderNodeBsdfPrincipled" == node.bl_idname:
                return node
        return None

    @classmethod
    def __findImageNodeRecur(cls, parentNode):
        if hasattr(parentNode, "links"):
            for linked in parentNode.links:
                node = linked.from_node
                if "ShaderNodeTexImage" == node.bl_idname:
                    return node
                else:
                    res = cls.__findImageNodeRecur(node)
                    if res is not None:
                        return res
        if hasattr(parentNode, "inputs"):
            for input in parentNode.inputs:
                res = cls.__findImageNodeRecur(input)
                if res is not None:
                    return res
            
        return None


class Datablock:
    def __init__(self):
        self.__array = bytearray()
    
    def addData(self, arr: bytearray) -> int:
        offset = len(self.__array)
        self.__array += arr
        return offset

    def makeJson(self, compress: bool):
        if (compress):
            data: bytes = zlib.compress(self.__array, zlib.Z_BEST_COMPRESSION)
        else:
            data: bytes = self.__array
        return {
            "size" : len(self.__array),
            "zipped_array" : base64.encodebytes(data).decode("utf8")
        }


class ModelBuilder:
    def __init__(self):
        self.__units = []

        self.__parseRenderUnits()

    def makeJson(self, compress: bool):
        data = {}
        datablock = Datablock()

        unitsData = []
        for unit in self.__units:
            v, t, n = unit.getVertexArrays()
            assert 2*len(v) == 3*len(t) == 2*len(n)
            assert len(v) % 3 == 0
            numVertices = len(v) // 3
            offset = datablock.addData(v.tobytes())
            datablock.addData(t.tobytes())
            datablock.addData(n.tobytes())

            unitsData.append({
                "name" : unit.m_name,
                "material" : unit.m_material.makeJson(),
                "vertex_datablock_offset" : offset,
                "number_of_vertices" : numVertices,
            })

        data["render_units"] = unitsData
        data["zipped_datablock"] = datablock.makeJson(compress)

        return data

    def printAll(self):
        for unit in self.__units:
            print(unit.m_name)
            print("\t{} : {}".format("roughness", unit.m_material.m_roughness))
            print("\t{} : {}".format("metallic", unit.m_material.m_metallic))
            print("\t{} : {}".format("diffuse map", unit.m_material.m_diffuseMap))
            print("\t{} : {}".format("roughness map", unit.m_material.m_roughnessMap))
            print("\t{} : {}".format("metallic map", unit.m_material.m_metallicMap))

    def __parseRenderUnits(self):
        for mesh in bpy.data.meshes:
            unit = RenderUnit(mesh.name)
            uvLayer = mesh.uv_layers.active.data

            unit.m_material = MaterialParser.parse(mesh.materials[0])

            for polygon in mesh.polygons:
                vertIndices = []
                vertPerFace = len(polygon.vertices)
                if 3 == vertPerFace:
                    vertIndices.append(polygon.vertices[0])
                    vertIndices.append(polygon.vertices[1])
                    vertIndices.append(polygon.vertices[2])
                elif 4 == vertPerFace:
                    vertIndices.append(polygon.vertices[0])
                    vertIndices.append(polygon.vertices[1])
                    vertIndices.append(polygon.vertices[2])
                    vertIndices.append(polygon.vertices[0])
                    vertIndices.append(polygon.vertices[2])
                    vertIndices.append(polygon.vertices[3])
                else:
                    raise RuntimeError("A face with {} vertices is not supported.".format(vertPerFace))

                for vertIndex in vertIndices:
                    vertex = mesh.vertices[vertIndex].co
                    texcoord = uvLayer[vertIndex].uv
                    normal = mesh.vertices[vertIndex].normal
                    unit.addVertex(vertex[0], vertex[1], vertex[2], texcoord[0], texcoord[1], normal[0], normal[1], normal[2])

            self.__units.append(unit)


class EmportDalModel(Operator, ExportHelper):
    """Export binary map file for Dalbargi engine."""

    bl_idname = "export_model.dmd"
    bl_label = "Export DMD"

    filename_ext = ".dmd"

    filter_glob: StringProperty(
        default="*.dmd",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    optionBool_compress: BoolProperty(
        name="Compress datablock",
        description="Compress datablock with zlib.",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        model = ModelBuilder()
        with open(self.filepath, "w", encoding="utf8") as file:
            json.dump(model.makeJson(self.optionBool_compress), file, indent=4, sort_keys=True)

        return {'FINISHED'}

    def write(self, context):
        print("running write_some_data...")
        f = open(self.filepath, 'w', encoding='utf-8')
        f.write("Hello World %s" % self.optionBool_compress)
        f.close()

        return {'FINISHED'}


def menu_func_export(self, context):
    # Only needed if you want to add into a dynamic menu
    self.layout.operator(EmportDalModel.bl_idname, text="Dalbaragi Model (.dmd)")

def register():
    bpy.utils.register_class(EmportDalModel)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(EmportDalModel)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export_model.dmd('INVOKE_DEFAULT')
