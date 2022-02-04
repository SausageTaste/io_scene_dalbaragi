import math
from typing import Dict, List, Tuple, Optional

import bpy

from . import rawdata as rwd
from . import smalltype as smt


_BLENDER_OBJ_TYPE_MESH        = "MESH"
_BLENDER_OBJ_TYPE_CURVE       = "CURVE"
_BLENDER_OBJ_TYPE_SURFACE     = "SURFACE"
_BLENDER_OBJ_TYPE_META        = "META"
_BLENDER_OBJ_TYPE_FONT        = "FONT"
_BLENDER_OBJ_TYPE_ARMATURE    = "ARMATURE"
_BLENDER_OBJ_TYPE_LATTICE     = "LATTICE"
_BLENDER_OBJ_TYPE_EMPTY       = "EMPTY"
_BLENDER_OBJ_TYPE_GPENCIL     = "GPENCIL"
_BLENDER_OBJ_TYPE_CAMERA      = "CAMERA"
_BLENDER_OBJ_TYPE_LIGHT       = "LIGHT"
_BLENDER_OBJ_TYPE_SPEAKER     = "SPEAKER"
_BLENDER_OBJ_TYPE_LIGHT_PROBE = "LIGHT_PROBE"

_BLENDER_MATERIAL_BLEND_OPAQUE = "OPAQUE"
_BLENDER_MATERIAL_BLEND_CLIP   = "CLIP"
_BLENDER_MATERIAL_BLEND_HASHED = "HASHED"
_BLENDER_MATERIAL_BLEND_BLEND  = "BLEND"

__PROPERTIES_TO_IGNORE = (
    "_RNA_UI",
    "cycles"
)


# In blender's coordinate system, -z is down.
# But in Dalbaragi engine, -y is down and -z is far direction.
def __fix_vec3_orientation(v: smt.Vec3) -> smt.Vec3:
    return smt.Vec3(v.x, v.z, -v.y)


def __fix_quat_orientation(q: smt.Quat) -> smt.Quat:
    v = __fix_vec3_orientation(smt.Vec3(q.x, q.y, q.z))
    return smt.Quat(q.w, v.x, v.y, v.z)


def __to_degrees(radian: float) -> float:
    return float(radian) * 180.0 / math.pi


def _gen_blender_objects():
    for obj in bpy.context.scene.objects:
        yield obj


