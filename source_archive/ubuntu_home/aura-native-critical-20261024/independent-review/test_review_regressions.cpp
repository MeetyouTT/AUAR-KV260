// Independent positive fault injection of the corrected source snapshot.
#include "corrected_native_lease.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
using aura::Completion;
using aura::NativeLease;
using aura::Outcome;
using aura::Snapshot;
using aura::Task;
struct Clock {
  std::uint64_t now=1'000'000'000, delay=0;
  unsigned calls=0, at=0;
  std::uint64_t tick() { if (++calls==at) now+=delay;return now; }
};
struct Work { Clock* clock;unsigned calls=0;std::uint64_t duration=0; };
static Completion work(void* pointer) {
  auto& value=*static_cast<Work*>(pointer);++value.calls;value.clock->now+=value.duration;
  return {true,true,0};
}
static Completion contradictory(void*) { return {false,true,0}; }
static void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
int main() {
  try {
    {
      Clock clock;clock.at=1;clock.delay=40'000'000;
      NativeLease gate([&] { return clock.tick(); });gate.announce_primary(1'036'000'000);
      Work native{&clock};auto result=gate.execute(Task::yunet,2'000'000'000,0,work,&native);
      Snapshot state;gate.snapshot(state);
      require(result.outcome==Outcome::deadline && native.calls==0 && state.admissions[1]==0,
              "final common sample must decline stale admission without a native call");
    }
    {
      Clock clock;clock.at=2;clock.delay=40'000'000;
      NativeLease gate([&] { return clock.tick(); });gate.announce_primary(1'036'000'000);
      Work native{&clock};auto result=gate.execute(Task::yunet,2'000'000'000,0,work,&native);
      Snapshot state;gate.snapshot(state);
      require(result.outcome==Outcome::deadline && native.calls==0 && !result.completion.submitted,
              "post-admission pause must withdraw before submission");
      require(result.start_ns==1'000'000'000 && result.hardcap && result.guard && !state.active && !state.fenced,
              "withdrawal must retain its real lease overrun and release safely");
    }
    {
      Clock clock;clock.at=3;clock.delay=20'000'000;
      NativeLease gate([&] { return clock.tick(); });gate.announce_primary(2'000'000'000);
      Work native{&clock,0,20'000'000};auto result=gate.execute(Task::sface,2'000'000'000,0,work,&native);
      require(native.calls==1 && result.start_ns==1'000'000'000 && result.hardcap,
              "active lease pause cannot vanish from the metered start");
      require(result.release_decision_ns-result.start_ns==40'000'000,
              "full recorded duration must include the simulated stall");
    }
    {
      Clock clock;
      NativeLease gate([&] { return clock.tick(); });gate.announce_primary(2'000'000'000);
      auto result=gate.execute(Task::sface,2'000'000'000,0,contradictory,nullptr);
      Snapshot state;gate.snapshot(state);
      require(result.outcome==Outcome::fenced && state.fenced && !state.active,
              "contradictory completion flags must fail closed");
    }
    std::cout << "{\"passed\":true,\"tests\":4,\"scope\":\"corrected native gate local fault injection; no VART or DPU\"}\n";
    return 0;
  } catch (const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
