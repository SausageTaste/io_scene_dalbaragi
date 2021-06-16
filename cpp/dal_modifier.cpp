#include "dal_modifier.h"

#include <unordered_set>


namespace {

    void fill_mesh_skinned(dal::parser::Mesh_IndexedJoint& output, const dal::parser::Mesh_StraightJoint& input) {
        const auto vertex_count = input.m_vertices.size() / 3;

        for (size_t i = 0; i < vertex_count; ++i) {
            dal::parser::VertexJoint vert;

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

            static_assert(4 == dal::parser::NUM_JOINTS_PER_VERTEX);

            vert.m_joint_weights = glm::vec4{
                input.m_boneWeights[dal::parser::NUM_JOINTS_PER_VERTEX * i + 0],
                input.m_boneWeights[dal::parser::NUM_JOINTS_PER_VERTEX * i + 1],
                input.m_boneWeights[dal::parser::NUM_JOINTS_PER_VERTEX * i + 2],
                input.m_boneWeights[dal::parser::NUM_JOINTS_PER_VERTEX * i + 3]
            };

            vert.m_joint_indices = glm::ivec4{
                input.m_boneIndex[dal::parser::NUM_JOINTS_PER_VERTEX * i + 0],
                input.m_boneIndex[dal::parser::NUM_JOINTS_PER_VERTEX * i + 1],
                input.m_boneIndex[dal::parser::NUM_JOINTS_PER_VERTEX * i + 2],
                input.m_boneIndex[dal::parser::NUM_JOINTS_PER_VERTEX * i + 3]
            };

            output.add_vertex(vert);
        }

    }

    void fill_mesh_basic(dal::parser::Mesh_Indexed& output, const dal::parser::Mesh_Straight& input) {
        const auto vertex_count = input.m_vertices.size() / 3;

        for (size_t i = 0; i < vertex_count; ++i) {
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

            output.add_vertex(vert);
        }

    }


    template <typename _Mesh>
    dal::parser::RenderUnit<_Mesh>* find_same_material(const dal::parser::RenderUnit<_Mesh>& criteria, std::vector<dal::parser::RenderUnit<_Mesh>>& units) {
        for (auto& x : units)
            if (x.m_material == criteria.m_material)
                return &x;

        return nullptr;
    };

    template <typename _Mesh>
    std::vector<dal::parser::RenderUnit<_Mesh>> merge_by_material(const std::vector<dal::parser::RenderUnit<_Mesh>>& units) {
        std::vector<dal::parser::RenderUnit<_Mesh>> output;
        if (units.empty())
            return output;

        output.push_back(units[0]);

        for (size_t i = 1; i < units.size(); ++i) {
            const auto& this_unit = units[i];

            if (this_unit.m_material.alpha_blend) {
                output.push_back(this_unit);
                continue;
            }

            auto dst_unit = ::find_same_material(this_unit, output);

            if (nullptr != dst_unit)
                dst_unit->m_mesh.concat(this_unit.m_mesh);
            else
                output.push_back(this_unit);
        }

        return output;
    }

}


// For reduce_joints
namespace {

    std::unordered_set<std::string> make_set_intersection(
        const std::unordered_set<std::string>& a,
        const std::unordered_set<std::string>& b
    ) {
        std::unordered_set<std::string> output;

        auto& smaller_set = a.size() < b.size() ? a : b;
        auto& larger_set = a.size() < b.size() ? b : a;

        for (auto iter = smaller_set.begin(); iter != smaller_set.end(); ++iter) {
            if (larger_set.end() != larger_set.find(*iter)) {
                output.insert(*iter);
            }
        }

        return output;
    }

    std::unordered_set<std::string> make_set_difference(
        const std::unordered_set<std::string>& a,
        const std::unordered_set<std::string>& b
    ) {
        std::unordered_set<std::string> output;

        for (auto iter = a.begin(); iter != a.end(); ++iter) {
            if (b.end() == b.find(*iter)) {
                output.insert(*iter);
            }
        }

        return output;
    }


