#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>

#include "dal_model_parser.h"
#include "dal_modifier.h"
#include "dal_byte_tool.h"


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
        dal::parser::Model_Straight model;
        const auto result = dal::parser::parse_model_straight(model_data.data(), model_data.size(), model);

        std::cout << "    * Loaded and parsed" << std::endl;
        std::cout << "        result code: " << static_cast<int>(result) << std::endl;
        std::cout << "        render units: " << model.m_render_units.size() << std::endl;
        std::cout << "        joints: " << model.m_skeleton.m_joints.size() << std::endl;
        std::cout << "        animations: " << model.m_animations.size() << std::endl;

        {
            size_t vertices_before = 0;
            size_t vertices_after = 0;

            for (const auto& unit : model.m_render_units) {
                assert(0 == unit.m_mesh.m_vertices.size() % 3);
                const auto indexed_mesh = dal::parser::convert_to_indexed(unit.m_mesh);
                vertices_before += unit.m_mesh.m_vertices.size() / 3;
                vertices_after += indexed_mesh.m_vertices.size();
            }

            std::cout << "    * Converted to indexed (polygons): " << vertices_before << " -> " << vertices_after << std::endl;
        }

        {
            const auto merged_by_mat = dal::parser::merge_by_material(model);
            std::cout << "    * Merged by materials (render units): " << model.m_render_units.size() << " -> " << merged_by_mat.m_render_units.size() << std::endl;
        }
    }

    void test_a_model(const std::string& model_path) {
        ::test_a_model(model_path.c_str());
    }

}


int main() {
    std::cout << std::endl; ::test_a_model(::find_cpp_path() + "/test/irin.dmd");
    std::cout << std::endl; ::test_a_model(::find_cpp_path() + "/test/sphere.dmd");
    std::cout << std::endl; ::test_byte_tools();
}
