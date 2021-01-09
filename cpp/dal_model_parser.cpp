#include "dal_model_parser.h"

#include <zlib.h>

#include "dal_byte_tool.h"
#include "konst.h"


namespace dalp = dal::parser;


namespace {

    size_t unzip(uint8_t* const dst, const size_t dst_size, const uint8_t* const src, const size_t src_size) {
        static_assert(sizeof(Bytef) == sizeof(uint8_t));

        uLongf decom_buffer_size = dst_size;

        const auto res = uncompress(dst, &decom_buffer_size, src, src_size);
        switch ( res ) {

        case Z_OK:
            return decom_buffer_size;
        case Z_BUF_ERROR:
            // dalError("Zlib fail: buffer is not large enough");
            return 0;
        case Z_MEM_ERROR:
            // dalError("Zlib fail: Insufficient memory");
            return 0;
        case Z_DATA_ERROR:
            // dalError("Zlib fail: Corrupted data");
            return 0;
        default:
            // dalError(fmt::format("Zlib fail: Unknown reason ({})", res));
            return 0;

        }
    }

    std::optional<std::vector<uint8_t>> unzip_dal_model(const uint8_t* const buf, const size_t buf_size) {
        const auto expected_unzipped_size = dal::parser::make_int32(buf + dalp::MAGIC_NUMBER_SIZE);
        const auto zipped_data_offset = dalp::MAGIC_NUMBER_SIZE + 4;

        std::vector<uint8_t> unzipped(expected_unzipped_size);
        const auto actual_unzip_size = ::unzip(unzipped.data(), unzipped.size(), buf + zipped_data_offset, buf_size - zipped_data_offset);
        if (0 == actual_unzip_size) {
            return std::nullopt;
        }
        else {
            return unzipped;
        }
    }

    bool is_magic_numbers_correct(const uint8_t* const buf) {
        for (int i = 0; i < dalp::MAGIC_NUMBER_SIZE; ++i) {
            if (buf[i] != dalp::MAGIC_NUMBERS_DAL_MODEL[i]) {
                return false;
            }
        }

        return true;
    }

}


// Parser functions
namespace {

    const uint8_t* parse_aabb(const uint8_t* header, const uint8_t* const end, dal::parser::AABB3& output) {
        float fbuf[6];
        header = dal::parser::assemble_4_bytes_array<float>(header, fbuf, 6);

        output.m_min = glm::vec3{ fbuf[0], fbuf[1], fbuf[2] };
        output.m_max = glm::vec3{ fbuf[3], fbuf[4], fbuf[5] };

        return header;
    }

    const uint8_t* parse_mat4(const uint8_t* header, const uint8_t* const end, glm::mat4& mat) {
        float fbuf[16];
        header = dalp::assemble_4_bytes_array<float>(header, fbuf, 16);

        for ( size_t row = 0; row < 4; ++row ) {
            for ( size_t col = 0; col < 4; ++col ) {
                mat[col][row] = fbuf[4 * row + col];
            }
        }

        return header;
    }

}


// Parse animations
namespace {

    const uint8_t* parse_skeleton(const uint8_t* header, const uint8_t* const end, dalp::Skeleton& output) {
        const auto joint_count = dal::parser::make_int32(header); header += 4;
        output.m_joints.resize(joint_count);

        for ( int i = 0; i < joint_count; ++i ) {
            auto& joint = output.m_joints.at(i);

            joint.m_name = reinterpret_cast<const char*>(header); header += joint.m_name.size() + 1;
            joint.m_parent_index = dalp::make_int32(header); header += 4;

            const auto joint_type_index = dalp::make_int32(header); header += 4;
            switch ( joint_type_index ) {
            case 0:
                joint.m_joint_type = dalp::JointType::basic;
                break;
            case 1:
                joint.m_joint_type = dalp::JointType::hair_root;
                break;
            case 2:
                joint.m_joint_type = dalp::JointType::skirt_root;
                break;
            default:
                joint.m_joint_type = dalp::JointType::basic;
            }

            header = parse_mat4(header, end, joint.m_offset_mat);
        }

        return header;
    }

    const uint8_t* parse_animJoint(const uint8_t* header, const uint8_t* const end, dalp::AnimJoint& output) {
        {
            header = parse_mat4(header, end, output.m_transform);
        }

        {
            const auto num = dalp::make_int32(header); header += 4;
            for ( int i = 0; i < num; ++i ) {
                float fbuf[4];
                header = dalp::assemble_4_bytes_array<float>(header, fbuf, 4);
                output.add_translate(fbuf[0], fbuf[1], fbuf[2], fbuf[3]);
            }
        }

        {
            const auto num = dalp::make_int32(header); header += 4;
            for ( int i = 0; i < num; ++i ) {
                float fbuf[5];
                header = dalp::assemble_4_bytes_array<float>(header, fbuf, 5);
                output.add_rotation(fbuf[0], fbuf[4], fbuf[1], fbuf[2], fbuf[3]);
            }
        }

        {
            const auto num = dalp::make_int32(header); header += 4;
            for ( int i = 0; i < num; ++i ) {
                float fbuf[2];
                header = dalp::assemble_4_bytes_array<float>(header, fbuf, 2);
                output.add_scale(fbuf[0], fbuf[1]);
            }
        }

        return header;
    }

