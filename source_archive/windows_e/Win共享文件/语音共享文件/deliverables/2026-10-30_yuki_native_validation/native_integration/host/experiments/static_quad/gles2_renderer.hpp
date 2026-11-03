// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
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
  Renderer(const nekomote::runtime::GeometryScene&, const std::filesystem::path& root);
  ~Renderer();
  Renderer(const Renderer&)=delete;
  void draw(nekomote::RenderFrame,int width,int height,View);
  void capture(const std::filesystem::path&,int width,int height); // diagnostics only
 private:
  struct Target { GLuint fbo{},texture{}; };
  struct Clip { GLint x{},y{}; GLsizei w{},h{}; };
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
  void command(const nekomote::DrawCommand&);
  void mode(int mask_write,int use_mask,int premultiply,int protection);
  Clip clip(nekomote::RenderFrame,std::span<const nekomote::DrawCommand>,nekomote::MaskId,View);
};
}