    bool is_joint_useless(const dal::parser::AnimJoint& joint) {
        if (!joint.m_translates.empty())
            return false;
        else if (!joint.m_rotations.empty())
            return false;
        else if (!joint.m_scales.empty())
            return false;
        else
            return true;
    }

    auto get_useless_joint_names(const dal::parser::Animation& anim) {
        std::unordered_set<std::string> output;

        for (auto& joint : anim.m_joints) {
            if (::is_joint_useless(joint)) {
                output.insert(joint.m_name);
            }
        }

        return output;
    }

    auto get_vital_joint_names(const dal::parser::Skeleton& skeleton) {
        // Super parents' children are all vital
        std::unordered_set<std::string> output, super_parents;

        for (auto& joint : skeleton.m_joints) {
            if (-1 == joint.m_parent_index) {
                output.insert(joint.m_name);
            }
            else if (dal::parser::JointType::hair_root == joint.m_joint_type || dal::parser::JointType::skirt_root == joint.m_joint_type) {
                super_parents.insert(joint.m_name);
                output.insert(joint.m_name);
            }
            else {
                const auto& parent_name = skeleton.m_joints.at(joint.m_parent_index).m_name;

                if (super_parents.end() != super_parents.find(parent_name)) {
                    super_parents.insert(joint.m_name);
                    output.insert(joint.m_name);
                }
            }
        }

        return output;
    }

    auto get_joint_names_to_remove(const std::vector<dal::parser::Animation>& animations, const dal::parser::Skeleton& skeleton) {
        const auto vital_joints = ::get_vital_joint_names(skeleton);

        auto useless_joints = ::get_useless_joint_names(animations[0]);
        for (int i = 1; i < animations.size(); ++i)
            useless_joints = ::make_set_intersection(useless_joints, ::get_useless_joint_names(animations[i]));

        return ::make_set_difference(useless_joints, vital_joints);
    }

}


namespace dal::parser {

    Mesh_Indexed convert_to_indexed(const Mesh_Straight& input) {
        Mesh_Indexed output;

        const auto vertex_count = input.m_vertices.size() / 3;
        assert(2 * vertex_count == input.m_texcoords.size());
        assert(3 * vertex_count == input.m_normals.size());

        ::fill_mesh_basic(output, input);

        return output;
    }

    Mesh_IndexedJoint convert_to_indexed(const Mesh_StraightJoint& input) {
        Mesh_IndexedJoint output;

        const auto vertex_count = input.m_vertices.size() / 3;
        assert(2 * vertex_count == input.m_texcoords.size());
        assert(3 * vertex_count == input.m_normals.size());
        assert(dal::parser::NUM_JOINTS_PER_VERTEX * vertex_count == input.m_boneIndex.size());
        assert(dal::parser::NUM_JOINTS_PER_VERTEX * vertex_count == input.m_boneWeights.size());

        ::fill_mesh_skinned(output, input);

        return output;
    }


    std::vector<RenderUnit<Mesh_Straight>> merge_by_material(const std::vector<RenderUnit<Mesh_Straight>>& units) {
        return ::merge_by_material(units);
    }

    std::vector<RenderUnit<Mesh_StraightJoint>> merge_by_material(const std::vector<RenderUnit<Mesh_StraightJoint>>& units) {
        return ::merge_by_material(units);
    }

    std::vector<RenderUnit<Mesh_Indexed>> merge_by_material(const std::vector<RenderUnit<Mesh_Indexed>>& units) {
        return ::merge_by_material(units);
    }

    std::vector<RenderUnit<Mesh_IndexedJoint>> merge_by_material(const std::vector<RenderUnit<Mesh_IndexedJoint>>& units) {
        return ::merge_by_material(units);
    }


    void reduce_joints(dal::parser::Model& model) {
        if (model.m_animations.empty())
            return;

        const auto to_remove = ::get_joint_names_to_remove(model.m_animations, model.m_skeleton);

        return;
    }

}
