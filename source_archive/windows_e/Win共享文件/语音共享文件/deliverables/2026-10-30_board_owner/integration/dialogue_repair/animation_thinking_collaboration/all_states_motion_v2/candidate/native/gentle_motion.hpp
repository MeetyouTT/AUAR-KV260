// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace aura_yuki {
enum class MotionMood { Calm, Thinking, Answer };

// Small additive authored-parameter movement. One call per existing 60 Hz
// author tick; no wall-clock reset, allocation, random source, I/O or timer.
// Idle and listening share the calm base; thinking is slower, real answer
// intervals add a smoothed energy response. Pause/cancel keep natural motion.
class GentleMotion {
 double phase_=0.,elapsed_=0.,strength_=1.,pace_=1.,speech_=0.;
 std::uint64_t ticks_=0;
 public:
 static constexpr std::array<double,6> maximum{3.6,1.6,1.9,.65,.5,.65};
 static constexpr std::array<const char*,6> names{
  "head_LR","head_UD","head_slant","body_LR","body_UD","body_slant"};
 std::uint64_t ticks() const noexcept { return ticks_; }
 std::array<float,6> step(MotionMood mood,double energy) noexcept {
  constexpr double dt=1./60.,tau=6.2831853071795864769;
  const double strength=mood==MotionMood::Thinking?.86:mood==MotionMood::Answer?1.08:1.;
  const double pace=mood==MotionMood::Thinking?.88:mood==MotionMood::Answer?1.045:1.;
  strength_+=(strength-strength_)*.025315;
  pace_+=(pace-pace_)*.018348;
  const double voice=mood==MotionMood::Answer?std::clamp(energy,0.,1.):0.;
  speech_+=(voice-speech_)*.0799556;
  phase_+=dt*pace_;elapsed_+=dt;++ticks_;
  double ramp=std::clamp(elapsed_/1.4,0.,1.);ramp=ramp*ramp*(3.-2.*ramp);
  const auto wave=[&](double period,double offset){return std::sin(tau*phase_/period+offset);};
  const double head=ramp*strength_;
  // Different periods and phase offsets give head and torso a little lag,
  // rather than sliding/rotating the entire rendered portrait as one image.
  std::array<double,6> value{
   head*(2.55*wave(7.6,.25)+.62*wave(13.7,1.1)),
   head*(.72*wave(5.9,1.3)+.25*wave(11.3,.2)+.38*speech_*wave(1.9,.6)),
   head*(1.24*wave(8.7,.8)+.34*wave(15.1,1.6)),
   ramp*(.34*wave(8.2,-.6)+.12*wave(14.3,.7)),
   ramp*.36*wave(4.8,.5),
   ramp*(.37*wave(8.7,-.1)+.11*wave(13.3,1.8))};
  std::array<float,6> output{};
  for(std::size_t i=0;i<value.size();++i)
   output[i]=static_cast<float>(std::clamp(value[i],-maximum[i],maximum[i]));
  return output;
 }
};
}
