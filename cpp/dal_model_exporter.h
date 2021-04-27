#pragma once

#include <vector>
#include <optional>

#include "dal_struct.h"


namespace dal::parser {

    using binary_buffer_t = std::vector<uint8_t>;


    enum class ModelExportResult{
        success,
        unknown_error,
    };

    ModelExportResult build_binary_model(binary_buffer_t& output, const Model& input);

    std::optional<binary_buffer_t> build_binary_model(const Model& input);

}
