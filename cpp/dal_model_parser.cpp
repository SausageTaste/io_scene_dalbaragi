#include "dal_model_parser.h"

#include <zlib.h>

#include "dal_byte_tool.h"


namespace {

    constexpr size_t MAGIC_NUMBER_COUNT = 6;
    constexpr char MAGIC_NUMBERS[] = "dalmdl";

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
        const auto expected_unzipped_size = dal::parser::make_int32(buf + ::MAGIC_NUMBER_COUNT);
        const auto zipped_data_offset = ::MAGIC_NUMBER_COUNT + 4;

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
        for (int i = 0; i < ::MAGIC_NUMBER_COUNT; ++i) {
            if (buf[i] != ::MAGIC_NUMBERS[i]) {
                return false;
            }
        }

        return true;
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

        output.result_code = unzipped->size();

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
