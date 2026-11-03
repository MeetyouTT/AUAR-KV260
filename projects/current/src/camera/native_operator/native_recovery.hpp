// Bounded recovery policy only. No model, gate, allocation, I/O or own mutex.
// The shared DPU owner must serialize all calls, including snapshot/import.
#pragma once
#include <array>
#include <cstdint>
#include <limits>

namespace aura {
class NativeRecovery {
 public:
  static constexpr std::uint64_t cooldown_ns = 10'000'000'000ULL;
  static constexpr std::uint64_t window_ns = 600'000'000'000ULL;
  static constexpr std::uint64_t primary_max_age_ns = 500'000'000ULL;
  static constexpr unsigned maximum_attempts = 2;
  static constexpr unsigned required_successes = 3;
  static constexpr std::uint64_t maximum_clock_ns =
      static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max());

  enum class Phase : std::uint8_t { running, cooldown, probation, latched };
  enum class Reason : std::uint8_t {
    none, unsafe_or_unknown_completion, recovery_budget_exhausted,
    completed_hardcap_only, primary_overrun_after_fault,
    primary_overrun_during_probation
  };
  enum class Error : std::uint8_t {
    none, invalid_clock, invalid_primary, counter_overflow,
    invalid_seed, already_used
  };
  struct Primary {
    std::uint64_t calls = 0, overruns = 0, last_finished_ns = 0;
    bool has_last = false;
  };
  struct Fault {
    bool completed = false, body_failed = false, hardcap = false, guard = false;
  };
  struct Probe {
    bool submitted = false, completed = false, result_usable = false;
    int native_status = -1;
    std::uint64_t source_expires_ns = 0;
  };
  struct State {
    Phase phase = Phase::running;
    Reason reason = Reason::none;
    std::array<std::uint64_t, maximum_attempts> attempt_times{};
    unsigned attempt_count = 0, probe_successes = 0;
    std::uint64_t cooldown_until_ns = 0;
    std::uint64_t fault_primary_calls = 0, fault_primary_overruns = 0;
    std::uint64_t faults = 0, attempts = 0, recoveries = 0;
    std::uint64_t observed_ns = 0;
  };
  struct Seed {
    std::uint32_t version = 1;
    std::uint64_t captured_ns = 0;
    State state{};
  };

  NativeRecovery() noexcept = default;
  NativeRecovery(const NativeRecovery&) = delete;
  NativeRecovery& operator=(const NativeRecovery&) = delete;
  NativeRecovery(NativeRecovery&&) = delete;
  NativeRecovery& operator=(NativeRecovery&&) = delete;

  const State& snapshot() const noexcept { return state_; }
  Error error() const noexcept { return error_; }
  bool normal_allowed() const noexcept { return state_.phase == Phase::running; }
  bool probation() const noexcept { return state_.phase == Phase::probation; }

  // Exactly one ended operation supplies this record. It is not an unlock API:
  // callers must never invent a new safe fault to reopen a latched policy.
  bool fault(std::uint64_t now, Fault fault, Primary primary) noexcept {
    used_ = true;error_ = Error::none;
    if (!valid_now(now) || !valid_primary(primary, now)) return false;
    if (state_.faults == std::numeric_limits<std::uint64_t>::max())
      return fail(Error::counter_overflow);
    const bool safe = fault.completed && !fault.body_failed && !fault.guard && fault.hardcap;
    if (safe && now > maximum_clock_ns - cooldown_ns) return fail(Error::invalid_clock);
    ++state_.faults;
    state_.observed_ns = now;
    state_.probe_successes = 0;
    state_.fault_primary_calls = primary.calls;
    state_.fault_primary_overruns = primary.overruns;
    if (!safe) {
      state_.phase = Phase::latched;
      state_.reason = Reason::unsafe_or_unknown_completion;
    } else if (state_.attempt_count == maximum_attempts &&
               now - state_.attempt_times[0] < window_ns) {
      state_.phase = Phase::latched;
      state_.reason = Reason::recovery_budget_exhausted;
    } else {
      state_.phase = Phase::cooldown;
      state_.reason = Reason::completed_hardcap_only;
      state_.cooldown_until_ns = now + cooldown_ns;
    }
    return true;
  }

