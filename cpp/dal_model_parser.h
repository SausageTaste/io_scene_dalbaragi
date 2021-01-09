#pragma once

#include <optional>

#include "dal_struct.h"


namespace dal::parser {

    std::optional<Model_Straight> parse_model_straight(const uint8_t* const buf, const size_t buf_size);

}
