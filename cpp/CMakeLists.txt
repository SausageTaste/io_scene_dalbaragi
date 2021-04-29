cmake_minimum_required(VERSION 3.4.1)

project(Dalbaragi-Model-Parser
    LANGUAGES CXX
)


add_library(dalbaragi_model_parser
    dal_model_parser.h        dal_model_parser.cpp
    dal_struct.h              dal_struct.cpp
    dal_byte_tool.h           dal_byte_tool.cpp
    dal_modifier.h            dal_modifier.cpp
    dal_model_exporter.h      dal_model_exporter.cpp
)
target_include_directories(dalbaragi_model_parser PUBLIC .)
target_compile_features(dalbaragi_model_parser PUBLIC cxx_std_17)


######## Import libraries ########

set(extern_dir ${CMAKE_CURRENT_SOURCE_DIR}/extern)


# zlib
if (ANDROID)
    target_link_libraries(dalbaragi_model_parser PRIVATE z)

else()
    if (NOT TARGET zlibstatic)
        add_subdirectory(${extern_dir}/zlib ${CMAKE_CURRENT_BINARY_DIR}/zlib)
    endif()
    target_link_libraries(dalbaragi_model_parser PRIVATE zlibstatic)
    target_include_directories(dalbaragi_model_parser PRIVATE ${extern_dir}/zlib ${CMAKE_CURRENT_BINARY_DIR}/zlib)

endif()

# GLM
target_include_directories(dalbaragi_model_parser PUBLIC ${extern_dir}/glm)


######## Test ########

enable_testing()


add_executable(dal_parser_test_1
    test/test_1.cpp
)
target_compile_features(dal_parser_test_1 PUBLIC cxx_std_17)
add_test(test_1 dal_parser_test_1)

target_link_libraries(dal_parser_test_1 PRIVATE dalbaragi_model_parser)
target_include_directories(dal_parser_test_1 PRIVATE .)


######## App ########

add_subdirectory(./app)
