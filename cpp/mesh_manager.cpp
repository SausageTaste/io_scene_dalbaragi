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


// FlatVertexBuffer
namespace b3dsung {

    void FlatVertexBuffer::set(VertexBuffer& vbuf) {
        this->vertex_count_ = vbuf.vertices_.size();

        for (auto& vert : vbuf.vertices_) {
            vertices_.append_float32(vert.pos_.x);
            vertices_.append_float32(vert.pos_.y);
            vertices_.append_float32(vert.pos_.z);

            uv_coords_.append_float32(vert.uv_coord_.x);
            uv_coords_.append_float32(vert.uv_coord_.y);

            normals_.append_float32(vert.normal_.x);
            normals_.append_float32(vert.normal_.y);
            normals_.append_float32(vert.normal_.z);

            vert.sort_joints();
            joints_.append_int32(vert.joints_.size());
            for (auto& [j_weight, j_index] : vert.joints_) {
                joints_.append_int32(j_index);
                joints_.append_float32(j_weight);
            }
        }
    }

    void FlatVertexBuffer::make_json(json_class& output, BinaryBuilder& bin_array) {
        output["vertex count"] = this->vertex_count_;

        // Vertices
        {
            auto [pos, size] = bin_array.add_bin_array(this->vertices_.data(), this->vertices_.size());
            output["vertices binary data"]["position"] = pos;
            output["vertices binary data"]["size"] = size;
        }

        // UV coordinates
        {
            auto [pos, size] = bin_array.add_bin_array(this->uv_coords_.data(), this->uv_coords_.size());
            output["uv coordinates binary data"]["position"] = pos;
            output["uv coordinates binary data"]["size"] = size;
        }

        // Normals
        {
            auto [pos, size] = bin_array.add_bin_array(this->normals_.data(), this->normals_.size());
            output["normals binary data"]["position"] = pos;
            output["normals binary data"]["size"] = size;
        }

        // Joints
        {
            auto [pos, size] = bin_array.add_bin_array(this->joints_.data(), this->joints_.size());
            output["joints binary data"]["position"] = pos;
            output["joints binary data"]["size"] = size;
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

    void Mesh::build_flat() {
        for (auto& [material_name, vertex_buffer] : this->vertex_buffers_) {
            vertex_buffer.second.set(vertex_buffer.first);
        }
    }

    void Mesh::make_json(json_class& output, BinaryBuilder& bin_array) {
        for (auto& [material_name, vertex_buffer] : this->vertex_buffers_) {
            auto& one = json_class::object();
            one["name"] = this->get_mangled_name(material_name.c_str());
            one["skeleton name"] = this->skeleton_name_;
            vertex_buffer.second.make_json(one, bin_array);
            output.push_back(one);
        }
    }

    // Private

    VertexBuffer& Mesh::get_vert_buf(const char* const material_name) {
        auto found = this->vertex_buffers_.find(material_name);
        if (found != this->vertex_buffers_.end()) {
            return found->second.first;
        }
        else {
            return this->vertex_buffers_.emplace(material_name, std::pair<VertexBuffer, FlatVertexBuffer>{}).first->second.first;
        }
    }

}