  // Readiness never consumes a round, clears disabled, or permits business use.
  bool due(std::uint64_t now, Primary primary) noexcept {
    used_ = true;error_ = Error::none;
    if (!valid_now(now) || !valid_primary(primary, now)) return false;
    state_.observed_ns = now;
    if (state_.phase != Phase::cooldown || now < state_.cooldown_until_ns) return false;
    if (primary.overruns != state_.fault_primary_overruns) {
      state_.phase = Phase::latched;
      state_.reason = Reason::primary_overrun_after_fault;
      return false;
    }
    if (primary.calls <= state_.fault_primary_calls || !primary.has_last ||
        now - primary.last_finished_ns > primary_max_age_ns) return false;
    while (state_.attempt_count && now - state_.attempt_times[0] >= window_ns) {
      for (unsigned i = 1; i < state_.attempt_count; ++i)
        state_.attempt_times[i - 1] = state_.attempt_times[i];
      state_.attempt_times[--state_.attempt_count] = 0;
    }
    if (state_.attempt_count >= maximum_attempts) {
      state_.phase = Phase::latched;
      state_.reason = Reason::recovery_budget_exhausted;
      return false;
    }
    return true;
  }

  // Invoke only after ordinary gate/deadline/TTL admission under the same lock.
  // YuNet's production hook is lease admission; SFace's is native_starting.
  bool admitted(std::uint64_t now, Primary primary) noexcept {
    if (!due(now, primary)) return false;
    if (state_.attempts == std::numeric_limits<std::uint64_t>::max())
      return fail(Error::counter_overflow);
    state_.attempt_times[state_.attempt_count++] = now;
    ++state_.attempts;
    state_.phase = Phase::probation;
    state_.reason = Reason::none;
    state_.probe_successes = 0;
    return true;
  }

  // Returns true only on the third qualified probe (recovery completed).
  // Expired/unsubmitted/unconfirmed requests do not advance or reset probes.
  // The caller records any real fault through fault(), not through this API.
  bool success(std::uint64_t now, Probe probe) noexcept {
    used_ = true;error_ = Error::none;
    if (!valid_now(now)) return false;
    state_.observed_ns = now;
    if (state_.phase != Phase::probation || !probe.submitted || !probe.completed ||
        !probe.result_usable || probe.native_status != 0 || !probe.source_expires_ns ||
        probe.source_expires_ns > maximum_clock_ns || now >= probe.source_expires_ns)
      return false;
    if (state_.probe_successes + 1 == required_successes &&
        state_.recoveries == std::numeric_limits<std::uint64_t>::max())
      return fail(Error::counter_overflow);
    if (++state_.probe_successes < required_successes) return false;
    state_.phase = Phase::running;
    state_.reason = Reason::none;
    ++state_.recoveries;
    return true;
  }

  bool primary_failed() noexcept {
    used_ = true;error_ = Error::none;
    if (state_.phase != Phase::probation) return false;
    state_.phase = Phase::latched;
    state_.reason = Reason::primary_overrun_during_probation;
    return true;
  }

  // Explicit operator action after the gate verified a new healthy interval.
  // Reopen only a safely completed budget latch after ALL prior rounds aged
  // out. Preserve every lifetime counter and the old attempt timestamps.
  bool operator_resume(std::uint64_t now, Primary primary) noexcept {
    used_ = true;error_ = Error::none;
    if (!valid_now(now) || !valid_primary(primary,now)) return false;
    if (state_.phase != Phase::latched || state_.reason != Reason::recovery_budget_exhausted ||
        state_.attempt_count != maximum_attempts ||
        now-state_.attempt_times[maximum_attempts-1] < window_ns ||
        !primary.has_last || now-primary.last_finished_ns > primary_max_age_ns ||
        primary.calls <= state_.fault_primary_calls || now > maximum_clock_ns-cooldown_ns)
      return false;
    state_.phase = Phase::cooldown;
    state_.reason = Reason::completed_hardcap_only;
    state_.probe_successes = 0;
    state_.cooldown_until_ns = now+cooldown_ns;
    state_.fault_primary_calls = primary.calls;
    state_.fault_primary_overruns = primary.overruns;
    state_.observed_ns = now;
    return true;
  }

  bool export_seed(std::uint64_t captured, Seed& output) const noexcept {
    if (!captured || captured > maximum_clock_ns || captured < state_.observed_ns) return false;
    output = Seed{1, captured, state_};
    return true;
  }

  // Startup only, before ANY operational call. The upper layer verifies boot,
  // owner identity, sole ownership, provenance and an idle old/new executor.
  // Invalid import leaves policy counters/phase unchanged and may be retried.
  bool import_seed(const Seed& seed, std::uint64_t now, Primary current) noexcept {
    error_ = Error::none;
    if (used_) return fail(Error::already_used);
    if (!seed_valid(seed, now, current)) return fail(Error::invalid_seed);
    state_ = seed.state;
    state_.observed_ns = now;
    used_ = true;
    return true;
  }

