// Isolation prototype: native callbacks only, no VART/device owner is created.
#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <mutex>
#include <unistd.h>

namespace aura {
enum class Task : unsigned { yolo = 0, yunet = 1, sface = 2 };
enum class Outcome { completed, deadline, busy, primary_waiting, disabled,
                     fenced, not_submitted, wrong_process, invalid };
struct Completion {
  bool submitted = false;
  bool completed = false;
  int status = -1;
};
struct Report {
  Outcome outcome = Outcome::invalid;
  bool hardcap = false, guard = false;
  std::uint64_t start_ns = 0, native_return_ns = 0, release_decision_ns = 0;
  std::uint64_t after_unlock_ns = 0;
  Completion completion{};
};
struct Snapshot {
  bool active = false, fenced = false;
  unsigned primary_waiting = 0;
  std::uint64_t next_primary_ns = 0;
  std::array<bool, 3> disabled{};
  std::array<std::uint64_t, 3> admissions{}, overruns{};
};
class NativeLease {
 public:
  static constexpr std::uint64_t hardcap_ns = 30'000'000;
  static constexpr std::uint64_t guard_ns = 5'000'000;
  using Clock = std::function<std::uint64_t()>;
  // A compiled C++ callback must perform execute + wait and prove completion.
  // Passing a Python/ctypes callback would reintroduce the GIL and is forbidden.
  using Callback = Completion (*)(void*);
  static std::uint64_t monotonic_ns() {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
  }
  explicit NativeLease(Clock clock = monotonic_ns) : clock_(std::move(clock)), pid_(getpid()) {}
  NativeLease(const NativeLease&) = delete;
  NativeLease& operator=(const NativeLease&) = delete;

  bool announce_primary(std::uint64_t next_deadline_ns) {
    if (getpid() != pid_) return false;  // Check before touching a fork-inherited mutex.
    std::lock_guard<std::mutex> lock(mutex_);
    state_.next_primary_ns = next_deadline_ns;
    condition_.notify_all();
    return true;
  }
  bool snapshot(Snapshot& value) {
    if (getpid() != pid_) return false;
    std::lock_guard<std::mutex> lock(mutex_);
    value = state_;
    return true;
  }

  Report execute(Task task, std::uint64_t source_expires_ns,
                 std::uint64_t primary_finish_ns, Callback callback, void* context) {
    Report result;
    if (getpid() != pid_) { result.outcome = Outcome::wrong_process; return result; }
    const auto index = static_cast<unsigned>(task);
    if (index >= 3 || !callback || !source_expires_ns) return result;
    std::uint64_t admitted_guard = 0;
    {
      std::unique_lock<std::mutex> lock(mutex_);
      if (state_.fenced) { result.outcome = Outcome::fenced; return result; }
      if (state_.disabled[index]) { result.outcome = Outcome::disabled; return result; }
      if (task == Task::yolo) {
        if (!primary_finish_ns) return result;
        state_.next_primary_ns = primary_finish_ns;
        ++state_.primary_waiting;
        while (state_.active && !state_.fenced) {
          const auto now = clock_();
          const auto deadline = std::min(source_expires_ns, primary_finish_ns);
          if (now >= deadline) break;
          condition_.wait_for(lock, std::chrono::nanoseconds(deadline - now));
        }
        --state_.primary_waiting;
        if (state_.fenced) { result.outcome = Outcome::fenced; return result; }
        if (state_.active) { result.outcome = Outcome::deadline; return result; }
      } else {
        if (state_.primary_waiting) { result.outcome = Outcome::primary_waiting; return result; }
        if (state_.active) { result.outcome = Outcome::busy; return result; }
      }
      const auto now = clock_();
      if (now >= source_expires_ns || (task == Task::yolo && now >= primary_finish_ns)) {
        result.outcome = Outcome::deadline;
        return result;
      }
      if (task != Task::yolo) {
        if (state_.next_primary_ns < now ||
            state_.next_primary_ns - now < hardcap_ns + guard_ns) {
          result.outcome = Outcome::deadline;
          return result;
        }
        admitted_guard = state_.next_primary_ns - guard_ns;
      }
      // Conservative start precedes publishing active, so a deschedule at
      // acquisition cannot disappear from the ownership duration.
      result.start_ns = now;
      state_.active = true;
      ++state_.admissions[index];
    }
    bool may_submit = true;
    Outcome withdrawal = Outcome::deadline;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      const auto now = clock_();
      if (state_.fenced) { may_submit = false; withdrawal = Outcome::fenced; }
      else if (now >= source_expires_ns || (task == Task::yolo && now >= primary_finish_ns)) {
        may_submit = false;
      } else if (task != Task::yolo) {
        if (state_.primary_waiting) { may_submit = false; withdrawal = Outcome::primary_waiting; }
        else if (state_.next_primary_ns < now ||
                 state_.next_primary_ns - now < hardcap_ns + guard_ns) may_submit = false;
      }
    }
    bool threw = false;
    try { if (may_submit) result.completion = callback(context); }
    catch (...) { threw = true; }
    result.native_return_ns = clock_();
    {
      std::lock_guard<std::mutex> lock(mutex_);
      // All protection decisions precede unlock. There is no Python, logging,
      // output conversion, buffer allocation or external diagnostics lock here.
      const auto& native = result.completion;
      const bool unknown = threw || (native.completed && !native.submitted) ||
                           (native.submitted && (!native.completed || native.status != 0));
      if (unknown) state_.fenced = true;
      // Use the retained release-decision sample for protection, not an
      // earlier completion sample. The post-unlock upper endpoint stays visible.
      result.release_decision_ns = clock_();
      const auto now = result.release_decision_ns;
      if (task != Task::yolo) {
        result.hardcap = now - result.start_ns > hardcap_ns;
        auto current_guard = admitted_guard;
        if (state_.next_primary_ns >= guard_ns)
          current_guard = std::min(current_guard, state_.next_primary_ns - guard_ns);
        result.guard = now > current_guard;
        if (result.hardcap || result.guard || unknown) {
          state_.disabled[index] = true;
          if (result.hardcap || result.guard) ++state_.overruns[index];
        }
      }
      result.outcome = unknown ? Outcome::fenced : !may_submit ? withdrawal :
                       native.submitted ? Outcome::completed : Outcome::not_submitted;
      state_.active = false;
      condition_.notify_all();
    }
    result.after_unlock_ns = clock_();
    return result;
  }

 private:
  Clock clock_;
  const pid_t pid_;
  std::mutex mutex_;
  std::condition_variable condition_;
  Snapshot state_{};
};
}  // namespace aura
