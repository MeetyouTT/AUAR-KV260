cmake_minimum_required(VERSION 3.16)
project(yuki_native_validation LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(ROOT "${CMAKE_CURRENT_LIST_DIR}/..")
set(UPSTREAM "${ROOT}/source")
add_library(yuki_core STATIC
  ${UPSTREAM}/src/model/model.cpp
  ${UPSTREAM}/src/runtime/deformation.cpp
  ${UPSTREAM}/src/runtime/geometry_scene.cpp
  ${UPSTREAM}/src/runtime/animation_curve.cpp
  ${UPSTREAM}/src/runtime/animation.cpp
  ${UPSTREAM}/src/runtime/spring.cpp
  ${UPSTREAM}/src/runtime/bend.cpp
  ${UPSTREAM}/src/runtime/chain.cpp
  ${UPSTREAM}/src/runtime/physics.cpp
  ${UPSTREAM}/src/runtime/playback.cpp
  ${UPSTREAM}/src/asset_io/import_emote.cpp
  ${UPSTREAM}/src/asset_io/validation.cpp)
target_include_directories(yuki_core PUBLIC ${UPSTREAM}/include)
target_include_directories(yuki_core SYSTEM PRIVATE
  ${ROOT}/deps/json ${ROOT}/deps/fast_float/include)
target_compile_options(yuki_core PRIVATE -Wall -Wextra -Wpedantic)
add_executable(yuki_runtime_audit ${UPSTREAM}/tools/runtime_audit/main.cpp)
target_include_directories(yuki_runtime_audit SYSTEM PRIVATE ${ROOT}/deps/json)
target_link_libraries(yuki_runtime_audit PRIVATE yuki_core)

# An explicitly isolated experiment; the pinned upstream remains unchanged.
add_library(yuki_mask_candidate_geometry OBJECT geometry_selfmask_candidate.cpp)
target_include_directories(yuki_mask_candidate_geometry PRIVATE ${UPSTREAM}/include)
target_include_directories(yuki_mask_candidate_geometry SYSTEM PRIVATE ${ROOT}/deps/fast_float/include)
target_compile_options(yuki_mask_candidate_geometry PRIVATE -O1 -Wall -Wextra -Wpedantic)
add_executable(yuki_runtime_mask_candidate
  ${UPSTREAM}/tools/runtime_audit/main.cpp
  $<TARGET_OBJECTS:yuki_mask_candidate_geometry>)
target_include_directories(yuki_runtime_mask_candidate SYSTEM PRIVATE ${ROOT}/deps/json)
target_compile_options(yuki_runtime_mask_candidate PRIVATE -O1)
target_link_libraries(yuki_runtime_mask_candidate PRIVATE yuki_core)

add_executable(yuki_frame_export
  ${ROOT}/agent_audit/frame_export.cpp
  $<TARGET_OBJECTS:yuki_mask_candidate_geometry>)
target_include_directories(yuki_frame_export PRIVATE ${UPSTREAM}/tools)
target_include_directories(yuki_frame_export SYSTEM PRIVATE ${ROOT}/deps/json)
target_compile_options(yuki_frame_export PRIVATE -O1)
target_link_libraries(yuki_frame_export PRIVATE yuki_core)