class _MaterialParser:
    NODE_BSDF            = "ShaderNodeBsdfPrincipled"
    NODE_HOLDOUT         = "ShaderNodeHoldout"
    NODE_MATERIAL_OUTPUT = "ShaderNodeOutputMaterial"
    NODE_TEX_IMAGE       = "ShaderNodeTexImage"
    NODE_GROUP           = "ShaderNodeGroup"

    @classmethod
    def parse(cls, blender_material) -> Optional[rwd.Scene.Material]:
        assert blender_material is not None

        shader_output = cls.__find_node_named(cls.NODE_MATERIAL_OUTPUT, blender_material.node_tree.nodes)
        linked_shader = shader_output.inputs["Surface"].links[0].from_node
        alpha_blend_enabled = True if blender_material.blend_method != _BLENDER_MATERIAL_BLEND_OPAQUE else False

        if cls.NODE_BSDF == linked_shader.bl_idname:
            return cls.__parse_principled_bsdf(linked_shader, alpha_blend_enabled)
        elif cls.NODE_HOLDOUT == linked_shader.bl_idname:
            return None
        elif cls.NODE_GROUP == linked_shader.bl_idname:
            if "XPS Shader" == linked_shader.node_tree.name_full:
                return cls.__parse_xps_shader(linked_shader, alpha_blend_enabled)
            else:
                print("[DAL] Not supported shader type: {}".format(linked_shader.node_tree.name_full))
                return None
        else:
            print("[DAL] Not supported shader type: {}".format(linked_shader.bl_idname))
            return None

    @staticmethod
    def __find_node_named(name: str, nodes):
        for node in nodes:
            if name == node.bl_idname:
                return node
        return None

    @classmethod
    def __find_node_recur_named(cls, name, parent_node):
        if hasattr(parent_node, "links"):
            for linked in parent_node.links:
                node = linked.from_node
                if name == node.bl_idname:
                    return node
                else:
                    res = cls.__find_node_recur_named(name, node)
                    if res is not None:
                        return res
        if hasattr(parent_node, "inputs"):
            for nodeinput in parent_node.inputs:
                res = cls.__find_node_recur_named(name, nodeinput)
                if res is not None:
                    return res

        return None

    @classmethod
    def __parse_principled_bsdf(cls, bsdf, alpha_blend: bool) -> rwd.Scene.Material:
        material = rwd.Scene.Material()

        node_roughness = bsdf.inputs["Roughness"]
        node_metallic  = bsdf.inputs["Metallic"]

        material.m_alphaBlend = alpha_blend
        material.m_roughness = node_roughness.default_value
        material.m_metallic = node_metallic.default_value

        image_node = cls.__find_node_recur_named(cls.NODE_TEX_IMAGE, bsdf.inputs["Base Color"])
        if image_node is not None:
            material.m_albedoMap = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.NODE_TEX_IMAGE, node_roughness)
        if image_node is not None:
            material.m_metallicMap = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.NODE_TEX_IMAGE, node_roughness)
        if image_node is not None:
            material.m_roughnessMap = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.NODE_TEX_IMAGE, bsdf.inputs["Normal"])
        if image_node is not None:
            material.m_normalMap = image_node.image.name

        return material

    @classmethod
    def __parse_xps_shader(cls, linked_shader, alpha_blend: bool):
        material = rwd.Scene.Material()

        material.m_alphaBlend = alpha_blend

        image_node = cls.__find_node_recur_named(cls.NODE_TEX_IMAGE, linked_shader.inputs["Diffuse"])
        if image_node is not None:
            material.m_albedoMap = image_node.image.name

        image_node = cls.__find_node_recur_named(cls.NODE_TEX_IMAGE, linked_shader.inputs["Bump Map"])
        if image_node is not None:
            material.m_normalMap = image_node.image.name

        return material

    @staticmethod
    def __print_props(obj):
        print(type(obj))
        for x in dir(obj):
            print("\t", x, "->", getattr(obj, x))


class _TimepointDict:
    def __init__(self):
        self.__data: Dict[float, Dict[int, float]] = {}

    def add(self, timepoint: float, channel: int, value: float):
        assert isinstance(timepoint, float)
        assert isinstance(channel, int)
        assert isinstance(value, float)

        if timepoint not in self.__data.keys():
            self.__data[timepoint] = {}
        self.__data[timepoint][channel] = value

    def get(self, timepoint: float, channel: int) -> float:
        assert isinstance(channel, int)
        assert isinstance(timepoint, float)

        return self.__data[timepoint][channel]

    def get_extended(self, timepoint: float, channel: int) -> float:
        assert isinstance(channel, int)
        assert isinstance(timepoint, float)

        try:
            return self.__data[timepoint][channel]
        except KeyError:
            requested_index = self.__convert_timepoint_to_index(timepoint)
            prev_index = requested_index - 1
            if prev_index < 0:
                raise RuntimeError("[DAL] First keyframe need all its channels with a value.")
            prev_timepoint = self.__convert_index_to_timepoint(prev_index)
            return self.get(prev_timepoint, channel)

    def iter_timepoints(self) -> iter:
        return iter(self.__make_sorted_timepoints())

    def __make_sorted_timepoints(self) -> List[float]:
        timepoints = list(self.__data.keys())
        timepoints.sort()
        return timepoints

    def __convert_index_to_timepoint(self, order: int) -> float:
        assert isinstance(order, int)
        assert order >= 0
        return self.__make_sorted_timepoints()[order]

    def __convert_timepoint_to_index(self, timepoint: float) -> int:
        assert isinstance(timepoint, float)
        return self.__make_sorted_timepoints().index(timepoint)


