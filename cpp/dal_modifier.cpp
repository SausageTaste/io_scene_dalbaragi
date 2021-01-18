#include "dal_modifier.h"


namespace {

    void fill_mesh_skinned(dal::parser::Mesh_Indexed& output, const dal::parser::Mesh_Straight& input) {
        const auto vertex_count = input.m_vertices.size() / 3;

        for (int i = 0; i < vertex_count; ++i) {
            dal::parser::Vertex vert;

            vert.m_position = glm::vec3{
                input.m_vertices[3 * i + 0],
                input.m_vertices[3 * i + 1],
                input.m_vertices[3 * i + 2]
            };

            vert.m_uv_coords = glm::vec2{
                input.m_texcoords[2 * i + 0],
                input.m_texcoords[2 * i + 1]
            };

            vert.m_normal = glm::vec3{
                input.m_normals[3 * i + 0],
                input.m_normals[3 * i + 1],
                input.m_normals[3 * i + 2]
            };

            vert.m_joint_weights = glm::vec3{
                input.m_boneWeights[3 * i + 0],
                input.m_boneWeights[3 * i + 1],
                input.m_boneWeights[3 * i + 2]
            };

            vert.m_joint_indices = glm::ivec3{
                input.m_boneIndex[3 * i + 0],
                input.m_boneIndex[3 * i + 1],
                input.m_boneIndex[3 * i + 2]
            };

            output.add_vertex(vert);
        }

    }

    void fill_mesh_basic(dal::parser::Mesh_Indexed& output, const dal::parser::Mesh_Straight& input) {
        const auto vertex_count = input.m_vertices.size() / 3;

        for (int i = 0; i < vertex_count; ++i) {
            dal::parser::Vertex vert;

            vert.m_position = glm::vec3{
                input.m_vertices[3 * i + 0],
                input.m_vertices[3 * i + 1],
                input.m_vertices[3 * i + 2]
            };

            vert.m_uv_coords = glm::vec2{
                input.m_texcoords[2 * i + 0],
                input.m_texcoords[2 * i + 1]
            };

            vert.m_normal = glm::vec3{
                input.m_normals[3 * i + 0],
                input.m_normals[3 * i + 1],
                input.m_normals[3 * i + 2]
            };

            vert.m_joint_weights = glm::vec3{ 0 };
            vert.m_joint_indices = glm::ivec3{ -1 };

            output.add_vertex(vert);
        }

    }

}


namespace dal::parser {

    Mesh_Indexed convert_to_indexed(const Mesh_Straight& input) {
        Mesh_Indexed output;

        const auto vertex_count = input.m_vertices.size() / 3;
        assert(2 * vertex_count == input.m_texcoords.size());
        assert(3 * vertex_count == input.m_normals.size());

        if (input.m_boneIndex.empty()) {
            output.m_has_joints = false;
            ::fill_mesh_basic(output, input);
        }
        else {
            assert(3 * vertex_count == input.m_boneIndex.size());
            assert(3 * vertex_count == input.m_boneWeights.size());

            output.m_has_joints = true;
            ::fill_mesh_skinned(output, input);
        }

        return output;
    }

}
