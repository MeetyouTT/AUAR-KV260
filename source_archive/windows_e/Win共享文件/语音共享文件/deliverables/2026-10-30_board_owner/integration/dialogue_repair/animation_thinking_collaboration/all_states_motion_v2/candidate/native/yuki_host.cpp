// SPDX-License-Identifier: AGPL-3.0-only
#include "yuki_host.h"
#include "gles2_renderer.hpp"
#include "gentle_motion.hpp"
#include <nekomote/asset_io/import_emote.hpp>
#include <nekomote/runtime/playback.hpp>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>

using namespace nekomote;
using namespace nekomote::runtime;
namespace {
using Clock=std::chrono::steady_clock;
thread_local std::string create_error;
constexpr std::array<std::array<float,4>,6> faces{{{0,0,0,4},{40,30,0,1},{20,10,0,4},{30,20,5,4},{30,0,0,4},{40,30,5,0}}};
void checked(PlaybackStatus value){
 if(!value)throw std::runtime_error("Runtime failure playback="+std::to_string(int(value.error))+" geometry="+
  std::to_string(int(value.geometry.error))+" node="+std::to_string(value.geometry.node.value)+" animation="+
  std::to_string(int(value.animation.error))+" physics="+std::to_string(int(value.physics.error)));
}
struct Host {
 std::unique_ptr<const PlaybackProgram> program;
 std::unique_ptr<PlaybackInstance> instance;
 std::unique_ptr<aura_yuki::Renderer> renderer;
 std::array<ParamId,4> face{};ParamId talk{},arm{};
 VariableSourceId facial_source{};
 VariableSourceId motion_source{};
 std::array<ParamId,6> motion{};
 std::array<float,6> motion_offsets{};
 aura_yuki::GentleMotion gentle_motion;
 std::array<TimelineId,2> idle{};
 YukiControl control{};YukiStats stats{};
 std::uint32_t expression=UINT32_MAX,pose=UINT32_MAX;
 double last_time=-1,mouth=0,left=-920,right=437,top=-3490,bottom=315;
 double control_age=1;bool failed=false;std::string error;
 Host(const char* model,const char* resx,const char* root,std::uint32_t seed){
  asset_io::ImportOptions options;options.json_path=model;options.resx_path=resx;options.resource_root=root;
  auto imported=asset_io::import_emote(options);
  if(!imported.ok){std::string e="EMS import failed";for(auto& v:imported.report.errors)e+="\n"+v;throw std::runtime_error(e);}
  const std::array<VariableSourceDefinition,2> sources{{
   {"aura_dialogue_face",{"face_eye_open","face_talk","face_mouth"}},
   {"aura_gentle_motion",{"head_LR","head_UD","head_slant","body_LR","body_UD","body_slant"}}
  }};
  auto compiled=compile_playback(imported.asset,PhysicsMode::Enabled,sources);
  if(!compiled.program){std::string e="Playback compile failed";for(auto& v:compiled.errors)e+="\n"+v;throw std::runtime_error(e);}
  program=std::move(compiled.program);const auto& scene=program->scene();
  facial_source=program->animation().find_variable_source("aura_dialogue_face");
  if(!facial_source.valid())throw std::runtime_error("Yuki dialogue facial source missing");
  motion_source=program->animation().find_variable_source("aura_gentle_motion");
  if(!motion_source.valid())throw std::runtime_error("Yuki gentle motion source missing");
  for(std::size_t i=0;i<motion.size();++i){
   motion[i]=scene.find_variable(aura_yuki::GentleMotion::names[i]);
   if(!motion[i].valid())throw std::runtime_error("Required Yuki motion parameter missing");
  }
  const std::array<const char*,4> names{"face_eyebrow","face_mouth","face_eye_open","face_cheek"};
  for(std::size_t i=0;i<names.size();++i){face[i]=scene.find_variable(names[i]);if(!face[i].valid())throw std::runtime_error("Required Yuki face parameter missing");}
  talk=scene.find_variable("face_talk");arm=scene.find_variable("arm_type");
  if(!talk.valid()||!arm.valid())throw std::runtime_error("Required Yuki talk/pose parameter missing");
  idle[0]=program->animation().find_timeline("ポーズA_通常待機");idle[1]=program->animation().find_timeline("ポーズB_通常待機");
  for(auto id:idle)if(!id.valid()||!program->animation().timeline_supported(id))throw std::runtime_error("Yuki idle timeline unsupported");
  std::ifstream input(model);const auto document=nlohmann::json::parse(input);
  const auto& markers=document.at("metadata").at("charaProfile").at("pixelMarker");
  left=markers.at("boundsLeft");right=markers.at("boundsRight");top=markers.at("boundsTop");bottom=markers.at("boundsBottom");
  if(!(std::isfinite(left)&&std::isfinite(right)&&std::isfinite(top)&&std::isfinite(bottom)&&right>left&&bottom>top))throw std::runtime_error("Invalid authored camera bounds");
  instance=std::make_unique<PlaybackInstance>(*program,AnimationConfig{seed});instance->reset();
  controls(true);checked(instance->step());checked(instance->prepare_frame());
  renderer=std::make_unique<aura_yuki::Renderer>(scene,imported.asset,root);
 }
 void controls(bool initial=false){
  if(pose!=control.pose){pose=control.pose;checked(instance->play(idle[pose],TimelinePlayMode::Replace));checked(instance->transition(arm,float(pose),0));}
  const auto selected=control.expression&YUKI_EXPRESSION_MASK;
  if(expression!=selected){expression=selected;for(std::size_t i=0;i<face.size();++i)checked(instance->transition(face[i],faces[expression][i],initial?0:6));}
 }
 bool answer_live() const noexcept {
  return control.playing&&!control.paused&&control.track==1&&
   (control.expression&YUKI_EYES_MASK)!=YUKI_EYES_THINKING_CLOSED&&control_age>=0&&control_age<=.150;
 }
 void apply_facials(){
  const bool live=answer_live();
  if(!live)mouth=0;
  auto policy=control.expression&YUKI_EYES_MASK;
  if(policy==YUKI_EYES_ANSWER_OPEN&&!live)policy=YUKI_EYES_THINKING_CLOSED;
  const bool closed=policy==YUKI_EYES_THINKING_CLOSED;
  const std::array<ParamId,3> ids{face[2],talk,face[1]};
  const std::array<bool,3> override{policy!=YUKI_EYES_AUTHORED,true,closed};
  const std::array<float,3> targets{closed?10.f:0.f,float(mouth),0.f};
  std::array<float,3> observed{};
  for(const auto p:instance->values())for(std::size_t i=0;i<ids.size();++i)if(p.id==ids[i])observed[i]=p.value;
  // Add a final numeric difference after authored animation/blinking. Remove
  // our previous difference first: no accumulated drift and no core changes.
  // Three fixed parameters, no steady allocation, I/O, timer or extra tick.
  for(std::size_t i=0;i<ids.size();++i){
   const float previous=instance->difference_value(facial_source,ids[i]);
   const float difference=override[i]?targets[i]-(observed[i]-previous):0.f;
   if(previous!=difference)checked(instance->transition_difference(facial_source,ids[i],difference));
  }
 }
 static PlaybackStatus author(void* pointer,std::uint64_t) noexcept {
  auto& h=*static_cast<Host*>(pointer);
  const bool live=h.answer_live();
  const auto eye_policy=h.control.expression&YUKI_EYES_MASK;
  const auto mood=live?aura_yuki::MotionMood::Answer:
   eye_policy!=YUKI_EYES_AUTHORED?aura_yuki::MotionMood::Thinking:aura_yuki::MotionMood::Calm;
  h.motion_offsets=h.gentle_motion.step(mood,live?double(h.control.gain*h.control.level):0.);
  // Applied BEFORE the same author tick evaluates geometry/physics. The
  // existing four hair and two parts chains see moving authored anchors;
  // no manual hair offsets or additional physical passes are introduced.
  for(std::size_t i=0;i<h.motion.size();++i){
   const auto status=h.instance->transition_difference(h.motion_source,h.motion[i],h.motion_offsets[i]);
   if(!status)return status;
  }
  const double target=live?std::clamp(double(h.control.gain*h.control.level),0.0,1.0)*5.0:0.0;
  // Audio cancellation must close in the next author tick, independently of smoothing.
  if(!live)h.mouth=0;else h.mouth+=(target-h.mouth)*(1-std::exp(-1.0/(60*.045)));
  return h.instance->transition(h.talk,float(h.mouth));
 }
 void draw(double now,int width,int height,YukiStats* output){
  if(failed)throw std::runtime_error(error);
  if(!std::isfinite(now)||now<0||(last_time>=0&&now<last_time))throw std::runtime_error("Monotonic render clock rewound");
  const auto begin=Clock::now();auto elapsed=last_time<0?0:now-last_time;last_time=now;
  stats.elapsed_dropped_seconds+=std::max(0.0,elapsed-kMaximumAdvanceSeconds);
  control_age=now-control.captured_at;if(control_age<0||control_age>.150)++stats.stale_frames;
  controls();
  checked(instance->advance(elapsed,{},AuthorTickHandler{this,author}));
  apply_facials();
  // A zero-step first frame still has a prepared state from construction.
  checked(instance->prepare_frame());
  const auto evaluated=Clock::now();constexpr double view_top=-3500.0,view_bottom=-2090.0,view_center_x=-50.0;
  const double scale=height/(view_bottom-view_top)*.96;
  renderer->draw(instance->frame(),width,height,{float(width*.5-view_center_x*scale),float(height*.5-(view_top+view_bottom)*.5*scale),float(scale)});
  const auto submitted=Clock::now();++stats.frames;stats.author_ticks=instance->tick_count();
  stats.owner=control.owner;stats.sequence=control.sequence;stats.audio_sample=control.audio_sample;
  stats.evaluate_ms=std::chrono::duration<double,std::milli>(evaluated-begin).count();
  stats.submit_ms=std::chrono::duration<double,std::milli>(submitted-evaluated).count();stats.mouth=mouth;
  for(auto p:instance->values())if(p.id==face[2])stats.eye=p.value;
  if(output)*output=stats;
 }
};
}
extern "C" {
std::uint32_t yuki_control_features(void){return YUKI_FEATURE_DIALOGUE_FACIALS|YUKI_FEATURE_CONTINUOUS_MOTION;}
void* yuki_create(const char* model,const char* resx,const char* root,std::uint32_t seed){
 try{create_error.clear();if(!model||!resx||!root)throw std::runtime_error("Null asset path");return new Host(model,resx,root,seed);}
 catch(const std::exception& e){create_error=e.what();return nullptr;}
}
const char* yuki_error(void* ptr){return ptr?static_cast<Host*>(ptr)->error.c_str():create_error.c_str();}
int yuki_control(void* ptr,const YukiControl* value){
 if(!ptr||!value)return 0;
 auto& h=*static_cast<Host*>(ptr);const auto& c=*value;
 const auto eye_policy=c.expression&YUKI_EYES_MASK;
 const bool valid=c.owner>0&&c.sequence>0&&c.sample_rate==24000&&c.track<=2&&c.playing<=1&&c.paused<=1&&
  (c.expression&YUKI_EXPRESSION_MASK)<6&&(c.expression&~(YUKI_EXPRESSION_MASK|YUKI_EYES_MASK))==0&&
  eye_policy!=YUKI_EYES_MASK&&c.pose<2&&
  std::isfinite(c.gain)&&c.gain>=0&&c.gain<=1&&std::isfinite(c.level)&&c.level>=0&&c.level<=1&&std::isfinite(c.captured_at)&&c.captured_at>=0;
 const bool same=c.owner==h.control.owner;
 if(h.failed||!valid||c.owner<h.control.owner||(same&&c.sequence<=h.control.sequence)||
  (same&&c.track==h.control.track&&c.audio_sample<h.control.audio_sample)){++h.stats.rejected_controls;return 0;}
 if(!same)h.mouth=0;
 h.control=c;return 1;
}
int yuki_render(void* ptr,double now,int w,int h,YukiStats* stats){
 if(!ptr)return 0;
 auto& host=*static_cast<Host*>(ptr);
 try{host.draw(now,w,h,stats);return 1;}catch(const std::exception& e){host.failed=true;host.error=e.what();return 0;}
}
int yuki_capture(void* ptr,const char* path,int w,int h){
 if(!ptr||!path)return 0;
 auto& host=*static_cast<Host*>(ptr);
 try{host.renderer->capture(path,w,h);return 1;}catch(const std::exception& e){host.error=e.what();return 0;}
}
void yuki_destroy(void* ptr){delete static_cast<Host*>(ptr);}
}