class _JointData:
    def __init__(self):
        # Channels for a pos and scale are x=0, y=1, z=2
        # For a quat, w=0, x=1, y=2, z=3
        self.__poses = _TimepointDict()
        self.__quats = _TimepointDict()
        self.__scales = _TimepointDict()

    @property
    def poses(self):
        return self.__poses

    @property
    def quats(self):
        return self.__quats

    @property
    def scales(self):
        return self.__scales


class _ActionAssembler:
    def __init__(self):
        self.__joints: Dict[str, _JointData] = {}

    def items(self):
        return self.__joints.items()

    def add(self, joint_name: str, var_name: str, timepoint: float, channel: int, value: float):
        joint_name = str(joint_name)
        var_name = str(var_name)

        if joint_name not in self.__joints.keys():
            self.__joints[joint_name] = _JointData()

        if "location" == var_name:
            self.__joints[joint_name].poses.add(timepoint, channel, value)
        elif "rotation_quaternion" == var_name:
            self.__joints[joint_name].quats.add(timepoint, channel, value)
        elif "scale" == var_name:
            self.__joints[joint_name].scales.add(timepoint, channel, value)
        else:
            print('[DAL] WARN::Unknown variable for a joint: "{}"'.format(var_name))


def __split_fcu_data_path(path: str) -> Tuple[str, str]:
    pass1 = path.split('"')
    bone_name = pass1[1]

    pass2 = pass1[2].split(".")
    var_name = pass2[-1]

    return bone_name, var_name


def __parse_animation(blender_action: bpy.types.Action):
    assert isinstance(blender_action, bpy.types.Action)

    anim = rwd.Scene.Animation(blender_action.name, bpy.context.scene.render.fps)

    assembler = _ActionAssembler()
    for fcu in blender_action.fcurves:
        # var_name is either location, rotation_quaternion or scale
        # channel stands for x, y, z for locations, w, x, y, z for quat, x, y, z for scale.
        joint_name, var_name = __split_fcu_data_path(fcu.data_path)
        channel = fcu.array_index

        for keyframe in fcu.keyframe_points:
            timepoint = keyframe.co[0]
            value = keyframe.co[1]
            assembler.add(joint_name, var_name, timepoint, channel, value)

    for joint_name, joint_data in assembler.items():
        joint_keyframes = anim.newJoint(joint_name)

        poses = joint_data.poses
        for tp in poses.iter_timepoints():
            x = poses.get(tp, 0)
            y = poses.get(tp, 1)
            z = poses.get(tp, 2)
            joint_keyframes.addPos(tp, x, y, z)

        quats = joint_data.quats
        for tp in quats.iter_timepoints():
            w = quats.get(tp, 0)
            x = quats.get(tp, 1)
            y = quats.get(tp, 2)
            z = quats.get(tp, 3)
            joint_keyframes.addRotate(tp, w, x, y, z)

        scales = joint_data.scales
        for tp in scales.iter_timepoints():
            x = scales.get(tp, 0)
            y = scales.get(tp, 1)
            z = scales.get(tp, 2)
            average_scale = (x + y + z) / 3
            joint_keyframes.addScale(tp, average_scale)

    return anim


def __parse_transform(obj) -> smt.Transform:
    dst = smt.Transform()

    dst.m_pos.x = obj.location[0]
    dst.m_pos.y = obj.location[1]
    dst.m_pos.z = obj.location[2]
    dst.m_pos = __fix_vec3_orientation(dst.m_pos)

    dst.m_rotate = __fix_quat_orientation(smt.Quat(
        obj.rotation_quaternion[0],
        obj.rotation_quaternion[1],
        obj.rotation_quaternion[2],
        obj.rotation_quaternion[3],
    ))

    dst.m_scale = (obj.scale[0] + obj.scale[1] + obj.scale[2]) / 3

    return dst


