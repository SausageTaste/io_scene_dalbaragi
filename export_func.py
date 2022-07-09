import os
import sys
import zlib
import json
import shutil
import base64
import pstats
import cProfile
import argparse

import bpy

try:
    from . import data_exporter as dex
except ImportError:
    import io_scene_dalbaragi.data_exporter as dex


def _copy_image(image: bpy.types.Image, dst_path: str) -> None:
    # Not packed
    if image.packed_file is None:
        src_path = bpy.path.abspath(image.filepath)
        if os.path.isfile(src_path):
            shutil.copyfile(src_path, dst_path)
        else:
            raise FileNotFoundError("Image not found: {}".format(src_path))
    # Packed
    else:
        packed = image.packed_files[0]
        original_path = packed.filepath
        packed.filepath = dst_path
        packed.save()
        packed.filepath = original_path


def export_json(
    file_path: str,
    configs:  dex.ParseConfigs,
    option_do_profile,
    option_compress_binary,
    option_embed_binary,
    option_copy_images,
):
    if option_do_profile:
        pr = cProfile.Profile()
        pr.enable()

    scenes, bin_array = dex.parse_scenes(configs)
    json_data, bin_data = dex.build_json(scenes, bin_array, configs)

    json_data["binary data"] = {
        "raw size": len(bin_data),
    }

    if option_compress_binary:
        bin_data = zlib.compress(bin_data, zlib.Z_BEST_COMPRESSION)
        json_data["binary data"]["compressed size"] = len(bin_data)

    if option_embed_binary:
        encoded = base64.b64encode(bin_data).decode('ascii')
        json_data["binary data"]["base64 size"] = len(encoded)
        json_data["binary data"]["base64"] = encoded
    else:
        with open(os.path.splitext(file_path)[0], "wb") as file:
            file.write(bin_data)

    with open(file_path, "w", encoding="utf8") as file:
        json.dump(json_data, file, indent=4)

    if option_copy_images:
        img_save_fol_path = os.path.splitext(file_path)[0] + "_textures"
        if not os.path.isdir(img_save_fol_path):
            os.mkdir(img_save_fol_path)

        image_names = set()
        for scene in scenes:
            a = scene.get_texture_names()
            image_names = image_names.union(a)

        for name in image_names:
            image: bpy.types.Image = bpy.data.images[name]
            dst_path = os.path.join(img_save_fol_path, name)
            _copy_image(image, dst_path)

    if option_do_profile:
        pr.disable()
        with open(os.path.splitext(file_path)[0] + "_profile.txt", "w", encoding="utf8") as file:
            ps = pstats.Stats(pr, stream=file)
            ps.sort_stats("tottime")
            ps.print_stats()


def __parse_args():
    parser = argparse.ArgumentParser(description="")

    parser.add_argument(
        "--output-folder",
        dest="output_folder",
        type=str,
        default=".",
        help=""
    )

    parser.add_argument('--texture', action=argparse.BooleanOptionalAction)

    if sys.argv.count("--"):
        args = sys.argv[sys.argv.index("--") + 1:]
    else:
        args = []

    args, unknown = parser.parse_known_args(args)
    return args


def __gen_blend_paths():
    for x in sys.argv:
        if x.endswith(".blend"):
            yield x


def __cmd_export():
    args = __parse_args()
    configs = dex.ParseConfigs()

    try:
        os.mkdir(args.output_folder)
    except FileExistsError:
        pass

    for blend_path in __gen_blend_paths():
        pure_file_name = os.path.split(os.path.splitext(blend_path)[0])[-1]
        json_path = os.path.join(args.output_folder, pure_file_name) + ".json"

        export_json(
            json_path,
            configs,
            False,
            True,
            True,
            bool(args.texture),
        )


if "__main__" == __name__:
    __cmd_export()
