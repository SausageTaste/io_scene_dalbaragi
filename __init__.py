import os
import shutil
import importlib

import bpy
import bpy.types
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import byteutils as byt
from . import smalltype as smt
from . import data_struct as dst
from . import data_exporter as dex
from . import export_func as exp


bl_info = {
    "name": "Dalbaragi Model Exporter",
    "author": "Sungmin Woo",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Export > Dalbaragi Tools",
    "description": "Export a model file for Dalbaragi engine.",
    "warning": "Under development.",
    "wiki_url": "",
    "category": "Import-Export",
    "tracker_url": ""
}


class EmportDalJson(Operator, ExportHelper):
    """Export intermediate json data"""

    bl_idname = "export_dalbaragi_scene.json"
    bl_label = "Export JSON"
    filename_ext = ".json"

    filter_glob: StringProperty(default="*.json", options={'HIDDEN'}, maxlen=255)

    option_copy_images: BoolProperty(
        name="Copy textures",
        description="Copy textures along with the exported file.",
        default=False,
    )

    option_compress_binary: BoolProperty(
        name="Compress binary",
        description="Compress binary data block using zlib.",
        default=True,
    )

    option_embed_binary: BoolProperty(
        name="Embed binary data",
        description="Store binary data as Base64 within JSON file.",
        default=True,
    )

    option_enum_exclude_hidden: EnumProperty(
        name="Exclude hidden",
        description="Select whether to export hidden objects or not",
        items=(
            ('OPT_1', "None", "All objects will be exported, including hidden ones"),
            ('OPT_2', "Meshes", "Hidden meshes will be excluded"),
            ('OPT_3', "All", "All types of hidden objects will be excluded"),
        ),
        default='OPT_1',
    )

    option_do_profile: BoolProperty(
        name="Generate profile result",
        description="Run with profiler enabled and export the result as a text file.",
        default=False,
    )

    def execute(self, context):
        configs = self.__parse_config()

        exp.export_json(
            self.filepath,
            configs,
            self.option_do_profile,
            self.option_compress_binary,
            self.option_embed_binary,
            self.option_copy_images,
        )

        self.report({'INFO'}, "Done exporting Dalbaragi scene")
        return {'FINISHED'}

    def __parse_config(self):
        if "OPT_3" == self.option_enum_exclude_hidden:
            exclude_obj = True
            exclude_mesh = True
        elif "OPT_2" == self.option_enum_exclude_hidden:
            exclude_obj = False
            exclude_mesh = True
        else:
            exclude_obj = False
            exclude_mesh = False

        return dex.ParseConfigs(
            exclude_mesh,
            exclude_obj,
        )


class DalExportSubMenu(bpy.types.Menu):
    bl_idname = "dal_export_menu"
    bl_label = "Dalbaragi Tools"

    def draw(self, context):
        self.layout.operator(EmportDalJson.bl_idname, text="Scene (.json)")


def menu_func_export(self, context):
    self.layout.menu(DalExportSubMenu.bl_idname)


modules = (
    byt,
    smt,
    dst,
    dex,
    exp,
)


classes = (
    EmportDalJson,
    DalExportSubMenu,
)


def register():
    for mod in modules:
        importlib.reload(mod)

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export_model.dmd('INVOKE_DEFAULT')
