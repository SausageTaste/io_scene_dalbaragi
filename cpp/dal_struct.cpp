#include "dal_struct.h"


namespace dal::parser {

    bool Vertex::operator==(const Vertex& other) const {
        return (
            this->m_position == other.m_position &&
            this->m_uv_coords == other.m_uv_coords &&
            this->m_normal == other.m_normal &&
            this->m_joint_weights == other.m_joint_weights &&
            this->m_joint_indices == other.m_joint_indices
        );
    }


    void Mesh_Indexed::add_vertex(const Vertex& vert) {
        for (size_t i = 0; i < this->m_vertices.size(); ++i) {
            if (vert == this->m_vertices[i]) {
                this->m_indices.push_back(i);
                return;
            }
        }

        this->m_indices.push_back(this->m_vertices.size());
        this->m_vertices.push_back(vert);
    }


    void AnimJoint::add_translate(float time, float x, float y, float z) {
        auto& added = this->m_translates.emplace_back();

        added.first = time;
        added.second = glm::vec3{ x, y, z };
    }

    void AnimJoint::add_rotation(float time, float w, float x, float y, float z) {
        auto& added = this->m_rotations.emplace_back();

        added.first = time;
        added.second = glm::quat{ w, x, y, z };
    }

    void AnimJoint::add_scale(float time, float x) {
        auto& added = this->m_scales.emplace_back();

        added.first = time;
        added.second = x;
    }

}
