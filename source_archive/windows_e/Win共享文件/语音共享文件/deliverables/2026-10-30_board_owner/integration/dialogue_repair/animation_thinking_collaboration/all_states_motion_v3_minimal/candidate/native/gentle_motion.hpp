// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace aura_yuki {
enum class MotionMood { Calm, Thinking, Answer };

// Only two additive head channels. Existing authored nod/breath/body and
// all four hair/two parts chains remain the source of the other movement.
// One update per existing author tick; phase survives every owner/state change.
class GentleMotion {
 double phase_=0.,elapsed_=0.,strength_=1.,pace_=1.;
 std::uint64_t ticks_=0;
 public:
 static constexpr std::array<double,2> maximum{3.6,1.9};
 static constexpr std::array<const char*,2> names{"head_LR","head_slant"};
 std::uint64_t ticks() const noexcept { return ticks_; }
 std::array<float,2> step(MotionMood mood) noexcept {
  constexpr double dt=1./60.,tau=6.2831853071795864769;
  const double strength=mood==MotionMood::Thinking?.86:mood==MotionMood::Answer?1.08:1.;
  const double pace=mood==MotionMood::Thinking?.88:mood==MotionMood::Answer?1.045:1.;
  strength_+=(strength-strength_)*.025315;
  pace_+=(pace-pace_)*.018348;
  phase_+=dt*pace_;elapsed_+=dt;++ticks_;
  double ramp=std::clamp(elapsed_/1.4,0.,1.);ramp=ramp*ramp*(3.-2.*ramp);
  const auto wave=[&](double period,double offset){return std::sin(tau*phase_/period+offset);};
  const double weight=ramp*strength_;
  const std::array<double,2> values{
   weight*(2.55*wave(7.6,.25)+.62*wave(13.7,1.1)),
   weight*(1.24*wave(8.7,.8)+.34*wave(15.1,1.6))};
  std::array<float,2> result{};
  for(std::size_t i=0;i<result.size();++i)
   result[i]=static_cast<float>(std::clamp(values[i],-maximum[i],maximum[i]));
  return result;
 }
};
}
