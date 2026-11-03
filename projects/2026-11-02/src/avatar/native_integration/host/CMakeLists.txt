cmake_minimum_required(VERSION 3.16)
project(aura_yuki_native LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
get_filename_component(BASE "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(CORE "${BASE}/native_integration/candidate_core")
find_package(PkgConfig REQUIRED)
pkg_check_modules(GLES REQUIRED IMPORTED_TARGET glesv2)
pkg_check_modules(PNG REQUIRED IMPORTED_TARGET libpng)
add_library(yuki_core STATIC
  ${CORE}/src/model/model.cpp
  ${CORE}/src/runtime/deformation.cpp
  ${CORE}/src/runtime/geometry_scene.cpp
  ${CORE}/src/runtime/animation_curve.cpp
  ${CORE}/src/runtime/animation.cpp
  ${CORE}/src/runtime/spring.cpp
  ${CORE}/src/runtime/bend.cpp
  ${CORE}/src/runtime/chain.cpp
  ${CORE}/src/runtime/physics.cpp
  ${CORE}/src/runtime/playback.cpp
  ${CORE}/src/asset_io/import_emote.cpp
  ${CORE}/src/asset_io/validation.cpp)
target_include_directories(yuki_core PUBLIC ${CORE}/include)
target_include_directories(yuki_core SYSTEM PRIVATE ${BASE}/deps/json ${BASE}/deps/fast_float/include)
target_compile_options(yuki_core PRIVATE -O1 -Wall -Wextra -Wpedantic)
# Optimize only actual per-tick work; keep JSON/import template compilation modest.
set_source_files_properties(
  ${CORE}/src/runtime/deformation.cpp
  ${CORE}/src/runtime/geometry_scene.cpp
  ${CORE}/src/runtime/animation.cpp
  ${CORE}/src/runtime/physics.cpp
  ${CORE}/src/runtime/playback.cpp
  PROPERTIES COMPILE_OPTIONS "-O3;-ffp-contract=off")
add_library(aura_yuki SHARED yuki_host.cpp gles2_renderer.cpp diagnostic_api.cpp)
target_include_directories(aura_yuki SYSTEM PRIVATE ${BASE}/deps/json)
target_compile_options(aura_yuki PRIVATE -O2 -Wall -Wextra -Wpedantic)
target_link_libraries(aura_yuki PRIVATE yuki_core PkgConfig::GLES PkgConfig::PNG)
add_executable(yuki_frame_export ${BASE}/agent_audit/frame_export.cpp)
target_include_directories(yuki_frame_export PRIVATE ${CORE}/tools)
target_include_directories(yuki_frame_export SYSTEM PRIVATE ${BASE}/deps/json)
target_link_libraries(yuki_frame_export PRIVATE yuki_core)
target_compile_options(yuki_frame_export PRIVATE -O1)
add_executable(yuki_runtime_audit ${CORE}/tools/runtime_audit/main.cpp)
target_include_directories(yuki_runtime_audit SYSTEM PRIVATE ${BASE}/deps/json)
target_link_libraries(yuki_runtime_audit PRIVATE yuki_core)
target_compile_options(yuki_runtime_audit PRIVATE -O1)
add_executable(yuki_tile_uv_test
  ${BASE}/native_integration/precision_candidate/uv_remap_test.cpp
  ${BASE}/native_integration/precision_candidate/allocation_counter.cpp)
target_include_directories(yuki_tile_uv_test PRIVATE ${CORE}/include)
target_compile_options(yuki_tile_uv_test PRIVATE -O2 -ffp-contract=off -Wall -Wextra -Wpedantic)
