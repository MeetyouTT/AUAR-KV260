// SPDX-License-Identifier: AGPL-3.0-only
// Actual candidate Host + existing core, with a GPU-free renderer substitute.
// No GTK, EGL, audio device, network, model inference, capture or sleeps.
#include "../candidate/native/yuki_host.cpp"
#include <cstddef>
#include <iostream>

namespace aura_yuki {
Renderer::Renderer(const nekomote::runtime::GeometryScene& scene,
 const nekomote::model::ModelAsset& asset,const std::filesystem::path&)
 :remapper_(scene.textures(),asset,scene.frame_capacity()){}
Renderer::~Renderer()=default;
void Renderer::draw(nekomote::RenderFrame,int width,int height,View){
 if(width!=423||height!=516)throw std::runtime_error("Unexpected portrait dimensions");
}
void Renderer::capture(const std::filesystem::path&,int,int){
 throw std::runtime_error("Capture disabled in headless test");
}
}

static_assert(sizeof(YukiControl)==64 && offsetof(YukiControl,captured_at)==56);
static_assert(sizeof(YukiStats)==96 && offsetof(YukiStats,eye)==80);

namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void equal(double value,double expected,const char* message){require(std::abs(value-expected)<.00002,message);}
float parameter(Host& host,ParamId id){
 for(const auto value:host.instance->values())if(value.id==id)return value.value;
 throw std::runtime_error("Missing parameter observation");
}
}

int main(int argc,char** argv){
 try{
  require(argc==4,"Pass public model.runtime.json, resx and resource directory");
  require(yuki_control_features()==YUKI_FEATURE_DIALOGUE_FACIALS,"Missing capability");
  Host host(argv[1],argv[2],argv[3],1);
  YukiStats stats{};
  YukiControl value{};
  value.owner=1;value.sample_rate=24000;value.gain=.8f;value.level=.7f;
  double now=10.;
  const auto frame=[&](double elapsed){
   now+=elapsed;value.captured_at=now;++value.sequence;
   value.audio_sample+=static_cast<std::uint64_t>(elapsed*24000);
   require(yuki_control(&host,&value)==1,"Valid control rejected");
   host.draw(now,423,516,&stats);
  };
  // Stay closed through many cycles of the unchanged authored blink graph,
  // including expression/pose changes and display frames with no author tick.
  value.expression=YUKI_EYES_THINKING_CLOSED;
  for(int i=0;i<640;++i){
   value.expression=YUKI_EYES_THINKING_CLOSED|std::uint32_t(i%6);
   value.pose=(i/80)%2;
   frame(i%17==0?0.:1./16);
   equal(stats.eye,10.,"Thinking blink reopened the eyes");
   equal(stats.mouth,0.,"Thinking mouth moved");
   equal(parameter(host,host.talk),0.,"Thinking talk parameter remained open");
   equal(parameter(host,host.face[1]),0.,"Thinking expression retained an open mouth");
  }
  // Each real answer interval owns both open eyes and the audio envelope.
  value.expression=YUKI_EYES_ANSWER_OPEN;value.track=1;value.playing=1;
  double maximum_mouth=0.;
  for(int i=0;i<64;++i){
   value.level=i<32?.8f:.2f;frame(1./16);
   equal(stats.eye,0.,"Authored blink overrode the audible answer eye policy");
   equal(parameter(host,host.talk),stats.mouth,"Displayed mouth differs from audio mouth");
   maximum_mouth=std::max(maximum_mouth,stats.mouth);
  }
  require(maximum_mouth>1.,"Answer envelope did not animate the mouth");
  // Pause/gap must close immediately, even at exactly the previous timestamp.
  value.paused=1;frame(0.);
  equal(stats.eye,10.,"Paused answer did not close eyes");
  equal(stats.mouth,0.,"Paused answer retained mouth smoothing");
  equal(parameter(host,host.talk),0.,"Zero-author-tick pause retained open talk");
  value.paused=0;frame(1./16);require(stats.mouth>0.,"Resume failed");
  // The native 150 ms lease expires without any fresh control offer.
  now+=.151;host.draw(now,423,516,&stats);
  equal(stats.eye,10.,"Stale answer eyes stayed open");
  equal(parameter(host,host.talk),0.,"Stale answer mouth stayed open");
  require(stats.stale_frames>0,"Stale controls were not counted");
  // Feedback is never mistaken for the actual answer, even if asked to play.
  ++value.owner;value.sequence=0;value.audio_sample=0;value.track=2;frame(1./16);
  equal(stats.eye,10.,"Thinking feedback opened the answer eyes");
  equal(parameter(host,host.talk),0.,"Thinking feedback animated the answer mouth");
  // Preserve all old rejection rules and reject unknown eye-policy bits.
  auto rejected=value;rejected.sequence++;
  rejected.expression=YUKI_EYES_MASK;require(!yuki_control(&host,&rejected),"Conflicting eye flags accepted");
  rejected.expression=0x400;require(!yuki_control(&host,&rejected),"Unknown eye flag accepted");
  rejected.expression=6;require(!yuki_control(&host,&rejected),"Unknown base expression accepted");
  rejected=value;require(!yuki_control(&host,&rejected),"Duplicate sequence accepted");
  rejected.sequence++;rejected.audio_sample--;
  require(!yuki_control(&host,&rejected),"Rewound sample accepted");
  // After cancel/idle, release the override and retain natural blinking.
  ++value.owner;value.sequence=0;value.audio_sample=0;
  value.expression=YUKI_EYES_AUTHORED;value.playing=0;value.track=0;
  double eye_min=100.,eye_max=-100.;
  for(int i=0;i<640;++i){
   frame(1./16);eye_min=std::min(eye_min,stats.eye);eye_max=std::max(eye_max,stats.eye);
   equal(parameter(host,host.talk),0.,"Idle mouth moved after cancel");
   equal(host.instance->difference_value(host.facial_source,host.face[2]),0.,"Idle retained an eye override");
  }
  require(eye_min<1. && eye_max>9.,"Authored idle blink did not resume");
  std::cout<<"{\"status\":\"PASS\",\"thinking_frames\":640,\"answer_frames\":64,"
   "\"idle_frames\":640,\"native_host_executed\":true,\"gpu_or_audio_device_opened\":false,"
   "\"physical_fps_measured\":false,\"visual_preview_passed\":false}\n";
  return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
