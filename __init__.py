import os
import sys
import zlib
import math
from typing import Tuple

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import datastruct as dat
from . import byteutils as byt


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


def _fixVecRotations(x: float, y: float, z: float) -> Tuple[float, float, float]:
    return ( float(x), float(z), -float(y) )

def _normalizeVec3(x: float, y: float, z: float):
    length = math.sqrt( x*x + y*y + z*z )
    return ( x/length, y/length, z/length )


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

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_int32(len(self.__units))

        for unit in self.__units:
            unit: dat.RenderUnit
            data += unit.makeBinary()

        return data

    def makeReadable(self):
        data = ""

        for unit in self.__units:
            unit: dat.RenderUnit
            data += unit.makeReadable()

        return data

    def getImgNames(self):
        imgNames = set()

        for unit in self.__units:
            imgNames.add(unit.m_material.m_diffuseMap)
            imgNames.add(unit.m_material.m_roughnessMap)
            imgNames.add(unit.m_material.m_metallicMap)

        imgNames.remove("")

        return imgNames

    def __parseRenderUnits(self):
        for obj in bpy.context.scene.objects:
            if not hasattr(obj.data, "polygons"): continue
            assert 1 == len(obj.data.materials)

            unit = dat.RenderUnit(obj.name)
            unit.m_material = MaterialParser.parse(obj.data.materials[0])

            for face in obj.data.polygons:
                lenVert = len(face.vertices)
                assert len(face.loop_indices) == lenVert
                if 3 == lenVert:
                    vertIndices = (0, 1, 2)
                elif 4 == lenVert:
                    vertIndices = (0, 1, 2, 0, 2, 3)
                else:
                    raise NotImplementedError("Loop with {} vertices is not supported!".format(lenVert))

                for i in vertIndices:
                    vert = face.vertices[i]
                    loop = face.loop_indices[i]

                    vertex = obj.data.vertices[vert].co
                    texcoord = (obj.data.uv_layers.active.data[loop].uv if obj.data.uv_layers.active is not None else (0.0, 0.0))
                    if face.use_smooth:
                        normal = obj.data.vertices[vert].normal
                    else:
                        normal = face.normal

                    vertex = _fixVecRotations(vertex[0], vertex[1], vertex[2])
                    normal = _fixVecRotations(normal[0], normal[1], normal[2])
                    normal = _normalizeVec3(normal[0], normal[1], normal[2])

                    unit.addVertex(
                        vertex[0], vertex[1], vertex[2],
                        texcoord[0], texcoord[1],
                        normal[0], normal[1], normal[2]
                    )

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
    optionBool_copyImages: BoolProperty(
        name = "Copy textures",
        description = "Copy textures to same path as exported model file.",
        default = False,
    )

    optionBool_createReadable: BoolProperty(
        name = "Create readable file.",
        description = "",
        default = False,
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

        binData = model.makeBinary()
        fullSize = len(binData)
        finalBin = byt.to_int32(fullSize) + zlib.compress(binData, zlib.Z_BEST_COMPRESSION)
        with open(self.filepath, "wb") as file:
            file.write(finalBin)

        if self.optionBool_copyImages:
            imgNames = model.getImgNames()
            saveFol = os.path.split(self.filepath)[0].replace("\\", "/")
            for name in imgNames:
                image = bpy.data.images[name]
                dstPath = saveFol + "/" + name
                image.save_render(dstPath)

        if self.optionBool_createReadable:
            with open(self.filepath[:-3] + "txt", "w", encoding="utf8") as file:
                file.write(model.makeReadable())

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
