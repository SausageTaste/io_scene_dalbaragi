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


    class FlatVertexBuffer {

    public:
        size_t vertex_count_ = 0;
        dal::parser::BinaryDataArray vertices_, uv_coords_, normals_, joints_;

    public:
        void set(VertexBuffer& vbuf);

        void make_json(json_class& output, BinaryBuilder& bin_array);

    };


    class Mesh {

    public:
        std::string name_;
        std::string skeleton_name_;
        std::map<std::string, std::pair<VertexBuffer, FlatVertexBuffer>> vertex_buffers_;

    public:
        bool has_material(const char* const material_name) const;

        Vertex& new_vertex(const char* const material_name);

        std::string get_mangled_name(const char* const material_name) const;

        void build_flat();

        void make_json(json_class& output, BinaryBuilder& bin_array);

    private:
        VertexBuffer& get_vert_buf(const char* const material_name);

    };

}
