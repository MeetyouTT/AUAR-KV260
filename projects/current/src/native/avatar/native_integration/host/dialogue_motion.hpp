// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include "yuki_host.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace aura_yuki {
// Deterministic 60 Hz additive layer. No I/O, allocations or clock ownership.
// Original hair/parts physics runs AFTER these joint targets in the core.
class DialogueMotion {
 struct Profile {double head,body,lower,front,nod,tilt,lean;};
 static constexpr std::array<Profile,YUKI_STATE_COUNT> profiles{{
  {.70,.65,.70,.60, 0.,0.,0.},       // idle
  {.60,.55,.60,.60,-.30,.20,.20},    // present
  {.60,.60,.65,.65,-.40,0.,-.20},    // awake
  {.35,.30,.45,.40, .25,.45,.65},    // listening
  {.28,.25,.35,.35, .70,.85,.25},    // thinking
  {.65,.60,.75,.80,-.20,0.,.20},     // neutral speech
  {.85,.75,.95,.95,-.90,-.15,-.15},  // happy speech
  {.38,.30,.45,.45, 1.00,.15,.15},   // low speech
  {.45,.40,.55,.65,-.20,0.,.15},     // nod overlay
  {.40,.35,.50,.55, .20,0.,.10},     // shake overlay
  {.30,.25,.35,.40, .45,.40,.10},    // puzzled overlay
  {.30,.25,.35,.30, 0.,0.,0.},       // cancelled
  {.25,.20,.30,.25, .55,.20,0.},     // error
  {.30,.25,.35,.30, 0.,0.,0.}        // paused
 }};
 Profile profile_=profiles[YUKI_IDLE];
 std::array<double,8> value_{},velocity_{};
 double phase_=0.,elapsed_=0.,speech_=0.,gesture_age_=0.;
 std::uint64_t generation_=0,seen_token_=0,active_token_=0,completed_token_=0,started_=0,completed_=0;
 std::uint32_t state_=YUKI_IDLE,requested_=YUKI_IDLE,action_=0;
 static double approach(double a,double b,double tau){return a+(b-a)*(1-std::exp(-(1./60)/tau));}
 static double duration(std::uint32_t action){return action==YUKI_ACTION_SHAKE?.80:action==YUKI_ACTION_PUZZLED?.84:.72;}
 void cancel_gesture() noexcept {action_=0;active_token_=0;gesture_age_=0.;}
 public:
 static constexpr std::array<const char*,8> names{
  "head_LR","head_slant","body_LR","body_slant","aura_arm_left","aura_arm_right","head_UD","body_UD"};
 // Arm units are LOCAL rotation degrees. Head/body are authored parameter units.
 static constexpr std::array<double,8> maximum{3.6,1.9,1.6,1.2,4.,7.5,4.,1.4};
 static constexpr std::array<double,8> speed_limit{16.,10.,8.,6.,6.,16.,18.,8.};
 void offer(std::uint64_t generation,std::uint32_t state,std::uint64_t token,std::uint32_t action) noexcept {
  if(generation!=generation_){generation_=generation;cancel_gesture();}
  requested_=state;
  if(state==YUKI_CANCELLED||state==YUKI_ERROR||state==YUKI_PAUSED){cancel_gesture();return;}
  if(action && token>seen_token_){
   seen_token_=token;active_token_=token;action_=action;gesture_age_=0.;++started_;
  }
 }
 std::array<float,8> step(bool fresh,bool paused,bool audible,double level) noexcept {
  constexpr double dt=1./60.,pi=3.14159265358979323846,tau=2*pi;
  phase_+=dt;elapsed_+=dt;
  state_=paused?YUKI_PAUSED:fresh?requested_:YUKI_IDLE;
  if(!fresh||paused||state_==YUKI_CANCELLED||state_==YUKI_ERROR)cancel_gesture();
  const auto target=profiles[state_];
  profile_.head=approach(profile_.head,target.head,.25);profile_.body=approach(profile_.body,target.body,.30);
  profile_.lower=approach(profile_.lower,target.lower,.35);profile_.front=approach(profile_.front,target.front,.28);
  profile_.nod=approach(profile_.nod,target.nod,.24);profile_.tilt=approach(profile_.tilt,target.tilt,.28);
  profile_.lean=approach(profile_.lean,target.lean,.32);
  speech_=approach(speech_,audible?std::clamp(level,0.,1.):0.,.24);
  double ramp=std::clamp(elapsed_/1.6,0.,1.);ramp=ramp*ramp*(3.-2.*ramp);
  const auto wave=[&](double period,double offset){return std::sin(tau*phase_/period+offset);};
  const bool speaking=state_==YUKI_SPEAKING||state_==YUKI_SPEAKING_HAPPY||state_==YUKI_SPEAKING_LOW;
  const double accent=speaking?speech_:0.;
  std::array<double,8> desired{
   profile_.head*(2.2*wave(7.6,.25)+.5*wave(13.7,1.1)),
   profile_.tilt+profile_.head*(1.05*wave(8.7,.8)+.25*wave(15.1,1.6)),
   profile_.body*1.1*wave(6.9,.6),profile_.body*.8*wave(8.1,1.4),
   profile_.lower*(2.6*wave(6.8,.4)+.45*wave(10.7,1.1)),
   profile_.front*(4.2*wave(5.7,2.2)+wave(10.1,.3))+accent*.8,
   profile_.nod+accent*.45*wave(4.7,.2),profile_.lean+profile_.body*.18*wave(6.9,.6)};
  if(action_){
   const double u=std::clamp(gesture_age_/duration(action_),0.,1.);
   const double bump=std::pow(std::sin(pi*u),2);
   if(action_==YUKI_ACTION_NOD){desired[6]+=3.2*bump;desired[0]*=.35;desired[1]*=.55;}
   if(action_==YUKI_ACTION_SHAKE){desired[0]=3.2*std::sin(tau*u)*bump;desired[1]*=.4;}
   if(action_==YUKI_ACTION_SURPRISED){desired[6]-=2.5*bump;desired[7]-=.45*bump;desired[5]+=1.15*bump;}
   if(action_==YUKI_ACTION_PUZZLED){desired[1]+=1.3*bump;desired[6]+=.45*bump;desired[0]*=.4;}
   gesture_age_+=dt;
   if(gesture_age_>=duration(action_)){
    completed_token_=active_token_;++completed_;cancel_gesture();
   }
  }
  std::array<float,8> result{};
  for(std::size_t i=0;i<desired.size();++i){
   desired[i]=std::clamp(desired[i]*ramp,-maximum[i],maximum[i]);
   const double omega=i==4?5.:i==5?6.:9.;
   const double damping=i==4?.85:i==5?.68:.90;
   velocity_[i]+=(omega*omega*(desired[i]-value_[i])-2*damping*omega*velocity_[i])*dt;
   velocity_[i]=std::clamp(velocity_[i],-speed_limit[i],speed_limit[i]);
   value_[i]+=velocity_[i]*dt;
   if(std::abs(value_[i])>maximum[i]){value_[i]=std::clamp(value_[i],-maximum[i],maximum[i]);velocity_[i]=0.;}
   result[i]=float(value_[i]);
  }
  return result;
 }
 YukiMotionStats stats() const noexcept {
  YukiMotionStats out{generation_,active_token_,completed_token_,started_,completed_,state_,action_,{}};
  for(std::size_t i=0;i<value_.size();++i)out.values[i]=float(value_[i]);
  return out;
 }
 std::uint64_t seen_token() const noexcept {return seen_token_;}
};
}
