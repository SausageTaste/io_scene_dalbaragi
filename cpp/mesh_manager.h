#pragma once

#include <map>
#include <vector>
#include <string>

#include <glm/glm.hpp>


namespace b3dsung {

    class BinaryBuilder {

    private:
        std::vector<uint8_t> data_;

    public:
        auto data() const {
            return this->data_.data();
        }

        auto size() const {
            return this->data_.size();
        }

        std::pair<size_t, size_t> add_bin_array(const uint8_t* const buf, const size_t size) {
            const auto start_index = this->data_.size();
            this->data_.insert(this->data_.end(), buf, buf + size);
            const auto end_index = this->data_.size();
            return std::make_pair(start_index, end_index - start_index);
        }

    };


    struct Vertex {
        glm::vec3 pos_;
        glm::vec3 normal_;
        glm::vec2 uv_coord_;
        std::vector<std::pair<float, int32_t>> joints_;

        void add_joint(const int32_t joint_index, const float weight) {
            this->joints_.emplace_back(weight, joint_index);
        }
    };


    struct VertexBuffer {
        std::vector<Vertex> vertices_;
    };


    class Mesh {

    public:
        std::string name_;
        std::string skeleton_name_;
        std::map<std::string, VertexBuffer> vertex_buffers_;

    public:
        bool has_material(const char* const material_name) const;

        Vertex& new_vertex(const char* const material_name);

        std::string get_mangled_name(const char* const material_name) const;

    private:
        VertexBuffer& get_vert_buf(const char* const material_name);

    };


    class MeshManager {

    private:
        std::vector<Mesh> meshes_;

    public:
        const Mesh* find_by_name(const char* const name) const;

        bool has_mesh(const char* const name) const;

        Mesh* find_by_name(const char* const name);

        Mesh& new_mesh(const char* const name);

        // Pair of mesh name, material name
        std::vector<std::pair<std::string, std::string>> get_mesh_mat_pairs(const char* const mesh_name) const;

    };

}
