// Independent CPU tests and real-asset evidence; never disables source fields.
#include <nekomote/asset_io/import_emote.hpp>
#include <nekomote/runtime/geometry_scene.hpp>
#include <nekomote/runtime/playback.hpp>
#include <nlohmann/json.hpp>
#include "asset_json.hpp"

#include <algorithm>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <new>
#include <set>
#include <stdexcept>
#include <vector>

namespace { bool measure_allocations = false; std::size_t allocations = 0; }
void* operator new(std::size_t size)
{
    if (measure_allocations) ++allocations;
    if (auto* result = std::malloc(size == 0 ? 1 : size)) return result;
    throw std::bad_alloc();
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete(void* pointer) noexcept { std::free(pointer); }
void operator delete[](void* pointer) noexcept { std::free(pointer); }
void operator delete(void* pointer, std::size_t) noexcept { std::free(pointer); }
void operator delete[](void* pointer, std::size_t) noexcept { std::free(pointer); }

namespace
{
using namespace nekomote;
using Json = nlohmann::json;
template<class T> model::Field<T> field(T value)
{
    model::Field<T> result; result.state = model::FieldState::Value;
    result.data = std::move(value); return result;
}
void require(bool condition, const std::string& message)
{
    if (!condition) throw std::runtime_error(message);
}
void close(float actual, float expected)
{
    require(std::abs(actual - expected) < 0.00001f,
            "expected " + std::to_string(expected) + ", actual " + std::to_string(actual));
}
model::CombinatorGrid grid(float dx, float dy, bool absolute)
{
    model::CombinatorGrid value{};
    for (std::size_t p = 0; p < 16; ++p)
    {
        value[p * 2] = (absolute ? float(p % 4) / 3 : 0) + dx;
        value[p * 2 + 1] = (absolute ? float(p / 4) / 3 : 0) + dy;
    }
    return value;
}
model::MeshCombinatorControl control(const std::string& variable, bool absolute)
{
    return {variable, "synthetic/" + variable, "#resource@0", 1, 1, -1, 1,
            {grid(absolute ? -.2f : 0, absolute ? 0 : -.1f, absolute),
             grid(0, 0, absolute),
             grid(absolute ? .2f : 0, absolute ? 0 : .1f, absolute)}};
}
model::ModelAsset fixture()
{
    model::ModelAsset a;
    a.spec="ems"; a.version=3.03f; a.screen_width=a.screen_height=100;
    a.base_group="rig"; a.base_motion="base";
    a.textures.push_back({"atlas","atlas.png","RGBA8",100,100});
    a.icons["atlas/a"]={"atlas",0,0,100,100,0,0,0,0};
    model::Part p; p.group="rig"; p.name="base";
    model::Layer l; l.label="surface"; l.type=0; l.inherit_mask=0x20007fc;
    l.mesh_transform=1; l.mesh_division=4; l.mesh_sync_child_mask=8;
    model::FrameContent c; c.src=field(std::string("atlas")); c.icon=field(std::string("a"));
    model::MeshData bp; bp.bp=field(grid(.9f,0,true)); c.mesh=field(bp);
    l.frame_list.push_back({0,2,field(c)});
    model::MeshCombinator comb; comb.controls={control("x",true),control("y",false)};
    l.mesh_combinator=field(comb); p.layers.push_back(l); a.parts.push_back(p);
    a.total_layers=1; a.total_frames=1; a.bp_nonnull=1;
    return a;
}
std::unique_ptr<const runtime::GeometryScene> compile(const model::ModelAsset& asset)
{
    auto c=runtime::compile_geometry_scene(asset);
    if (!c.scene) throw std::runtime_error(c.errors.empty()?"compile failed":c.errors.front());
    return std::move(c.scene);
}
runtime::GeometryNodeObservation evaluate(runtime::GeometryInstance& instance,
                                         const runtime::GeometryScene& scene,
                                         float x, float y)
{
    require(bool(instance.set_parameter(scene.find_variable("x"),x)),"set x failed");
    require(bool(instance.set_parameter(scene.find_variable("y"),y)),"set y failed");
    require(bool(instance.evaluate()),"geometry evaluate failed");
    require(bool(instance.build_frame()),"frame failed");
    const auto result=instance.observe_node(NodeId{1});
    require(result.has_value(),"node observation failed");
    return *result;
}
void write_json(const std::filesystem::path& path,const Json& value)
{
    std::ofstream output(path,std::ios::binary);
    output<<value.dump(2,' ',true)<<'\n';
    require(bool(output),"cannot write "+path.string());
}
Json source_fixture()
{
    Json content{{"src","atlas"},{"icon","a"}};
    Json entry{{"meshType",1},{"neutralIndex",1},{"rawMeshList","#resource@0"},
        {"variable",{{"key","x"},{"meshCount",3},{"rangeBegin",-1},{"rangeEnd",1}}}};
    Json layer{{"label","surface"},{"type",0},{"inheritMask",0x20007fc},
        {"meshDivision",4},{"meshTransform",1},{"meshSyncChildMask",8},
        {"meshCombinator",{{"combinatorList",Json::array({entry})}}},
        {"frameList",Json::array({{{"time",0},{"type",2},{"content",content}}})}};
    Json result;
    result["spec"]="ems"; result["version"]=3.03;
    result["screenSize"]={{"width",100},{"height",100},{"originX",0},{"originY",0}};
    result["source"]["atlas"]["texture"]={{"width",100},{"height",100},
                                           {"type","RGBA8"},{"pixel","#resource#0"}};
    result["source"]["atlas"]["icon"]["a"]={{"left",0},{"top",0},{"width",100},
        {"height",100},{"originX",0},{"originY",0},{"attr",0}};
    result["object"]["rig"]["motion"]["base"]={{"type",0},{"lastTime",0},
                                                {"layer",Json::array({layer})}};
    result["metadata"]["base"]={{"chara","rig"},{"motion","base"}};
    return result;
}
Json flat_resource()
{
    Json flat=Json::array();
    for (const auto& g:control("x",true).grids)
        for(float value:g) flat.push_back(value);
    return {{"Resources",{{"0","atlas.png"}}},{"ExtraResources",Json::object()},
            {"ExtraFlattenArrays",{{"@0",flat}}}};
}
void binary_resource(const std::filesystem::path& path, bool nonfinite=false)
{
    std::ofstream output(path,std::ios::binary);
    std::size_t index=0;
    for(const auto& g:control("x",true).grids)
        for(float value:g)
        {
            const auto bits=(nonfinite&&index++==0)?std::uint32_t{0x7fc00000}:std::bit_cast<std::uint32_t>(value);
            for(unsigned shift:{0u,8u,16u,24u}) output.put(static_cast<char>((bits>>shift)&255u));
        }
}
Json self_tests(const std::filesystem::path& directory)
{
    std::filesystem::create_directories(directory);
    Json report{{"ok",true},{"tests",Json::array()},{"visual_certified",false}};
    const auto test=[&](const char* name,const auto& run)
    {
        try { run(); report["tests"].push_back({{"name",name},{"ok",true}}); }
        catch(const std::exception& e)
        { report["ok"]=false; report["tests"].push_back({{"name",name},{"ok",false},{"error",e.what()}}); }
    };
    test("fractional absolute plus additive grids",[&]{
        auto scene=compile(fixture()); runtime::GeometryInstance i(*scene);
        auto n=evaluate(i,*scene,.5f,.5f);
        require(n.combinator_owned&&n.combinator_effective&&n.combinator_control_count==2,"not consumed");
        close(n.combinator_patch[0].x,.1f); close(n.combinator_patch[0].y,.05f);
        close(i.frame().vertices.front().x,10); close(i.frame().vertices.front().y,5);
    });
    test("endpoint clamping",[&]{
        auto scene=compile(fixture()); runtime::GeometryInstance i(*scene);
        auto n=evaluate(i,*scene,4,-4); close(n.combinator_patch[0].x,.2f);
        close(n.combinator_patch[0].y,-.1f);
    });
    test("neutral owns field and never falls back to bp",[&]{
        auto scene=compile(fixture()); runtime::GeometryInstance i(*scene);
        auto n=evaluate(i,*scene,0,0);
        require(n.combinator_owned&&!n.combinator_effective,"neutral state wrong");
        close(i.frame().vertices.front().x,0);
    });
    test("reversed range",[&]{
        auto a=fixture(); auto& c=a.parts[0].layers[0].mesh_combinator.data.controls[0];
        c.range_begin=1; c.range_end=-1;
        auto scene=compile(a); runtime::GeometryInstance i(*scene);
        close(evaluate(i,*scene,.5f,0).combinator_patch[0].x,-.1f);
    });
    test("typed meshType2 fails compilation",[&]{
        auto a=fixture(); a.parts[0].layers[0].mesh_combinator.data.controls[0].mesh_type=2;
        require(!runtime::compile_geometry_scene(a).scene,"unsupported type accepted");
    });
    test("schema typed roundtrip retains grids",[&]{
        auto a=fixture(); Json encoded=a; auto decoded=encoded.get<model::ModelAsset>();
        require(decoded.parts[0].layers[0].mesh_combinator.data.controls[0].grids==
                a.parts[0].layers[0].mesh_combinator.data.controls[0].grids,"grids lost");
    });
    // Texture decoding is outside this import/CPU test; only resource existence is checked.
    std::ofstream(directory/"atlas.png",std::ios::binary).put('\0');
    asset_io::ImportOptions options{directory/"model.json",directory/"resx.json",directory,{}};
    auto source=source_fixture(), resx=flat_resource();
    const auto import=[&]{
        write_json(options.json_path,source); write_json(options.resx_path,resx);
        return asset_io::import_emote(options);
    };
    test("flattened resources import",[&]{
        auto r=import(); require(r.ok,"flattened import failed");
        require(r.report.mesh_combinators_count==1&&r.report.mesh_combinator_controls_count==1,"counts");
        close(r.asset.parts[0].layers[0].mesh_combinator.data.controls[0].grids[0][0],-.2f);
    });
    test("binary float32LE resources import",[&]{
        resx=flat_resource(); resx["ExtraFlattenArrays"]=Json::object();
        resx["ExtraResources"]={{"@0","raw.bin"}}; binary_resource(directory/"raw.bin");
        auto r=import(); require(r.ok,"binary import failed");
        close(r.asset.parts[0].layers[0].mesh_combinator.data.controls[0].grids[2][0],.2f);
    });
    test("truncated binary rejected",[&]{
        std::ofstream(directory/"raw.bin",std::ios::binary).put('\0');
        auto r=import(); require(!r.ok,"truncated raw data accepted");
        require(!r.report.errors.empty()&&r.report.errors.front().find("meshCount * 128")!=std::string::npos,
                "did not reach byte length check");
    });
    test("binary NaN rejected",[&]{
        binary_resource(directory/"raw.bin",true);
        auto r=import(); require(!r.ok,"NaN accepted");
        require(r.report.errors.front().find("nonfinite float32LE")!=std::string::npos,"wrong branch");
    });
    test("flattened length rejected",[&]{
        resx=flat_resource(); resx["ExtraFlattenArrays"]["@0"].erase(0);
        require(!import().ok,"wrong flattened length accepted");
    });
    test("missing resource rejected",[&]{
        resx=flat_resource(); resx["ExtraFlattenArrays"]=Json::object();
        require(!import().ok,"missing resource accepted");
    });
    test("resource traversal rejected",[&]{
        resx=flat_resource(); resx["ExtraFlattenArrays"]=Json::object();
        resx["ExtraResources"]={{"@0","../raw.bin"}};
        auto r=import(); require(!r.ok,"path traversal accepted");
        require(r.report.errors.front().find("path traversal")!=std::string::npos,"wrong branch");
    });
    test("oversized count rejected before grid allocation",[&]{
        resx=flat_resource(); source=source_fixture();
        source["object"]["rig"]["motion"]["base"]["layer"][0]["meshCombinator"]
              ["combinatorList"][0]["variable"]["meshCount"]=100000000;
        auto r=import(); require(!r.ok,"oversized count accepted");
        require(r.report.errors.front().find("decoded control budget")!=std::string::npos,"wrong branch");
    });
    test("unknown combinator field explicitly rejected",[&]{
        source=source_fixture(); resx=flat_resource();
        source["object"]["rig"]["motion"]["base"]["layer"][0]["meshCombinator"]["future"]=1;
        auto r=import(); require(!r.ok,"unknown field ignored");
        require(r.report.errors.front().find("unsupported meshCombinator field")!=std::string::npos,"wrong branch");
    });
    test("steady geometry path allocation and timing",[&]{
        auto scene=compile(fixture()); runtime::GeometryInstance i(*scene);
        for(int n=0;n<60;++n) evaluate(i,*scene,.5f,.5f);
        std::vector<double> times(300);
        const auto parameter=scene->find_variable("x");
        allocations=0; measure_allocations=true;
        for(auto& time:times)
        {
            auto start=std::chrono::steady_clock::now();
            // No observation/assertion strings or JSON are inside the measured path.
            auto s=i.set_parameter(parameter,.5f);
            if(s) s=i.evaluate();
            if(s) s=i.build_frame();
            if(!s) { measure_allocations=false; throw std::runtime_error("measured geometry failed"); }
            time=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        }
        measure_allocations=false;
        std::sort(times.begin(),times.end());
        report["geometry_benchmark"]={{"samples",300},{"allocations",allocations},
            {"p50_ms",times[149]},{"p95_ms",times[284]},{"p99_ms",times[296]},
            {"scope","synthetic geometry evaluate+build_frame, no physics/GPU/JSON"}};
        require(allocations==0,"steady geometry allocated");
    });
    return report;
}
Json real_model(const asset_io::ImportOptions& options)
{
    auto imported=asset_io::import_emote(options);
    Json out{{"ok",false},{"visual_certified",false},{"import_ok",imported.ok},
        {"combinators",imported.report.mesh_combinators_count},
        {"controls",imported.report.mesh_combinator_controls_count},
        {"import_errors",imported.report.errors},{"unsupported_fields",imported.report.unsupported_fields}};
    if(!imported.ok) return out;
    auto compiled=runtime::compile_geometry_scene(imported.asset);
    out["compile_errors"]=compiled.errors;
    if(!compiled.scene) return out;
    const auto& scene=*compiled.scene;
    runtime::GeometryInstance instance(scene);
    auto status=instance.evaluate();
    if(!status) {out["baseline_error"]=static_cast<int>(status.error);return out;}
    std::vector<runtime::GeometryNodeObservation> baseline;
    for(std::uint32_t n=1;n<=scene.node_count();++n) baseline.push_back(*instance.observe_node(NodeId{n}));
    std::set<std::string> variables;
    const auto collect=[&](auto&& self,const model::Layer& l)->void{
        if(l.mesh_combinator.has_value())
            for(const auto& c:l.mesh_combinator.data.controls) variables.insert(c.variable);
        for(const auto& c:l.children)self(self,c);
    };
    for(const auto& p:imported.asset.parts)for(const auto& l:p.layers)collect(collect,l);
    out["samples"]=Json::array();
    bool all=true; std::size_t changing_samples=0;
    for(const auto& variable:variables)
        for(float value:{-15.0f,15.0f})
        {
            const auto id=scene.find_variable(variable);
            auto set=instance.set_parameter(id,value);
            auto evaluated=set?instance.evaluate():set;
            Json sample{{"variable",variable},{"value",value},{"ok",bool(evaluated)}};
            if(!evaluated)
            {
                sample["error"]=static_cast<int>(evaluated.error);
                sample["node"]=evaluated.node.value;
                sample["path"]=std::string(scene.node_label(evaluated.node)); all=false;
            }
            else
            {
                std::size_t changed=0; double max_delta=0; Json examples=Json::array();
                for(std::uint32_t n=1;n<=scene.node_count();++n)
                {
                    const auto current=*instance.observe_node(NodeId{n});
                    if(!current.active||!current.combinator_owned)continue;
                    double delta=0;
                    for(std::size_t p=0;p<16;++p)
                        delta=std::max({delta,std::abs(double(current.combinator_patch[p].x)-baseline[n-1].combinator_patch[p].x),
                            std::abs(double(current.combinator_patch[p].y)-baseline[n-1].combinator_patch[p].y)});
                    if(delta>1e-7)
                    {
                        ++changed; max_delta=std::max(max_delta,delta);
                        if(examples.size()<3)examples.push_back({{"id",n},{"path",std::string(scene.node_label(NodeId{n}))},
                            {"own_patch_delta",delta},{"controls",current.combinator_control_count}});
                    }
                }
                sample["changed_owned_grids"]=changed; sample["max_delta"]=max_delta;
                sample["examples"]=examples;
                if(changed)++changing_samples;
            }
            out["samples"].push_back(std::move(sample));
            require(bool(instance.set_parameter(id,0)),"reset real variable failed");
        }
    out["ok"]=all;
    out["changing_samples"]=changing_samples;
    out["variable_count"]=variables.size();
    out["scope"]="CPU owned combinator grids; no mask/GPU/SDK visual parity claim";
    return out;
}
} // namespace
int main(int argc,char**argv)
{
    try
    {
        Json report; std::filesystem::path output;
        if(argc==4&&std::string(argv[1])=="--self-test")
        { report=self_tests(argv[2]); output=argv[3]; }
        else if(argc==6&&std::string(argv[1])=="--model")
        { asset_io::ImportOptions o{argv[2],argv[3],argv[4],{}}; report=real_model(o); output=argv[5]; }
        else {std::fprintf(stderr,"usage: probe --self-test TMP_DIR OUTPUT | --model JSON RESX RESOURCE_ROOT OUTPUT\n");return 1;}
        write_json(output,report);
        std::printf("ok=%s output=%s\n",report.value("ok",false)?"yes":"no",output.string().c_str());
        return report.value("ok",false)?0:2;
    }
    catch(const std::exception&e){measure_allocations=false;std::fprintf(stderr,"%s\n",e.what());return 1;}
}
