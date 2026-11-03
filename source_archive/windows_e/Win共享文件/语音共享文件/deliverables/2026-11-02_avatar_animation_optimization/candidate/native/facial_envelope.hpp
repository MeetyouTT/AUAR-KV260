// SPDX-License-Identifier: AGPL-3.0-only
#pragma once
#include <algorithm>

namespace aura_yuki {
// The native model already has a seeded blink controller. This envelope only
// blends its current result into/out of the existing thinking closure policy.
// It advances with the same 60 Hz author clock, never with GTK render count.
class FacialEnvelope {
 float closed_=0.f;
 public:
 float closed_weight() const noexcept { return closed_; }
 void step(bool thinking_closed) noexcept {
  constexpr float maximum_step=1.f/9.f; // 150 ms, continuous on policy reversal
  const float target=thinking_closed?1.f:0.f;
  closed_+=std::clamp(target-closed_,-maximum_step,maximum_step);
  if(closed_<.00001f)closed_=0.f;
  if(closed_>.99999f)closed_=1.f;
 }
};
}