def __parse_skeleton(blender_armature) -> rwd.Scene.Skeleton:
    assert isinstance(blender_armature, bpy.types.Armature)

    skeleton = rwd.Scene.Skeleton(blender_armature.name)

    for bone in blender_armature.bones:
        parent_name = ""
        if bone.parent is not None:
            parent_name = bone.parent.name

        joint_data = skeleton.newJoint(bone.name, parent_name)

        if bone.get("dal_phy_hairRoot", None) is not None:
            joint_data.m_jointType = rwd.Scene.JointType.hair_root
        elif bone.get("dal_phy_skirtRoot", None) is not None:
            joint_data.m_jointType = rwd.Scene.JointType.skirt_root

        joint_data.m_offsetMat.set(bone.matrix_local)

    return skeleton


def __parse_model(obj, data_id: int) -> rwd.Scene.Model:
    assert isinstance(obj.data, bpy.types.Mesh)

    model = rwd.Scene.Model(data_id)

    armature = obj.find_armature()
    armature_name = "" if armature is None else armature.name
    del armature

    units: List[Optional[rwd.Scene.RenderUnit]] = []

    # Generate render units with materials
    if 0 == len(obj.data.materials):
        raise RuntimeError("Object '{}' has no material".format(obj.name))
    for i in range(len(obj.data.materials)):
        material = _MaterialParser.parse(obj.data.materials[i])
        if material is None:
            units.append(None)
        else:
            unit = rwd.Scene.RenderUnit()
            unit.m_material = material
            unit.m_mesh.m_skeletonName = armature_name
            units.append(unit)
            del unit

    # Generate mesh
    for face in obj.data.polygons:
        material_index = int(face.material_index)

        vert_count_per_face = len(face.vertices)
        assert len(face.loop_indices) == vert_count_per_face
        if 3 == vert_count_per_face:
            vert_indices = (0, 1, 2)
        elif 4 == vert_count_per_face:
            vert_indices = (0, 1, 2, 0, 2, 3)
        else:
            print("[DAL] WARN: Loop with {} vertices is not supported, thus omitted".format(vert_count_per_face))
            continue

        for i in vert_indices:
            # Vertex
            vert_index: int = face.vertices[i]
            vertex_data = obj.data.vertices[vert_index].co
            vertex = smt.Vec3(vertex_data[0], vertex_data[1], vertex_data[2])
            vertex = __fix_vec3_orientation(vertex)

            model.m_aabb.resizeToContain(vertex.x, vertex.y, vertex.z)
            if units[material_index] is None:
                continue

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
            normal = __fix_vec3_orientation(normal)
            normal.normalize()

            # Rest
            vert_data = rwd.Scene.VertexData()
            vert_data.m_vertex = vertex
            vert_data.m_uvCoord = uv_coord
            vert_data.m_normal = normal

            for g in obj.data.vertices[vert_index].groups:
                group_name = str(obj.vertex_groups[g.group].name)
                vert_data.addJoint(group_name, g.weight)

            units[material_index].m_mesh.addVertex(vert_data)

    for unit in units:
        if unit is not None:
            model.addUnit(unit)

    return model


def __parse_light_base(obj, light: rwd.Scene.ILight) -> None:
    light.m_name = obj.name

    light.m_color.x = obj.data.color.r
    light.m_color.y = obj.data.color.g
    light.m_color.z = obj.data.color.b

    light.m_useShadow = obj.data.use_shadow
    light.m_intensity = obj.data.energy


def __parse_light_point(obj):
    assert isinstance(obj.data, bpy.types.PointLight)

    plight = rwd.Scene.PointLight()

    __parse_light_base(obj, plight)

    plight.m_pos = __fix_vec3_orientation(smt.Vec3(obj.location.x, obj.location.y, obj.location.z))

    if not obj.data.use_custom_distance:
        print("[DAL] WARN::custom distance is not enabled for light \"{}\"".format(plight.m_name))
    plight.m_maxDistance = float(obj.data.cutoff_distance)
    plight.m_halfIntenseDist = float(obj.data.distance)

    return plight


