#pragma once

#include <map>
#include <vector>
#include <string>

#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>


namespace dal::parser {

    struct AABB3 {
        glm::vec3 m_min, m_max;
    };


    struct Mesh_Straight {
        std::vector<float> m_vertices, m_texcoords, m_normals, m_boneWeights;
        std::vector<int32_t> m_boneIndex;
    };

    struct Material {
        std::string m_albedo_map;
        std::string m_roughness_map;
        std::string m_metallic_map;
        std::string m_normal_map;
        std::string m_emision_map;
        float m_roughness = 0.5;
        float m_metallic = 1;
    };

    struct RenderUnit_Straight {
        std::string m_name;
        Mesh_Straight m_mesh;
        Material m_material;
    };


    enum class JointType {
        basic        = 0,
        hair_root    = 1,
        skirt_root   = 2,
    };

    struct SkelJoint {
        std::string m_name;
        int32_t m_parent_index;
        JointType m_joint_type;
        glm::mat4 m_offset_mat;
    };

    struct Skeleton {
        std::vector<SkelJoint> m_joints;
    };

    struct AnimJoint {
        std::string m_name;
        glm::mat4 m_transform;  // i dont remember what this was...
        std::vector<std::pair<float, glm::vec3>> m_translates;
        std::vector<std::pair<float, glm::quat>> m_rotations;
        std::vector<std::pair<float, float>> m_scales;

        void add_translate(float time, float x, float y, float z);
        void add_rotation(float time, float w, float x, float y, float z);
        void add_scale(float time, float x);
    };

    struct Animation {
        std::string m_name;
        std::vector<AnimJoint> m_joints;
        float m_duration_tick;
        float m_ticks_par_sec;
    };


    struct Model_Straight {
        std::vector<RenderUnit_Straight> m_render_units;
        std::vector<Animation> m_animations;
        Skeleton m_skeleton;
        AABB3 m_aabb;
    };

}
