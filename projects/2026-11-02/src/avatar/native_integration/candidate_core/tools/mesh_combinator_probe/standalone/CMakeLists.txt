cmake_minimum_required(VERSION 3.16)
project(yuki_mesh_combinator_validation LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
get_filename_component(CORE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
get_filename_component(VALIDATION_ROOT "${CORE_ROOT}/../.." ABSOLUTE)
add_library(mesh_validation_core STATIC
    ${CORE_ROOT}/src/model/model.cpp
    ${CORE_ROOT}/src/runtime/deformation.cpp
    ${CORE_ROOT}/src/runtime/geometry_scene.cpp
    ${CORE_ROOT}/src/runtime/animation_curve.cpp
    ${CORE_ROOT}/src/runtime/animation.cpp
    ${CORE_ROOT}/src/runtime/spring.cpp
    ${CORE_ROOT}/src/runtime/bend.cpp
    ${CORE_ROOT}/src/runtime/chain.cpp
    ${CORE_ROOT}/src/runtime/physics.cpp
    ${CORE_ROOT}/src/runtime/playback.cpp
    ${CORE_ROOT}/src/asset_io/import_emote.cpp
    ${CORE_ROOT}/src/asset_io/validation.cpp)
target_include_directories(mesh_validation_core PUBLIC ${CORE_ROOT}/include)
target_include_directories(mesh_validation_core SYSTEM PRIVATE
    ${VALIDATION_ROOT}/deps/json ${VALIDATION_ROOT}/deps/fast_float/include)
target_compile_options(mesh_validation_core PRIVATE -Wall -Wextra -Wpedantic)
add_executable(mesh_combinator_probe ../main.cpp)
target_include_directories(mesh_combinator_probe PRIVATE ${CORE_ROOT}/src/asset_io)
target_include_directories(mesh_combinator_probe SYSTEM PRIVATE ${VALIDATION_ROOT}/deps/json)
target_link_libraries(mesh_combinator_probe PRIVATE mesh_validation_core)
target_compile_options(mesh_combinator_probe PRIVATE -Wall -Wextra -Wpedantic)
add_executable(mesh_runtime_audit ${CORE_ROOT}/tools/runtime_audit/main.cpp)
target_include_directories(mesh_runtime_audit SYSTEM PRIVATE ${VALIDATION_ROOT}/deps/json)
target_link_libraries(mesh_runtime_audit PRIVATE mesh_validation_core)
