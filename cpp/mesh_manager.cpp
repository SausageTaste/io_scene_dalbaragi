#include "mesh_manager.h"

#include <cassert>
#include <algorithm>


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
