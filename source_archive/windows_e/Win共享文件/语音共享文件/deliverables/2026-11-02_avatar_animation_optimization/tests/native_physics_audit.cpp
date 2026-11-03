#define main original_policy_main
#include "native_original_policy.cpp"
#undef main
#include <limits>
#include <ctime>
int main(int argc,char** argv){
 try{
  require(original_policy_main(argc,argv)==0,"Original audio/eye/owner rules failed");
  constexpr std::array<const char*,26> names{
   "head_LR","head_slant","body_LR","body_slant","aura_arm_left","aura_arm_right",
   "hair_LR_front","hair_UD_front","hair_LR_M_front","hair_LR_sideL","hair_UD_sideL","hair_LR_M_sideL",
   "hair_LR_sideR","hair_UD_sideR","hair_LR_M_sideR","hair_LR","hair_UD","hair_LR_M",
   "quake_LR","quake_UD","quake_LR_M","quake_LR_spare","quake_UD_spare","quake_LR_M_spare","act_sp","body_UD"};
  Host host(argv[1],argv[2],argv[3],1);YukiStats stats{};double now=10.;
  YukiControl c{};c.owner=1;c.sample_rate=24000;c.gain=.8f;host.draw(now,423,516,&stats);
  std::array<ParamId,names.size()> ids{};
  for(std::size_t i=0;i<names.size();++i)ids[i]=host.program->scene().find_variable(names[i]);
  nlohmann::json rows=nlohmann::json::array();
  for(int scene=0;scene<6;++scene){
   ++c.owner;c.sequence=0;c.audio_sample=0;c.pose=scene/3;c.track=scene%3==2?1:0;c.playing=scene%3==2;
   c.expression=scene%3==1?YUKI_EYES_THINKING_CLOSED:scene%3==2?YUKI_EYES_ANSWER_OPEN:0;
   std::array<double,names.size()> low,high;low.fill(1e30);high.fill(-1e30);
   for(int frame=0;frame<256;++frame){
    now+=1./16;c.captured_at=now;++c.sequence;c.audio_sample+=1500;c.level=float(.5+.4*std::sin(now*7.));
    require(yuki_control(&host,&c),"Fresh control rejected");host.draw(now,423,516,&stats);
    if(frame<48)continue;
    for(std::size_t i=0;i<names.size();++i)if(ids[i].valid()){
     const auto v=parameter(host,ids[i]);require(std::isfinite(v),"Nonfinite physical value");
     low[i]=std::min(low[i],double(v));high[i]=std::max(high[i],double(v));
    }
   }
   nlohmann::json row{{"pose",c.pose},{"state",scene%3==0?"IDLE":scene%3==1?"THINKING":"ANSWER"},{"parameters",nlohmann::json::object()}};
   for(std::size_t i=0;i<names.size();++i)if(ids[i].valid())row["parameters"][names[i]]={{"min",low[i]},{"max",high[i]},{"span",high[i]-low[i]}};
#ifdef OPTIMIZED
   require(high[4]-low[4]>5. && high[5]-low[5]>3.,"Arms did not move enough");
   require(low[4]>=-10.50001&&high[4]<=10.50001&&low[5]>=-7.50001&&high[5]<=7.50001,"Arm bound exceeded");
   int groups=0;for(int g=0;g<4;++g)if(high[6+3*g]-low[6+3*g]>.001||high[7+3*g]-low[7+3*g]>.001)++groups;
   require(groups>=3,"Original hair solvers did not react");
#endif
   rows.push_back(row);
  }
  nlohmann::json out{{"status","PASS"},{"original_audio_eye_owner_policy_passed",true},{"frames",1536},{"states_and_poses",rows},{"gpu_opened",false}};
  std::cout<<out.dump()<<'\n';return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
