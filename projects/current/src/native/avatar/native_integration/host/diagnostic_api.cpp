// SPDX-License-Identifier: AGPL-3.0-only
// Explicit offline tests. These functions are never used by the GTK steady path.
#include "gles2_renderer.hpp"
#include <nekomote/asset_io/import_emote.hpp>
#include <nlohmann/json.hpp>
#include <fstream>
#include <iomanip>
#include <memory>
#include <sstream>
#include <stdexcept>

using namespace nekomote;
using Json=nlohmann::json;
namespace {
thread_local std::string diagnostic_error;
Json read(const char* path){std::ifstream input(path);if(!input)throw std::runtime_error("Diagnostic input missing");return Json::parse(input);}
struct Geometry {
 std::unique_ptr<const runtime::GeometryScene> scene;
 std::unique_ptr<runtime::GeometryInstance> instance;
 std::unique_ptr<aura_yuki::Renderer> renderer;
 Geometry(const char* model,const char* resx,const char* root){
  asset_io::ImportOptions options;options.json_path=model;options.resx_path=resx;options.resource_root=root;
  auto input=asset_io::import_emote(options);if(!input.ok)throw std::runtime_error("Diagnostic import failed");
  auto compiled=runtime::compile_geometry_scene(input.asset);if(!compiled.scene)throw std::runtime_error("Diagnostic compile failed");
  scene=std::move(compiled.scene);instance=std::make_unique<runtime::GeometryInstance>(*scene);
  renderer=std::make_unique<aura_yuki::Renderer>(*scene,input.asset,root);
 }
};
DrawCommand command(const Json& c){return {TextureId{c.at("texture")},c.at("first_index"),c.at("index_count"),
 static_cast<BlendMode>(c.at("blend").get<int>()),static_cast<ColorProtection>(c.at("protection").get<int>()),MaskId{c.at("mask")}};}
struct OwnedFrame {
 std::vector<RenderVertex> vertices;std::vector<std::uint32_t> indices;
 std::vector<DrawCommand> commands,mask_commands;std::vector<MaskDefinition> masks;ColorComposition composition;
 explicit OwnedFrame(const Json& f){
  for(const auto& v:f.at("vertices")){
   if(v.size()!=8)throw std::runtime_error("Diagnostic vertex size");
   vertices.push_back({v[0],v[1],v[2],v[3],{v[4],v[5],v[6],v[7]}});
  }
  indices=f.at("indices").get<std::vector<std::uint32_t>>();
  for(auto i:indices)if(i>=vertices.size())throw std::runtime_error("Diagnostic index range");
  for(const auto& c:f.at("commands"))commands.push_back(command(c));
  for(const auto& c:f.at("mask_commands"))mask_commands.push_back(command(c));
  for(const auto& m:f.at("masks"))masks.push_back({m.at("first_command"),m.at("command_count")});
  composition=static_cast<ColorComposition>(f.at("composition").get<int>());
 }
 RenderFrame frame(){return {vertices,indices,commands,composition,mask_commands,masks};}
};
aura_yuki::View view(const Json& d,int w,int h,double fraction){
 const auto& m=d.at("metadata").at("charaProfile").at("pixelMarker");
 const double l=m.at("boundsLeft"),r=m.at("boundsRight"),t=m.at("boundsTop"),b=t+(m.at("boundsBottom").get<double>()-t)*fraction;
 const double s=std::min(w/(r-l),h/(b-t))*.88;return {float(w/2.0-(l+r)/2*s),float(h/2.0-(t+b)/2*s),float(s)};
}
}
extern "C" {
const char* yuki_diagnostic_error(){return diagnostic_error.c_str();}
int yuki_diagnostic_geometry(const char* model,const char* resx,const char* root,const char* output,int w,int h){
 try{
  Geometry g(model,resx,root);auto evaluated=g.instance->evaluate();auto built=g.instance->build_frame();
  if(!evaluated||!built)throw std::runtime_error("Diagnostic geometry failed: "+std::to_string(int(built.error))+" node="+std::to_string(built.node.value));
  g.renderer->draw(g.instance->frame(),w,h,view(read(model),w,h,1));g.renderer->capture(output,w,h);return 1;
 }catch(const std::exception& e){diagnostic_error=e.what();return 0;}
}
int yuki_diagnostic_parameters(const char* model,const char* resx,const char* root,const char* parameters,const char* output,int w,int h){
 try{
  Geometry g(model,resx,root);const auto values=read(parameters);
  for(const auto& [name,value]:values.items()){
   auto id=g.scene->find_variable(name);if(!id.valid())throw std::runtime_error("Unknown diagnostic parameter: "+name);
   if(!g.instance->set_parameter(id,value.get<float>()))throw std::runtime_error("Invalid diagnostic parameter: "+name);
  }
  auto evaluated=g.instance->evaluate();auto built=g.instance->build_frame();
  if(!evaluated||!built)throw std::runtime_error("Diagnostic fixed geometry failed");
  g.renderer->draw(g.instance->frame(),w,h,view(read(model),w,h,.48));g.renderer->capture(output,w,h);return 1;
 }catch(const std::exception& e){diagnostic_error=e.what();return 0;}
}
int yuki_diagnostic_frames(const char* model,const char* resx,const char* root,const char* frames,const char* output,int w,int h){
 try{
  Geometry g(model,resx,root);auto document=read(frames);if(!document.at("ok").get<bool>())throw std::runtime_error("Failed exported frames");
  auto camera=view(read(model),w,h,.48);std::filesystem::create_directories(output);std::size_t count=0;
  for(const auto& scenario:document.at("scenarios"))for(const auto& snapshot:scenario.at("snapshots")){
   OwnedFrame owned(snapshot.at("frame"));g.renderer->draw(owned.frame(),w,h,camera);
   std::ostringstream name;name<<scenario.at("name").get<std::string>()<<'-'<<std::setw(4)<<std::setfill('0')<<snapshot.at("tick").get<unsigned>()<<".png";
   g.renderer->capture(std::filesystem::path(output)/name.str(),w,h);++count;
  }
  return static_cast<int>(count);
 }catch(const std::exception& e){diagnostic_error=e.what();return 0;}
}
}
