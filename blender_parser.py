from typing import Dict, List, Tuple

import bpy


BLENDER_OBJ_TYPE_MESH        = "MESH"
BLENDER_OBJ_TYPE_CURVE       = "CURVE"
BLENDER_OBJ_TYPE_SURFACE     = "SURFACE"
BLENDER_OBJ_TYPE_META        = "META"
BLENDER_OBJ_TYPE_FONT        = "FONT"
BLENDER_OBJ_TYPE_ARMATURE    = "ARMATURE"
BLENDER_OBJ_TYPE_LATTICE     = "LATTICE"
BLENDER_OBJ_TYPE_EMPTY       = "EMPTY"
BLENDER_OBJ_TYPE_GPENCIL     = "GPENCIL"
BLENDER_OBJ_TYPE_CAMERA      = "CAMERA"
BLENDER_OBJ_TYPE_LIGHT       = "LIGHT"
BLENDER_OBJ_TYPE_SPEAKER     = "SPEAKER"
BLENDER_OBJ_TYPE_LIGHT_PROBE = "LIGHT_PROBE"


def get_objects():
    for obj in bpy.context.scene.objects:
        yield obj


def get_valid_meshes():
    for obj in get_objects():
        if obj.type != BLENDER_OBJ_TYPE_MESH:
            continue
        if not obj.visible_get():
            continue
        if not hasattr(obj.data, "polygons"):
            continue


class Scene:
    class RenderUnit:
        def __init__(self):
            self.m_ref_count = 0

    class StaticActor:
        def __init__(self):
            self.m_name = ""
            self.m_renderUnitID = 0

    def __init__(self):
        self.m_render_units: Dict[int, Scene.RenderUnit] = {}
        self.m_static_actors: List[Scene.StaticActor] = []

        # Tuple(name, reason)
        self.m_skipped_objs: List[Tuple[str, str]] = []

    def printInfo(self, println) -> str:
        for uid, unit in self.m_render_units.items():
            println("[DAL] Render unit{{ id={}, ref_count={} }}".format(
                uid, unit.m_ref_count))
        for actor in self.m_static_actors:
            println("[DAL] Static actor{{ name={}, uid={} }}".format(
                actor.m_name, actor.m_renderUnitID))
        for name, reason in self.m_skipped_objs:
            print("[DAL] Skipped {{ name={}, reason={} }}".format(name, reason))


def parse_raw_data():
    scene = Scene()

    for obj in get_objects():
        typeStr = str(obj.type)

        if not obj.visible_get():
            scene.m_skipped_objs.append((obj.name, "Hiddel object"))
            continue

        if BLENDER_OBJ_TYPE_MESH == str(typeStr):
            dataID = id(obj.data)
            if dataID not in scene.m_render_units.keys():
                unit = Scene.RenderUnit()
                scene.m_render_units[dataID] = unit
            scene.m_render_units[dataID].m_ref_count += 1

            actor = Scene.StaticActor()
            actor.m_name = obj.name
            actor.m_renderUnitID = dataID
            scene.m_static_actors.append(actor)
        else:
            scene.m_skipped_objs.append((obj.name,
                "Not supported object type: {}".format(typeStr)))

    return scene
