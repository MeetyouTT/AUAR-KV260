// JSON/stdin harness only; its streams may allocate, the policy does not.
#include "native_recovery.hpp"
#include <iostream>
#include <string>

int main() {
  using P = aura::NativeRecovery;
  P policy;
  std::string operation;
  while (std::cin >> operation) {
    std::uint64_t now;bool accepted = false;
    if (operation == "F") {
      P::Fault fault;P::Primary primary;
      std::cin >> now >> fault.completed >> fault.body_failed >> fault.hardcap >> fault.guard
          >> primary.calls >> primary.overruns >> primary.last_finished_ns >> primary.has_last;
      accepted = policy.fault(now, fault, primary);
    } else if (operation == "D" || operation == "A") {
      P::Primary primary;
      std::cin >> now >> primary.calls >> primary.overruns >> primary.last_finished_ns >> primary.has_last;
      accepted = operation == "D" ? policy.due(now, primary) : policy.admitted(now, primary);
    } else if (operation == "S") {
      P::Probe probe;
      std::cin >> now >> probe.submitted >> probe.completed >> probe.result_usable >> probe.native_status
          >> probe.source_expires_ns;
      accepted = policy.success(now, probe);
    } else if (operation == "P") {
      accepted = policy.primary_failed();
    } else return 2;
    if (!std::cin) return 3;
    const auto& s = policy.snapshot();
    std::cout << "{\"accepted\":" << (accepted ? "true" : "false")
      << ",\"phase\":" << static_cast<unsigned>(s.phase)
      << ",\"reason\":" << static_cast<unsigned>(s.reason)
      << ",\"faults\":" << s.faults << ",\"attempts\":" << s.attempts
      << ",\"recoveries\":" << s.recoveries << ",\"probe_successes\":" << s.probe_successes
      << ",\"cooldown_until_ns\":" << s.cooldown_until_ns
      << ",\"fault_primary_calls\":" << s.fault_primary_calls
      << ",\"fault_primary_overruns\":" << s.fault_primary_overruns
      << ",\"attempt_times\":[";
    for (unsigned i = 0; i < s.attempt_count; ++i)
      std::cout << (i ? "," : "") << s.attempt_times[i];
    std::cout << "]}\n";
  }
}
