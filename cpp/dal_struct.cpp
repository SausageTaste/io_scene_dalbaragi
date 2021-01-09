#include "dal_struct.h"


namespace dal::parser {

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
