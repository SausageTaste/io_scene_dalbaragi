#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>

#include "dal_model_parser.h"
#include "dal_modifier.h"
#include "dal_byte_tool.h"
#include "dal_model_exporter.h"


#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define CHECK_TRUTH(condition) { if (!(condition)) std::cout << "(" << (condition) << ") " TOSTRING(condition) << std::endl; }

namespace dalp = dal::parser;


namespace {

    std::vector<std::string> get_all_dir_within_folder(std::string folder) {
        std::vector<std::string> names;

        for (const auto & entry : std::filesystem::directory_iterator(folder)) {
            names.push_back(entry.path().filename().string());
        }

        return names;
    }

    std::string find_cpp_path() {
        std::string current_dir = ".";

        for (int i = 0; i < 10; ++i) {
            for (const auto& x : ::get_all_dir_within_folder(current_dir)) {
                if ( x == ".git" ) {
                    return current_dir + "/cpp";
                }
            }

            current_dir += "/..";
        }

        throw std::runtime_error{ "failed to find resource folder." };
    }


    std::vector<uint8_t> read_file(const char* const path) {
        std::ifstream file{ path, std::ios::ate | std::ios::binary | std::ios::in };

        if ( !file.is_open() ) {
            throw std::runtime_error(std::string{"failed to open file: "} + path);
        }

        const auto fileSize = static_cast<size_t>(file.tellg());
        std::vector<uint8_t> buffer;
        buffer.resize(fileSize);

        file.seekg(0);
        file.read(reinterpret_cast<char*>(buffer.data()), buffer.size());
        file.close();

        return buffer;
    }

    double compare_binary_buffers(const std::vector<uint8_t>& one, const std::vector<uint8_t>& two) {
        if (one.size() != two.size()) {
            return 0.0;
        }

        size_t same_count = 0;

        for (size_t i = 0; i < one.size(); ++i) {
            if (one[i] == two[i]) {
                ++same_count;
            }
        }

        return static_cast<double>(same_count) / static_cast<double>(one.size());
    }

    void compare_models(const dal::parser::Model& one, const dal::parser::Model& two) {
        CHECK_TRUTH(one.m_aabb.m_max == two.m_aabb.m_max);
        CHECK_TRUTH(one.m_aabb.m_min == two.m_aabb.m_min);

        CHECK_TRUTH(one.m_skeleton.m_joints.size() == two.m_skeleton.m_joints.size());
        for (size_t i = 0; i < std::min(one.m_skeleton.m_joints.size(), two.m_skeleton.m_joints.size()); ++i) {
            CHECK_TRUTH(one.m_skeleton.m_joints[i].m_name == two.m_skeleton.m_joints[i].m_name);
            CHECK_TRUTH(one.m_skeleton.m_joints[i].m_joint_type == two.m_skeleton.m_joints[i].m_joint_type);
            CHECK_TRUTH(one.m_skeleton.m_joints[i].m_offset_mat == two.m_skeleton.m_joints[i].m_offset_mat);
            CHECK_TRUTH(one.m_skeleton.m_joints[i].m_parent_index == two.m_skeleton.m_joints[i].m_parent_index);
        }

        CHECK_TRUTH(one.m_animations.size() == two.m_animations.size());
        for (size_t i = 0; i < std::min(one.m_animations.size(), two.m_animations.size()); ++i) {
            CHECK_TRUTH(one.m_animations[i].m_name == two.m_animations[i].m_name);
            CHECK_TRUTH(one.m_animations[i].m_duration_tick == two.m_animations[i].m_duration_tick);
            CHECK_TRUTH(one.m_animations[i].m_ticks_par_sec == two.m_animations[i].m_ticks_par_sec);

            CHECK_TRUTH(one.m_animations[i].m_joints.size() == two.m_animations[i].m_joints.size());
            for (size_t j = 0; j < std::min(one.m_animations[i].m_joints.size(), two.m_animations[i].m_joints.size()); ++j) {
                CHECK_TRUTH(one.m_animations[i].m_joints[j].m_name == two.m_animations[i].m_joints[j].m_name);
                CHECK_TRUTH(one.m_animations[i].m_joints[j].m_transform == two.m_animations[i].m_joints[j].m_transform);
                CHECK_TRUTH(one.m_animations[i].m_joints[j].m_translates == two.m_animations[i].m_joints[j].m_translates);
                CHECK_TRUTH(one.m_animations[i].m_joints[j].m_rotations == two.m_animations[i].m_joints[j].m_rotations);
                CHECK_TRUTH(one.m_animations[i].m_joints[j].m_scales == two.m_animations[i].m_joints[j].m_scales);
            }
        }

        CHECK_TRUTH(one.m_units_straight.size() == two.m_units_straight.size());
        for (size_t i = 0; i < std::min(one.m_units_straight.size(), two.m_units_straight.size()); ++i) {
            CHECK_TRUTH(one.m_units_straight[i].m_name == two.m_units_straight[i].m_name);
            CHECK_TRUTH(one.m_units_straight[i].m_material == two.m_units_straight[i].m_material);
            CHECK_TRUTH(one.m_units_straight[i].m_mesh.m_vertices == two.m_units_straight[i].m_mesh.m_vertices);
            CHECK_TRUTH(one.m_units_straight[i].m_mesh.m_texcoords == two.m_units_straight[i].m_mesh.m_texcoords);
            CHECK_TRUTH(one.m_units_straight[i].m_mesh.m_normals == two.m_units_straight[i].m_mesh.m_normals);
        }

        CHECK_TRUTH(one.m_units_straight_joint.size() == two.m_units_straight_joint.size());
        for (size_t i = 0; i < std::min(one.m_units_straight_joint.size(), two.m_units_straight_joint.size()); ++i) {
            CHECK_TRUTH(one.m_units_straight_joint[i].m_name == two.m_units_straight_joint[i].m_name);
            CHECK_TRUTH(one.m_units_straight_joint[i].m_material == two.m_units_straight_joint[i].m_material);
            CHECK_TRUTH(one.m_units_straight_joint[i].m_mesh.m_vertices == two.m_units_straight_joint[i].m_mesh.m_vertices);
            CHECK_TRUTH(one.m_units_straight_joint[i].m_mesh.m_texcoords == two.m_units_straight_joint[i].m_mesh.m_texcoords);
            CHECK_TRUTH(one.m_units_straight_joint[i].m_mesh.m_normals == two.m_units_straight_joint[i].m_mesh.m_normals);
        }

        CHECK_TRUTH(one.m_units_indexed.size() == two.m_units_indexed.size());
        CHECK_TRUTH(one.m_units_indexed_joint.size() == two.m_units_indexed_joint.size());
    }

}