def __parse_light_directional(obj):
    assert isinstance(obj.data, bpy.types.SunLight)

    dlight = rwd.Scene.DirectionalLight()

    __parse_light_base(obj, dlight)

    quat = smt.Quat()
    quat.w = obj.rotation_quaternion[0]
    quat.x = obj.rotation_quaternion[1]
    quat.y = obj.rotation_quaternion[2]
    quat.z = obj.rotation_quaternion[3]
    down = smt.Vec3(0, 0, -1)  # Take a look at the comment near "_fix_rotation" function
    dlight.m_direction = __fix_vec3_orientation(quat.rotateVec(down))

    return dlight


def __parse_light_spot(obj):
    assert isinstance(obj.data, bpy.types.SpotLight)

    slight = rwd.Scene.SpotLight()

    __parse_light_base(obj, slight)

    slight.m_pos = __fix_vec3_orientation(smt.Vec3(obj.location.x, obj.location.y, obj.location.z))

    if not obj.data.use_custom_distance:
        print("[DAL] WARN::custom distance is not enabled for light \"{}\"".format(slight.m_name))
    slight.m_maxDistance = float(obj.data.cutoff_distance)
    slight.m_halfIntenseDist = float(obj.data.distance)

    quat = smt.Quat()
    quat.w = obj.rotation_quaternion[0]
    quat.x = obj.rotation_quaternion[1]
    quat.y = obj.rotation_quaternion[2]
    quat.z = obj.rotation_quaternion[3]
    down = smt.Vec3(0, 0, -1)  # Take a look at the comment near "_fix_rotation" function
    slight.m_direction = __fix_vec3_orientation(quat.rotateVec(down))

    slight.m_spotDegree = __to_degrees(obj.data.spot_size)
    slight.m_spotBlend = float(obj.data.spot_blend)

    return slight


# Special meshes
def __parse_water_plane(obj) -> rwd.Scene.WaterPlane:
    model = __parse_model(obj, 0)
    transform = __parse_transform(obj)
    aabb = model.m_aabb
    aabb.m_min = transform.transform(aabb.m_min)
    aabb.m_max = transform.transform(aabb.m_max)

    water = rwd.Scene.WaterPlane()

    water.m_centerPos = smt.Vec3(
        (aabb.m_min.x + aabb.m_max.x) / 2,
        aabb.m_max.y,
        (aabb.m_min.z + aabb.m_max.z) / 2,
    )

    water.m_width = abs(aabb.m_max.x - aabb.m_min.x)
    water.m_height = abs(aabb.m_max.z - aabb.m_min.z)

    return water


def __parse_env_map(obj) -> rwd.Scene.EnvMap:
    transform = __parse_transform(obj)

    envmap = rwd.Scene.EnvMap()

    name_start_index = str(obj.name).index("%", 1) + 1
    envmap.m_name = str(obj.name)[name_start_index:]
    envmap.m_pos = __fix_vec3_orientation(smt.Vec3(obj.location.x, obj.location.y, obj.location.z))

    if "pcorrect" in obj and "true" == obj["pcorrect"]:
        for face in obj.data.polygons:
            point = __fix_vec3_orientation(smt.Vec3(face.center.x, face.center.y, face.center.z))
            normal = __fix_vec3_orientation(smt.Vec3(face.normal.x, face.normal.y, face.normal.z))

            point = transform.transform(point)
            normal = transform.transform0(normal)
            normal.normalize()

            plane = smt.Plane()
            plane.setPointNormal(point, normal)
            envmap.m_volume.append(plane)

    return envmap


