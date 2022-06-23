#include "mesh_manager.h"

#include <cassert>
#include <algorithm>

// Vertex
namespace b3dsung {

    void Vertex::add_joint(const int32_t joint_index, const float weight) {
        this->joints_.emplace_back(weight, joint_index);
    }

    void Vertex::sort_joints() {
        std::sort(this->joints_.begin(), this->joints_.end(), std::greater<>());
    }

}

// VertexBuffer
namespace b3dsung {

    void VertexBuffer::make_json(json_class& output, BinaryBuilder& bin_array) {
        output["vertex count"] = this->vertices_.size();

        // Vertices
        {
            const auto start_index = bin_array.size();
            for (auto& vert : this->vertices_) {
                bin_array->append_float32(vert.pos_.x);
                bin_array->append_float32(vert.pos_.y);
                bin_array->append_float32(vert.pos_.z);
            }
            const auto end_index = bin_array.size();

            output["vertices binary data"]["position"] = start_index;
            output["vertices binary data"]["size"] = end_index - start_index;
        }

        // UV coordinates
        {
            const auto start_index = bin_array.size();
            for (auto& vert : this->vertices_) {
                bin_array->append_float32(vert.uv_coord_.x);
                bin_array->append_float32(vert.uv_coord_.y);
            }
            const auto end_index = bin_array.size();

            output["uv coordinates binary data"]["position"] = start_index;
            output["uv coordinates binary data"]["size"] = end_index - start_index;
        }

        // Normals
        {
            const auto start_index = bin_array.size();
            for (auto& vert : this->vertices_) {
                bin_array->append_float32(vert.normal_.x);
                bin_array->append_float32(vert.normal_.y);
                bin_array->append_float32(vert.normal_.z);
            }
            const auto end_index = bin_array.size();

            output["normals binary data"]["position"] = start_index;
            output["normals binary data"]["size"] = end_index - start_index;
        }

        // Joints
        {
            const auto start_index = bin_array.size();
            for (auto& vert : this->vertices_) {
                vert.sort_joints();

                bin_array->append_int32(vert.joints_.size());
                for (auto& [j_weight, j_index] : vert.joints_) {
                    bin_array->append_int32(j_index);
                    bin_array->append_float32(j_weight);
                }
            }
            const auto end_index = bin_array.size();

            output["joints binary data"]["position"] = start_index;
            output["joints binary data"]["size"] = end_index - start_index;
        }
    }

}


// Mesh
namespace b3dsung {

    bool Mesh::has_material(const char* const material_name) const {
        for (auto& [mat_name, vert_buf] : this->vertex_buffers_) {
            if (mat_name == material_name) {
                return true;
            }
        }
        return false;
    }

    Vertex& Mesh::new_vertex(const char* const material_name) {
        auto& vbuf = this->get_vert_buf(material_name);
        return vbuf.vertices_.emplace_back();
    }

    std::string Mesh::get_mangled_name(const char* const material_name) const {
        assert(this->has_material(material_name));

        if (1 == this->vertex_buffers_.size()) {
            return this->name_;
        }
        else {
            return this->name_ + "+" + material_name;
        }
    }

    void Mesh::make_json(json_class& output, BinaryBuilder& bin_array) {
        for (auto& [material_name, vertex_buffer] : this->vertex_buffers_) {
            auto& one = json_class::object();
            one["name"] = this->get_mangled_name(material_name.c_str());
            one["skeleton name"] = this->skeleton_name_;
            vertex_buffer.make_json(one, bin_array);
            output.push_back(one);
        }
    }

    // Private

    VertexBuffer& Mesh::get_vert_buf(const char* const material_name) {
        auto found = this->vertex_buffers_.find(material_name);
        if (found != this->vertex_buffers_.end()) {
            return found->second;
        }
        else {
            return this->vertex_buffers_.emplace(material_name, VertexBuffer{}).first->second;
        }
    }

}


// MeshManager
namespace b3dsung {

    using namespace std;


    bool MeshManager::has_mesh(const char* const name) const {
        for (auto& mesh : this->meshes_) {
            if (mesh.name_ == name) {
                return true;
            }
        }
        return false;
    }

    const Mesh* MeshManager::find_by_name(const char* const name) const {
        for (auto& mesh : this->meshes_) {
            if (mesh.name_ == name) {
                return &mesh;
            }
        }

        return nullptr;
    }

    Mesh* MeshManager::find_by_name(const char* const name) {
        for (auto& mesh : this->meshes_) {
            if (mesh.name_ == name) {
                return &mesh;
            }
        }
        return nullptr;
    }

    Mesh& MeshManager::new_mesh(const char* const name) {
        auto& mesh = this->meshes_.emplace_back();
        mesh.name_ = name;
        return mesh;
    }

    json_class MeshManager::make_json(BinaryBuilder& bin_array) {
        auto output = json_class::array();
        for (auto& mesh : this->meshes_) {
            mesh.make_json(output, bin_array);
        }
        return output;
    }

    vector<pair<string, string>> MeshManager::get_mesh_mat_pairs(const char* const mesh_name) const {
        std::vector<std::pair<std::string, std::string>> output;

        const auto mesh = this->find_by_name(mesh_name);
        if (nullptr == mesh) {
            return output;
        }

        for (auto& [mat_name, vert_buf] : mesh->vertex_buffers_) {
            output.emplace_back(mesh->get_mangled_name(mat_name.c_str()), mat_name);
        }

        return output;
    }

}
