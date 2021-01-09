#pragma once

#include <vector>
#include <string>

#include <glm/glm.hpp>


namespace dal::parser {

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
        Mesh_Straight m_mesh;
        Material m_material;
    };

    struct Model_Straight {
        int32_t result_code = 0;

        std::vector<RenderUnit_Straight> m_render_units;
    };

}
