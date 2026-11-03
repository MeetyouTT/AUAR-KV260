// SPDX-License-Identifier: AGPL-3.0-only
// GLES2 implementation of NekoMote's render-frame contract. Source LICENSE retained.
#include "gles2_renderer.hpp"
#include <png.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>

using namespace nekomote;
namespace aura_yuki {
namespace {
const char* vertex_shader=R"(attribute vec2 position;attribute vec2 uv;attribute vec4 color;
uniform mediump vec2 output_size;uniform vec3 view;
varying mediump vec2 texture_uv;varying lowp vec4 vertex_color;
void main(){vec2 p=position*view.z+view.xy;
gl_Position=vec4(p.x*2.0/output_size.x-1.0,1.0-p.y*2.0/output_size.y,0.0,1.0);
texture_uv=uv;vertex_color=color;})";
const char* fragment_shader=R"(precision mediump float;
varying mediump vec2 texture_uv;varying lowp vec4 vertex_color;
uniform sampler2D atlas;uniform sampler2D alpha_mask;uniform mediump vec2 output_size;
uniform int mask_write;uniform int use_mask;uniform int premultiply;uniform int protection_pass;
void main(){vec4 s=texture2D(atlas,texture_uv);
if(mask_write!=0){gl_FragColor=vec4(0.0,s.a,0.0,0.0);return;}
vec4 c=s*vertex_color;if(use_mask!=0)c.a*=texture2D(alpha_mask,gl_FragCoord.xy/output_size).g;
if(protection_pass!=0&&c.a<0.0000001)discard;
gl_FragColor=vec4(premultiply!=0?c.rgb*c.a:c.rgb,c.a);})";
void check(const char* where) {
 auto code=glGetError();if(code!=GL_NO_ERROR)throw std::runtime_error(std::string(where)+": GLES error "+std::to_string(code));
}
GLuint shader(GLenum kind,const char* source) {
 auto handle=glCreateShader(kind);glShaderSource(handle,1,&source,nullptr);glCompileShader(handle);
 GLint ok=0;glGetShaderiv(handle,GL_COMPILE_STATUS,&ok);
 if(!ok){char log[4096]{};glGetShaderInfoLog(handle,sizeof(log),nullptr,log);glDeleteShader(handle);throw std::runtime_error(log);}
 return handle;
}
GLuint texture(int width,int height,const void* pixels,bool fivebit) {
 GLuint handle=0;glGenTextures(1,&handle);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,handle);
 glPixelStorei(GL_UNPACK_ALIGNMENT,1);
 glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,width,height,0,GL_RGBA,fivebit?GL_UNSIGNED_SHORT_5_5_5_1:GL_UNSIGNED_BYTE,pixels);
 for(auto param:{GL_TEXTURE_MIN_FILTER,GL_TEXTURE_MAG_FILTER})glTexParameteri(GL_TEXTURE_2D,param,GL_LINEAR);
 for(auto param:{GL_TEXTURE_WRAP_S,GL_TEXTURE_WRAP_T})glTexParameteri(GL_TEXTURE_2D,param,GL_CLAMP_TO_EDGE);
 try {check("texture upload");}catch(...){glDeleteTextures(1,&handle);throw;}return handle;
}
std::vector<unsigned char> png_read(const std::filesystem::path& path,int expected_w,int expected_h) {
 png_image image{};image.version=PNG_IMAGE_VERSION;
 if(!png_image_begin_read_from_file(&image,path.c_str()))throw std::runtime_error("Cannot read PNG: "+path.string());
 image.format=PNG_FORMAT_RGBA;
 if(image.width!=static_cast<png_uint_32>(expected_w)||image.height!=static_cast<png_uint_32>(expected_h)){
  png_image_free(&image);throw std::runtime_error("Atlas size mismatch");}
 std::vector<unsigned char> result(PNG_IMAGE_SIZE(image));
 if(!png_image_finish_read(&image,nullptr,result.data(),0,nullptr)){
  auto message=std::string(image.message);png_image_free(&image);throw std::runtime_error(message);}
 png_image_free(&image);return result;
}
int floor_power2(int value){int p=1;while(p<=value/2)p*=2;return p;}
}
Renderer::Renderer(const runtime::GeometryScene& scene,const model::ModelAsset& asset,const std::filesystem::path& root)
 :remapper_(scene.textures(),asset,scene.frame_capacity()) {
 GLuint vs=0,fs=0;
 try {
 vs=shader(GL_VERTEX_SHADER,vertex_shader);fs=shader(GL_FRAGMENT_SHADER,fragment_shader);
 program_=glCreateProgram();glAttachShader(program_,vs);glAttachShader(program_,fs);
 for(const auto& [index,name]:std::array<std::pair<GLuint,const char*>,3>{{{0,"position"},{1,"uv"},{2,"color"}}})glBindAttribLocation(program_,index,name);
 glLinkProgram(program_);glDeleteShader(vs);vs=0;glDeleteShader(fs);fs=0;GLint ok=0;glGetProgramiv(program_,GL_LINK_STATUS,&ok);
 if(!ok){char log[4096]{};glGetProgramInfoLog(program_,sizeof(log),nullptr,log);throw std::runtime_error(log);}
 glUseProgram(program_);
 glUniform1i(glGetUniformLocation(program_,"atlas"),0);glUniform1i(glGetUniformLocation(program_,"alpha_mask"),1);
 output_size_=glGetUniformLocation(program_,"output_size");view_=glGetUniformLocation(program_,"view");
 mask_write_=glGetUniformLocation(program_,"mask_write");use_mask_=glGetUniformLocation(program_,"use_mask");
 premultiply_=glGetUniformLocation(program_,"premultiply");protection_=glGetUniformLocation(program_,"protection_pass");
 GLint maximum_texture_size=0;glGetIntegerv(GL_MAX_TEXTURE_SIZE,&maximum_texture_size);
 if(maximum_texture_size<1)throw std::runtime_error("Invalid GLES texture limit");
 const auto& tiles=remapper_.tiles();textures_.resize(tiles.size());
 for(const auto& t:tiles)if(t.width>maximum_texture_size||t.height>maximum_texture_size)
  throw std::runtime_error("Cropped icon exceeds GLES texture limit");
 const auto canonical_root=std::filesystem::canonical(root);
 for(auto& t:scene.textures()){
  if(std::none_of(tiles.begin(),tiles.end(),[&](const auto& icon){return icon.atlas==t.id;}))continue;
  const auto path=std::filesystem::canonical(canonical_root/t.path);
  auto relative=path.lexically_relative(canonical_root);
  if(relative.empty()||*relative.begin()=="..")throw std::runtime_error("Atlas escapes resource root");
  // Decode once per atlas, copy the actual neighbouring atlas pixels, upload
  // one local texture per icon, then discard the complete atlas CPU buffer.
  // The original PNG and all runtime TextureBinding values stay unchanged.
  auto pixels=png_read(path,t.width,t.height);
  std::size_t largest=0;for(const auto& icon:tiles)if(icon.atlas==t.id)
   largest=std::max(largest,std::size_t(icon.width)*icon.height*4);
  std::vector<unsigned char> cropped(largest);
  for(std::size_t i=0;i<tiles.size();++i){const auto& icon=tiles[i];if(icon.atlas!=t.id)continue;
   for(int y=0;y<icon.height;++y)
    std::memcpy(cropped.data()+std::size_t(y)*icon.width*4,
     pixels.data()+(std::size_t(icon.y+y)*t.width+icon.x)*4,std::size_t(icon.width)*4);
   textures_[i]=texture(icon.width,icon.height,cropped.data(),false);
  }
 }
 if(std::any_of(textures_.begin(),textures_.end(),[](GLuint id){return id==0;}))
  throw std::runtime_error("Cropped texture was not initialized");
 glGenBuffers(1,&vbo_);glGenBuffers(1,&ebo_);glGenBuffers(1,&quad_vbo_);glGenBuffers(1,&quad_ebo_);
 constexpr std::array<std::uint16_t,6> quad_indices{0,1,2,0,2,3};
 glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,quad_ebo_);glBufferData(GL_ELEMENT_ARRAY_BUFFER,sizeof(quad_indices),quad_indices.data(),GL_STATIC_DRAW);
 const auto capacity=scene.frame_capacity();
 indices_.resize(capacity.indices);clips_.resize(capacity.masks);
 if(capacity.vertices>std::size_t(std::numeric_limits<GLsizeiptr>::max())/sizeof(RenderVertex)||
    capacity.indices>std::size_t(std::numeric_limits<GLsizeiptr>::max())/sizeof(std::uint16_t))
  throw std::runtime_error("GPU buffer capacity overflow");
 vertex_bytes_=capacity.vertices*sizeof(RenderVertex);index_bytes_=capacity.indices*sizeof(std::uint16_t);
 glBindBuffer(GL_ARRAY_BUFFER,vbo_);glBufferData(GL_ARRAY_BUFFER,static_cast<GLsizeiptr>(vertex_bytes_),nullptr,GL_DYNAMIC_DRAW);
 glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,ebo_);glBufferData(GL_ELEMENT_ARRAY_BUFFER,static_cast<GLsizeiptr>(index_bytes_),nullptr,GL_DYNAMIC_DRAW);
 check("native renderer initialization");
 } catch(...) {if(vs)glDeleteShader(vs);if(fs)glDeleteShader(fs);release();throw;}
}
Renderer::~Renderer(){release();}
void Renderer::release() noexcept {
 for(auto id:textures_)if(id)glDeleteTextures(1,&id);
 for(auto t:{color_,mask_}){if(t.fbo)glDeleteFramebuffers(1,&t.fbo);if(t.texture)glDeleteTextures(1,&t.texture);}
 if(vbo_)glDeleteBuffers(1,&vbo_);
 if(ebo_)glDeleteBuffers(1,&ebo_);
 if(quad_vbo_)glDeleteBuffers(1,&quad_vbo_);
 if(quad_ebo_)glDeleteBuffers(1,&quad_ebo_);
 if(program_)glDeleteProgram(program_);
}
Renderer::Target Renderer::target(int w,int h,bool fivebit){
 Target t;t.texture=texture(w,h,nullptr,fivebit);glGenFramebuffers(1,&t.fbo);glBindFramebuffer(GL_FRAMEBUFFER,t.fbo);
 glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,t.texture,0);
 if(glCheckFramebufferStatus(GL_FRAMEBUFFER)!=GL_FRAMEBUFFER_COMPLETE){
  glDeleteFramebuffers(1,&t.fbo);glDeleteTextures(1,&t.texture);throw std::runtime_error("Native FBO incomplete");}
 return t;
}
void Renderer::resize(int w,int h){
 if(w==w_&&h==h_)return;
 if(w<1||h<1||w>4096||h>4096)throw std::runtime_error("Unsupported output size");
 const int mw=floor_power2(w),mh=floor_power2(h);
 Target color=target(w,h,false),mask;
 try{mask=target(mw,mh,true);}catch(...){glDeleteFramebuffers(1,&color.fbo);glDeleteTextures(1,&color.texture);throw;}
 for(auto t:{color_,mask_}){if(t.fbo)glDeleteFramebuffers(1,&t.fbo);if(t.texture)glDeleteTextures(1,&t.texture);}
 w_=w;h_=h;mw_=mw;mh_=mh;color_=color;mask_=mask;
 const std::array<RenderVertex,4> quad{{{0,0,0,1,{1,1,1,1}},{float(w),0,1,1,{1,1,1,1}},
  {float(w),float(h),1,0,{1,1,1,1}},{0,float(h),0,0,{1,1,1,1}}}};
 glBindBuffer(GL_ARRAY_BUFFER,quad_vbo_);glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad.data(),GL_STATIC_DRAW);
}
void Renderer::geometry(std::span<const RenderVertex> vertices,std::span<const std::uint32_t> indices){
 if(vertices.size_bytes()>vertex_bytes_||indices.size()>indices_.size())
  throw std::runtime_error("Renderer frame capacity exceeded");
 for(std::size_t i=0;i<indices.size();++i){if(indices[i]>=65536||indices[i]>=vertices.size())throw std::runtime_error("GLES2 uint16 index overflow");indices_[i]=static_cast<std::uint16_t>(indices[i]);}
 auto vb=vertices.size_bytes(),ib=indices.size()*sizeof(std::uint16_t);
 glBindBuffer(GL_ARRAY_BUFFER,vbo_);
 if(vb)glBufferSubData(GL_ARRAY_BUFFER,0,vb,vertices.data());
 glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,ebo_);
 if(ib)glBufferSubData(GL_ELEMENT_ARRAY_BUFFER,0,ib,indices_.data());
 attributes();
}
void Renderer::attributes(){
 static_assert(sizeof(RenderVertex)==32);
 for(GLuint i=0;i<3;++i)glEnableVertexAttribArray(i);
 glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,sizeof(RenderVertex),nullptr);
 glVertexAttribPointer(1,2,GL_FLOAT,GL_FALSE,sizeof(RenderVertex),reinterpret_cast<void*>(8));
 glVertexAttribPointer(2,4,GL_FLOAT,GL_FALSE,sizeof(RenderVertex),reinterpret_cast<void*>(16));
}
void Renderer::command(const DrawCommand& c){
 if(!c.index_count)return;
 const auto tile=remapper_.tile_index(c);
 if(tile>=textures_.size()||!textures_[tile])throw std::runtime_error("Unknown cropped texture binding");
 glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,textures_[tile]);
 glDrawElements(GL_TRIANGLES,c.index_count,GL_UNSIGNED_SHORT,reinterpret_cast<void*>(std::size_t(c.first_index)*2));
}
void Renderer::mode(int mw,int um,int pm,int protect){glUniform1i(mask_write_,mw);glUniform1i(use_mask_,um);glUniform1i(premultiply_,pm);glUniform1i(protection_,protect);}
Renderer::Clip Renderer::clip(RenderFrame frame,std::span<const DrawCommand> sources,MaskId id,View view){
 struct Bounds{double l=INFINITY,t=INFINITY,r=-INFINITY,b=-INFINITY;};
 auto add=[&](Bounds& out,const DrawCommand& c){
  if(std::uint64_t(c.first_index)+c.index_count>frame.indices.size())throw std::runtime_error("Draw range overflow");
  for(std::uint32_t i=0;i<c.index_count;++i){const auto& v=frame.vertices[frame.indices[c.first_index+i]];out.l=std::min(out.l,double(v.x));out.r=std::max(out.r,double(v.x));out.t=std::min(out.t,double(v.y));out.b=std::max(out.b,double(v.y));}};
 Bounds a,b;for(const auto& c:sources)add(a,c);for(const auto& c:frame.commands)if(c.mask==id)add(b,c);
 auto rectangle=[&](Bounds v)->Clip{
  if(!std::isfinite(v.l))return{};
  auto l=std::max(0,int(std::floor(v.l*view.scale+view.x))-2),r=std::min(w_,int(std::ceil(v.r*view.scale+view.x))+2);
  auto bottom=std::max(0,h_-int(std::ceil(v.b*view.scale+view.y))-2),top=std::min(h_,h_-int(std::floor(v.t*view.scale+view.y))+2);
  return {l,bottom,std::max(0,r-l),std::max(0,top-bottom)};};
 auto ra=rectangle(a),rb=rectangle(b);auto x=std::max(ra.x,rb.x),y=std::max(ra.y,rb.y);
 return {x,y,std::max(0,std::min(ra.x+ra.w,rb.x+rb.w)-x),std::max(0,std::min(ra.y+ra.h,rb.y+rb.h)-y)};
}
void Renderer::draw(RenderFrame frame,int w,int h,View view){
 GLint output_fbo=0;glGetIntegerv(GL_FRAMEBUFFER_BINDING,&output_fbo);
 resize(w,h);glUseProgram(program_);geometry(remapper_.remap(frame),frame.indices);
 for(auto state:{GL_DEPTH_TEST,GL_STENCIL_TEST,GL_CULL_FACE,GL_DITHER})glDisable(state);
 glEnable(GL_BLEND);glBlendEquationSeparate(GL_FUNC_ADD,GL_FUNC_ADD);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
 glUniform2f(output_size_,float(w),float(h));glUniform3f(view_,view.x,view.y,view.scale);mode(0,0,0,0);
 glBindFramebuffer(GL_FRAMEBUFFER,color_.fbo);glViewport(0,0,w,h);glDisable(GL_SCISSOR_TEST);glClearColor(0,0,0,0);glClear(GL_COLOR_BUFFER_BIT);
 const bool straight=frame.composition==ColorComposition::ProtectedStraight;
 if(frame.masks.size()>clips_.size())throw std::runtime_error("Mask capacity exceeded");
 MaskId previous{};Clip active{};
 for(const auto& c:frame.commands){
  if(c.mask.valid()&&c.mask!=previous){
   if(c.mask.value>frame.masks.size())throw std::runtime_error("Invalid mask ID");
   const auto& definition=frame.masks[c.mask.value-1];
   if(std::uint64_t(definition.first_command)+definition.command_count>frame.mask_commands.size())throw std::runtime_error("Mask range overflow");
   auto sources=frame.mask_commands.subspan(definition.first_command,definition.command_count);active=clip(frame,sources,c.mask,view);
   glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,0);glBindFramebuffer(GL_FRAMEBUFFER,mask_.fbo);glViewport(0,0,mw_,mh_);
   glDisable(GL_SCISSOR_TEST);glClearColor(0,0,0,0);glClear(GL_COLOR_BUFFER_BIT);glEnable(GL_SCISSOR_TEST);
   glScissor(active.x*mw_/w,active.y*mh_/h,active.w*mw_/w,active.h*mh_/h);
   mode(1,0,0,0);glBlendFuncSeparate(GL_ONE,GL_ONE_MINUS_SRC_COLOR,GL_ZERO,GL_ONE);
   for(const auto& source:sources)command(source);
   glBindFramebuffer(GL_FRAMEBUFFER,color_.fbo);glViewport(0,0,w,h);glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,mask_.texture);previous=c.mask;
  }
  if(c.mask.valid()){glEnable(GL_SCISSOR_TEST);glScissor(active.x,active.y,active.w,active.h);}else glDisable(GL_SCISSOR_TEST);
  const bool premul=c.blend==BlendMode::Multiply||!straight;mode(0,c.mask.valid(),premul,0);
  if(straight&&c.protection==ColorProtection::PreserveTranslucent){
   glUniform1i(protection_,1);glBlendFuncSeparate(GL_ONE_MINUS_DST_ALPHA,GL_DST_ALPHA,GL_ZERO,GL_ONE);command(c);glUniform1i(protection_,0);}
  if(c.blend==BlendMode::Multiply)glBlendFuncSeparate(GL_DST_COLOR,GL_ONE_MINUS_SRC_ALPHA,GL_ZERO,GL_ONE);
  else if(c.blend==BlendMode::Over)glBlendFuncSeparate(straight?GL_SRC_ALPHA:GL_ONE,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ONE_MINUS_SRC_ALPHA);
  else throw std::runtime_error("Unsupported native blend mode");
  command(c);
 }
 // Keep model buffers immutable throughout colour/mask/resolve submission.
 // The final quad no longer overwrites their in-flight storage.
 glBindBuffer(GL_ARRAY_BUFFER,quad_vbo_);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,quad_ebo_);attributes();
 glBindFramebuffer(GL_FRAMEBUFFER,output_fbo);glViewport(0,0,w,h);glDisable(GL_SCISSOR_TEST);
 glClearColor(252.f/255,252.f/255,243.f/255,1);glClear(GL_COLOR_BUFFER_BIT);
 glUniform3f(view_,0,0,1);mode(0,0,straight,0);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,color_.texture);
 glBlendFuncSeparate(GL_ONE,GL_ONE_MINUS_SRC_ALPHA,GL_ONE,GL_ONE_MINUS_SRC_ALPHA);glDrawElements(GL_TRIANGLES,6,GL_UNSIGNED_SHORT,nullptr);
 glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_2D,0);glActiveTexture(GL_TEXTURE0);
 glDisable(GL_BLEND);glBindBuffer(GL_ARRAY_BUFFER,0);glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,0);
 for(GLuint i=0;i<3;++i)glDisableVertexAttribArray(i);
 glUseProgram(0);check("native frame submit");
}
void Renderer::capture(const std::filesystem::path& output,int w,int h){
 std::vector<unsigned char> pixels(std::size_t(w)*h*4),flipped(pixels.size());
 glPixelStorei(GL_PACK_ALIGNMENT,1);glReadPixels(0,0,w,h,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());check("diagnostic readback");
 for(int y=0;y<h;++y)std::memcpy(flipped.data()+std::size_t(y)*w*4,pixels.data()+std::size_t(h-y-1)*w*4,std::size_t(w)*4);
 png_image image{};image.version=PNG_IMAGE_VERSION;image.width=w;image.height=h;image.format=PNG_FORMAT_RGBA;
 if(!png_image_write_to_file(&image,output.c_str(),0,flipped.data(),0,nullptr))throw std::runtime_error(image.message);
}
}
