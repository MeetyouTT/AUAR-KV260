#include "native_lease_v2.hpp"
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <sys/wait.h>

using aura::Completion;
using aura::NativeLease;
using aura::Outcome;
using aura::Snapshot;
using aura::Task;
static void check(bool condition, const char* message) {
  if (!condition) throw std::runtime_error(message);
}
static Completion success(void*) { return {true, true, 0}; }
static Completion unknown(void*) { return {true, false, -1}; }
static Completion fail(void*) { throw std::runtime_error("native completion unknown"); }
struct Block {
  std::atomic<bool> entered{false}, release{false};
};
static Completion block(void* context) {
  auto& value = *static_cast<Block*>(context);
  value.entered = true;
  while (!value.release) std::this_thread::sleep_for(std::chrono::microseconds(100));
  return {true, true, 0};
}
static void wait_for(const std::function<bool()>& condition) {
  const auto until = NativeLease::monotonic_ns() + 1'000'000'000;
  while (!condition()) {
    check(NativeLease::monotonic_ns() < until, "test synchronization timeout");
    std::this_thread::sleep_for(std::chrono::microseconds(100));
  }
}
static void boundaries() {
  std::atomic<std::uint64_t> now{1'000'000'000};
  NativeLease gate([&] { return now.load(); });
  gate.announce_primary(now + 25'909'669);
  auto rejected = gate.execute(Task::yunet, now + 1'000'000'000, 0, success, nullptr);
  check(rejected.outcome == Outcome::deadline, "narrow historic slot must be declined");
  gate.announce_primary(now + 1'000'000'000);
  auto advance = [](void* p) -> Completion {
    *static_cast<std::atomic<std::uint64_t>*>(p) += 31'000'000;
    return {true, true, 0};
  };
  auto fault = gate.execute(Task::yunet, now + 1'000'000'000, 0, advance, &now);
  check(fault.hardcap && !fault.guard, "unchanged 30ms hardcap");
  Snapshot state;
  gate.snapshot(state);
  check(state.overruns[1] == 1 && state.disabled[1] && !state.active, "fault retained after release");
}
static void changed_primary_guard() {
  std::uint64_t now = 1'000'000'000;
  NativeLease gate([&] { return now; });
  gate.announce_primary(now + 100'000'000);
  struct Context { NativeLease* gate; std::uint64_t* now; } context{&gate, &now};
  auto callback = [](void* pointer) -> Completion {
    auto& c = *static_cast<Context*>(pointer);
    c.gate->announce_primary(*c.now + 15'000'000);
    *c.now += 20'000'000;
    return {true, true, 0};
  };
  auto report = gate.execute(Task::sface, now + 1'000'000'000, 0, callback, &context);
  check(report.guard && !report.hardcap, "new primary guard cannot be hidden by old snapshot");
}
static void completion_fence() {
  for (auto callback : {unknown, fail}) {
    NativeLease gate;
    auto now = NativeLease::monotonic_ns();
    gate.announce_primary(now + 1'000'000'000);
    auto bad = gate.execute(Task::sface, now + 1'000'000'000, 0, callback, nullptr);
    check(bad.outcome == Outcome::fenced, "unconfirmed native completion must fence");
    auto primary = gate.execute(Task::yolo, now + 1'000'000'000, now + 100'000'000, success, nullptr);
    check(primary.outcome == Outcome::fenced, "fenced owner cannot run another primary");
  }
}
static void expired_source() {
  NativeLease gate;
  auto now = NativeLease::monotonic_ns();
  gate.announce_primary(now + 100'000'000);
  auto result = gate.execute(Task::sface, now - 1, 0, success, nullptr);
  Snapshot state;
  gate.snapshot(state);
  check(result.outcome == Outcome::deadline && state.admissions[2] == 0, "stale source must not start native work");
}
static void primary_priority() {
  NativeLease gate;
  const auto now = NativeLease::monotonic_ns();
  gate.announce_primary(now + 1'000'000'000);
  Block busy;
  std::thread optional([&] { gate.execute(Task::yunet, now + 1'000'000'000, 0, block, &busy); });
  wait_for([&] { return busy.entered.load(); });
  std::atomic<bool> primary_done{false};
  std::thread primary([&] {
    auto result = gate.execute(Task::yolo, now + 1'000'000'000, now + 1'000'000'000, success, nullptr);
    primary_done = result.outcome == Outcome::completed;
  });
  wait_for([&] { Snapshot s; gate.snapshot(s); return s.primary_waiting == 1; });
  auto denied = gate.execute(Task::sface, now + 1'000'000'000, 0, success, nullptr);
  check(denied.outcome == Outcome::primary_waiting, "pending primary has priority");
  busy.release = true;
  optional.join();primary.join();
  check(primary_done, "primary eventually owns the released gate");
}
static void unavailable_caller_does_not_retain_lease() {
  NativeLease gate;
  const auto now = NativeLease::monotonic_ns();
  gate.announce_primary(now + 1'000'000'000);
  std::atomic<bool> native_done{false}, caller_may_return{false}, caller_returned{false};
  std::thread optional([&] {
    auto result = gate.execute(Task::yunet, now + 1'000'000'000, 0, success, nullptr);
    check(result.outcome == Outcome::completed, "native result complete");
    native_done = true;
    while (!caller_may_return) std::this_thread::sleep_for(std::chrono::microseconds(100));
    caller_returned = true;
  });
  wait_for([&] { return native_done.load(); });
  Snapshot state;gate.snapshot(state);
  check(!state.active && !caller_returned, "native release precedes unavailable caller returning");
  auto primary = gate.execute(Task::yolo, now + 1'000'000'000, now + 1'000'000'000, success, nullptr);
  check(primary.outcome == Outcome::completed && !caller_returned, "YOLO proceeds while previous caller is delayed");
  caller_may_return = true;optional.join();
}
static void fork_is_rejected_before_lock() {
  NativeLease gate;
  const auto pid = fork();
  check(pid >= 0, "fork works");
  if (pid == 0) {
    const auto result = gate.execute(Task::yolo, 1, 1, success, nullptr);
    _exit(result.outcome == Outcome::wrong_process ? 0 : 1);
  }
  int status = 0;waitpid(pid, &status, 0);
  check(WIFEXITED(status) && WEXITSTATUS(status) == 0, "child cannot inherit device execution gate");
}
static void decision_and_post_unlock_are_not_confused() {
  unsigned calls = 0;
  NativeLease gate([&] {
    ++calls;
    return std::uint64_t{1'000'000'000} + (calls >= 5 ? 31'000'000 : 0);
  });
  gate.announce_primary(2'000'000'000);
  const auto result = gate.execute(Task::yunet, 2'000'000'000, 0, success, nullptr);
  check(result.hardcap == (result.release_decision_ns - result.start_ns > NativeLease::hardcap_ns),
        "cap decision must use its published release endpoint");
  check(result.after_unlock_ns - result.release_decision_ns == 31'000'000,
        "caller delay after actual unlock is separately observable");
  Snapshot state;gate.snapshot(state);
  check(!state.active && !result.hardcap, "post-unlock caller stall cannot retain the device gate");
}
int main() {
  try {
    boundaries();changed_primary_guard();completion_fence();expired_source();
    primary_priority();unavailable_caller_does_not_retain_lease();fork_is_rejected_before_lock();
    decision_and_post_unlock_are_not_confused();
    std::cout << "{\"passed\":true,\"tests\":8,\"scope\":\"native gate isolation; fake callbacks, no DPU jobs\"}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
