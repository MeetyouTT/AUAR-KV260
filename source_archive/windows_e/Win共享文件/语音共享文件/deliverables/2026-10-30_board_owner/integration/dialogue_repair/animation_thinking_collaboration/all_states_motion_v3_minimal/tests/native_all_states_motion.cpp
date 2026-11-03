// SPDX-License-Identifier: AGPL-3.0-only
// Compile twice: AURA_BASELINE for unchanged b243 source, otherwise candidate.
// Public asset parameter observations; no GPU, audio, network or real-time waits.
#define main eye_regression_main
#ifdef AURA_BASELINE
#include "baseline_eye_gate.cpp"
#else
#include "native_eye_gate.cpp"
#endif
#undef main
#include <ctime>
#include <limits>

struct Span {
 double low=std::numeric_limits<double>::infinity(),high=-std::numeric_limits<double>::infinity();
 void add(double v){require(std::isfinite(v),"Nonfinite observation");low=std::min(low,v);high=std::max(high,v);}
 double extent() const {return high-low;}
};

int main(int argc,char** argv){
 try {
  require(eye_regression_main(argc,argv)==0,"Existing eye/mouth/owner/TTL tests failed");
#ifndef AURA_BASELINE
  aura_yuki::GentleMotion policy;
  std::array<float,2> previous{};
  for(int tick=0;tick<12000;++tick){
   auto values=policy.step(static_cast<aura_yuki::MotionMood>((tick/37)%3));
   for(std::size_t i=0;i<values.size();++i){
    require(std::abs(values[i])<=aura_yuki::GentleMotion::maximum[i]+.000001,"Offset exceeds bound");
    require(std::abs(values[i]-previous[i])<.17,"State transition jumps");
   }
   previous=values;
  }
#endif
  constexpr std::array<const char*,24> names{
   "head_LR","head_UD","head_slant","body_LR","body_UD","body_slant",
   "hair_LR_front","hair_UD_front","hair_LR_M_front",
   "hair_LR_sideL","hair_UD_sideL","hair_LR_M_sideL",
   "hair_LR_sideR","hair_UD_sideR","hair_LR_M_sideR",
   "hair_LR","hair_UD","hair_LR_M",
   "quake_LR","quake_UD","quake_LR_M","quake_LR_spare","quake_UD_spare","quake_LR_M_spare"};
  constexpr std::array<const char*,6> states{"IDLE","LISTENING","THINKING","ANSWER","PAUSED","CANCELLED"};
  Host host(argv[1],argv[2],argv[3],1);YukiStats stats{};
  std::array<ParamId,24> ids{};
  for(std::size_t i=0;i<ids.size();++i){ids[i]=host.program->scene().find_variable(names[i]);require(ids[i].valid(),"Missing parameter");}
  YukiControl value{};value.owner=1;value.sample_rate=24000;value.gain=.85f;
  double now=10.;host.draw(now,423,516,&stats);
  nlohmann::json observations=nlohmann::json::array();
  const auto cpu_started=std::clock();
  for(std::uint32_t pose=0;pose<2;++pose)for(std::size_t state=0;state<states.size();++state){
   ++value.owner;value.sequence=0;value.audio_sample=0;value.pose=pose;
   value.expression=state==2?YUKI_EYES_THINKING_CLOSED:
       (state==3||state==4)?YUKI_EYES_ANSWER_OPEN:YUKI_EYES_AUTHORED;
   value.track=(state==3||state==4)?1:0;value.playing=state==3||state==4;value.paused=state==4;
   std::array<Span,24> spans{};
#ifndef AURA_BASELINE
   std::array<Span,2> offsets{};
#endif
   for(int frame=0;frame<160;++frame){
    now+=1./16;++value.sequence;value.captured_at=now;value.audio_sample+=1500;
    value.level=float(.12+.78*(.5+.5*std::sin(frame*.29)));
    require(yuki_control(&host,&value)==1,"Valid control rejected");host.draw(now,423,516,&stats);
#ifndef AURA_BASELINE
    require(host.gentle_motion.ticks()+1==host.instance->tick_count(),"Additional author/physics tick");
    for(std::size_t i=0;i<host.motion.size();++i){
     const auto delta=host.instance->difference_value(host.motion_source,host.motion[i]);
     require(std::abs(delta)<=aura_yuki::GentleMotion::maximum[i]+.000001,"Offset bound failed in real Host");
     if(frame>=32)offsets[i].add(delta);
    }
#endif
    if(frame>=32)for(std::size_t i=0;i<ids.size();++i)spans[i].add(parameter(host,ids[i]));
    if(state==2||state==4)equal(stats.eye,10.,"Thinking/paused eyes regressed");
    if(state==3)equal(stats.eye,0.,"Audible answer eyes regressed");
    else equal(parameter(host,host.talk),0.,"Silent state opened mouth");
   }
   nlohmann::json row{{"state",states[state]},{"pose",pose},{"warmup_frames",32},{"parameters",nlohmann::json::object()}};
   for(std::size_t i=0;i<ids.size();++i)row["parameters"][names[i]]={{"min",spans[i].low},{"max",spans[i].high},{"span",spans[i].extent()}};
#ifndef AURA_BASELINE
   for(auto span:offsets)require(span.extent()>.035,"Extra head channel stopped in a requested state");
   for(std::size_t i=0;i<6;++i)require(spans[i].extent()>.0001,"Head/body final channel is static");
   int hair=0,parts=0,hair_groups=0;
   for(std::size_t i=6;i<18;++i)if(spans[i].extent()>.0001)++hair;
   for(std::size_t i=18;i<24;++i)if(spans[i].extent()>.0001)++parts;
   for(std::size_t group=0;group<4;++group){
    bool moving=false;
    for(std::size_t axis=0;axis<3;++axis)if(spans[6+group*3+axis].extent()>.0001)moving=true;
    if(moving)++hair_groups;
   }
   require(hair_groups>=3,"Fewer than three independent hair chains move");
   require(parts>=1,"No parts output moves");
   row["moving_hair_outputs"]=hair;row["moving_hair_chains"]=hair_groups;row["moving_parts_outputs"]=parts;
#endif
   observations.push_back(row);
  }
  nlohmann::json report{{"status","PASS"},{"native_frames",1920},{"states",6},{"poses",2},
   {"parameter_observations",observations},{"eye_regression_passed",true},{"author_ticks",stats.author_ticks},
   {"readback_cpu_ms",1000.*double(std::clock()-cpu_started)/CLOCKS_PER_SEC},
   {"readback_cpu_includes_parameter_observation",true},{"gpu_or_audio_device_opened",false},
   {"physical_fps_measured",false},{"visual_preview_passed",false}};
#ifdef AURA_BASELINE
  report["variant"]="baseline_b243_source";
#else
  report["variant"]="minimal_two_head_channels";report["policy_author_ticks"]=12000;
#endif
  std::cout<<report.dump()<<'\n';return 0;
 }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
