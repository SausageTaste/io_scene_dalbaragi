import bpy

from . import rawdata as rwd
from . import smalltype as smt


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


def _fix_rotation(v: smt.Vec3) -> smt.Vec3:
    return smt.Vec3(v.x, v.z, -v.y)


def get_objects():
    for obj in bpy.context.scene.objects:
        yield obj


class _MaterialParser:
    @classmethod
    def parse(cls, blender_material):
        assert blender_material is not None

        bsdf = cls.__findPrincipledBSDFNode(blender_material.node_tree.nodes)
        if bsdf is None:
            raise RuntimeError("[DAL] Only Principled BSDF node is supported.")

        material = rwd.Scene.Material()

        node_base_color = bsdf.inputs["Base Color"]
        node_metallic   = bsdf.inputs["Metallic"]
        node_roughness  = bsdf.inputs["Roughness"]

        material.m_roughness = node_roughness.default_value
        material.m_metallic = node_metallic.default_value

        image_node = cls.__findImageNodeRecur(node_base_color)
        if image_node is not None:
            material.m_albedoMap = image_node.image.name

        image_node = cls.__findImageNodeRecur(node_metallic)
        if image_node is not None:
            material.m_metallicMap = image_node.image.name

        image_node = cls.__findImageNodeRecur(node_roughness)
        if image_node is not None:
            material.m_roughnessMap = image_node.image.name

        return material

    @staticmethod
    def __findPrincipledBSDFNode(nodes):
        for node in nodes:
            if "ShaderNodeBsdfPrincipled" == node.bl_idname:
                return node
        return None

    @classmethod
    def __findImageNodeRecur(cls, parent_node):
        if hasattr(parent_node, "links"):
            for linked in parent_node.links:
                node = linked.from_node
                if "ShaderNodeTexImage" == node.bl_idname:
                    return node
                else:
                    res = cls.__findImageNodeRecur(node)
                    if res is not None:
                        return res
        if hasattr(parent_node, "inputs"):
            for nodeinput in parent_node.inputs:
                res = cls.__findImageNodeRecur(nodeinput)
                if res is not None:
                    return res
            
        return None


def _parse_render_unit(obj) -> rwd.Scene.RenderUnit:
    unit = rwd.Scene.RenderUnit()

    if obj.data.materials[0] is not None:
        unit.m_material = _MaterialParser.parse(obj.data.materials[0])

    for face in obj.data.polygons:
        verts_per_face = len(face.vertices)
        assert len(face.loop_indices) == verts_per_face
        if 3 == verts_per_face:
            vert_indices = (0, 1, 2)
        elif 4 == verts_per_face:
            vert_indices = (0, 1, 2, 0, 2, 3)
        else:
            print("[DAL] WARNING:: Loop with {} vertices is not supported, thus omitted".format(verts_per_face))
            continue

        for i in vert_indices:
            # Vertex
            vert_index: int = face.vertices[i]
            vertex_data = obj.data.vertices[vert_index].co
            vertex = smt.Vec3(vertex_data[0], vertex_data[1], vertex_data[2])
            vertex = _fix_rotation(vertex)

            # UV coord
            loop: int = face.loop_indices[i]
            uv_data = (obj.data.uv_layers.active.data[loop].uv if obj.data.uv_layers.active is not None else (0.0, 0.0))
            uv_coord = smt.Vec2(uv_data[0], uv_data[1])

            # Normal
            if face.use_smooth:
                normal_data = obj.data.vertices[vert_index].normal
            else:
                normal_data = face.normal
            normal = smt.Vec3(normal_data[0], normal_data[1], normal_data[2])
            normal = _fix_rotation(normal)
            normal.normalize()

            # Rest
            vdata = rwd.Scene.VertexData()
            vdata.m_vertex = vertex
            vdata.m_uvCoord = uv_coord
            vdata.m_normal = normal

            for g in obj.data.vertices[vert_index].groups:
                group_name = str(obj.vertex_groups[g.group].name)
                vdata.addJoint(group_name, g.weight)

            unit.m_mesh.addVertex(vdata)

    return unit


def parse_raw_data():
    scene = rwd.Scene()

    for obj in get_objects():
        type_str = str(obj.type)

        if not obj.visible_get():
            scene.m_skipped_objs.append((obj.name, "Hiddel object"))
            continue

        if BLENDER_OBJ_TYPE_MESH == str(type_str):
            data_id = id(obj.data)
            if data_id not in scene.m_render_units.keys():
                scene.m_render_units[data_id] = _parse_render_unit(obj)
            scene.m_render_units[data_id].m_ref_count += 1

            actor = rwd.Scene.StaticActor()
            actor.m_name = obj.name
            actor.m_renderUnitID = data_id
            scene.m_static_actors.append(actor)
        else:
            scene.m_skipped_objs.append((obj.name, "Not supported object type: {}".format(type_str)))

    return scene
