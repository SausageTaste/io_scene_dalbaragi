#pragma once

#include <map>
#include <vector>
#include <string>

#include <glm/glm.hpp>
#include <nlohmann/json.hpp>

#include <daltools/byte_tool.h>


namespace b3dsung {

    using json_class = nlohmann::json;


    class BinaryBuilder {

    private:
        dal::parser::BinaryDataArray data_;

    public:
        dal::parser::BinaryDataArray* operator->() {
            return &this->data_;
        }

        auto data() const {
            return this->data_.data();
        }

        auto size() const {
            return this->data_.size();
        }

        std::pair<size_t, size_t> add_bin_array(const uint8_t* const buf, const size_t size) {
            const auto start_index = this->size();
            this->data_.insert_back(buf, buf + size);
            const auto end_index = this->size();
            return std::make_pair(start_index, end_index - start_index);
        }

    };


    struct Vertex {

    public:
        glm::vec3 pos_;
        glm::vec3 normal_;
        glm::vec2 uv_coord_;
        std::vector<std::pair<float, int32_t>> joints_;


    public:
        void add_joint(const int32_t joint_index, const float weight);

        void sort_joints();

    };


    struct VertexBuffer {

    public:
        std::vector<Vertex> vertices_;

    public:
        void make_json(json_class& output, BinaryBuilder& bin_array);

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

        void make_json(json_class& output, BinaryBuilder& bin_array);

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

        json_class make_json(BinaryBuilder& bin_array);

        // Pair of mesh name, material name
        std::vector<std::pair<std::string, std::string>> get_mesh_mat_pairs(const char* const mesh_name) const;

    };

}
