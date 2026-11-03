// SPDX-License-Identifier: AGPL-3.0-only
#include "tile_uv.hpp"
#include "allocation_counter.hpp"
#include "yuki_icons_fixture.hpp"
#include <array>
#include <cstdio>
#include <cstring>
using namespace nekomote;
using namespace aura_yuki;
namespace {
unsigned tests=0;
void require(bool good,const char* message){if(!good)throw std::runtime_error(message);}
void close(double a,double b,double tolerance=.0005){require(std::abs(a-b)<=tolerance,"coordinate mismatch");}
template<class F> void rejects(F call){bool failed=false;try{call();}catch(const std::runtime_error&){failed=true;}require(failed,"expected explicit rejection");++tests;}
void quad(std::span<RenderVertex,4> out,float l,float t,float r,float b,float w=4096,float h=4096){
 out[0]={2,3,l/w,t/h,{1,.5f,1,.7f}};out[1]={9,3,r/w,t/h,{1,.5f,1,.7f}};
 out[2]={2,11,l/w,b/h,{1,.5f,1,.7f}};out[3]={9,11,r/w,b/h,{1,.5f,1,.7f}};
}
}
int main(){try{
 const std::array<runtime::TextureBinding,2> bindings{{{TextureId{1},"atlas","atlas.png",4096,4096},{TextureId{2},"other","other.png",1024,1024}}};
 model::ModelAsset asset;
 asset.icons.emplace("A",model::IconRect{"atlas",100,200,64,80,0,0,0,0});
 asset.icons.emplace("A-alias",model::IconRect{"atlas",100,200,64,80,30,40,1,0});
 asset.icons.emplace("B",model::IconRect{"atlas",1000,2000,32,40,0,0,0,0});
 asset.icons.emplace("edge",model::IconRect{"atlas",0,0,3,2,0,0,0,0});
 asset.icons.emplace("other",model::IconRect{"other",256,512,16,20,0,0,0,0});
 asset.icons.emplace("adjacent",model::IconRect{"atlas",164,200,64,80,0,0,0,0});
 TileUvRemapper remapper(bindings,asset,{8,12,2,2,1});
 require(remapper.tiles().size()==5,"exact UV aliases were not deduplicated");++tests;
 const auto edge=std::find_if(remapper.tiles().begin(),remapper.tiles().end(),[](const auto& t){return t.name=="edge";});
 require(edge!=remapper.tiles().end()&&edge->x==0&&edge->y==0&&edge->width==5&&edge->height==4,"atlas-edge crop mismatch");++tests;
 std::array<RenderVertex,4> vertices;quad(vertices,100,200,164,280);
 const auto original=vertices;
 std::array<std::uint32_t,6> indices{0,1,2,1,3,2};
 std::array<DrawCommand,1> commands{{{TextureId{1},0,6}}};
 std::array<DrawCommand,1> masks=commands;
 RenderFrame frame{vertices,indices,commands,ColorComposition::ProtectedStraight,masks,{}};
 auto mapped=remapper.remap(frame);auto first_tile=remapper.tile_index(commands[0]);
 const auto& first=remapper.tiles()[first_tile];
 close(mapped[0].u,2./68,1e-6);close(mapped[0].v,2./84,1e-6);
 require(std::memcmp(original.data(),vertices.data(),sizeof(vertices))==0,"source vertices changed");
 require(mapped[0].x==vertices[0].x&&mapped[0].color==vertices[0].color,"non-UV fields changed");
 require(remapper.tile_index(masks[0])==first_tile,"shared primary/mask range mismatch");++tests;
 const auto saved=mapped[0];mapped=remapper.remap(frame);
 require(std::memcmp(&saved,&mapped[0],sizeof(saved))==0,"repeated frame double-remapped UVs");++tests;
 quad(vertices,1000,2000,1032,2040);mapped=remapper.remap(frame);
 require(remapper.tile_index(commands[0])!=first_tile,"resource swap retained stale tile");
 close(mapped[0].u,2./36,1e-6);close(mapped[0].v,2./44,1e-6);++tests;
 quad(vertices,256,512,272,532,1024,1024);commands[0].texture=TextureId{2};masks[0]=commands[0];
 mapped=remapper.remap(frame);require(remapper.tiles()[remapper.tile_index(commands[0])].atlas.value==2,"atlas swap retained stale tile");++tests;
 quad(vertices,100,200,164,280);commands[0].texture=TextureId{1};masks[0]=commands[0];
 // Move outside the icon bounds. Moving one corner inward still leaves the
 // other corners' full rectangle and is a valid affine-remapping input.
 vertices[0].u-=.01f;rejects([&]{remapper.remap(frame);});
 quad(vertices,100,200,164,280);indices[0]=999;rejects([&]{remapper.remap(frame);});indices[0]=0;
 masks[0].index_count=3;rejects([&]{remapper.remap(frame);});masks[0]=commands[0];
 TileUvRemapper small(bindings,asset,{3,6,1,1,0});rejects([&]{small.remap(frame);});
 auto invalid=asset;invalid.icons.at("A").left=-1;rejects([&]{TileUvRemapper bad(bindings,invalid,{4,6,1,1,0});});
 std::array<RenderVertex,6> shared;
 quad(std::span<RenderVertex,4>(shared.data(),4),100,200,164,280);
 shared[4]={13,3,228.f/4096,200.f/4096,{1,1,1,1}};shared[5]={13,11,228.f/4096,280.f/4096,{1,1,1,1}};
 const std::array<std::uint32_t,12> shared_indices{0,1,2,1,3,2,1,4,3,4,5,3};
 const std::array<DrawCommand,2> shared_commands{{{TextureId{1},0,6},{TextureId{1},6,6}}};
 rejects([&]{remapper.remap({shared,shared_indices,shared_commands});});

 // All68 real source icon rectangles, including attr1, complete 2x2 quads,
 // duplicate mask ranges and dynamic XY positions. No JSON/import/GL is used.
 model::ModelAsset yuki;load_yuki_icons(yuki);
 const std::array<runtime::TextureBinding,1> yuki_binding{{{TextureId{1},"tex","atlas.png",4096,4096}}};
 std::vector<RenderVertex> yv;std::vector<std::uint32_t> yi;std::vector<DrawCommand> yc;
 yv.resize(yuki_icons.size()*4);yi.resize(yuki_icons.size()*6);yc.resize(yuki_icons.size());
 for(std::size_t i=0;i<yuki_icons.size();++i){const auto& icon=yuki_icons[i];
  quad(std::span<RenderVertex,4>(yv.data()+i*4,4),icon.left,icon.top,icon.left+icon.width,icon.top+icon.height);
  for(std::size_t j=0;j<6;++j)yi[i*6+j]=static_cast<std::uint32_t>(i*4+indices[j]);
  yc[i]={TextureId{1},static_cast<std::uint32_t>(i*6),6};
 }
 TileUvRemapper all(yuki_binding,yuki,{yv.size(),yi.size(),yc.size(),yc.size(),0});
 RenderFrame yf{yv,yi,yc,ColorComposition::ProtectedStraight,yc,{}};
 auto local=all.remap(yf);
 require(all.tiles().size()==68&&all.budget().rgba_bytes==27415660,"Yuki tile budget mismatch");
 for(std::size_t i=0;i<yc.size();++i){const auto& tile=all.tiles()[all.tile_index(yc[i])];
  for(std::size_t j=0;j<4;++j){auto k=i*4+j;
   close(double(local[k].u)*tile.width+tile.x,double(yv[k].u)*4096);
   close(double(local[k].v)*tile.height+tile.y,double(yv[k].v)*4096);
  }
 }
 ++tests;
 track_allocations(true);
 for(unsigned i=0;i<500;++i){yv[0].x+=.001f;all.remap(yf);for(const auto& c:yc)(void)all.tile_index(c);}
 track_allocations(false);const auto allocations=tracked_allocations();require(allocations==0,"steady UV path allocated");++tests;
 // Silence only a genuine unused local in test diagnostics; production shaders
 // and model/mask semantics are untouched by this CPU test.
 require(first.width==68,"unexpected first crop");
 std::printf("{\"ok\":true,\"tests\":%u,\"yuki_icons\":68,\"tile_rgba_bytes\":%llu,\"steady_allocations\":%zu}\n",
  tests,static_cast<unsigned long long>(all.budget().rgba_bytes),allocations);
 return 0;
 }catch(const std::exception& error){track_allocations(false);std::fprintf(stderr,"UV test failed: %s\n",error.what());return 2;}}
