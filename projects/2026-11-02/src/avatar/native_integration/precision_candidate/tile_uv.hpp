// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <nekomote/runtime/geometry_scene.hpp>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace aura_yuki {
// Top-origin texel rectangle, with original atlas neighbours retained. Attributes
// and origin affect runtime geometry/protection, not this saved UV rectangle.
struct IconTile {
 nekomote::TextureId atlas;
 int atlas_width{},atlas_height{},x{},y{},width{},height{};
 float left{},top{},right{},bottom{};
 std::string name;
};
struct TileBudget {
 std::uint64_t pixels{},rgba_bytes{},power2_rgba_bytes{};
 int maximum_width{},maximum_height{};
};

// CPU-only, testable UV adapter. All storage is allocated during construction.
// Source RenderFrame vertices/indices/commands remain unmodified. It recognizes
// complete icon ranges emitted by GeometryInstance, not arbitrary submeshes.
class TileUvRemapper {
 public:
 static constexpr unsigned border=2;
 static constexpr std::uint64_t maximum_rgba_bytes=256ULL*1024*1024;
 TileUvRemapper(std::span<const nekomote::runtime::TextureBinding> bindings,
                const nekomote::model::ModelAsset& asset,
                nekomote::runtime::GeometryCapacity capacity) {
  std::vector<std::string> names;
  names.reserve(asset.icons.size());
  for(const auto& [name,rect]:asset.icons){(void)rect;names.push_back(name);}
  std::sort(names.begin(),names.end());tiles_.reserve(names.size());
  for(const auto& name:names){
   const auto& r=asset.icons.at(name);
   const auto found=std::find_if(bindings.begin(),bindings.end(),[&](const auto& b){return b.name==r.texture;});
   if(found==bindings.end()||!found->id.valid()||found->width<1||found->height<1)
    throw std::runtime_error("Tile has no valid atlas binding");
   if(!std::isfinite(r.left)||!std::isfinite(r.top)||!std::isfinite(r.width)||!std::isfinite(r.height)||
      r.width<=0||r.height<=0||r.left<0||r.top<0||
      double(r.left)+r.width>found->width||double(r.top)+r.height>found->height)
    throw std::runtime_error("Icon rectangle is outside atlas");
   const float right=static_cast<float>(double(r.left)+r.width);
   const float bottom=static_cast<float>(double(r.top)+r.height);
   if(std::any_of(tiles_.begin(),tiles_.end(),[&](const auto& t){
      return t.atlas==found->id&&t.left==r.left&&t.top==r.top&&t.right==right&&t.bottom==bottom;}))
    continue; // Exact UV aliases use identical pixels and identical local mapping.
   const int x=std::max(0,int(std::floor(r.left))-int(border));
   const int y=std::max(0,int(std::floor(r.top))-int(border));
   const int end_x=static_cast<int>(std::min<std::int64_t>(found->width,static_cast<std::int64_t>(std::ceil(double(r.left)+r.width))+border));
   const int end_y=static_cast<int>(std::min<std::int64_t>(found->height,static_cast<std::int64_t>(std::ceil(double(r.top)+r.height))+border));
   const int w=end_x-x,h=end_y-y;
   const auto pixels=std::uint64_t(w)*std::uint64_t(h);
   if(w<1||h<1||pixels>maximum_rgba_bytes/4||budget_.rgba_bytes>maximum_rgba_bytes-pixels*4)
    throw std::runtime_error("Cropped texture budget exceeded");
   tiles_.push_back({found->id,found->width,found->height,x,y,w,h,r.left,r.top,right,bottom,name});
   budget_.pixels+=pixels;budget_.rgba_bytes+=pixels*4;
   budget_.power2_rgba_bytes+=power2(w)*power2(h)*4;
   budget_.maximum_width=std::max(budget_.maximum_width,w);
   budget_.maximum_height=std::max(budget_.maximum_height,h);
  }
  vertices_.resize(capacity.vertices);vertex_tiles_.resize(capacity.vertices,none);
  ranges_.resize(capacity.indices);index_capacity_=capacity.indices;
 }
 const std::vector<IconTile>& tiles() const noexcept{return tiles_;}
 TileBudget budget() const noexcept{return budget_;}
 std::span<const nekomote::RenderVertex> remap(nekomote::RenderFrame frame) {
  if(frame.vertices.size()>vertices_.size()||frame.indices.size()>index_capacity_)
   throw std::runtime_error("Tile adapter frame capacity exceeded");
  std::copy(frame.vertices.begin(),frame.vertices.end(),vertices_.begin());
  std::fill_n(vertex_tiles_.begin(),frame.vertices.size(),none);
  if(++epoch_==0){for(auto& r:ranges_)r.epoch=0;epoch_=1;}
  // Source UVs are read from frame in both passes. Duplicate ranges are cached,
  // and shared primary/mask vertices are never remapped twice.
  for(const auto& c:frame.commands)prepare(frame,c);
  for(const auto& c:frame.mask_commands)prepare(frame,c);
  return {vertices_.data(),frame.vertices.size()};
 }
 std::size_t tile_index(const nekomote::DrawCommand& c) const {
  if(!c.index_count||c.first_index>=ranges_.size())
   throw std::runtime_error("Unprepared tile command");
  const auto& r=ranges_[c.first_index];
  if(r.epoch!=epoch_||r.count!=c.index_count||r.atlas!=c.texture.value||r.tile>=tiles_.size())
   throw std::runtime_error("Unprepared or conflicting tile range");
  return r.tile;
 }
 private:
 static constexpr std::uint32_t none=std::numeric_limits<std::uint32_t>::max();
 struct Range {std::uint64_t epoch{};std::uint32_t count{},atlas{},tile{none};};
 struct Bounds {double left=INFINITY,top=INFINITY,right=-INFINITY,bottom=-INFINITY;};
 std::vector<IconTile> tiles_;
 TileBudget budget_;
 std::vector<nekomote::RenderVertex> vertices_;
 std::vector<std::uint32_t> vertex_tiles_;
 std::vector<Range> ranges_;
 std::size_t index_capacity_{};
 std::uint64_t epoch_{};
 static std::uint64_t power2(int value) noexcept {std::uint64_t p=1;while(p<std::uint64_t(value))p*=2;return p;}
 static bool matches(const IconTile& t,const nekomote::DrawCommand& c,const Bounds& b) noexcept {
  // Bounds come from Float32 runtime UVs. 0.01 atlas pixel covers their rounding
  // at4K without accepting the neighbouring packed icon one pixel away.
  constexpr double epsilon=.01;
  return t.atlas==c.texture&&std::abs(b.left*t.atlas_width-t.left)<=epsilon&&
   std::abs(b.right*t.atlas_width-t.right)<=epsilon&&
   std::abs(b.top*t.atlas_height-t.top)<=epsilon&&std::abs(b.bottom*t.atlas_height-t.bottom)<=epsilon;
 }
 static bool same_crop(const IconTile& a,const IconTile& b) noexcept {
  return a.atlas==b.atlas&&a.x==b.x&&a.y==b.y&&a.width==b.width&&a.height==b.height;
 }
 void prepare(nekomote::RenderFrame frame,const nekomote::DrawCommand& c) {
  if(!c.index_count)return;
  if(std::uint64_t(c.first_index)+c.index_count>frame.indices.size()||c.first_index>=ranges_.size())
   throw std::runtime_error("Tile command index range overflow");
  auto& range=ranges_[c.first_index];
  if(range.epoch==epoch_){
   if(range.count!=c.index_count||range.atlas!=c.texture.value)
    throw std::runtime_error("Conflicting commands at same first_index");
   return;
  }
  Bounds bounds;
  for(std::uint32_t j=0;j<c.index_count;++j){
   const auto index=frame.indices[std::size_t(c.first_index)+j];
   if(index>=frame.vertices.size()||index>=65536)throw std::runtime_error("Tile vertex index overflow");
   const auto& v=frame.vertices[index];
   if(!std::isfinite(v.u)||!std::isfinite(v.v))throw std::runtime_error("Nonfinite atlas UV");
   bounds.left=std::min(bounds.left,double(v.u));bounds.right=std::max(bounds.right,double(v.u));
   bounds.top=std::min(bounds.top,double(v.v));bounds.bottom=std::max(bounds.bottom,double(v.v));
  }
  std::size_t tile=range.tile;
  if(tile>=tiles_.size()||!matches(tiles_[tile],c,bounds)){
   tile=tiles_.size();
   for(std::size_t i=0;i<tiles_.size();++i)if(matches(tiles_[i],c,bounds)){
    if(tile!=tiles_.size()&&!same_crop(tiles_[tile],tiles_[i]))
     throw std::runtime_error("Ambiguous icon UV rectangle");
    tile=i;
   }
   if(tile==tiles_.size())throw std::runtime_error("Command UV bounds do not match an imported icon");
  }
  const auto& t=tiles_[tile];
  for(std::uint32_t j=0;j<c.index_count;++j){
   const auto index=frame.indices[std::size_t(c.first_index)+j];
   if(vertex_tiles_[index]!=none){
    if(vertex_tiles_[index]!=tile&&!same_crop(tiles_[vertex_tiles_[index]],t))
     throw std::runtime_error("One vertex belongs to different icon tiles");
    continue;
   }
   vertex_tiles_[index]=static_cast<std::uint32_t>(tile);
   const auto& original=frame.vertices[index];auto& mapped=vertices_[index];
   mapped.u=static_cast<float>((double(original.u)*t.atlas_width-t.x)/t.width);
   mapped.v=static_cast<float>((double(original.v)*t.atlas_height-t.y)/t.height);
  }
  range={epoch_,c.index_count,c.texture.value,static_cast<std::uint32_t>(tile)};
 }
};
} // namespace aura_yuki
