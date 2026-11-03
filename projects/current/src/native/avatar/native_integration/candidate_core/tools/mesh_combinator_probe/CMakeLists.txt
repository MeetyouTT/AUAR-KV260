add_executable(nekomote_mesh_combinator_probe main.cpp)
target_include_directories(nekomote_mesh_combinator_probe PRIVATE ${PROJECT_SOURCE_DIR}/src/asset_io)
target_link_libraries(nekomote_mesh_combinator_probe PRIVATE
    nekomote::runtime nekomote::importer nlohmann_json::nlohmann_json)
