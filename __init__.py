import os
import sys
import json

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import datastruct as dat


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


class MaterialParser:
    @classmethod
    def parse(cls, blenderMat):
        bsdf = cls.__findPrincipledBSDFNode(blenderMat.node_tree.nodes)
        if bsdf is None:
            raise ValueError("Only Principled BSDF node is supported.")

        material = dat.Material()

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


class ModelBuilder:
    def __init__(self):
        self.__units = []

        self.__parseRenderUnits()

    def makeJson(self, compress: bool):
        data = {}

        datablock = dat.Datablock()
        materialList = dat.IndexSet(dat.Material)

        unitsData = []
        for unit in self.__units:
            v, t, n = unit.getVertexArrays()
            assert 2*len(v) == 3*len(t) == 2*len(n)
            assert len(v) % 3 == 0
            numVertices = len(v) // 3
            offset = datablock.addData(v.tobytes())
            datablock.addData(t.tobytes())
            datablock.addData(n.tobytes())

            materialIndex = materialList.addGetIndex(unit.m_material)

            unitsData.append({
                "name" : unit.m_name,
                "material_index" : materialIndex,
                "vert_data_offset" : offset,
                "num_vert" : numVertices,
            })

        data["materials"] = [x.makeJson() for x in materialList]
        data["render_units"] = unitsData
        data["zipped_datablock"] = datablock.makeJson(compress)

        return data

    def __parseRenderUnits(self):
        for mesh in bpy.data.meshes:
            unit = dat.RenderUnit(mesh.name)
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
    import importlib
    importlib.reload(dat)

    register()
    bpy.ops.export_model.dmd('INVOKE_DEFAULT')
