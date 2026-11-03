// SPDX-License-Identifier: AGPL-3.0-only
// Reuse the real Host/core and GPU-free renderer, including the eye regression.
#define main eye_regression_main
#include "native_eye_gate.cpp"
#undef main
#include <limits>

namespace {
struct Span {
 double low=std::numeric_limits<double>::infinity(),high=-std::numeric_limits<double>::infinity();
 void add(double v){require(std::isfinite(v),"Nonfinite motion observation");low=std::min(low,v);high=std::max(high,v);}
 double extent() const{return high-low;}
};
}

int main(int argc,char** argv){
 try{
  require(eye_regression_main(argc,argv)==0,"Eye/mouth/cancel regression failed");
  aura_yuki::GentleMotion policy;
  std::array<float,6> previous{};
  for(int tick=0;tick<12000;++tick){
   const auto mode=static_cast<aura_yuki::MotionMood>((tick/37)%3);
   const auto value=policy.step(mode,(tick%41)/40.);
   for(std::size_t i=0;i<value.size();++i){
    require(std::abs(value[i])<=aura_yuki::GentleMotion::maximum[i]+.000001,"Motion exceeds its small additive bound");
    require(std::abs(value[i]-previous[i])<(i<3?.17:.05),"Motion jumps on a mode/voice transition");
   }
   previous=value;
  }
  Host host(argv[1],argv[2],argv[3],1);
  YukiControl value{};value.owner=1;value.sample_rate=24000;
  YukiStats stats{};double now=10.;
  host.draw(now,423,516,&stats); // Establish the native clock before measuring advancement.
  constexpr std::array<const char*,8> physical_names{
   "hair_LR_front","hair_LR_M_front","hair_LR_sideL","hair_LR_sideR", "hair_LR","hair_LR_M","quake_LR","quake_LR_M"};
  std::array<ParamId,8> physical{};std::array<Span,8> physics_span{};
  for(std::size_t i=0;i<physical.size();++i){
   physical[i]=host.program->scene().find_variable(physical_names[i]);
   require(physical[i].valid(),"Missing existing hair/parts chain output");
  }
  constexpr std::array<const char*,6> states{"IDLE","LISTENING","THINKING","ANSWER","PAUSED","CANCELLED"};
  std::array<std::array<Span,6>,6> offsets{};
  std::uint64_t previous_ticks=0;
  for(std::size_t state=0;state<states.size();++state){
   ++value.owner;value.sequence=0;value.audio_sample=0;
   value.expression=state==2?YUKI_EYES_THINKING_CLOSED:
    (state==3||state==4)?YUKI_EYES_ANSWER_OPEN:YUKI_EYES_AUTHORED;
   value.track=(state==3||state==4)?1:0;value.playing=state==3||state==4;value.paused=state==4;
   value.pose=state%2;value.gain=.85f;
   for(int frame=0;frame<160;++frame){
    now+=1./16;++value.sequence;value.captured_at=now;value.audio_sample+=1500;
    value.level=float(.12+.78*(.5+.5*std::sin(frame*.29)));
    require(yuki_control(&host,&value)==1,"Motion control rejected");host.draw(now,423,516,&stats);
    require(host.gentle_motion.ticks()>previous_ticks,"Motion stopped outside thinking");
    previous_ticks=host.gentle_motion.ticks();
    require(host.gentle_motion.ticks()+1==host.instance->tick_count(),"Extra author/physics tick introduced");
    for(std::size_t i=0;i<host.motion.size();++i){
     const auto delta=host.instance->difference_value(host.motion_source,host.motion[i]);
     offsets[state][i].add(delta);
     require(std::abs(delta)<=aura_yuki::GentleMotion::maximum[i]+.000001,"Bound exceeded in real native core");
     require(std::abs(parameter(host,host.motion[i]))<=30.,"Authored parameter left its supported range");
    }
    for(std::size_t i=0;i<physical.size();++i)physics_span[i].add(parameter(host,physical[i]));
    if(state==2||state==4)equal(stats.eye,10.,"Thinking/pause eye rule regressed");
    if(state==3)equal(stats.eye,0.,"Actual answer eye rule regressed");
    else equal(parameter(host,host.talk),0.,"Body motion opened a silent mouth");
   }
   for(std::size_t i=0;i<host.motion.size();++i)
    require(offsets[state][i].extent()>.035,"A head/body component is static in a requested state");
  }
  int hair_moving=0;
  for(std::size_t i=0;i<6;++i)if(physics_span[i].extent()>.0001)++hair_moving;
  require(hair_moving>=3,"Existing multiple hair chains did not move");
  require(physics_span[6].extent()>.0001||physics_span[7].extent()>.0001,"Existing parts chain did not move");
  std::cout<<"{\"status\":\"PASS\",\"states\":6,\"native_frames\":960,"
   "\"motion_policy_author_ticks\":12000,\"head_body_channels\":6,\"moving_hair_outputs\":"<<hair_moving
   <<",\"parts_chain_moved\":true,\"eye_regression_passed\":true,\"gpu_or_audio_device_opened\":false,"
   "\"physical_fps_measured\":false,\"visual_preview_passed\":false}\n";
  return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
