#define main original_policy_main
#include "native_original_policy.cpp"
#undef main
#include <limits>

static_assert(sizeof(YukiDialogueControl)==88 && sizeof(YukiMotionStats)==80);
int main(int argc,char** argv){
 try{
  require(original_policy_main(argc,argv)==0,"Original audio/eye/owner policy regression");
  require((yuki_control_features()&YUKI_FEATURE_DIALOGUE_MOTION)!=0,"Motion capability missing");
  Host host(argv[1],argv[2],argv[3],1);YukiStats stats{};YukiMotionStats motion{};
  YukiDialogueControl c{};c.audio.owner=1;c.audio.sample_rate=24000;c.generation=1;
  double now=10.;host.draw(now,423,516,&stats);
  std::array<double,8> previous{};std::uint64_t frames=0;double rear_peak=0.,rear_speed=0.;
  constexpr std::array<const char*,10> physical_names{"hair_LR_front","hair_UD_front","hair_LR_sideL","hair_UD_sideL","hair_LR_sideR","hair_UD_sideR","hair_LR","hair_UD","quake_LR","quake_UD"};
  std::array<ParamId,10> physical_ids{};
  for(std::size_t i=0;i<10;++i){physical_ids[i]=host.program->scene().find_variable(physical_names[i]);require(physical_ids[i].valid(),"Existing physical channel missing");}
  const auto frame=[&](double dt=1./60){
   now+=dt;c.audio.captured_at=now;++c.audio.sequence;c.audio.audio_sample+=std::uint64_t(dt*24000);
   require(yuki_control_v2(&host,&c),"Fresh v2 control rejected");host.draw(now,423,516,&stats);
   require(yuki_motion_status(&host,&motion),"Motion observation failed");
   for(std::size_t i=0;i<8;++i){
    const double x=motion.values[i];require(std::isfinite(x),"Nonfinite motion");
    require(std::abs(x)<=aura_yuki::DialogueMotion::maximum[i]+.00001,"Composed joint limit exceeded");
    if(dt>0 && frames){const double speed=std::abs(x-previous[i])/dt;require(speed<=aura_yuki::DialogueMotion::speed_limit[i]+.01,"Joint slew limit exceeded");if(i==4)rear_speed=std::max(rear_speed,speed);}
    previous[i]=x;
   }
   rear_peak=std::max(rear_peak,std::abs(double(motion.values[4])));++frames;
  };
  nlohmann::json states=nlohmann::json::array();
  for(unsigned pose=0;pose<2;++pose){
   c.audio.pose=pose;
   for(unsigned state=0;state<YUKI_STATE_COUNT;++state){
    c.state=state;c.action=0;c.action_token=0;c.audio.playing=state>=YUKI_SPEAKING&&state<=YUKI_SPEAKING_LOW;
    c.audio.track=c.audio.playing?1:0;c.audio.expression=c.audio.playing?YUKI_EYES_ANSWER_OPEN:state==YUKI_THINKING?YUKI_EYES_THINKING_CLOSED:0;
    c.audio.gain=.8f;c.audio.level=.65f;
    std::array<double,10> low,high;low.fill(1e30);high.fill(-1e30);
    for(int i=0;i<240;++i){
     frame();if(i<60)continue;
     for(std::size_t j=0;j<10;++j){const auto v=parameter(host,physical_ids[j]);require(std::isfinite(v),"Nonfinite existing physics");low[j]=std::min(low[j],double(v));high[j]=std::max(high[j],double(v));}
    }
    require(motion.state==state,"State profile was not applied");
    nlohmann::json physical=nlohmann::json::object();
    unsigned moving_hair_groups=0;
    for(std::size_t j=0;j<10;++j)physical[physical_names[j]]=high[j]-low[j];
    for(std::size_t j=0;j<4;++j)if(high[2*j]-low[2*j]>.001||high[2*j+1]-low[2*j+1]>.001)++moving_hair_groups;
    require(moving_hair_groups>=3,"Dialogue posture lost the existing hair follow-through");
    states.push_back({{"pose",pose},{"state",state},{"values",motion.values},{"physical_spans",physical}});
   }
  }
  c.audio.pose=0;c.audio.playing=1;c.audio.track=1;c.audio.expression=YUKI_EYES_ANSWER_OPEN;c.audio.paused=0;
  std::uint64_t token=1;
  nlohmann::json reactions=nlohmann::json::array();
  for(unsigned action=1;action<=4;++action){
   ++c.generation;c.action=0;c.action_token=0;c.state=YUKI_SPEAKING;
   for(int i=0;i<120;++i)frame();
   c.action=action;c.action_token=token++;c.state=action==1?YUKI_ACK_NOD:action==2?YUKI_DENY_SHAKE:action==3?YUKI_AWAKE:YUKI_PUZZLED;
   const auto before=motion.gestures_started;double lo=100,hi=-100,nod=0,tilt=0;
   for(int i=0;i<100;++i){
    frame();lo=std::min(lo,double(motion.values[0]));hi=std::max(hi,double(motion.values[0]));
    nod=std::max(nod,std::abs(double(motion.values[6])));tilt=std::max(tilt,std::abs(double(motion.values[1])));
   }
   require(motion.gestures_started==before+1,"Repeated mailbox offer restarted a gesture");
   require(motion.completed_token==c.action_token,"Native gesture did not complete");
   if(action==1)require(nod>1.1,"Nod was not visible in head_UD");
   if(action==2)require(hi-lo>1.0,"Shake was not visible in head_LR");
   if(action==4)require(tilt>.7,"Puzzled tilt missing");
   reactions.push_back({{"action",action},{"head_LR_min",lo},{"head_LR_max",hi},{"head_UD_absmax",nod},{"head_slant_absmax",tilt}});
  }
  // A new generation and cancellation stop the old cue without snapping joints.
  c.action=YUKI_ACTION_SHAKE;c.action_token=token++;frame();const auto started=motion.gestures_started;
  c.audio.paused=1;frame();require(!motion.action,"Paused gesture still active");equal(stats.mouth,0,"Pause retained answer mouth");
  c.audio.paused=0;++c.generation;c.action_token=0;c.action=0;c.state=YUKI_LISTENING;frame();require(!motion.action,"Old generation gesture survived");
  const auto accepted=c;auto bad=c;bad.audio.sequence++;bad.generation--;
  require(!yuki_control_v2(&host,&bad),"Old generation accepted");
  require(host.control.sequence==accepted.audio.sequence,"Rejected v2 partially mutated audio control");
  bad=c;bad.audio.sequence++;bad.state=YUKI_STATE_COUNT;require(!yuki_control_v2(&host,&bad),"Invalid state accepted");
  bad=c;bad.audio.sequence++;bad.action=1;bad.action_token=1;require(!yuki_control_v2(&host,&bad),"Old action token accepted");
  now+=.151;host.draw(now,423,516,&stats);yuki_motion_status(&host,&motion);
  require(motion.state==YUKI_IDLE&&!motion.action,"Stale motion did not settle to idle");equal(stats.mouth,0,"Stale answer mouth remained open");
  nlohmann::json out{{"status","PASS"},{"original_audio_eye_owner_policy_passed",true},{"frames",frames},
   {"state_pose_cases",states},{"reactions",reactions},{"lower_arm_absmax_deg",rear_peak},{"lower_arm_peak_speed_deg_s",rear_speed},
   {"gestures_started_before_pause",started},{"renderer","CPU stub; real playback and physics core"},{"GPU_or_audio_opened",false}};
  std::cout<<out.dump()<<'\n';return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
