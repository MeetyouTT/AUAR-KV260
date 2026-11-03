#include "native_recovery.hpp"
#include <array>
#include <iostream>
#include <stdexcept>
#include <type_traits>

using Policy = aura::NativeRecovery;
using Phase = Policy::Phase;
using Reason = Policy::Reason;
constexpr std::uint64_t second = 1'000'000'000ULL;
static void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}
static Policy::Primary primary(std::uint64_t now, std::uint64_t calls = 11,
                               std::uint64_t overruns = 0) {
  return {calls, overruns, now, true};
}
static void fault(Policy& policy, std::uint64_t now, std::uint64_t calls = 10) {
  require(policy.fault(now, {true, false, true, false}, primary(now, calls)), "safe fault rejected");
}
static Policy::Probe proof(std::uint64_t expires) { return {true, true, true, 0, expires}; }
static void recover(Policy& policy, std::uint64_t now) {
  require(!policy.success(now + 1, proof(now + second)), "first probe recovered early");
  require(!policy.success(now + 2, proof(now + second)), "second probe recovered early");
  require(policy.success(now + 3, proof(now + second)), "third probe did not recover");
}
static Policy::Seed twice_recovered_seed() {
  Policy p;fault(p, 100 * second);
  require(p.admitted(110 * second, primary(110 * second)), "first attempt rejected");
  recover(p, 110 * second);
  fault(p, 120 * second, 20);
  require(p.admitted(130 * second, primary(130 * second, 21)), "second attempt rejected");
  recover(p, 130 * second);
  Policy::Seed seed;
  require(p.export_seed(131 * second, seed), "export failed");
  return seed;
}

