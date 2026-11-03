# Include this from the separate validation CMake project AFTER yuki_core exists.
# ROOT and UPSTREAM are already defined in ../probe_build/CMakeLists.txt.
if(NOT TARGET yuki_core)
    message(FATAL_ERROR "frame exporter requires the independent yuki_core validation target")
endif()
add_executable(yuki_frame_export "${CMAKE_CURRENT_LIST_DIR}/frame_export.cpp")
target_compile_features(yuki_frame_export PRIVATE cxx_std_20)
target_include_directories(yuki_frame_export PRIVATE "${UPSTREAM}/tools")
target_include_directories(yuki_frame_export SYSTEM PRIVATE "${ROOT}/deps/json")
target_link_libraries(yuki_frame_export PRIVATE yuki_core)
