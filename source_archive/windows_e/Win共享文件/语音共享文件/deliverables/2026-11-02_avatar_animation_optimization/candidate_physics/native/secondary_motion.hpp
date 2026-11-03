// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <nekomote/model/asset.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace aura_yuki {
// Add continuous rotation at the four existing arm branch origins. Original
// art, masks, shoulder position, selector, skinning and child meshes stay intact.
// Imported in-memory asset only; the signed resource files are never rewritten.
inline void bind_arm_swing(nekomote::model::ModelAsset& asset){
 using namespace nekomote::model;
 int bound=0;
 for(auto& part:asset.parts){
  if(part.group!="body_parts"||part.name!="全身変形基礎")continue;
  if(part.layers.size()!=1)throw std::runtime_error("Unexpected arm hierarchy");
  for(auto& branch:part.layers[0].children){
   const bool left=branch.label=="腕LA_le"||branch.label=="腕LB_le";
   const bool right=branch.label=="腕RA_le"||branch.label=="腕RB_le";
   if(!left&&!right)continue;
   if(branch.parameterize.has_value()||branch.frame_list.size()!=2||
      !branch.frame_list[0].content.has_value()||branch.frame_list[0].content.data.angle.has_value())
       throw std::runtime_error("Unexpected authored arm transform");
   const auto original=branch.frame_list[0];
   branch.parameter={{left?"aura_arm_left":"aura_arm_right",-12.f,12.f,60,0,true}};
   branch.parameterize={FieldState::Value,0};
   branch.frame_list.clear();
   for(int i=0;i<3;++i){
    auto f=original;f.time=float(i*30);f.type=2;
    f.content.data.angle={FieldState::Value,float(i*12-12)};
    branch.frame_list.push_back(std::move(f));
   }
   LayerFrame end;end.time=61;end.type=0;branch.frame_list.push_back(end);
   ++bound;
  }
 }
 if(bound!=4)throw std::runtime_error("Original four arm branches not found");
}

class SecondaryMotion {
 double phase_=0.,elapsed_=0.,energy_=1.;
 std::array<double,2> angle_{},velocity_{};
 public:
 static constexpr std::array<const char*,6> names{"head_LR","head_slant","body_LR","body_slant","aura_arm_left","aura_arm_right"};
 static constexpr std::array<double,6> maximum{3.6,1.9,1.6,1.2,10.5,7.5};
 std::array<float,6> step(int mood) noexcept {
  constexpr double dt=1./60.,tau=6.2831853071795864769;
  const double target=mood==1?1.18:mood==2?.78:1.;
  energy_+=(target-energy_)*.025315;
  phase_+=dt;elapsed_+=dt;
  double ramp=std::clamp(elapsed_/1.6,0.,1.);ramp=ramp*ramp*(3.-2.*ramp);
  const auto wave=[&](double period,double offset){return std::sin(tau*phase_/period+offset);};
  const double weight=ramp*energy_;
  const std::array<double,2> desired{
    weight*(6.5*wave(4.8,.4)+1.3*wave(9.3,1.1)),
    weight*(4.2*wave(5.7,2.2)+1.0*wave(10.1,.3))};
  // Semi-implicit damped spring: 60 Hz, f~0.95 Hz, damping ratio .58.
  // Keep velocity through state/owner changes for follow-through and settling.
  for(std::size_t i=0;i<2;++i){
   constexpr double omega=6.,damping=.58;
   velocity_[i]+=(omega*omega*(desired[i]-angle_[i])-2*damping*omega*velocity_[i])*dt;
   velocity_[i]=std::clamp(velocity_[i],-16.,16.);
   angle_[i]+=velocity_[i]*dt;
   const auto bound=maximum[i+4];
   if(std::abs(angle_[i])>bound){angle_[i]=std::clamp(angle_[i],-bound,bound);velocity_[i]=0.;}
  }
  const std::array<double,6> values{
   weight*(2.2*wave(7.6,.25)+.5*wave(13.7,1.1)),
   weight*(1.05*wave(8.7,.8)+.25*wave(15.1,1.6)),
   weight*1.1*wave(6.9,.6),weight*.8*wave(8.1,1.4),angle_[0],angle_[1]};
  std::array<float,6> result{};
  for(std::size_t i=0;i<6;++i)result[i]=float(std::clamp(values[i],-maximum[i],maximum[i]));
  return result;
 }
};
}
