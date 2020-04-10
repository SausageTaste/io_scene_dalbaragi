import os
import zlib
import json
import shutil
import importlib

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


def _copyImage(image: bpy.types.Image, dstpath: str) -> None:
    # Not packed
    if image.packed_file is None:
        srcpath = bpy.path.abspath(image.filepath)
        if os.path.isfile(srcpath):
            shutil.copyfile(srcpath, dstpath)
            print("[DAL] Image copied: {}".format(dstpath))
        else:
            raise FileNotFoundError("[DAL] Image not found: {}".format(srcpath))
    # Packed
    else:
        packed = image.packed_files[0]
        original_path = packed.filepath
        packed.filepath = dstpath
        packed.save()
        packed.filepath = original_path
        print("[DAL] Image exported from packed: {}".format(dstpath))


class EmportDalModel(Operator, ExportHelper):
    """Export binary map file for Dalbargi engine."""

    bl_idname = "export_model.dmd"
    bl_label = "Export DMD"

    filename_ext = ".dmd"

    filter_glob = StringProperty(
        default="*.dmd",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    optionBool_copyImages = BoolProperty(
        name="Copy textures",
        description="Copy textures to same path as exported model file.",
        default=False,
    )

    optionBool_createReadable = BoolProperty(
        name="Create readable file",
        description="Create a txt file that contains model info.",
        default=True,
    )

    optionBool_removeUselessJoints = BoolProperty(
        name="Remove useless joints",
        description="Remove all the joints without keyframes.",
        default=False,
    )

    """
    enum_example = EnumProperty(
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
        scene = bpa.parse_raw_data()
        mfd.MaterialDuplacateRemover.process(scene.m_render_units, scene.m_static_actors)
        if self.optionBool_removeUselessJoints:
            mfd.JointRemover.process(scene.m_skeletons[0], scene.m_animations, scene.m_render_units.values())
        print("[DAL] Building done")

        if self.optionBool_createReadable:
            readable_path = os.path.splitext(self.filepath)[0] + ".json"
            readable_content = scene.makeJson()
            with open(readable_path, "w", encoding="utf8") as file:
                json.dump(readable_content, file, indent=4, sort_keys=False)
            print("[DAL] Readable file created")

        bin_data = mex.make_binary_dmd(scene)
        full_size = len(bin_data)
        final_bin = bytearray() + b"dalmdl" + byt.to_int32(full_size) + zlib.compress(bin_data, zlib.Z_BEST_COMPRESSION)
        with open(self.filepath, "wb") as file:
            file.write(final_bin)
        print("[DAL] Model exported")

        if self.optionBool_copyImages:
            img_names = scene.imageNames()
            save_fol = os.path.split(self.filepath)[0].replace("\\", "/")
            for name in img_names:
                image: bpy.types.Image = bpy.data.images[name]
                dst_path = save_fol + "/" + name
                _copyImage(image, dst_path)
            print("[DAL] Image copied")

        print("[DAL] Finished")
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
        scenes = bpa.parse_raw_data_map()

        if self.optionBool_createReadable:
            readable_content = {}
            for collection_name, scene in scenes.items():
                readable_content[collection_name] = scene.makeJson()

            readable_path = os.path.splitext(self.filepath)[0] + ".json"
            with open(readable_path, "w", encoding="utf8") as file:
                json.dump(readable_content, file, indent=4, sort_keys=False)
            print("[DAL] Readable file created")

        print("[DAL] Finished")
        return {'FINISHED'}


class DalExportSubMenu(bpy.types.Menu):
    bl_idname = "dal_export_menu"
    bl_label = "Dalbaragi Tools"

    def draw(self, context):
        layout = self.layout
        layout.operator(EmportDalModel.bl_idname, text="Model (.dmd)")
        layout.operator(ExportDalMap.bl_idname, text="Map (.dlb)")


def menu_func_export(self, context):
    self.layout.menu(DalExportSubMenu.bl_idname)

def register():
    importlib.reload(byt)
    importlib.reload(smt)
    importlib.reload(rwd)
    importlib.reload(bpa)
    importlib.reload(mfd)
    importlib.reload(mex)

    bpy.utils.register_class(EmportDalModel)
    bpy.utils.register_class(ExportDalMap)
    bpy.utils.register_class(DalExportSubMenu)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(EmportDalModel)
    bpy.utils.unregister_class(ExportDalMap)
    bpy.utils.unregister_class(DalExportSubMenu)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export_model.dmd('INVOKE_DEFAULT')