def __parse_objects(objects: iter, scene: rwd.Scene, ignore_hidden: bool) -> None:
    for obj in objects:
        type_str = str(obj.type)
        obj_name = str(obj.name)

        if _BLENDER_OBJ_TYPE_MESH == type_str:
            if "%" == obj_name[0]:
                tail = obj_name.find("%", 1)
                if -1 == tail:
                    tail = len(obj_name)
                special_mesh_type = obj_name[1:tail]

                if "envmap" == special_mesh_type:
                    print("[DAL] Parsing environment map: " + obj_name)
                    envmap = __parse_env_map(obj)
                    scene.m_envmaps.append(envmap)
                elif "water" == special_mesh_type:
                    print("[DAL] Parsing water: " + obj_name)
                    water = __parse_water_plane(obj)
                    scene.m_waters.append(water)
                else:
                    raise RuntimeError(
                        "invalid special mesh type \'{}\' for object \'{}\'".format(special_mesh_type, obj_name)
                    )
            else:
                if (not obj.visible_get()) and ignore_hidden:
                    print("[DAL] Ignoring hidden actor: {}, {}".format(obj_name, type_str))
                    scene.m_skipped_objs.append((obj.name, "Hidden object"))
                    continue

                print("[DAL] Parsing actor: " + obj_name)
                data_id = id(obj.data)
                if data_id not in scene.m_models.keys():
                    scene.m_models[data_id] = __parse_model(obj, data_id)
                scene.m_models[data_id].m_refCount += 1

                actor = rwd.Scene.StaticActor()
                actor.m_name = obj.name
                actor.m_renderUnitID = data_id
                actor.m_transform = __parse_transform(obj)

                for key in (str(xx) for xx in obj.keys()):
                    if key in __PROPERTIES_TO_IGNORE:
                        continue
                    elif "collider" == key:
                        value = obj[key]
                        if "" == value:
                            actor.m_collider = rwd.Scene.StaticActor.ColliderType.aabb
                        elif value in rwd.Scene.StaticActor.COLLIDER_TYPE_MAP.keys():
                            actor.m_collider = rwd.Scene.StaticActor.COLLIDER_TYPE_MAP[value]
                        else:
                            raise RuntimeError("Unidentified collider type '{}' in object '{}'".format(value, obj_name))

                        if rwd.Scene.StaticActor.ColliderType.mesh == actor.m_collider:
                            scene.m_models[data_id].m_hasMeshCollider = True
                    elif key.startswith("envmap"):
                        postfix = key[6:]
                        if "" == postfix:
                            actor.setDefaultEnv(obj[key])
                        elif postfix.isnumeric():
                            actor.setEnvmapOf(int(postfix), obj[key])
                        else:
                            raise RuntimeError("Invalid envmap syntax \'{}\' for \'{}\'".format(key, obj.name))
                    else:
                        print("[DAL] WARN: property '{}' ignored in object '{}'".format(key, obj_name))

                scene.m_static_actors.append(actor)
        elif _BLENDER_OBJ_TYPE_ARMATURE == type_str:
            print("[DAL] Parsing skeleton: " + obj_name)
            skeleton = __parse_skeleton(obj.data)
            scene.m_skeletons.append(skeleton)
        elif _BLENDER_OBJ_TYPE_LIGHT == type_str:
            if isinstance(obj.data, bpy.types.PointLight):
                print("[DAL] Parsing point light: " + obj_name)
                plight = __parse_light_point(obj)
                scene.m_plights.append(plight)
            elif isinstance(obj.data, bpy.types.SunLight):
                print("[DAL] Parsing sun light: " + obj_name)
                dlight = __parse_light_directional(obj)
                scene.m_dlights.append(dlight)
            elif isinstance(obj.data, bpy.types.SpotLight):
                print("[DAL] Parsing spot light: " + obj_name)
                slight = __parse_light_spot(obj)
                scene.m_slights.append(slight)
            else:
                raise RuntimeError("Unkown type of light: {}".format(type(obj.data)))
        else:
            print("[DAL] Ignoring not supported object type: {}, {}".format(obj_name, type_str))
            scene.m_skipped_objs.append((obj.name, "Not supported object type: {}".format(type_str)))


def parse_raw_data() -> rwd.Scene:
    scene = rwd.Scene()

    __parse_objects(_gen_blender_objects(), scene, True)

    for action in bpy.data.actions:
        animation = __parse_animation(action)
        animation.cleanUp()
        animation.removeUselessJoints()
        scene.m_animations.append(animation)

    return scene


def parse_raw_data_map() -> Dict[str, rwd.Scene]:
    scenes: Dict[str, rwd.Scene] = {}

    for collection in bpy.data.collections:
        scene = rwd.Scene()
        __parse_objects(collection.all_objects, scene, False)
        scenes[collection.name] = scene

    return scenes
