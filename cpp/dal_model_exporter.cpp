#include "dal_model_exporter.h"

#include <zlib.h>

#include "dal_byte_tool.h"


namespace dalp = dal::parser;


namespace {

    auto resize_back(dalp::binary_buffer_t& buffer, const size_t bytes) {
        const auto header = buffer.data() + buffer.size();
        buffer.resize(buffer.size() + bytes);
        return header;
    }


    void append_bin_aabb(const dalp::AABB3& aabb, dalp::binary_buffer_t& output) {
        auto header = ::resize_back(output, 4 * 6);

        dalp::to_float32(aabb.m_min.x, header); header += 4;
        dalp::to_float32(aabb.m_min.y, header); header += 4;
        dalp::to_float32(aabb.m_min.z, header); header += 4;
        dalp::to_float32(aabb.m_max.x, header); header += 4;
        dalp::to_float32(aabb.m_max.y, header); header += 4;
        dalp::to_float32(aabb.m_max.z, header); header += 4;
    }

}


namespace dal::parser {

    ModelExportResult build_binary_model_indexed(const Model& input, binary_buffer_t& output) {
        return ModelExportResult::unknown_error;
    }

    std::optional<binary_buffer_t> build_binary_model_indexed(const Model& input) {
        binary_buffer_t result;

        if (ModelExportResult::success != build_binary_model_indexed(input, result)) {
            return std::nullopt;
        }
        else {
            return result;
        }
    }

}
