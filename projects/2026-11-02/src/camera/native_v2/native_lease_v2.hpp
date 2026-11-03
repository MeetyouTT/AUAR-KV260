// Native execution/recovery candidate. No Python callback, model or device I/O.
#pragma once
#include "native_recovery.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <limits>
#include <mutex>
#include <unistd.h>

namespace aura {
enum class Task : unsigned { yolo=0, yunet=1, sface=2 };
enum class Outcome : unsigned { completed, deadline, busy, primary_waiting, disabled,
                                fenced, not_submitted, wrong_process, invalid, seed_required, quiesced };
enum class FenceReason : unsigned { none, native_completion_unconfirmed, invalid_policy,
                                   counter_overflow, inherited_fence };
struct Completion { bool submitted=false, completed=false;int status=-1; };
struct Report {
  Outcome outcome=Outcome::invalid;
  bool hardcap=false, guard=false;
  std::uint64_t start_ns=0, native_return_ns=0, release_decision_ns=0, after_unlock_ns=0;
  Completion completion{};
  bool business_ready=false, result_fresh=false;
  unsigned recovery_phase=0;
  std::uint64_t result_token=0;
};
struct RecoverySnapshot {
  bool enabled=false, history_opaque=false;
  unsigned opaque_attempt_count=0;
  NativeRecovery::State policy{};
};
struct Snapshot {
  bool active=false, fenced=false, seed_loaded=false, quiesced=false;
  unsigned primary_waiting=0, active_task=3;
  unsigned checkpoint_kind=0;
  FenceReason fence_reason=FenceReason::none;
  std::uint64_t next_primary_ns=0;
  std::array<bool,3> disabled{};
  std::array<std::uint64_t,3> admissions{}, overruns{}, completed{}, native_failures{}, not_submitted{};
  std::uint64_t primary_calls=0, primary_period_overruns=0, last_primary_ns=0;
  std::array<std::uint64_t,3> pending_result_tokens{};
  std::array<RecoverySnapshot,2> recovery{};
};
struct RecoverySeed {
  bool enabled=false, history_opaque=false;
  unsigned opaque_attempt_count=0;
  NativeRecovery::Seed policy{};
};
struct GateSeed {
  std::uint64_t captured_ns=0;
  unsigned checkpoint_kind=1;
  bool fenced=false;
  std::array<bool,3> disabled{};
  std::array<std::uint64_t,3> admissions{}, overruns{}, completed{}, native_failures{}, not_submitted{};
  std::uint64_t primary_calls=0, primary_period_overruns=0, last_primary_ns=0;
  std::array<RecoverySeed,2> recovery{};
};
struct Acknowledgement {
  bool accepted=false, business_ready=false, result_fresh=false;
  unsigned recovery_phase=0;
  std::uint64_t result_token=0;
};

class NativeLease {
 public:
  static constexpr std::uint64_t hardcap_ns=30'000'000, guard_ns=5'000'000;
  static constexpr std::uint64_t maximum_wait_ns=100'000'000;
  using Clock=std::function<std::uint64_t()>;
  using Callback=Completion (*)(void*); // Compiled native callbacks ONLY.
  static std::uint64_t monotonic_ns() {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count());
  }
  // Production Context sets require_seed=true. false is isolation-only legacy
  // behavior and never enables recovery without an explicit startup seed.
  explicit NativeLease(Clock clock=monotonic_ns, bool require_seed=false)
      : clock_(std::move(clock)),pid_(getpid()),require_seed_(require_seed) {}
  NativeLease(const NativeLease&)=delete;
  NativeLease& operator=(const NativeLease&)=delete;