 private:
  State state_{};
  Error error_ = Error::none;
  bool used_ = false;
  bool fail(Error error) noexcept { error_ = error;return false; }
  bool valid_now(std::uint64_t now) noexcept {
    return now && now <= maximum_clock_ns && now >= state_.observed_ns ? true : fail(Error::invalid_clock);
  }
  bool valid_primary(Primary primary, std::uint64_t now) noexcept {
    if (primary.overruns > primary.calls || primary.calls < state_.fault_primary_calls ||
        primary.overruns < state_.fault_primary_overruns ||
        (primary.has_last ? !primary.last_finished_ns || primary.last_finished_ns > now :
                            primary.last_finished_ns != 0)) return fail(Error::invalid_primary);
    return true;
  }
  static bool seed_valid(const Seed& seed, std::uint64_t now, Primary primary) noexcept {
    const auto& s = seed.state;
    if (seed.version != 1 || !seed.captured_ns || seed.captured_ns > now ||
        now > maximum_clock_ns || s.observed_ns > seed.captured_ns ||
        static_cast<unsigned>(s.phase) > static_cast<unsigned>(Phase::latched) ||
        static_cast<unsigned>(s.reason) > static_cast<unsigned>(Reason::primary_overrun_during_probation) ||
        s.attempt_count > maximum_attempts || s.probe_successes > required_successes ||
        s.cooldown_until_ns > maximum_clock_ns ||
        (s.cooldown_until_ns > seed.captured_ns && s.cooldown_until_ns - seed.captured_ns > cooldown_ns) ||
        s.fault_primary_overruns > s.fault_primary_calls ||
        primary.overruns > primary.calls || s.fault_primary_calls > primary.calls ||
        s.fault_primary_overruns > primary.overruns ||
        (primary.has_last ? !primary.last_finished_ns || primary.last_finished_ns > now :
                            primary.last_finished_ns != 0) ||
        s.recoveries > s.attempts || s.attempts > s.faults || s.attempt_count > s.attempts)
      return false;
    for (unsigned i = 0; i < maximum_attempts; ++i) {
      if (i < s.attempt_count) {
        if (!s.attempt_times[i] || s.attempt_times[i] > s.observed_ns ||
            (i && s.attempt_times[i] <= s.attempt_times[i - 1])) return false;
      } else if (s.attempt_times[i] != 0) return false;
    }
    if (!s.faults)
      return s.phase == Phase::running && s.reason == Reason::none && !s.attempts &&
             !s.recoveries && !s.probe_successes && !s.cooldown_until_ns &&
             !s.fault_primary_calls && !s.fault_primary_overruns;
    if (!s.observed_ns || (s.cooldown_until_ns &&
        (s.cooldown_until_ns < cooldown_ns || s.cooldown_until_ns - cooldown_ns > s.observed_ns)))
      return false;
    switch (s.phase) {
      case Phase::running:
        return s.reason == Reason::none && s.recoveries && s.probe_successes == required_successes &&
               s.cooldown_until_ns && s.attempt_count;
      case Phase::cooldown:
        return s.reason == Reason::completed_hardcap_only && !s.probe_successes &&
               s.cooldown_until_ns >= cooldown_ns &&
               (s.attempt_count < maximum_attempts ||
                seed.captured_ns - s.attempt_times[0] >= window_ns);
      case Phase::probation:
        return s.reason == Reason::none && s.probe_successes < required_successes &&
               s.attempts && s.attempt_count && s.cooldown_until_ns &&
               s.attempt_times[s.attempt_count - 1] >= s.cooldown_until_ns;
      case Phase::latched:
        if (s.reason == Reason::none || s.reason == Reason::completed_hardcap_only) return false;
        if (s.reason == Reason::recovery_budget_exhausted)
          return s.attempt_count == maximum_attempts && !s.probe_successes;
        if (s.reason == Reason::primary_overrun_during_probation)
          return s.attempts && s.attempt_count && s.probe_successes < required_successes &&
                 primary.overruns > s.fault_primary_overruns;
        if (s.reason == Reason::primary_overrun_after_fault)
          return !s.probe_successes && primary.overruns > s.fault_primary_overruns;
        return !s.probe_successes;
    }
    return false;
  }
};
}  // namespace aura
