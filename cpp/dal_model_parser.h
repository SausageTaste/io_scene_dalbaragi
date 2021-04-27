#pragma once

#include <optional>

#include "dal_struct.h"


namespace dal::parser {

    enum class ModelParseResult{
        success,
        magic_numbers_dont_match,
        decompression_failed,
        corrupted_content,
    };

    ModelParseResult parse_model_straight(const uint8_t* const buf, const size_t buf_size, Model& output);

    std::optional<Model> parse_model_straight(const uint8_t* const buf, const size_t buf_size);

}
