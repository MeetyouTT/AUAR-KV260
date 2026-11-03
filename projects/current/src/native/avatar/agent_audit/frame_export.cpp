// Offline CPU protocol exporter for NekoMote 4fbf55aa6009df76ac40dc5f18e3781914bc464f.
// No asset_file/model.nkm, GPU, display, audio, service or disabled-physics path.
// Include the unchanged upstream tools/ directory for frame_json.hpp.
#include <nekomote/asset_io/import_emote.hpp>
#include <nekomote/runtime/playback.hpp>
#include <nlohmann/json.hpp>
#include "frame_json.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <initializer_list>
#include <limits>
#include <set>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace
{
using namespace nekomote;
using Json = nlohmann::ordered_json;
constexpr const char* kCommit = "4fbf55aa6009df76ac40dc5f18e3781914bc464f";

struct ExportError : std::runtime_error
{
    Json detail;
    ExportError(std::string message, Json value)
        : std::runtime_error(std::move(message)), detail(std::move(value)) {}
};
[[noreturn]] void fail(const std::string& message, Json detail = Json::object())
{
    throw ExportError(message, std::move(detail));
}
void fields(const Json& value, std::initializer_list<std::string_view> allowed,
            const std::string& context)
{
    if (!value.is_object()) fail("expected object: " + context);
    for (const auto& [key, ignored] : value.items())
    {
        static_cast<void>(ignored);
        if (std::find(allowed.begin(), allowed.end(), std::string_view(key)) == allowed.end())
            fail("unknown field: " + context + "/" + key);
    }
}
unsigned tick_value(const Json& value, const std::string& context)
{
    if (!value.is_number_integer()) fail("expected integer tick: " + context);
    const auto number = value.get<std::int64_t>();
    if (number < 0 || number > 36000) fail("tick must be in 0..36000: " + context);
    return static_cast<unsigned>(number);
}
float finite_number(const Json& value, const std::string& context)
{
    if (!value.is_number()) fail("expected number: " + context);
    const float result = value.get<float>();
    if (!std::isfinite(result)) fail("nonfinite number: " + context);
    return result;
}
Json status_json(runtime::PlaybackStatus status, const runtime::GeometryScene& scene)
{
    Json controller = nullptr;
    if (status.physics.controller != runtime::kNoPhysicsController)
        controller = status.physics.controller;
    return {{"playback_error", static_cast<int>(status.error)},
            {"animation_error", static_cast<int>(status.animation.error)},
            {"animation_timeline", status.animation.timeline.value},
            {"animation_parameter", status.animation.parameter.value},
            {"geometry_error", static_cast<int>(status.geometry.error)},
            {"node", status.geometry.node.value},
            {"node_path", std::string(scene.node_label(status.geometry.node))},
            {"geometry_parameter", status.geometry.parameter.value},
            {"physics_error", static_cast<int>(status.physics.error)},
            {"physics_controller", controller},
            {"physics_geometry_error", static_cast<int>(status.physics.geometry.error)},
            {"physics_geometry_node", status.physics.geometry.node.value},
            {"physics_geometry_parameter", status.physics.geometry.parameter.value}};
}
void checked(runtime::PlaybackStatus status, const runtime::GeometryScene& scene,
             const std::string& scenario, unsigned tick, const std::string& operation)
{
    if (!status)
        fail("playback operation failed", {{"scenario", scenario}, {"tick", tick},
             {"operation", operation}, {"status", status_json(status, scene)}});
}
void parameters(runtime::PlaybackInstance& instance, const runtime::GeometryScene& scene,
                const Json& values, const std::string& scenario, unsigned tick)
{
    if (!values.is_object()) fail("parameters must be an object", {{"scenario", scenario}});
    for (const auto& [name, request] : values.items())
    {
        const auto id = scene.find_variable(name);
        if (!id.valid())
            fail("unknown parameter", {{"scenario", scenario}, {"tick", tick}, {"parameter", name}});
        float value = 0, frames = 0, easing = 0;
        if (request.is_number())
            value = finite_number(request, name);
        else
        {
            fields(request, {"value", "frames", "easing"}, "parameter/" + name);
            value = finite_number(request.at("value"), name + "/value");
            frames = finite_number(request.value("frames", Json(0)), name + "/frames");
            easing = finite_number(request.value("easing", Json(0)), name + "/easing");
            if (frames < 0) fail("transition frames must be nonnegative", {{"parameter", name}});
        }
        checked(instance.transition(id, value, frames, easing), scene, scenario, tick,
                "transition:" + name);
    }
}

struct Bounds
{
    bool empty{true};
    double xmin{0}, ymin{0}, xmax{0}, ymax{0};
    void add(const RenderVertex& v)
    {
        if (empty) { xmin = xmax = v.x; ymin = ymax = v.y; empty = false; }
        else { xmin = std::min(xmin, double(v.x)); xmax = std::max(xmax, double(v.x));
               ymin = std::min(ymin, double(v.y)); ymax = std::max(ymax, double(v.y)); }
    }
    Json json() const
    {
        if (empty) return nullptr;
        return {{"min", {xmin, ymin}}, {"max", {xmax, ymax}},
                {"width", xmax - xmin}, {"height", ymax - ymin}};
    }
};
Bounds command_bounds(RenderFrame frame, std::span<const DrawCommand> commands)
{
    Bounds bounds;
    for (const auto& command : commands)
    {
        const auto end = std::uint64_t(command.first_index) + command.index_count;
        if (end > frame.indices.size()) fail("command index range exceeds frame");
        for (std::uint64_t i = command.first_index; i < end; ++i)
            bounds.add(frame.vertices[frame.indices[static_cast<std::size_t>(i)]]);
    }
    return bounds;
}
void validate_frame(RenderFrame frame, std::span<const runtime::TextureBinding> textures)
{
    for (const auto& vertex : frame.vertices)
    {
        const float values[] = {vertex.x, vertex.y, vertex.u, vertex.v,
                                vertex.color[0], vertex.color[1], vertex.color[2], vertex.color[3]};
        for (float value : values)
            if (!std::isfinite(value)) fail("nonfinite exported vertex");
    }
    for (auto index : frame.indices)
        if (index >= frame.vertices.size()) fail("frame vertex index out of bounds");
    const auto validate_commands = [&](std::span<const DrawCommand> commands)
    {
        for (const auto& command : commands)
        {
            const auto end = std::uint64_t(command.first_index) + command.index_count;
            if (end > frame.indices.size() || command.index_count % 3 != 0)
                fail("invalid triangle command index range");
            if (std::none_of(textures.begin(), textures.end(),
                             [&](const auto& t) { return t.id == command.texture; }))
                fail("command references unknown texture");
            if (command.mask.value > frame.masks.size()) fail("command references unknown mask");
            const auto blend = static_cast<int>(command.blend);
            const auto protection = static_cast<int>(command.protection);
            if (blend < 0 || blend > 3 || protection < 0 || protection > 1)
                fail("unknown blend/protection enum");
        }
    };
    validate_commands(frame.commands);
    validate_commands(frame.mask_commands);
    for (const auto& mask : frame.masks)
        if (std::uint64_t(mask.first_command) + mask.command_count > frame.mask_commands.size())
            fail("mask command range exceeds frame");
    const auto composition = static_cast<int>(frame.composition);
    if (composition < 0 || composition > 1) fail("unknown composition enum");
    if (frame.commands.empty()) fail("scenario has no drawable commands");
}
Json capture(runtime::PlaybackInstance& instance, const runtime::PlaybackProgram& program,
             TimelineId idle, unsigned tick)
{
    const auto& scene = program.scene();
    const auto frame = instance.frame();
    validate_frame(frame, scene.textures());
    Bounds all;
    for (const auto& v : frame.vertices) all.add(v);
    Json values = Json::object();
    for (const auto& value : instance.values())
    {
        if (!value.id.valid() || value.id.value > scene.variables().size() ||
            !std::isfinite(value.value)) fail("invalid exported parameter state");
        values[scene.variables()[value.id.value - 1].name] = value.value;
    }
    return {{"tick", tick}, {"author_seconds", double(tick) / 60.0},
            {"state", {{"ok", true}, {"status", status_json({}, scene)},
                       {"tick_count", instance.tick_count()}, {"physics_enabled", true},
                       {"idle_playing", instance.is_playing(idle)},
                       {"idle_weight", instance.timeline_weight(idle)}}},
            {"parameters", std::move(values)},
            {"bounds", {{"all_vertices", all.json()},
                        {"draw_commands", command_bounds(frame, frame.commands).json()},
                        {"mask_commands", command_bounds(frame, frame.mask_commands).json()}}},
            {"frame", diagnostics::frame_json(frame, scene.textures())}};
}

void export_scenario(Json& result, const Json& config,
                     const runtime::PlaybackProgram& program, const model::ModelAsset& asset)
{
    fields(config, {"name", "idle_timeline", "parameters", "events", "ticks", "capture_ticks"},
           "scenario");
    const auto name = config.at("name").get<std::string>();
    if (name.empty()) fail("scenario name cannot be empty");
    const auto idle_name = config.at("idle_timeline").get<std::string>();
    const unsigned ticks = tick_value(config.at("ticks"), name + "/ticks");
    const auto& scene = program.scene();
    const auto idle = program.animation().find_timeline(idle_name);
    if (!idle.valid() || !program.animation().timeline_supported(idle))
        fail("unknown or unsupported idle timeline", {{"scenario", name}, {"timeline", idle_name}});
    const auto definition = std::find_if(asset.timelines.begin(), asset.timelines.end(),
                                         [&](const auto& t) { return t.label == idle_name; });
    if (definition == asset.timelines.end() || definition->diff != 0)
        fail("idle_timeline must be a main timeline", {{"scenario", name}});
    const auto& capture_ticks = config.at("capture_ticks");
    if (!capture_ticks.is_array() || capture_ticks.empty()) fail("capture_ticks must be nonempty");
    std::set<unsigned> captures;
    for (const auto& value : capture_ticks)
    {
        const auto tick = tick_value(value, name + "/capture_ticks");
        if (tick > ticks || !captures.insert(tick).second)
            fail("capture tick duplicated or beyond ticks", {{"scenario", name}, {"tick", tick}});
    }
    const auto events = config.value("events", Json::array());
    if (!events.is_array()) fail("events must be an array");
    unsigned previous = 0;
    for (const auto& event : events)
    {
        fields(event, {"tick", "parameters"}, "event");
        const auto tick = tick_value(event.at("tick"), name + "/event/tick");
        if (tick == 0 || tick > ticks || tick < previous)
            fail("event ticks must be ordered and within 1..ticks", {{"scenario", name}});
        previous = tick;
        if (!event.at("parameters").is_object()) fail("event parameters must be an object");
    }
    result = {{"name", name}, {"ok", false}, {"complete", false}, {"config", config},
              {"snapshots", Json::array()}};
    runtime::PlaybackInstance instance(program, {1});
    instance.reset();
    checked(instance.play(idle, runtime::TimelinePlayMode::Replace), scene, name, 0, "play_idle");
    parameters(instance, scene, config.value("parameters", Json::object()), name, 0);
    checked(instance.prepare_frame(), scene, name, 0, "prepare_frame");
    if (captures.contains(0)) result["snapshots"].push_back(capture(instance, program, idle, 0));
    std::size_t event_index = 0;
    for (unsigned tick = 1; tick <= ticks; ++tick)
    {
        while (event_index < events.size() &&
               tick_value(events[event_index].at("tick"), "event/tick") == tick)
        {
            parameters(instance, scene, events[event_index].at("parameters"), name, tick);
            ++event_index;
        }
        // Every intermediate tick is evaluated. No physics or failed branch is skipped.
        checked(instance.step(), scene, name, tick, "step_animation_anchors_physics");
        checked(instance.prepare_frame(), scene, name, tick, "prepare_frame");
        if (captures.contains(tick))
            result["snapshots"].push_back(capture(instance, program, idle, tick));
    }
    result["ok"] = true;
    result["complete"] = true;
}

int run(int argc, char** argv)
{
    if (argc < 5)
    {
        std::fprintf(stderr, "usage: frame_export MODEL.ems.json MODEL.ems.resx.json "
                             "SCENARIO.json OUTPUT.json [--resource-root DIR] "
                             "[--texture NAME=RELATIVE_PATH]\n");
        return 1;
    }
    Json report{{"schema", "yuki.nekomote.frame_export.v1"}, {"ok", false},
                {"complete", false}, {"upstream_commit", kCommit}, {"author_hz", 60},
                {"seed", 1}, {"physics_enabled", true}, {"visual_certified", false},
                {"scenarios", Json::array()}};
    int exit_code = 2;
    try
    {
        asset_io::ImportOptions options;
        options.json_path = argv[1];
        options.resx_path = argv[2];
        options.resource_root = options.json_path.parent_path();
        for (int i = 5; i < argc; ++i)
        {
            const std::string argument = argv[i];
            if (i + 1 >= argc) fail("missing option value: " + argument);
            const std::string value = argv[++i];
            if (argument == "--resource-root") options.resource_root = value;
            else if (argument == "--texture")
            {
                const auto eq = value.find('=');
                if (eq == 0 || eq == std::string::npos || eq + 1 == value.size() ||
                    !options.external_textures.emplace(value.substr(0, eq), value.substr(eq + 1)).second)
                    fail("invalid/duplicate --texture mapping");
            }
            else fail("unknown option: " + argument);
        }
        report["source"] = {{"model_json", options.json_path.string()},
                            {"resx_json", options.resx_path.string()},
                            {"resource_root", options.resource_root.string()}};
        std::ifstream input(argv[3]);
        if (!input) fail("cannot open scenario JSON");
        const auto request = Json::parse(input);
        fields(request, {"seed", "scenarios"}, "request");
        if (request.value("seed", Json(1)) != Json(1)) fail("this probe requires seed=1");
        const auto& configs = request.at("scenarios");
        if (!configs.is_array() || configs.empty()) fail("scenarios must be a nonempty array");
        auto imported = asset_io::import_emote(options);
        report["import"] = {{"ok", imported.ok}, {"errors", imported.report.errors},
                            {"warnings", imported.report.warnings},
                            {"unsupported_fields", imported.report.unsupported_fields}};
        if (!imported.ok) fail("EMS import failed", report["import"]);
        const auto& asset = imported.asset;
        Json author_scale = nullptr;
        if (asset.author_scale.has_value()) author_scale = asset.author_scale.data;
        report["model"] = {{"spec", asset.spec}, {"version", asset.version},
                            {"screen_width", asset.screen_width}, {"screen_height", asset.screen_height},
                            {"screen_origin_x", asset.screen_origin_x},
                            {"screen_origin_y", asset.screen_origin_y},
                            {"author_scale", author_scale}, {"mirror", asset.mirror},
                            {"base_group", asset.base_group}, {"base_motion", asset.base_motion},
                            {"origin", {0, 0}}, {"instance_scale", 1}};
        auto compiled = runtime::compile_playback(asset, runtime::PhysicsMode::Enabled);
        report["compile_errors"] = compiled.errors;
        if (!compiled.program) fail("playback compilation failed", {{"errors", compiled.errors}});
        const auto& program = *compiled.program;
        const auto& scene = program.scene();
        report["geometry_diagnostics"] = scene.diagnostics();
        report["animation_diagnostics"] = program.animation().diagnostics();
        report["texture_bindings"] = Json::array();
        for (const auto& texture : scene.textures())
            report["texture_bindings"].push_back(
                {{"id", texture.id.value}, {"name", texture.name}, {"path", texture.path},
                 {"width", texture.width}, {"height", texture.height}});
        report["protocol"] = {
            {"vertex_layout", {"x", "y", "u", "v", "r", "g", "b", "a"}},
            {"coordinates", "model/pixel XY, Y down; normalized top-left UV; straight vertex RGBA"},
            {"blend", {{"Over", 0}, {"Add", 1}, {"Multiply", 2}, {"Screen", 3}}},
            {"protection", {{"None", 0}, {"PreserveTranslucent", 1}}},
            {"composition", {{"PremultipliedOver", 0}, {"ProtectedStraight", 1}}},
            {"mask_id", "0=no mask; otherwise one-based index into frame.masks"},
            {"event_order", "apply event before step(tick); capture after physics+prepare_frame"}};
        std::set<std::string> names;
        for (const auto& config : configs)
        {
            const auto name = config.at("name").get<std::string>();
            if (!names.insert(name).second) fail("duplicate scenario name: " + name);
            report["scenarios"].push_back(Json::object());
            export_scenario(report["scenarios"].back(), config, program, asset);
        }
        report["ok"] = true;
        report["complete"] = true;
        exit_code = 0;
    }
    catch (const ExportError& error)
    {
        report["error"] = {{"message", error.what()}, {"detail", error.detail}};
        std::fprintf(stderr, "frame_export: %s\n", error.what());
    }
    catch (const std::exception& error)
    {
        report["error"] = {{"message", error.what()}};
        std::fprintf(stderr, "frame_export: %s\n", error.what());
    }
    std::ofstream output(argv[4], std::ios::binary | std::ios::trunc);
    if (!output)
    {
        std::fprintf(stderr, "frame_export: cannot create output JSON\n");
        return 1;
    }
    output << report.dump(2, ' ', true) << '\n';
    output.close();
    if (!output) { std::fprintf(stderr, "frame_export: output write failed\n"); return 1; }
    std::printf("ok=%s physics=enabled scenarios=%zu output=%s\n",
                exit_code == 0 ? "yes" : "no", report["scenarios"].size(), argv[4]);
    return exit_code;
}
} // namespace
int main(int argc, char** argv) { return run(argc, argv); }
