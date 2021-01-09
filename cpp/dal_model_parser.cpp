#include "dal_model_parser.h"

#include <zlib.h>

#include "dal_byte_tool.h"


// Consts
namespace {

    constexpr size_t MAGIC_NUMBER_COUNT = 6;
    constexpr char MAGIC_NUMBERS[] = "dalmdl";

}


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

}


namespace dal::parser {

    std::optional<Model_Straight> parse_model_straight(const uint8_t* const buf, const size_t buf_size) {
        // Decompress
        std::vector<uint8_t> unzipped;
        {
            const auto fullSize = make_int32(buf + MAGIC_NUMBER_COUNT);
            const auto zippedBytesOffset = MAGIC_NUMBER_COUNT + 4;

            unzipped.resize(fullSize);
            const auto unzipSize = ::unzip(unzipped.data(), unzipped.size(), buf + zippedBytesOffset, buf_size - zippedBytesOffset);
            if ( 0 == unzipSize ) {
                return std::nullopt;
            }
        }

        Model_Straight model{};

        model.result_code = unzipped.size();

        return model;
    }

}
