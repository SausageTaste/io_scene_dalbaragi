#include "dal_modifier.h"

#include <unordered_set>
#include <unordered_map>


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

    using str_set_t = std::unordered_set<std::string>;

    ::str_set_t make_set_intersection(const ::str_set_t& a, const ::str_set_t& b) {
        ::str_set_t output;

        auto& smaller_set = a.size() < b.size() ? a : b;
        auto& larger_set = a.size() < b.size() ? b : a;

        for (auto iter = smaller_set.begin(); iter != smaller_set.end(); ++iter) {
            if (larger_set.end() != larger_set.find(*iter)) {
                output.insert(*iter);
            }
        }

        return output;
    }

    ::str_set_t make_set_difference(const ::str_set_t& a, const ::str_set_t& b) {
        ::str_set_t output;

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
        ::str_set_t output;

        for (auto& joint : anim.m_joints) {
            if (::is_joint_useless(joint)) {
                output.insert(joint.m_name);
            }
        }

        return output;
    }

    auto get_vital_joint_names(const dal::parser::Skeleton& skeleton) {
        // Super parents' children are all vital
        ::str_set_t output, super_parents;

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


    class JointReplaceMap {

    private:
        std::unordered_map<std::string, std::string> m_map;

    public:
        JointReplaceMap(const dal::parser::Skeleton& skeleton) {
            for (auto& joint : skeleton.m_joints) {
                this->m_map[joint.m_name] = joint.m_name;
            }
        }

        void replace(const std::string& from_name, const std::string& to_name) {
            for (auto& iter : this->m_map) {
                if (iter.first == from_name) {
                    iter.second = to_name;
                }
            }
        }

    };

    bool is_joint_order_valid(const dal::parser::Skeleton& skeleton) {
        if (-1 != skeleton.m_joints[0].m_parent_index)
            return false;

        for (size_t i = 1; i < skeleton.m_joints.size(); ++i) {
            const auto& joint_i = skeleton.m_joints[i];
            const auto& parent_name = skeleton.m_joints[joint_i.m_parent_index].m_name;

            if (parent_name.empty())
                continue;

            bool has_parent = false;

            for (size_t j = 0; j < skeleton.m_joints.size(); ++j) {
                const auto& joint_j = skeleton.m_joints[j];

                if (joint_j.m_name == parent_name) {
                    if (i <= j) {
                        return false;
                    }
                    else {
                        has_parent = true;
                        break;
                    }
                }
            }

            if (!has_parent)
                return false;
        }
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


    bool reduce_joints(dal::parser::Model& model) {
        if (model.m_animations.empty())
            return false;
        if (!::is_joint_order_valid(model.m_skeleton))
            return false;

        const auto to_remove = ::get_joint_names_to_remove(model.m_animations, model.m_skeleton);

        return true;
    }

}
