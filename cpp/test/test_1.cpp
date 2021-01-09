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


int main() {
    const auto model_path = ::find_cpp_path() + "/test/irin.dmd";
    const auto model_data = ::read_file(model_path.c_str());

    dal::parser::Model_Straight model;
    const auto result = dal::parser::parse_model_straight(model_data.data(), model_data.size(), model);

    std::cout << "Result code: " << static_cast<int>(result) << std::endl;
    std::cout << "Render unit count: " << model.m_render_units.size() << std::endl;
    std::cout << "Joint count: " << model.m_skeleton.m_joints.size() << std::endl;
    std::cout << "Animation count: " << model.m_animations.size() << std::endl;

    const auto indexed_mesh = dal::parser::convert_to_indexed(model.m_render_units[0].m_mesh);
    std::cout << "Before indexing: " << model.m_render_units[0].m_mesh.m_vertices.size() / 3 << std::endl;
    std::cout << "After indexing: " << indexed_mesh.m_vertices.size() << std::endl;

    {
        const float TEST = 45.5;
        uint8_t buffer[4];
        dalp::to_float32(TEST, buffer);
        std::cout << "After casting: " << dalp::make_float32(buffer) << std::endl;
    }

    {
        const int32_t TEST = 76;
        uint8_t buffer[4];
        dalp::to_int32(TEST, buffer);
        std::cout << "After casting: " << dalp::make_int32(buffer) << std::endl;
    }

    {
        const int32_t TEST = 72;
        uint8_t buffer[2];
        dalp::to_int16(TEST, buffer);
        std::cout << "After casting: " << dalp::make_int16(buffer) << std::endl;
    }
}