  bool restore_seed(const GateSeed& seed) {
    if(getpid()!=pid_)return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if(used_ || state_.seed_loaded || state_.active || state_.primary_waiting)return false;
    const auto now=raw_clock();
    if(!seed.captured_ns || seed.captured_ns>now || now>NativeRecovery::maximum_clock_ns ||
       seed.checkpoint_kind>2 || (seed.checkpoint_kind==2&&!seed.fenced) ||
       seed.primary_period_overruns>seed.primary_calls || seed.last_primary_ns>seed.captured_ns ||
       seed.admissions[0]>seed.primary_calls || seed.disabled[0])return false;
    NativeRecovery::Primary primary{seed.primary_calls,seed.primary_period_overruns,
                                   seed.last_primary_ns,seed.last_primary_ns!=0};
    std::array<NativeRecovery,2> validation;
    for(unsigned i=0;i<3;++i) {
      if(seed.overruns[i]>seed.admissions[i] || seed.completed[i]>seed.admissions[i] ||
         seed.native_failures[i]>seed.admissions[i] ||
         seed.not_submitted[i]>(i==0?seed.primary_calls:seed.admissions[i]))return false;
    }
    for(unsigned i=0;i<2;++i) {
      const auto& input=seed.recovery[i];const auto& p=input.policy.state;
      if(seed.checkpoint_kind==2 && (!seed.disabled[i+1] || !input.history_opaque))return false;
      if(input.policy.captured_ns!=seed.captured_ns || input.policy.version!=1 ||
         input.opaque_attempt_count>NativeRecovery::maximum_attempts)return false;
      if(input.history_opaque) {
        if(!seed.disabled[i+1] || p.phase!=NativeRecovery::Phase::latched ||
           p.reason==NativeRecovery::Reason::none || p.reason==NativeRecovery::Reason::completed_hardcap_only ||
           static_cast<unsigned>(p.reason)>5 || p.attempt_count || p.attempt_times[0] || p.attempt_times[1] ||
           p.probe_successes>=NativeRecovery::required_successes || p.recoveries>p.attempts ||
           p.attempts>p.faults || input.opaque_attempt_count>p.attempts || p.observed_ns>seed.captured_ns ||
           p.fault_primary_overruns>p.fault_primary_calls ||
           p.fault_primary_calls>seed.primary_calls || p.fault_primary_overruns>seed.primary_period_overruns ||
           p.cooldown_until_ns>NativeRecovery::maximum_clock_ns ||
           (p.cooldown_until_ns>seed.captured_ns&&p.cooldown_until_ns-seed.captured_ns>NativeRecovery::cooldown_ns))return false;
      } else {
        if(input.opaque_attempt_count || !validation[i].import_seed(input.policy,now,primary))return false;
        const bool blocked=p.phase==NativeRecovery::Phase::cooldown || p.phase==NativeRecovery::Phase::latched;
        if(!seed.fenced && seed.disabled[i+1]!=blocked)return false;
      }
      if(p.faults<seed.overruns[i+1])return false;
    }
    // No mutation above: a malformed seed can be rejected and corrected.
    for(unsigned i=0;i<2;++i) {
      const auto& input=seed.recovery[i];auto& target=recovery_[i+1];
      if(!input.history_opaque && !target.policy.import_seed(input.policy,now,primary)) {
        used_=true;fence_locked(FenceReason::invalid_policy);return false;
      }
      target.enabled=input.enabled;target.history_opaque=input.history_opaque;
      target.opaque_attempt_count=input.opaque_attempt_count;target.opaque=input.policy.state;
    }
    state_.disabled=seed.disabled;state_.admissions=seed.admissions;state_.overruns=seed.overruns;
    state_.completed=seed.completed;state_.native_failures=seed.native_failures;
    state_.not_submitted=seed.not_submitted;state_.primary_calls=seed.primary_calls;
    state_.primary_period_overruns=seed.primary_period_overruns;state_.last_primary_ns=seed.last_primary_ns;
    state_.seed_loaded=true;state_.next_primary_ns=0;last_clock_ns_=now;state_.checkpoint_kind=seed.checkpoint_kind;
    used_=true;
    if(seed.fenced)fence_locked(FenceReason::inherited_fence);
    return true;
  }