int main() {
  try {
    static_assert(std::is_trivially_copyable<Policy::State>::value, "state must be bounded plain data");
    static_assert(std::is_nothrow_default_constructible<Policy>::value, "construction must not allocate");
    unsigned groups = 0;
    {
      Policy p;require(p.normal_allowed(), "fresh policy is not running");
      fault(p, 100 * second);
      require(!p.normal_allowed() && p.snapshot().phase == Phase::cooldown, "fault not disabled");
      require(!p.due(110 * second - 1, primary(110 * second - 1)), "cooldown rounded early");
      auto edge = primary(110 * second);edge.last_finished_ns -= Policy::primary_max_age_ns;
      require(p.due(110 * second, edge), "0.5s primary boundary rejected");
      require(!p.normal_allowed() && p.snapshot().attempts == 0, "due enabled/consumed a round");
      require(p.due(110 * second, edge), "repeated due changed readiness");
      require(p.admitted(110 * second, edge), "admission refused");
      require(!p.admitted(110 * second, edge), "probation spent another round");
      require(p.probation() && !p.normal_allowed() && p.snapshot().attempts == 1, "admission state wrong");
      recover(p, 110 * second);
      require(p.normal_allowed() && p.snapshot().recoveries == 1 && p.snapshot().faults == 1,
          "recovery erased fault history");
      ++groups;
    }
    {
      Policy p;fault(p, 100 * second);
      auto same = primary(110 * second, 10);
      require(!p.due(110 * second, same), "primary did not advance");
      auto missing = primary(110 * second);missing.has_last = false;missing.last_finished_ns = 0;
      require(!p.due(110 * second, missing), "missing primary accepted");
      auto stale = primary(110 * second);stale.last_finished_ns -= Policy::primary_max_age_ns + 1;
      require(!p.due(110 * second, stale), "old primary accepted");
      auto future = primary(110 * second);++future.last_finished_ns;
      require(!p.due(110 * second, future) && p.error() == Policy::Error::invalid_primary,
          "future primary accepted");
      require(p.due(110 * second, primary(110 * second)), "fresh advanced primary rejected");
      ++groups;
    }
    {
      Policy p;fault(p, 100 * second);
      require(p.admitted(110 * second, primary(110 * second)), "admission refused");
      auto invalid = proof(120 * second);invalid.submitted = false;
      require(!p.success(111 * second, invalid), "unsubmitted probe counted");
      invalid = proof(120 * second);invalid.completed = false;
      require(!p.success(111 * second, invalid), "unconfirmed probe counted");
      invalid = proof(120 * second);invalid.native_status = 1;
      require(!p.success(111 * second, invalid), "failed status counted");
      invalid = proof(120 * second);invalid.result_usable = false;
      require(!p.success(111 * second, invalid), "unusable probe counted");
      require(!p.success(111 * second, proof(111 * second)), "TTL equality counted");
      require(p.snapshot().probe_successes == 0, "bad probes changed success count");
      require(!p.success(112 * second, proof(120 * second)), "first valid probe recovered");
      require(!p.success(113 * second, proof(120 * second)), "second valid probe recovered");
      require(p.probation() && !p.normal_allowed(), "SFace first two probes business-ready");
      require(!p.success(114 * second, proof(114 * second)), "expired third probe counted");
      require(p.snapshot().probe_successes == 2, "expiry reset qualified probes");
      require(p.success(115 * second, proof(120 * second)), "third qualified probe rejected");
      ++groups;
    }
    {
      const auto seed = twice_recovered_seed();Policy p;
      require(p.import_seed(seed, 132 * second, primary(132 * second, 30)), "running seed refused");
      fault(p, 140 * second, 30);
      require(p.snapshot().phase == Phase::latched && p.snapshot().reason == Reason::recovery_budget_exhausted,
          "third round did not latch");
      require(p.snapshot().faults == 3 && p.snapshot().attempts == 2 && p.snapshot().recoveries == 2,
          "budget latch lost counters");
      require(!p.due(1000 * second, primary(1000 * second, 100)), "latched budget reopened with time");
      require(!p.success(1000 * second, proof(1001 * second)) && !p.normal_allowed(), "success reopened latch");
      ++groups;
    }
    {
      const auto seed = twice_recovered_seed();Policy before,exact;
      require(before.import_seed(seed, 132 * second, primary(132 * second, 30)), "seed refused");
      require(exact.import_seed(seed, 132 * second, primary(132 * second, 30)), "seed refused");
      fault(before, 710 * second - 1, 30);
      require(before.snapshot().phase == Phase::latched, "600s budget boundary rounded early");
      fault(exact, 710 * second, 30);
      require(exact.snapshot().phase == Phase::cooldown, "600s equality did not expire old budget");
      require(exact.due(720 * second, primary(720 * second, 31)), "expired oldest round blocked");
      require(exact.snapshot().attempt_count == 1 && exact.snapshot().attempt_times[0] == 130 * second,
          "window pruning dropped the newer round");
      require(exact.admitted(720 * second, primary(720 * second, 31)), "third lifetime round rejected");
      require(exact.snapshot().attempts == 3 && exact.snapshot().attempt_count == 2,
          "window expiry erased lifetime attempts");
      ++groups;
    }
    {
      Policy p;fault(p, 100 * second);
      require(!p.primary_failed(), "cooldown primary_failed differs from Python");
      require(!p.due(105 * second, primary(105 * second, 11, 1)) &&
          p.snapshot().phase == Phase::cooldown, "cooldown overrun check ran early");
      require(!p.due(110 * second, primary(110 * second, 12, 1)) &&
          p.snapshot().reason == Reason::primary_overrun_after_fault, "primary overrun did not latch due");
      Policy q;fault(q, 100 * second);
      require(q.admitted(110 * second, primary(110 * second)), "admission refused");
      require(!q.success(111 * second, proof(120 * second)), "early recovery");
      require(q.primary_failed() && q.snapshot().phase == Phase::latched &&
          q.snapshot().reason == Reason::primary_overrun_during_probation && q.snapshot().probe_successes == 1,
          "probation primary failure did not latch/preserve probes");
      require(!q.success(112 * second, proof(120 * second)), "latched success counted");
      ++groups;
    }
    {
      const std::array<Policy::Fault,4> unsafe{{{false,false,true,false}, {true,true,true,false},
          {true,false,true,true}, {true,false,false,false}}};
      for (auto f : unsafe) {
        Policy p;require(p.fault(100 * second, f, primary(100 * second)), "unsafe fault rejected");
        require(p.snapshot().phase == Phase::latched && p.snapshot().reason == Reason::unsafe_or_unknown_completion,
            "guard/unknown/body/no-hardcap did not latch");
        require(!p.due(1000 * second, primary(1000 * second, 100)), "unsafe latch reopened");
      }
      ++groups;
    }
    {
      Policy p;fault(p, 100 * second);
      require(p.admitted(110 * second, primary(110 * second)), "first admission failed");
      require(!p.success(111 * second, proof(112 * second)), "early recovery");
      fault(p, 112 * second, 20);
      require(p.snapshot().probe_successes == 0 && p.snapshot().phase == Phase::cooldown, "probe fault not reset");
      require(p.admitted(122 * second, primary(122 * second, 21)), "second admission failed");
      fault(p, 123 * second, 30);
      require(p.snapshot().phase == Phase::latched && p.snapshot().attempts == 2, "failed probes bypass budget");
      ++groups;
    }
    {
      Policy yunet,sface;fault(yunet, 100 * second);
      require(sface.normal_allowed() && !sface.snapshot().faults, "policies share fault state");
      require(yunet.admitted(110 * second, primary(110 * second)), "YuNet attempt failed");
      require(sface.fault(110 * second, {false,false,false,false}, primary(110 * second)), "SFace fault failed");
      recover(yunet, 110 * second);
      require(yunet.normal_allowed() && sface.snapshot().phase == Phase::latched &&
          sface.snapshot().attempts == 0, "one policy changed the other");
      ++groups;
    }
    {
      Policy p;fault(p, 100 * second);Policy::Seed cooldown;
      require(p.export_seed(101 * second, cooldown), "cooldown export failed");
      Policy q;require(q.import_seed(cooldown, 102 * second, primary(102 * second)), "cooldown import failed");
      require(!q.normal_allowed() && q.snapshot().faults == 1 && q.snapshot().cooldown_until_ns == 110 * second,
          "seed cleared disabled/history");
      require(q.admitted(110 * second, primary(110 * second)), "seeded attempt refused");
      require(!q.success(111 * second, proof(120 * second)), "early recovery");
      Policy::Seed probation;require(q.export_seed(111 * second, probation), "probation export failed");
      Policy r;require(r.import_seed(probation, 112 * second, primary(112 * second)), "probation import failed");
      require(r.snapshot().probe_successes == 1 && r.snapshot().attempts == 1, "seed dropped probe/attempt");
      require(!r.success(112 * second, proof(120 * second)), "seeded second probe recovered");
      require(r.success(113 * second, proof(120 * second)), "seeded third probe failed");
      require(!r.import_seed(cooldown, 114 * second, primary(114 * second)) &&
          r.error() == Policy::Error::already_used && r.snapshot().recoveries == 1, "reseed reset history");
      Policy used;require(!used.due(100 * second, primary(100 * second)), "fresh policy due");
      require(!used.import_seed(cooldown, 102 * second, primary(102 * second)), "used policy accepted seed");
      ++groups;
    }
    {
      const auto good = twice_recovered_seed();unsigned rejected = 0;
      for (unsigned i = 0; i < 14; ++i) {
        auto bad = good;
        switch (i) {
          case 0: bad.version = 2;break;
          case 1: bad.captured_ns = 200 * second;break;
          case 2: bad.state.observed_ns = 200 * second;break;
          case 3: bad.state.phase = static_cast<Phase>(99);break;
          case 4: bad.state.reason = static_cast<Reason>(99);break;
          case 5: bad.state.attempt_count = 3;break;
          case 6: bad.state.recoveries = bad.state.attempts + 1;break;
          case 7: bad.state.attempts = bad.state.faults + 1;break;
          case 8: bad.state.probe_successes = 0;break;
          case 9: bad.state.attempt_times[0] = 200 * second;break;
          case 10: bad.state.attempt_times[0] = bad.state.attempt_times[1];break;
          case 11: bad.state.fault_primary_calls = 31;break;
          case 12: bad.state.cooldown_until_ns = 150 * second;break;
          case 13: bad.state.reason = Reason::completed_hardcap_only;break;
        }
        Policy p;require(!p.import_seed(bad, 132 * second, primary(132 * second, 30)), "invalid seed accepted");
        require(p.error() == Policy::Error::invalid_seed && !p.snapshot().faults && p.normal_allowed(),
            "invalid seed changed state");++rejected;
      }
      require(rejected == 14, "seed cases missing");++groups;
    }
    {
      Policy p;fault(p, 100 * second);
      require(!p.due(99 * second, primary(99 * second)) && p.error() == Policy::Error::invalid_clock,
          "clock regression accepted");
      auto bad = primary(110 * second, 9);
      require(!p.due(110 * second, bad) && p.error() == Policy::Error::invalid_primary,
          "primary counter regression accepted");
      require(!p.normal_allowed() && p.snapshot().faults == 1, "invalid inputs reset protection");
      ++groups;
    }
    {
      Policy::Seed seed;seed.captured_ns = 100 * second;
      seed.state.phase = Phase::latched;seed.state.reason = Reason::unsafe_or_unknown_completion;
      seed.state.observed_ns = 100 * second;
      seed.state.faults = std::numeric_limits<std::uint64_t>::max();
      Policy p;require(p.import_seed(seed, 100 * second, primary(100 * second)), "counter boundary seed rejected");
      require(!p.fault(101 * second, {false,false,false,false}, primary(101 * second)) &&
          p.error() == Policy::Error::counter_overflow &&
          p.snapshot().faults == std::numeric_limits<std::uint64_t>::max() && !p.normal_allowed(),
          "fault counter wrapped or reopened");
      ++groups;
    }
    std::cout << "{\"passed\":true,\"groups\":" << groups
              << ",\"illegal_seed_cases\":14,\"scope\":\"standalone bounded recovery state machine; no gate/VART/DPU\"}\n";
    return 0;
  } catch (const std::exception& error) { std::cerr << error.what() << '\n';return 1; }
}
