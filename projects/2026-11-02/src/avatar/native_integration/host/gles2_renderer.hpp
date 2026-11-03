// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "tile_uv.hpp"
#include <nekomote/runtime/geometry_scene.hpp>
#include <GLES2/gl2.h>
#include <array>
#include <filesystem>
#include <vector>

namespace aura_yuki {
struct View { float x{}, y{}, scale{1}; };
// The caller owns a current GLES2 context. No readback or file I/O in draw().
class Renderer {
 public:
  Renderer(const nekomote::runtime::GeometryScene&, const nekomote::model::ModelAsset&,
           const std::filesystem::path& root);
  ~Renderer();
  Renderer(const Renderer&)=delete;
  void draw(nekomote::RenderFrame,int width,int height,View);
  void capture(const std::filesystem::path&,int width,int height); // diagnostics only
  TileBudget tile_budget() const noexcept { return remapper_.budget(); }
 private:
  struct Target { GLuint fbo{},texture{}; };
  struct Clip { GLint x{},y{}; GLsizei w{},h{}; };
  // Valid only within one draw(). GTK/resize may mutate GL between frames.
  // All flags start unknown, so the first use always establishes actual state.
  struct StateCache {
    int mask_write{-1},use_mask{-1},premultiply{-1},protection{-1};
    int active_texture{-1},scissor_enabled{-1};
    std::array<GLuint,2> textures{};
    std::array<bool,2> texture_known{};
    GLuint framebuffer{};bool framebuffer_known{false};
    std::array<GLint,4> viewport{},scissor{};
    bool viewport_known{false},scissor_known{false};
    std::array<GLenum,4> blend{};bool blend_known{false};
    std::array<GLfloat,4> clear_color{};bool clear_color_known{false};
  } state_;
  static_assert(sizeof(StateCache)<=160,"Unexpected GL state-cache size");
  TileUvRemapper remapper_;
  GLuint program_{},vbo_{},ebo_{},quad_vbo_{},quad_ebo_{};
  GLint output_size_{},view_{},mask_write_{},use_mask_{},premultiply_{},protection_{};
  Target color_{},mask_{};
  int w_{},h_{},mw_{},mh_{};
  std::size_t vertex_bytes_{},index_bytes_{};
  std::vector<GLuint> textures_;
  std::vector<std::uint16_t> indices_;
  std::vector<Clip> clips_;
  Target target(int,int,bool);
  void resize(int,int);
  void geometry(std::span<const nekomote::RenderVertex>,std::span<const std::uint32_t>);
  void attributes();
  void release() noexcept;
  void command(const nekomote::DrawCommand&);
  void mode(int mask_write,int use_mask,int premultiply,int protection);
  void protection(int);
  void active_texture(unsigned unit);
  void bind_texture(unsigned unit,GLuint);
  void framebuffer(GLuint);
  void viewport(GLint,GLint,GLsizei,GLsizei);
  void scissor_enabled(bool);
  void scissor(Clip);
  void blend(GLenum,GLenum,GLenum,GLenum);
  void clear_color(GLfloat,GLfloat,GLfloat,GLfloat);
  Clip clip(nekomote::RenderFrame,std::span<const nekomote::DrawCommand>,nekomote::MaskId,View);
};
}