  bool announce_primary(std::uint64_t deadline) {
    if(getpid()!=pid_)return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if(!initialized_locked() || state_.quiesced || !deadline || deadline>NativeRecovery::maximum_clock_ns)return false;
    used_=true;state_.next_primary_ns=deadline;condition_.notify_all();return true;
  }
  bool snapshot(Snapshot& value) {
    if(getpid()!=pid_)return false;
    std::lock_guard<std::mutex> lock(mutex_);
    value=state_;
    for(unsigned i=0;i<2;++i) {
      const auto& r=recovery_[i+1];value.recovery[i]={r.enabled,r.history_opaque,r.opaque_attempt_count,
          r.history_opaque?r.opaque:r.policy.snapshot()};
    }
    for(unsigned i=0;i<3;++i)value.pending_result_tokens[i]=pending_[i].token;
    return true;
  }
  bool task_quiescent(Task task) {
    if(getpid()!=pid_)return false;
    const auto index=static_cast<unsigned>(task);if(index>2)return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if(state_.fenced || state_.active || state_.primary_waiting)return false;
    const auto now=clock_locked();if(!now)return false;
    expire_pending_locked(index,now);
    return !pending_[index].token;
  }
  bool checkpoint(GateSeed& output) {
    if(getpid()!=pid_)return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if(!initialized_locked() || state_.quiesced || state_.active || state_.primary_waiting)return false;
    const auto now=clock_locked();if(!now)return false;
    for(unsigned i=1;i<3;++i) {
      expire_pending_locked(i,now);if(pending_[i].token)return false;
    }
    GateSeed result;result.captured_ns=now;result.fenced=state_.fenced;
    result.checkpoint_kind=state_.checkpoint_kind==2?2:1;
    result.disabled=state_.disabled;result.admissions=state_.admissions;result.overruns=state_.overruns;
    result.completed=state_.completed;result.native_failures=state_.native_failures;
    result.not_submitted=state_.not_submitted;result.primary_calls=state_.primary_calls;
    result.primary_period_overruns=state_.primary_period_overruns;result.last_primary_ns=state_.last_primary_ns;
    for(unsigned i=0;i<2;++i) {
      const auto& from=recovery_[i+1];auto& to=result.recovery[i];
      to.enabled=from.enabled;to.history_opaque=from.history_opaque;to.opaque_attempt_count=from.opaque_attempt_count;
      to.policy.version=1;to.policy.captured_ns=now;
      to.policy.state=from.history_opaque?from.opaque:from.policy.snapshot();
    }
    output=result;used_=true;state_.quiesced=true;condition_.notify_all();return true;
  }

  int wait_optional(Task task,std::uint64_t until) {
    if(getpid()!=pid_)return -1;
    const auto index=static_cast<unsigned>(task);
    if(index<1 || index>2 || !until || until>NativeRecovery::maximum_clock_ns)return -1;
    std::unique_lock<std::mutex> lock(mutex_);
    if(!initialized_locked() || state_.quiesced)return 1;
    used_=true;const auto began=clock_locked();if(!began)return -2;
    const auto deadline=std::min(until,began+maximum_wait_ns);
    while(true) {
      if(state_.quiesced)return 1;
      const auto now=clock_locked();if(!now || state_.fenced)return -2;
      if(now>=deadline)return 1;
      expire_pending_locked(index,now);
      if(!state_.active && !state_.primary_waiting && !pending_[index].token) {
        if(optional_allowed_locked(index,now) && fits_locked(now))return 0;
        if(state_.fenced)return -2;
        const auto& r=recovery_[index];
        if(state_.disabled[index] && (!r.enabled || r.history_opaque ||
            r.policy.snapshot().phase==NativeRecovery::Phase::latched))return 1;
      }
      auto wake=deadline;
      if(pending_[index].token)wake=std::min(wake,pending_[index].source_expires_ns);
      condition_.wait_for(lock,std::chrono::nanoseconds(wake>now?wake-now:1));
    }
  }

  Acknowledgement acknowledge(Task task,std::uint64_t token,bool usable) {
    Acknowledgement output;output.result_token=token;
    if(getpid()!=pid_)return output;
    const auto index=static_cast<unsigned>(task);if(index<1 || index>2 || !token)return output;
    std::lock_guard<std::mutex> lock(mutex_);
    output.recovery_phase=phase_locked(index);
    if(!initialized_locked() || state_.fenced || state_.quiesced)return output;
    const auto now=clock_locked();if(!now)return output;
    auto& p=pending_[index];
    if(p.token!=token)return output;
    const auto expiry=p.source_expires_ns;p={};
    output.accepted=true;output.result_fresh=now<expiry;
    auto& recovery=recovery_[index];
    if(recovery.enabled && !recovery.history_opaque && recovery.policy.probation()) {
      recovery.policy.success(now,{true,true,usable,0,expiry});
      if(recovery.policy.error()!=NativeRecovery::Error::none)fence_locked(FenceReason::invalid_policy);
    }
    output.recovery_phase=phase_locked(index);
    output.business_ready=usable && output.result_fresh && business_allowed_locked(index);
    condition_.notify_all();return output;
  }

