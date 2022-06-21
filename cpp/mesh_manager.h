#pragma once

#include <map>
#include <vector>
#include <string>


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


    struct Vec3 {
        float x = 0, y = 0, z = 0;
    };


    struct Vec2 {
        float x = 0, y = 0;
    };


    struct Vertex {
        Vec3 pos_;
        Vec3 normal_;
        Vec2 uv_coord_;
        std::vector<std::pair<float, int32_t>> joints_;
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

        std::string get_mangled_name(const char* const material_name) const;

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
