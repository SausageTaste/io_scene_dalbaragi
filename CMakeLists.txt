project(B3D-Sung-Module)
cmake_minimum_required(VERSION 3.11.0)


# External library
find_package(Python3 COMPONENTS Development)


# Shared library definition
add_library(b3dsung SHARED ./cpp/b3dsung.cpp)
target_include_directories(b3dsung PUBLIC ./include)
target_link_libraries(b3dsung PUBLIC Python3::Python)


# Script that moves generated pyd file
add_custom_command(TARGET b3dsung POST_BUILD COMMAND ${CMAKE_COMMAND} -E
    copy_if_different
    "$<TARGET_FILE:b3dsung>"
    ${PROJECT_SOURCE_DIR}/b3dsung.pyd
)

add_custom_command(TARGET b3dsung POST_BUILD COMMAND ${CMAKE_COMMAND} -E
    echo "Copied shared library from $<TARGET_FILE:b3dsung>"
)
