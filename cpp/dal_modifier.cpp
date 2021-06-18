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

    ::str_set_t make_set_union(const ::str_set_t& a, const ::str_set_t& b) {
        ::str_set_t output;
        output.insert(a.begin(), a.end());
        output.insert(b.begin(), b.end());
        return output;
    }

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

    ::str_set_t get_vital_joint_names(const dal::parser::Skeleton& skeleton) {
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

    ::str_set_t get_joint_names_with_non_identity_transform(const std::vector<dal::parser::Animation>& animations, const dal::parser::Skeleton& skeleton) {
        ::str_set_t output;

        if (skeleton.m_joints.empty())
            return output;

        // Root nodes
        for (auto& joint : skeleton.m_joints) {
            if (-1 == joint.m_parent_index) {
                output.insert(joint.m_name);
            }
        }

        // Nodes with keyframes
        for (auto& anim : animations) {
            for (auto& joint : anim.m_joints) {
                if (!::is_joint_useless(joint)) {
                    output.insert(joint.m_name);
                }
            }
        }

        return output;
    }


    class JointParentNameManager {

    private:
        struct JointParentName {
            std::string m_name, m_parent_name;
        };

    public:
        const std::string NO_PARENT_NAME = "{%{%-1%}%}";

    private:
        std::vector<JointParentName> m_data;
        std::unordered_map<std::string, std::string> m_replace_map;

    public:
        void fill_joints(const dal::parser::Skeleton& skeleton) {
            this->m_data.resize(skeleton.m_joints.size());

            for (size_t i = 0; i < skeleton.m_joints.size(); ++i) {
                auto& joint = skeleton.m_joints[i];

                this->m_data[i].m_name = joint.m_name;
                if (-1 != joint.m_parent_index)
                    this->m_data[i].m_parent_name = skeleton.m_joints[joint.m_parent_index].m_name;
                else
                    this->m_data[i].m_parent_name = this->NO_PARENT_NAME;

                this->m_replace_map[joint.m_name] = joint.m_name;
            }
        }

        void remove_joint(const std::string& name) {
            const auto found_index = this->find_by_name(name);
            if (-1 == found_index)
                return;

            const auto parent_of_victim = this->m_data[found_index].m_parent_name;
            this->m_data.erase(this->m_data.begin() + found_index);

            for (auto& joint : this->m_data) {
                if (joint.m_parent_name == name) {
                    joint.m_parent_name = parent_of_victim;
                }
            }

            for (auto& iter : this->m_replace_map) {
                if (iter.second == name) {
                    iter.second = parent_of_victim;
                }
            }
        }

        void remove_except(const ::str_set_t& survivor_names) {
            const auto names_to_remove = ::make_set_difference(this->make_names_set(), survivor_names);

            for (auto& name : names_to_remove) {
                this->remove_joint(name);
            }
        }

        ::str_set_t make_names_set() const {
            ::str_set_t output;

            for (auto& joint : this->m_data) {
                output.insert(joint.m_name);
            }

            return output;
        }

        auto& get_replaced_name(const std::string& name) const {
            if (name == this->NO_PARENT_NAME) {
                return this->NO_PARENT_NAME;
            }
            else {
                return this->m_replace_map.find(name)->second;
            }
        }

    private:
        jointID_t find_by_name(const std::string& name) {
            if (this->NO_PARENT_NAME == name)
                return -1;

            for (jointID_t i = 0; i < this->m_data.size(); ++i) {
                if (this->m_data[i].m_name == name) {
                    return i;
                }
            }

            return -1;
        }

    };

    dal::parser::Skeleton make_new_skeleton(const dal::parser::Skeleton& src_skeleton, const JointParentNameManager& jname_manager) {
        dal::parser::Skeleton output;
        const auto survivor_joints = jname_manager.make_names_set();

        for (auto& src_joint : src_skeleton.m_joints) {
            if (survivor_joints.end() == survivor_joints.find(src_joint.m_name))
                continue;

            const std::string& parent_name = (-1 != src_joint.m_parent_index) ? src_skeleton.m_joints[src_joint.m_parent_index].m_name : jname_manager.NO_PARENT_NAME;
            const auto& parent_replace_name = jname_manager.get_replaced_name(parent_name);
            output.m_joints.push_back(src_joint);
        }

        for (auto& joint : output.m_joints) {
            if (-1 == joint.m_parent_index)
                continue;

            const auto& original_parent_name = src_skeleton.m_joints[joint.m_parent_index].m_name;
            const auto& new_parent_name = jname_manager.get_replaced_name(original_parent_name);
            if (jname_manager.NO_PARENT_NAME != new_parent_name) {
                joint.m_parent_index = output.find_by_name(new_parent_name);
            }
            else {
                joint.m_parent_index = -1;
            }
        }

        return output;
    }

    std::unordered_map<jointID_t, jointID_t> make_index_replace_map(
        const dal::parser::Skeleton& from_skeleton,
        const dal::parser::Skeleton& to_skeleton,
        const JointParentNameManager& jname_manager
    ) {
        std::unordered_map<jointID_t, jointID_t> output;
        output[-1] = -1;

        for (size_t i = 0; i < from_skeleton.m_joints.size(); ++i) {
            const auto& from_name = from_skeleton.m_joints[i].m_name;
            const auto& to_name = jname_manager.get_replaced_name(from_name);
            const auto to_index = to_skeleton.find_by_name(to_name);
            assert(-1 != to_index);
            output[i] = to_index;
        }

        return output;
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

        const auto needed_joint_names = ::make_set_union(
            ::get_joint_names_with_non_identity_transform(model.m_animations, model.m_skeleton),
            ::get_vital_joint_names(model.m_skeleton)
        );

        ::JointParentNameManager joint_parent_names;
        joint_parent_names.fill_joints(model.m_skeleton);
        joint_parent_names.remove_except(needed_joint_names);

        const auto new_skeleton = ::make_new_skeleton(model.m_skeleton, joint_parent_names);
        const auto index_replace_map = ::make_index_replace_map(model.m_skeleton, new_skeleton, joint_parent_names);

        for (auto& unit : model.m_units_indexed_joint) {
            for (auto& vert : unit.m_mesh.m_vertices) {
                for (size_t i = 0; i < 4; ++i) {
                    const auto new_index = index_replace_map.find(vert.m_joint_indices[i])->second;
                    assert(-1 <= new_index && new_index < static_cast<int64_t>(new_skeleton.m_joints.size()));
                    vert.m_joint_indices[i] = new_index;
                }
            }
        }

        for (auto& unit : model.m_units_straight_joint) {
            for (auto& index : unit.m_mesh.m_boneIndex) {
                const auto new_index = index_replace_map.find(index)->second;
                assert(-1 <= new_index && new_index < static_cast<int64_t>(new_skeleton.m_joints.size()));
                index = new_index;
            }
        }

        model.m_skeleton = new_skeleton;

        return true;
    }

}