    const uint8_t* parse_animations(const uint8_t* header, const uint8_t* const end, std::vector<dalp::Animation>& animations) {
        const auto anim_count = dalp::make_int32(header); header += 4;
        animations.resize(anim_count);

        for ( int i = 0; i < anim_count; ++i ) {
            auto& anim = animations.at(i);

            anim.m_name = reinterpret_cast<const char*>(header);
            header += anim.m_name.size() + 1;

            anim.m_duration_tick = dalp::make_float32(header); header += 4;
            anim.m_ticks_par_sec = dalp::make_float32(header); header += 4;

            const auto joint_count = dalp::make_int32(header); header += 4;
            anim.m_joints.resize(joint_count);

            for ( int j = 0; j < joint_count; ++j ) {
                header = ::parse_animJoint(header, end, anim.m_joints.at(i));
            }
        }

        return header;
    }

}


// Parse render units
namespace {

    const uint8_t* parse_material(const uint8_t* header, const uint8_t* const end, dalp::Material& material) {
        material.m_roughness = dalp::make_float32(header); header += 4;
        material.m_metallic = dalp::make_float32(header); header += 4;

        material.m_albedo_map = reinterpret_cast<const char*>(header);
        header += material.m_albedo_map.size() + 1;

        material.m_roughness_map = reinterpret_cast<const char*>(header);
        header += material.m_roughness_map.size() + 1;

        material.m_metallic_map = reinterpret_cast<const char*>(header);
        header += material.m_metallic_map.size() + 1;

        material.m_normal_map = reinterpret_cast<const char*>(header);
        header += material.m_normal_map.size() + 1;

        return header;
    }

    const uint8_t* parse_render_unit_straight(const uint8_t* header, const uint8_t* const end, dalp::RenderUnit<dalp::Mesh_Straight>& unit) {
        // Name
        unit.m_name = reinterpret_cast<const char*>(header);
        header += unit.m_name.size() + 1;

        // Material
        header = ::parse_material(header, end, unit.m_material);

        // Vertices
        {
            const auto vert_count = dalp::make_int32(header); header += 4;
            const auto bas_joints = dalp::make_bool8(header); header += 1;
            const auto vert_count_times_3 = vert_count * 3;
            const auto vert_count_times_2 = vert_count * 2;

            unit.m_mesh.m_vertices.resize(vert_count_times_3);
            header = dalp::assemble_4_bytes_array<float>(header, unit.m_mesh.m_vertices.data(), vert_count_times_3);

            unit.m_mesh.m_texcoords.resize(vert_count_times_2);
            header = dalp::assemble_4_bytes_array<float>(header, unit.m_mesh.m_texcoords.data(), vert_count_times_2);

            unit.m_mesh.m_normals.resize(vert_count_times_3);
            header = dalp::assemble_4_bytes_array<float>(header, unit.m_mesh.m_normals.data(), vert_count_times_3);

            if ( bas_joints ) {
                unit.m_mesh.m_boneWeights.resize(vert_count_times_3);
                header = dalp::assemble_4_bytes_array<float>(header, unit.m_mesh.m_boneWeights.data(), vert_count_times_3);

                unit.m_mesh.m_boneIndex.resize(vert_count_times_3);
                header = dalp::assemble_4_bytes_array<int32_t>(header, unit.m_mesh.m_boneIndex.data(), vert_count_times_3);
            }
        }

        return header;
    }

}


namespace dal::parser {

    dal::parser::ModelParseResult parse_model_straight(const uint8_t* const buf, const size_t buf_size, Model_Straight& output) {
        // Check magic numbers
        if (!::is_magic_numbers_correct(buf)) {
            return ModelParseResult::magic_numbers_dont_match;
        }

        // Decompress
        const auto unzipped = ::unzip_dal_model(buf, buf_size);
        if (!unzipped) {
            return ModelParseResult::decompression_failed;
        }

        // Parsing
        {
            const uint8_t* const end = unzipped->data() + unzipped->size();
            const uint8_t* header = unzipped->data();

            header = ::parse_aabb(header, end, output.m_aabb);
            header = ::parse_skeleton(header, end, output.m_skeleton);
            header = ::parse_animations(header, end, output.m_animations);

            const auto render_unit_count = dalp::make_int32(header); header += 4;
            output.m_render_units.resize(render_unit_count);

            for ( int i = 0; i < render_unit_count; ++i ) {
                header = ::parse_render_unit_straight(header, end, output.m_render_units.at(i));
            }

            if (header != end) {
                return ModelParseResult::corrupted_content;
            }
        }

        return ModelParseResult::success;
    }

    std::optional<Model_Straight> parse_model_straight(const uint8_t* const buf, const size_t buf_size) {
        Model_Straight result;

        if (ModelParseResult::success != parse_model_straight(buf, buf_size, result)) {
            return std::nullopt;
        }
        else {
            return result;
        }
    }

}
