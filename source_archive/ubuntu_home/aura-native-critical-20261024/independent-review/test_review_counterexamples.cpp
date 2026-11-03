// Review of a byte-pinned source copy; no board, model, VART or DPU owner.
#include "reviewed_native_lease.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>

using aura::Completion;
using aura::NativeLease;
using aura::Outcome;
using aura::Snapshot;
using aura::Task;

struct VirtualClock {
  std::uint64_t now = 1'000'000'000;
  unsigned calls = 0, delay_at = 0;
  std::uint64_t delay = 0;
  std::uint64_t tick() {
    ++calls;
    if (calls == delay_at) now += delay;
    return now;
  }
};
struct NativeWork {
  VirtualClock* clock;
  unsigned calls = 0;
  std::uint64_t duration = 0, started = 0;
};
static Completion run_native(void* pointer) {
  auto& value = *static_cast<NativeWork*>(pointer);
  ++value.calls;
  value.started = value.clock->now;
  value.clock->now += value.duration;
  return {true, true, 0};
}
static void check(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}

int main() {
  try {
    // Current source: optional admission reads clock once for slack and a
    // second time for source TTL. Simulate being descheduled between them.
    VirtualClock stale;
    stale.delay_at = 2; stale.delay = 40'000'000;
    NativeLease stale_gate([&] { return stale.tick(); });
    stale_gate.announce_primary(1'036'000'000);  // Initially 36ms >= 30+5.
    NativeWork work{&stale};
    const auto stale_report = stale_gate.execute(Task::yunet, 2'000'000'000, 0, run_native, &work);
    const bool stale_submitted = work.calls == 1 && work.started > 1'031'000'000;
    check(stale_submitted && stale_report.guard, "expected stale-admission counterexample changed");

    // Current source sets active=true before the start timestamp. Simulate
    // a pause at that timestamp: 20ms lease hold disappears from elapsed.
    VirtualClock late;
    late.delay_at = 3; late.delay = 20'000'000;
    NativeLease late_gate([&] { return late.tick(); });
    late_gate.announce_primary(2'000'000'000);
    NativeWork delayed{&late, 0, 20'000'000};
    const auto late_report = late_gate.execute(Task::sface, 2'000'000'000, 0, run_native, &delayed);
    const auto recorded = late_report.release_decision_ns - late_report.start_ns;
    const auto simulated_hold = late_report.release_decision_ns - std::uint64_t{1'000'000'000};
    check(recorded == 20'000'000 && simulated_hold == 40'000'000 && !late_report.hardcap,
          "expected late-start metering counterexample changed");
    Snapshot state;late_gate.snapshot(state);
    check(!state.active && !state.disabled[2], "counterexample requires a missed overrun");
    std::cout << "{\"review_counterexamples_reproduced\":2,"
              << "\"stale_admission_native_calls\":" << work.calls << ','
              << "\"stale_admission_native_started_ns\":" << work.started << ','
              << "\"start_meter_recorded_ns\":" << recorded << ','
              << "\"simulated_actual_gate_hold_ns\":" << simulated_hold << ','
              << "\"hardcap_recorded\":" << (late_report.hardcap ? "true" : "false") << ','
              << "\"scope\":\"deterministic fake-clock source audit; no DPU execution\"}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