namespace {

    void test_byte_tools() {
        std::cout << "< Test byte tools >" << std::endl;

        {
            const float TEST = 45.5;
            uint8_t buffer[4];
            dalp::to_float32(TEST, buffer);
            std::cout << "    after casting: " << dalp::make_float32(buffer) << std::endl;
        }

        {
            const int32_t TEST = 76;
            uint8_t buffer[4];
            dalp::to_int32(TEST, buffer);
            std::cout << "    after casting: " << dalp::make_int32(buffer) << std::endl;
        }

        {
            const int32_t TEST = 72;
            uint8_t buffer[2];
            dalp::to_int16(TEST, buffer);
            std::cout << "    after casting: " << dalp::make_int16(buffer) << std::endl;
        }
    }

    void test_a_model(const char* const model_path) {
        std::cout << "< " << model_path << " >" << std::endl;

        const auto model_data = ::read_file(model_path);
        const auto unzipped = dal::parser::unzip_dmd(model_data.data(), model_data.size());
        const auto model = dal::parser::parse_dmd(unzipped->data(), unzipped->size());

        std::cout << "    * Loaded and parsed" << std::endl;
        std::cout << "        render units straight:       " << model->m_units_straight.size() << std::endl;
        std::cout << "        render units straight joint: " << model->m_units_straight_joint.size() << std::endl;
        std::cout << "        render units indexed:        " << model->m_units_indexed.size() << std::endl;
        std::cout << "        render units indexed joint:  " << model->m_units_indexed_joint.size() << std::endl;
        std::cout << "        joints: " << model->m_skeleton.m_joints.size() << std::endl;
        std::cout << "        animations: " << model->m_animations.size() << std::endl;

        {
            size_t vertices_before = 0;
            size_t vertices_after = 0;

            for (const auto& unit : model->m_units_straight) {
                assert(0 == unit.m_mesh.m_vertices.size() % 3);
                const auto indexed_mesh = dal::parser::convert_to_indexed(unit.m_mesh);
                vertices_before += unit.m_mesh.m_vertices.size() / 3;
                vertices_after += indexed_mesh.m_vertices.size();
            }

            for (const auto& unit : model->m_units_straight_joint) {
                assert(0 == unit.m_mesh.m_vertices.size() % 3);
                const auto indexed_mesh = dal::parser::convert_to_indexed(unit.m_mesh);
                vertices_before += unit.m_mesh.m_vertices.size() / 3;
                vertices_after += indexed_mesh.m_vertices.size();
            }

            std::cout << "    * Converted to indexed (polygons): " << vertices_before << " -> " << vertices_after << std::endl;
        }

        /*{
            const auto merged_by_mat = dal::parser::merge_by_material(model);
            std::cout << "    * Merged by materials (render units): " << model.m_render_units.size() << " -> " << merged_by_mat.m_render_units.size() << std::endl;
        }*/

        {
            const auto binary = dal::parser::build_binary_model(*model);
            const auto zipped_second = dalp::zip_binary_model(binary->data(), binary->size());
            const auto unzipped_second = dalp::unzip_dmd(zipped_second->data(), zipped_second->size());

            std::cout << "    * Built binary" << std::endl;
            std::cout << "        built binary size:  " << unzipped_second->size() << std::endl;
            std::cout << "        unzipped file size: " << unzipped->size() << std::endl;
            std::cout << "        compare: " << ::compare_binary_buffers(*unzipped_second, *unzipped) << std::endl;

            const auto model_second = dal::parser::parse_dmd(unzipped_second->data(), unzipped_second->size());
            std::cout << "    * Second order model parsed" << std::endl;
            std::cout << "        render units straight:       " << model_second->m_units_straight.size() << std::endl;
            std::cout << "        render units straight joint: " << model_second->m_units_straight_joint.size() << std::endl;
            std::cout << "        render units indexed:        " << model_second->m_units_indexed.size() << std::endl;
            std::cout << "        render units indexed joint:  " << model_second->m_units_indexed_joint.size() << std::endl;
            std::cout << "        joints: " << model_second->m_skeleton.m_joints.size() << std::endl;
            std::cout << "        animations: " << model_second->m_animations.size() << std::endl;

            ::compare_models(*model, *model_second);
        }
    }

    void test_a_model(const std::string& model_path) {
        ::test_a_model(model_path.c_str());
    }

}


int main() {
    std::cout << std::endl; ::test_a_model(::find_cpp_path() + "/test/irin.dmd");
    std::cout << std::endl; ::test_byte_tools();
}
