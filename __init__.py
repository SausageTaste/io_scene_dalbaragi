import os
import zlib
import json
import shutil
import importlib
from typing import Tuple

import bpy
import bpy.types
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

from . import blender_parser as bpa
from . import byteutils as byt
from . import rawdata as rwd
from . import smalltype as smt
from . import modify_data as mfd
from . import model_exporter as mex
from . import map_data as mpd
from . import map_exporter_lvl as mpx
from . import data_struct as dst
from . import data_exporter as dex
from . import export_func as exp


bl_info = {
    "name": "Dalbaragi Model Exporter",
    "author": "Sungmin Woo",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    "location": "File > Export > Dalbaragi Model (.dmd)",
    "description": "Export a model file for Dalbaragi engine.",
    "warning": "Under development.",
    "wiki_url": "",
    "category": "Import-Export",
    "tracker_url": ""
}


def _copy_image(image: bpy.types.Image, dst_path: str) -> None:
    # Not packed
    if image.packed_file is None:
        src_path = bpy.path.abspath(image.filepath)
        if os.path.isfile(src_path):
            shutil.copyfile(src_path, dst_path)
            print("[DAL] Image copied: {}".format(dst_path))
        else:
            raise FileNotFoundError("[DAL] Image not found: {}".format(src_path))
    # Packed
    else:
        packed = image.packed_files[0]
        original_path = packed.filepath
        packed.filepath = dst_path
        packed.save()
        packed.filepath = original_path
        print("[DAL] Image exported from packed: {}".format(dst_path))


def _split_path_3(path: str) -> Tuple[str, str, str]:
    rest, ext = os.path.splitext(path)
    fol, filename = os.path.split(rest)
    return fol, filename, ext


class EmportDalModel(Operator, ExportHelper):
    """Export binary map file for Dalbaragi engine."""

    bl_idname = "export_model.dmd"
    bl_label = "Export DMD"

    filename_ext = ".dmd"

    filter_glob: StringProperty(
        default="*.dmd",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    optionBool_copyImages: BoolProperty(
        name="Copy textures",
        description="Copy textures to same path as exported model file.",
        default=False,
    )

    optionBool_createReadable: BoolProperty(
        name="Create readable file",
        description="Create a txt file that contains model info.",
        default=True,
    )

    """
    enum_example: EnumProperty(
        name        = "Example Enum",
        description = "Choose between two items",
        items       = (
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default     = 'OPT_A',
    )
    """

    def execute(self, context):
        print("[DAL] Started exporting Dalbaragi model")

        scene = bpa.parse_raw_data()
        print("[DAL] Building done")

        if self.optionBool_createReadable:
            readable_path = os.path.splitext(self.filepath)[0] + ".json"
            readable_content = scene.makeJson()
            with open(readable_path, "w", encoding="utf8") as file:
                json.dump(readable_content, file, indent=4, sort_keys=False)
            print("[DAL] Readable file created: " + readable_path)

        bin_data = mex.make_binary_dmd(scene)
        full_size = len(bin_data)
        final_bin = bytearray() + b"dalmdl" + byt.to_int32(full_size) + zlib.compress(bin_data, zlib.Z_BEST_COMPRESSION)
        with open(self.filepath, "wb") as file:
            file.write(final_bin)
        print("[DAL] Model exported: " + self.filepath)

        if self.optionBool_copyImages:
            img_save_fol_path = os.path.splitext(self.filepath)[0] + "_textures"
            if not os.path.isdir(img_save_fol_path):
                os.mkdir(img_save_fol_path)

            for name in scene.imageNames():
                image: bpy.types.Image = bpy.data.images[name]
                dst_path = os.path.join(img_save_fol_path, name)
                _copy_image(image, dst_path)
            print("[DAL] Image copied")

        print("[DAL] Finished")
        self.report({'INFO'}, "Export done: dmd")
        return {'FINISHED'}


class ExportDalMap(Operator, ExportHelper):
    bl_idname = "export_map.dlb"
    bl_label = "Export DLB"

    filename_ext = ".dlb"

    filter_glob = StringProperty(
        default="*.dlb",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    optionBool_createReadable = BoolProperty(
        name="Create readable file",
        description="Create a txt file that contains map info.",
        default=True,
    )

    def execute(self, context):
        print("[DAL] Started exporting Dalbaragi map")

        fol, level_name, ext_dlb = _split_path_3(self.filepath)

        scenes = bpa.parse_raw_data_map()
        maps = mpd.Level(scenes, level_name)
        print("[DAL] Building done")

        if self.optionBool_createReadable:
            readable_content = {}
            for collection_name, scene in scenes.items():
                readable_content[collection_name] = scene.makeJson()

            readable_path = os.path.splitext(self.filepath)[0] + ".json"
            with open(readable_path, "w", encoding="utf8") as file:
                json.dump(readable_content, file, indent=4, sort_keys=False)
            print("[DAL] Readable file created: " + readable_path)

        bin_data = mpx.make_binary_dlb(maps)
        final_bin = bytearray(b"dallvl") + bin_data
        with open(self.filepath, "wb") as file:
            file.write(final_bin)
        print("[DAL] Level exported: " + self.filepath)

        for name, chunk in maps.items():
            chunk_path = os.path.join(fol, name) + ".dmc"
            bin_data = mpx.make_binary_dmc(chunk.m_data)
            full_size = len(bin_data)
            final_bin = bytearray(b"dalchk") + byt.to_int32(full_size) + zlib.compress(bin_data, zlib.Z_BEST_COMPRESSION)
            with open(chunk_path, "wb") as file:
                file.write(final_bin)
            print("[DAL] Map chunk exported: " + chunk_path)

        print("[DAL] Finished")
        self.report({'INFO'}, "Export done: dlb")
        return {'FINISHED'}


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
        self.layout.operator(EmportDalModel.bl_idname, text="Model (.dmd)")
        self.layout.operator(ExportDalMap.bl_idname, text="Map (.dlb)")
        self.layout.operator(EmportDalJson.bl_idname, text="Scene (.json)")


def menu_func_export(self, context):
    self.layout.menu(DalExportSubMenu.bl_idname)


modules = (
    byt,
    smt,
    rwd,
    bpa,
    mfd,
    mex,
    mpd,
    mpx,
    dst,
    dex,
    exp,
)


classes = (
    EmportDalModel,
    ExportDalMap,
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