  Report execute(Task task,std::uint64_t expires,std::uint64_t primary_finish,
                 Callback callback,void* context) {
    Report out;
    if(getpid()!=pid_) { out.outcome=Outcome::wrong_process;return out; }
    const auto index=static_cast<unsigned>(task);
    if(index>2 || !callback || !expires || expires>NativeRecovery::maximum_clock_ns)return out;
    std::uint64_t admitted_guard=0,pre_submit_ns=0;
    NativeRecovery::Primary primary_before_submit;
    bool sface_recovery_request=false;
    {
      std::unique_lock<std::mutex> lock(mutex_);
      if(!initialized_locked()) { out.outcome=Outcome::seed_required;return out; }
      if(state_.quiesced) { out.outcome=Outcome::quiesced;return out; }
      used_=true;
      if(state_.fenced) { out.outcome=Outcome::fenced;return out; }
      if(index==0) {
        if(!primary_finish || primary_finish>NativeRecovery::maximum_clock_ns)return out;
        state_.next_primary_ns=primary_finish;++state_.primary_waiting;
        while(state_.active && !state_.fenced) {
          const auto now=clock_locked();if(!now)break;
          const auto deadline=std::min(expires,primary_finish);if(now>=deadline)break;
          condition_.wait_for(lock,std::chrono::nanoseconds(deadline-now));
        }
        --state_.primary_waiting;
        if(state_.fenced) { out.outcome=Outcome::fenced;return out; }
        if(state_.active) {
          const auto now=clock_locked();
          if(now)finish_primary_locked(now,primary_finish,false,true);
          out.outcome=state_.fenced?Outcome::fenced:Outcome::deadline;
          return out;
        }
      } else {
        if(state_.primary_waiting) { out.outcome=Outcome::primary_waiting;return out; }
        if(state_.active) { out.outcome=Outcome::busy;return out; }
      }
      const auto now=clock_locked();if(!now) { out.outcome=Outcome::fenced;return out; }
      if(now>=expires || (index==0 && now>=primary_finish)) {
        if(index==0)finish_primary_locked(now,primary_finish,false,true);
        out.outcome=state_.fenced?Outcome::fenced:Outcome::deadline;
        return out;
      }
      if(index) {
        expire_pending_locked(index,now);
        if(pending_[index].token) { out.outcome=Outcome::busy;return out; }
        if(!optional_allowed_locked(index,now)) { out.outcome=state_.fenced?Outcome::fenced:Outcome::disabled;return out; }
        if(!fits_locked(now)) { out.outcome=Outcome::deadline;return out; }
        admitted_guard=state_.next_primary_ns-guard_ns;
        auto& recovery=recovery_[index];
        if(recovery.enabled && !recovery.history_opaque &&
            recovery.policy.snapshot().phase==NativeRecovery::Phase::cooldown) {
          if(index==1) {
            if(!recovery.policy.admitted(now,primary_locked())) {
              if(recovery.policy.error()!=NativeRecovery::Error::none)fence_locked(FenceReason::invalid_policy);
              out.outcome=state_.fenced?Outcome::fenced:Outcome::disabled;return out;
            }
            state_.disabled[index]=false;
          } else sface_recovery_request=true;
        }
      }
      if(!increment_locked(state_.admissions[index])) { out.outcome=Outcome::fenced;return out; }
      out.start_ns=now;state_.active=true;state_.active_task=index;
    }
    bool may_submit=true;Outcome withdrawal=Outcome::deadline;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      pre_submit_ns=clock_locked();primary_before_submit=primary_locked();
      if(!pre_submit_ns || state_.fenced) { may_submit=false;withdrawal=Outcome::fenced; }
      else if(pre_submit_ns>=expires || (index==0 && pre_submit_ns>=primary_finish))may_submit=false;
      else if(index && (state_.primary_waiting || !fits_locked(pre_submit_ns))) {
        may_submit=false;if(state_.primary_waiting)withdrawal=Outcome::primary_waiting;
      } else if(sface_recovery_request && !recovery_[2].policy.due(pre_submit_ns,primary_before_submit)) {
        may_submit=false;withdrawal=Outcome::disabled;
        if(recovery_[2].policy.error()!=NativeRecovery::Error::none)fence_locked(FenceReason::invalid_policy);
      }
    }
    bool threw=false;
    try { if(may_submit)out.completion=callback(context); } catch(...) { threw=true; }
    out.native_return_ns=raw_clock();
    {
      std::lock_guard<std::mutex> lock(mutex_);
      const auto& native=out.completion;
      if(!out.native_return_ns || out.native_return_ns<out.start_ns ||
          out.native_return_ns>NativeRecovery::maximum_clock_ns)fence_locked(FenceReason::invalid_policy);
      const bool unknown=threw || (native.completed&&!native.submitted) ||
                         (native.submitted&&(!native.completed || native.status!=0));
      if(unknown) { fence_locked(FenceReason::native_completion_unconfirmed);increment_locked(state_.native_failures[index]); }
      else if(native.submitted && native.completed && native.status==0)increment_locked(state_.completed[index]);
      else increment_locked(state_.not_submitted[index]);
      // No other task mutates this model's policy while active. Commit SFace
      // recovery only after a real native attempt (or an unknown thrown call),
      // using the retained pre-submit instant. Proven unsubmitted callbacks do
      // not consume a SFace round. YuNet consumed its round at lease admission.
      if(sface_recovery_request && may_submit && (native.submitted || threw)) {
        if(!recovery_[2].policy.admitted(pre_submit_ns,primary_before_submit))fence_locked(FenceReason::invalid_policy);
        else state_.disabled[2]=false;
      }
      out.release_decision_ns=clock_locked();const auto now=out.release_decision_ns;
      if(index) {
        out.hardcap=now && now-out.start_ns>hardcap_ns;
        auto deadline=admitted_guard;
        if(state_.next_primary_ns>=guard_ns)deadline=std::min(deadline,state_.next_primary_ns-guard_ns);
        out.guard=now>deadline;
        auto& recovery=recovery_[index];
        if(out.hardcap || out.guard || unknown) {
          state_.disabled[index]=true;
          if(out.hardcap || out.guard)increment_locked(state_.overruns[index]);
          if(recovery.enabled && !recovery.history_opaque && now &&
             !recovery.policy.fault(now,{native.completed&&native.status==0,threw||unknown,
                                        out.hardcap,out.guard},primary_locked()))fence_locked(FenceReason::invalid_policy);
        }
        out.result_fresh=now && now<expires;
        const bool qualified=may_submit && !state_.fenced && !unknown && native.submitted && native.completed &&
                             native.status==0 && !out.hardcap && !out.guard;
        if(qualified && recovery.enabled && !recovery.history_opaque && recovery.policy.probation()) {
          if(next_result_token_==std::numeric_limits<std::uint64_t>::max())fence_locked(FenceReason::counter_overflow);
          else { out.result_token=next_result_token_++;pending_[index]={out.result_token,expires}; }
        }
        out.business_ready=qualified && out.result_fresh && business_allowed_locked(index);
        out.recovery_phase=phase_locked(index);
      } else {
        finish_primary_locked(now,primary_finish,
            !unknown && native.submitted && native.completed && native.status==0,false);
        out.result_fresh=now && now<expires;
        out.business_ready=!unknown && native.submitted && native.completed && native.status==0 && out.result_fresh;
      }
      out.outcome=state_.fenced?Outcome::fenced:!may_submit?withdrawal:
          native.submitted?Outcome::completed:Outcome::not_submitted;
      state_.active=false;state_.active_task=3;condition_.notify_all();
    }
    out.after_unlock_ns=raw_clock();
    if(!out.after_unlock_ns || out.after_unlock_ns<out.release_decision_ns ||
        out.after_unlock_ns>NativeRecovery::maximum_clock_ns) {
      std::lock_guard<std::mutex> lock(mutex_);fence_locked(FenceReason::invalid_policy);
      out.outcome=Outcome::fenced;out.business_ready=false;
    }
    return out;
  }

 private:
  struct RecoveryRecord {
    bool enabled=false,history_opaque=false;
    unsigned opaque_attempt_count=0;
    NativeRecovery policy;
    NativeRecovery::State opaque{};
  };
  struct Pending { std::uint64_t token=0,source_expires_ns=0; };
  Clock clock_;const pid_t pid_;const bool require_seed_;
  std::mutex mutex_;std::condition_variable condition_;Snapshot state_{};
  std::array<RecoveryRecord,3> recovery_{};
  std::array<Pending,3> pending_{};
  bool used_=false;
  std::uint64_t last_clock_ns_=0,next_result_token_=1;
  std::uint64_t raw_clock() noexcept { try { return clock_(); } catch(...) { return 0; } }
  bool initialized_locked() const { return !require_seed_ || state_.seed_loaded; }
  void fence_locked(FenceReason reason) {
    if(!state_.fenced)state_.fence_reason=reason;
    state_.fenced=true;state_.disabled[1]=state_.disabled[2]=true;condition_.notify_all();
  }
  bool increment_locked(std::uint64_t& counter) {
    if(counter==std::numeric_limits<std::uint64_t>::max()) { fence_locked(FenceReason::counter_overflow);return false; }
    ++counter;return true;
  }
  std::uint64_t clock_locked() {
    const auto now=raw_clock();
    if(!now || now>NativeRecovery::maximum_clock_ns || now<last_clock_ns_) {
      fence_locked(FenceReason::invalid_policy);return 0;
    }
    last_clock_ns_=now;return now;
  }
  NativeRecovery::Primary primary_locked() const {
    return {state_.primary_calls,state_.primary_period_overruns,state_.last_primary_ns,state_.last_primary_ns!=0};
  }
  void finish_primary_locked(std::uint64_t now,std::uint64_t finish,
                             bool confirmed_native,bool pre_admission_rejection) {
    // A missed primary period is still a period even when its deadline makes
    // submission unsafe. Keep real lease admissions separate from these calls.
    // This also lets a waiting/entry deadline miss latch recovery probation,
    // rather than hiding it by skipping the native callback.
    increment_locked(state_.primary_calls);
    if(pre_admission_rejection)increment_locked(state_.not_submitted[0]);
    if(now>finish) {
      increment_locked(state_.primary_period_overruns);
      for(unsigned i=1;i<3;++i)if(recovery_[i].enabled && !recovery_[i].history_opaque &&
          recovery_[i].policy.primary_failed())state_.disabled[i]=true;
    }
    if(confirmed_native)state_.last_primary_ns=now;
  }
  bool fits_locked(std::uint64_t now) const {
    return state_.next_primary_ns>=now && state_.next_primary_ns-now>=hardcap_ns+guard_ns;
  }
  bool optional_allowed_locked(unsigned index,std::uint64_t now) {
    if(!state_.disabled[index])return true;
    auto& recovery=recovery_[index];
    if(!recovery.enabled || recovery.history_opaque)return false;
    const auto due=recovery.policy.due(now,primary_locked());
    if(recovery.policy.error()!=NativeRecovery::Error::none)fence_locked(FenceReason::invalid_policy);
    return due && !state_.fenced;
  }
  unsigned phase_locked(unsigned index) const {
    const auto& r=recovery_[index];
    return static_cast<unsigned>(r.history_opaque?r.opaque.phase:r.policy.snapshot().phase);
  }
  bool business_allowed_locked(unsigned index) const {
    if(state_.fenced || state_.disabled[index])return false;
    const auto& r=recovery_[index];if(!r.enabled)return true;
    if(r.history_opaque)return false;
    return r.policy.normal_allowed() || (index==1 && r.policy.probation());
  }
  void expire_pending_locked(unsigned index,std::uint64_t now) {
    if(pending_[index].token && now>=pending_[index].source_expires_ns) {
      pending_[index]={};condition_.notify_all();
    }
  }
};
}  // namespace aura
