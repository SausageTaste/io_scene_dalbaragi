cmake_minimum_required(VERSION 3.11.0)

include(FetchContent)

project(B3D-Sung-Module)


# External library

FetchContent_Declare(
    fetch_daltools
    GIT_REPOSITORY https://github.com/SausageTaste/DalbaragiTools
    GIT_TAG        main
)

FetchContent_MakeAvailable(fetch_daltools)

find_package(Python3 3.10 COMPONENTS Development)


# Shared library definition
add_library(b3dsung SHARED
    ./cpp/b3dsung.cpp
    ./cpp/mesh_manager.cpp
)

target_compile_features(b3dsung PUBLIC cxx_std_17)
target_include_directories(b3dsung PUBLIC ./cpp)
target_link_libraries(b3dsung PUBLIC Python3::Python libdaltools)


# Script that moves generated pyd file
add_custom_command(TARGET b3dsung POST_BUILD COMMAND ${CMAKE_COMMAND} -E
    copy_if_different
    "$<TARGET_FILE:b3dsung>"
    ${PROJECT_SOURCE_DIR}/b3dsung.pyd
)

add_custom_command(TARGET b3dsung POST_BUILD COMMAND ${CMAKE_COMMAND} -E
    echo "Copied shared library from $<TARGET_FILE:b3dsung>"
)
