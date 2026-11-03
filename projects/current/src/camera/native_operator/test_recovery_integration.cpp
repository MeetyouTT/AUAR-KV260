#include "native_lease_v2.hpp"
#include <atomic>
#include <iostream>
#include <stdexcept>
#include <thread>

using namespace aura;
constexpr std::uint64_t ms=1'000'000,s=1'000'000'000;
static void require(bool value,const char* message) { if(!value)throw std::runtime_error(message); }
static Completion ok(void*) { return {true,true,0}; }
static Completion unsubmitted(void*) { return {false,false,-1}; }
static Completion unknown(void*) { return {true,false,-1}; }
struct Harness {
  std::uint64_t now=100*s;
  unsigned clock_calls=0,jump_at=0;
  std::uint64_t jump_ns=0;
  NativeLease gate{[this] { if(++clock_calls==jump_at)now+=jump_ns;return now; },true};
  explicit Harness(bool initialize=true) { if(initialize)require(gate.restore_seed(clean()),"clean seed accepted"); }
  GateSeed clean() const {
    GateSeed seed;seed.captured_ns=now;
    for(auto& r:seed.recovery) { r.enabled=true;r.policy.captured_ns=now; }
    return seed;
  }
  Snapshot snapshot() { Snapshot value;require(gate.snapshot(value),"snapshot");return value; }
  static Completion advance(void* pointer) {
    auto& h=*static_cast<std::pair<Harness*,std::uint64_t>*>(pointer);h.first->now+=h.second;return {true,true,0};
  }
  Report primary(std::uint64_t duration=ms,std::uint64_t budget=100*ms) {
    std::pair<Harness*,std::uint64_t> args{this,duration};
    return gate.execute(Task::yolo,now+s,now+budget,advance,&args);
  }
  Report optional(Task task,std::uint64_t duration=ms,std::uint64_t ttl=s) {
    std::pair<Harness*,std::uint64_t> args{this,duration};
    return gate.execute(task,now+ttl,0,advance,&args);
  }
  void completed_hardcap(Task task) {
    require(primary().outcome==Outcome::completed,"healthy primary before fault");
    const auto fault=optional(task,31*ms);
    require(fault.hardcap&&!fault.guard&&fault.completion.completed,"safe completed hardcap");
    require(snapshot().recovery[static_cast<unsigned>(task)-1].policy.phase==NativeRecovery::Phase::cooldown,"cooldown entered");
  }
  void cooldown_ready() { now+=10*s;require(primary().outcome==Outcome::completed,"fresh healthy primary"); }
};
static void seed_validation_once() {
  Harness h(false);
  require(h.gate.execute(Task::sface,h.now+s,0,ok,nullptr).outcome==Outcome::seed_required,"production requires seed");
  auto invalid=h.clean();invalid.primary_period_overruns=1;
  require(!h.gate.restore_seed(invalid),"invalid baseline rejected");
  require(h.snapshot().primary_calls==0&&!h.snapshot().seed_loaded,"bad seed no mutation");
  require(h.gate.restore_seed(h.clean()),"valid retry");
  require(!h.gate.restore_seed(h.clean()),"seed cannot replay/reset");
}
static void preserve_mixed_latched_unknown_history() {
  Harness h(false);auto seed=h.clean();seed.primary_calls=100;seed.primary_period_overruns=3;
  seed.last_primary_ns=h.now-ms;seed.admissions={100,62491,391};seed.completed={100,62491,391};
  seed.overruns[1]=5;seed.disabled[1]=true;
  auto& r=seed.recovery[0];r.history_opaque=true;r.opaque_attempt_count=1;
  auto& p=r.policy.state;p.phase=NativeRecovery::Phase::latched;
  p.reason=NativeRecovery::Reason::unsafe_or_unknown_completion;p.faults=5;p.attempts=4;p.recoveries=4;
  require(h.gate.restore_seed(seed),"mixed guard LATCHED preserved with explicit opaque history");
  require(h.primary().outcome==Outcome::completed,"YOLO still usable");
  require(h.optional(Task::yunet).outcome==Outcome::disabled,"old guard LATCHED not reopened");
  require(h.optional(Task::sface).business_ready,"independent SFace running");
  auto state=h.snapshot();require(state.overruns[1]==5&&state.recovery[0].policy.recoveries==4,"all source fault/recovery totals retained");
  require(state.recovery[0].history_opaque&&state.recovery[0].opaque_attempt_count==1,"unknown queue not called empty");
  require(state.primary_calls==101&&state.completed[2]==392,"new work adds to inherited totals");
  auto unsafe=seed;unsafe.recovery[0].policy.state.phase=NativeRecovery::Phase::cooldown;
  Harness other(false);require(!other.gate.restore_seed(unsafe),"opaque cooldown cannot authorize recovery");
}
static void cooldown_requires_primary_progress() {
  Harness h;h.completed_hardcap(Task::yunet);h.now+=10*s;
  h.gate.announce_primary(h.now+100*ms);
  require(h.optional(Task::yunet).outcome==Outcome::disabled,"old primary cannot certify recovery");
  h.primary();auto probe=h.optional(Task::yunet);
  require(probe.result_token&&probe.business_ready,"real YuNet probe may supply detection");
  const auto first=h.gate.acknowledge(Task::yunet,probe.result_token,true);
  require(first.accepted&&first.recovery_phase==2,"first ACK not recovered");
  require(h.snapshot().recovery[0].policy.attempts==1,"one bounded round consumed");
}
static void sface_three_post_GIL_acks() {
  Harness h;h.completed_hardcap(Task::sface);h.cooldown_ready();
  for(unsigned i=1;i<=3;++i) {
    const auto native=h.optional(Task::sface);
    require(native.completion.completed&&native.result_token&&!native.business_ready,"native completion separate from business ready");
    auto before=h.snapshot();require(before.recovery[1].policy.probe_successes==i-1,"native release never advances probe");
    const auto ack=h.gate.acknowledge(Task::sface,native.result_token,true);
    require(ack.accepted&&ack.business_ready==(i==3),"only third qualified ACK ready");
    require(!h.gate.acknowledge(Task::sface,native.result_token,true).accepted,"replayed ACK rejected");
  }
  auto after=h.snapshot();require(after.recovery[1].policy.recoveries==1&&after.recovery[1].policy.probe_successes==3,"recovered once after three ACKs");
  require(after.completed[2]==4&&after.overruns[2]==1,"fault native plus three probes all counted");
}
static void expired_post_GIL_result_does_not_advance() {
  Harness h;h.completed_hardcap(Task::sface);h.cooldown_ready();
  auto native=h.optional(Task::sface,ms,5*ms);
  require(native.result_token&&native.result_fresh,"native end fresh");
  h.now+=5*ms;
  const auto ack=h.gate.acknowledge(Task::sface,native.result_token,true);
  require(ack.accepted&&!ack.result_fresh&&!ack.business_ready,"GIL-return expiry cannot count");
  require(h.snapshot().recovery[1].policy.probe_successes==0,"no successful probe credited");
  auto again=h.optional(Task::sface,6*ms,5*ms);
  require(again.completion.completed&&!again.result_fresh,"in-flight TTL expiry still confirms completion");
  h.gate.acknowledge(Task::sface,again.result_token,false);
  require(h.snapshot().recovery[1].policy.probe_successes==0,"expired native result not a probe");
}
static void pending_isolated_and_immutable() {
  Harness h;h.completed_hardcap(Task::sface);h.cooldown_ready();auto first=h.optional(Task::sface,ms,20*ms);
  require(h.optional(Task::sface).outcome==Outcome::busy,"pending token cannot be overwritten");
  require(h.primary().outcome==Outcome::completed,"YOLO proceeds before Python ACK");
  require(h.optional(Task::yunet).business_ready,"other optional proceeds before ACK");
  require(!h.gate.task_quiescent(Task::sface),"unexpired pending blocks model close");
  h.now+=20*ms;require(h.gate.task_quiescent(Task::sface),"expired pending can be dropped without success");
  auto second=h.optional(Task::sface);
  require(second.result_token!=first.result_token,"token not reused");
  require(!h.gate.acknowledge(Task::sface,first.result_token,true).accepted,"late old token cannot consume new result");
  require(h.snapshot().pending_result_tokens[2]==second.result_token,"new pending retained");
  require(h.snapshot().recovery[1].policy.probe_successes==0,"dropped pending does not advance");
}
static void primary_late_between_release_and_ack_latches() {
  Harness h;h.completed_hardcap(Task::sface);h.cooldown_ready();auto probe=h.optional(Task::sface);
  h.primary(11*ms,10*ms);
  require(h.snapshot().recovery[1].policy.phase==NativeRecovery::Phase::latched,"primary late during probation locks");
  const auto ack=h.gate.acknowledge(Task::sface,probe.result_token,true);
  require(ack.accepted&&!ack.business_ready&&ack.recovery_phase==3,"old ACK cannot resurrect LATCHED");
  require(h.snapshot().recovery[1].policy.recoveries==0,"no false recovery");
}
static void unsubmitted_round_semantics() {
  for(auto task:{Task::yunet,Task::sface}) {
    Harness h;h.completed_hardcap(task);h.cooldown_ready();
    auto result=h.gate.execute(task,h.now+s,0,unsubmitted,nullptr);
    require(result.outcome==Outcome::not_submitted&&!result.result_token,"no native/no probe ACK");
    const auto r=h.snapshot().recovery[static_cast<unsigned>(task)-1].policy;
    require(r.attempts==(task==Task::yunet?1U:0U),"YuNet admission versus SFace native attempt round accounting");
    require(r.probe_successes==0,"unsubmitted never a successful probe");
  }
}
static void unknown_completion_fences_and_ACK_cannot_unlock() {
  Harness h;h.primary();auto result=h.gate.execute(Task::sface,h.now+s,0,unknown,nullptr);
  require(result.outcome==Outcome::fenced&&!result.result_token,"unknown fences before any result token");
  require(!h.gate.acknowledge(Task::sface,1,true).accepted,"ACK cannot clear fence");
  require(h.primary().outcome==Outcome::fenced,"no new owner jobs");
  require(!h.gate.task_quiescent(Task::sface),"unknown model cannot be closed");
}
static void checkpoint_seals_and_restores_exact_history() {
  Harness h;h.completed_hardcap(Task::sface);h.cooldown_ready();
  auto probe=h.optional(Task::sface);GateSeed checkpoint;
  require(!h.gate.checkpoint(checkpoint),"pending result cannot be checkpointed");
  h.gate.acknowledge(Task::sface,probe.result_token,true);
  require(h.gate.checkpoint(checkpoint),"quiescent exact checkpoint");
  require(h.snapshot().quiesced,"source sealed");
  require(h.primary().outcome==Outcome::quiesced,"sealed source cannot alter counters");
  require(!h.gate.announce_primary(h.now+s),"sealed source cannot announce new epoch");
  Harness target(false);target.now=h.now;
  require(target.gate.restore_seed(checkpoint),"strict exact checkpoint imported once");
  auto state=target.snapshot();require(state.recovery[1].policy.probe_successes==1&&state.recovery[1].policy.attempts==1,"probe/round retained");
  require(state.admissions==h.snapshot().admissions&&state.completed==h.snapshot().completed,"native totals retained");
  target.primary();auto next=target.optional(Task::sface);auto ack=target.gate.acknowledge(Task::sface,next.result_token,true);
  require(ack.accepted&&!ack.business_ready&&target.snapshot().recovery[1].policy.probe_successes==2,"new epoch continues second probe, not fresh counters");
}
static void counter_overflow_fail_closed() {
  Harness h(false);auto seed=h.clean();seed.admissions[0]=std::numeric_limits<std::uint64_t>::max();
  seed.primary_calls=seed.admissions[0];
  require(h.gate.restore_seed(seed),"max source counter retained");
  require(h.primary().outcome==Outcome::fenced,"overflow cannot wrap or start work");
  require(h.snapshot().admissions[0]==std::numeric_limits<std::uint64_t>::max(),"counter never reset");
}
static void primary_entry_refusals_preserve_period_and_probation() {
  Harness h;h.completed_hardcap(Task::sface);h.cooldown_ready();
  const auto probe=h.optional(Task::sface);
  auto before=h.snapshot();const auto last_primary=before.last_primary_ns;
  unsigned callbacks=0;
  auto callback=[](void* pointer)->Completion { ++*static_cast<unsigned*>(pointer);return {true,true,0}; };
  for(unsigned i=0;i<5;++i) {
    const auto refusal=h.gate.execute(Task::yolo,h.now+s,h.now-1,callback,&callbacks);
    require(refusal.outcome==Outcome::deadline&&!refusal.completion.submitted,"expired primary period never submitted");
  }
  const auto after=h.snapshot();
  require(callbacks==0&&after.admissions[0]==before.admissions[0],"entry refusal is not an actual native lease");
  require(after.primary_calls==before.primary_calls+5&&after.not_submitted[0]==before.not_submitted[0]+5,
      "deadline refusals remain visible primary calls and no-submit facts");
  require(after.primary_period_overruns==before.primary_period_overruns+5&&after.last_primary_ns==last_primary,
      "skipping expired primary does not hide late periods or fabricate success");
  require(after.recovery[1].policy.phase==NativeRecovery::Phase::latched,"entry late period latches probation");
  const auto ack=h.gate.acknowledge(Task::sface,probe.result_token,true);
  require(ack.accepted&&!ack.business_ready&&ack.recovery_phase==3,"old result cannot undo rejected late primary");
  GateSeed checkpoint;require(h.gate.checkpoint(checkpoint),"deadline-refusal counters checkpoint");
  Harness restored(false);restored.now=h.now;
  require(restored.gate.restore_seed(checkpoint),"no-submit count may exceed real lease count without losing history");
  require(restored.snapshot().primary_calls==after.primary_calls&&
      restored.snapshot().not_submitted[0]==after.not_submitted[0],"deadline-refusal totals inherited exactly");
}
static void primary_TTL_refusal_before_period_is_not_late() {
  Harness h;h.primary();const auto before=h.snapshot();
  unsigned callbacks=0;
  auto callback=[](void* pointer)->Completion { ++*static_cast<unsigned*>(pointer);return {true,true,0}; };
  const auto refusal=h.gate.execute(Task::yolo,h.now-1,h.now+100*ms,callback,&callbacks);
  const auto after=h.snapshot();
  require(refusal.outcome==Outcome::deadline&&callbacks==0,"expired source is rejected before native");
  require(after.primary_calls==before.primary_calls+1&&after.not_submitted[0]==before.not_submitted[0]+1,
      "expired source records the skipped cycle separately from leases");
  require(after.primary_period_overruns==before.primary_period_overruns&&after.last_primary_ns==before.last_primary_ns,
      "source TTL rejection does not fabricate a period overrun or healthy native completion");
}
static void primary_wait_deadline_does_not_disappear() {
  std::atomic<std::uint64_t> now{100*s};std::atomic<bool> entered{false},release{false};
  NativeLease gate([&] { return now.load(); },true);
  GateSeed seed;seed.captured_ns=now;
  for(auto& r:seed.recovery) { r.enabled=true;r.policy.captured_ns=now; }
  require(gate.restore_seed(seed),"wait-deadline initial seed");
  require(gate.execute(Task::yolo,now+s,now+100*ms,ok,nullptr).outcome==Outcome::completed,"initial primary");
  struct Blocking { std::atomic<bool>* entered;std::atomic<bool>* release; } blocking{&entered,&release};
  auto block=[](void* pointer)->Completion {
    auto& value=*static_cast<Blocking*>(pointer);*value.entered=true;
    while(!*value.release)std::this_thread::yield();
    return {true,true,0};
  };
  std::thread optional([&] { gate.execute(Task::sface,now+s,0,block,&blocking); });
  while(!entered)std::this_thread::yield();
  std::atomic<unsigned> callbacks{0};Report refused;
  auto callback=[](void* pointer)->Completion { ++*static_cast<std::atomic<unsigned>*>(pointer);return {true,true,0}; };
  const auto deadline=now+5*ms;
  std::thread primary([&] { refused=gate.execute(Task::yolo,now+s,deadline,callback,&callbacks); });
  Snapshot state;
  do { gate.snapshot(state);std::this_thread::yield(); } while(!state.primary_waiting);
  now+=6*ms;gate.announce_primary(deadline);primary.join();gate.snapshot(state);
  const bool passed=refused.outcome==Outcome::deadline&&!callbacks&&state.active&&
      state.admissions[0]==1&&state.primary_calls==2&&state.not_submitted[0]==1&&state.primary_period_overruns==1;
  release=true;optional.join();
  require(passed,"primary wait timeout counts late cycle while optional still active, without submitting");
}
static void preserve_both_current_latched_histories() {
  Harness h(false);auto seed=h.clean();seed.primary_calls=100;seed.primary_period_overruns=3;
  seed.last_primary_ns=h.now-ms;seed.admissions={100,62491,900};seed.completed={100,62491,900};
  seed.overruns={0,5,3};seed.disabled={false,true,true};
  for(unsigned i=0;i<2;++i) {
    auto& r=seed.recovery[i];r.history_opaque=true;r.opaque_attempt_count=i==0?1:2;
    auto& p=r.policy.state;p.phase=NativeRecovery::Phase::latched;
    p.reason=i==0?NativeRecovery::Reason::unsafe_or_unknown_completion:NativeRecovery::Reason::recovery_budget_exhausted;
    p.faults=i==0?5:3;p.attempts=p.recoveries=i==0?4:2;
  }
  require(h.gate.restore_seed(seed),"both known LATCHED histories import without invented timestamps");
  require(h.primary().outcome==Outcome::completed,"only healthy primary remains usable");
  require(h.optional(Task::yunet).outcome==Outcome::disabled&&h.optional(Task::sface).outcome==Outcome::disabled,
      "neither guard nor budget-exhausted task silently reopens");
  auto state=h.snapshot();
  require(state.overruns[1]==5&&state.overruns[2]==3&&state.recovery[0].policy.recoveries==4&&
      state.recovery[1].policy.recoveries==2,"both actual fault/recovery source totals preserved");
}
static void notification_wait_owns_no_lease() {
  NativeLease gate;const auto now=NativeLease::monotonic_ns();
  gate.announce_primary(now+10*ms);std::atomic<bool> started{false};int result=-9;
  std::thread waiter([&] { started=true;result=gate.wait_optional(Task::sface,NativeLease::monotonic_ns()+100*ms); });
  while(!started)std::this_thread::yield();
  gate.announce_primary(NativeLease::monotonic_ns()+s);waiter.join();
  Snapshot state;gate.snapshot(state);require(result==0&&!state.active&&!state.admissions[2],"notification opportunity owns no DPU lease");
  gate.announce_primary(NativeLease::monotonic_ns()+ms);const auto began=NativeLease::monotonic_ns();
  require(gate.wait_optional(Task::sface,began+s)==1,"wait capped despite distant caller deadline");
  require(NativeLease::monotonic_ns()-began<250*ms,"native notification bounded near100ms");
}
static void bounded_rounds_and_window_expiry() {
  for(bool expire_window:{false,true}) {
    Harness h;
    for(unsigned round=0;round<2;++round) {
      h.completed_hardcap(Task::sface);h.cooldown_ready();
      for(unsigned probe=0;probe<3;++probe) {
        auto report=h.optional(Task::sface);
        require(report.result_token,"recovery probe requires real native completion");
        h.gate.acknowledge(Task::sface,report.result_token,true);
      }
    }
    require(h.snapshot().recovery[1].policy.attempts==2&&h.snapshot().recovery[1].policy.recoveries==2,"two real bounded rounds");
    if(expire_window)h.now+=600*s;
    h.primary();auto third=h.optional(Task::sface,31*ms);
    require(third.hardcap,"third actual fault still measured");
    if(!expire_window) {
      require(h.snapshot().recovery[1].policy.phase==NativeRecovery::Phase::latched,"third fault within600s locks budget");
      h.now+=600*s;h.primary();require(h.optional(Task::sface).outcome==Outcome::disabled,"LATCHED never silently times out");
    } else {
      require(h.snapshot().recovery[1].policy.phase==NativeRecovery::Phase::cooldown,"expired window may enter bounded cooldown");
      h.cooldown_ready();auto next=h.optional(Task::sface);
      require(next.result_token&&h.snapshot().recovery[1].policy.attempts==3&&
          h.snapshot().recovery[1].policy.attempt_count==1,"new window keeps lifetime attempts but prunes old timestamps");
    }
  }
}
static void guard_and_cooldown_primary_failure_latch() {
  {
    Harness h;h.primary();
    auto callback=[](void* pointer)->Completion {
      auto& h=*static_cast<Harness*>(pointer);h.gate.announce_primary(h.now+10*ms);h.now+=6*ms;return {true,true,0};
    };
    auto report=h.gate.execute(Task::yunet,h.now+s,0,callback,&h);
    require(report.guard&&!report.hardcap,"dynamic earlier primary guard still protected");
    h.now+=10*s;h.primary();require(h.optional(Task::yunet).outcome==Outcome::disabled,"guard LATCHED cannot recover");
  }
  {
    Harness h;h.completed_hardcap(Task::yunet);h.primary(11*ms,10*ms);
    require(h.snapshot().recovery[0].policy.phase==NativeRecovery::Phase::cooldown,"cooldown preserves legacy due-time primary comparison");
    h.now+=10*s;h.primary();require(h.optional(Task::yunet).outcome==Outcome::disabled,"primary overrun after fault prevents recovery");
    require(h.snapshot().recovery[0].policy.reason==NativeRecovery::Reason::primary_overrun_after_fault,"primary failure reason retained");
  }
}
static void source_expired_after_admission_no_false_probe() {
  for(auto task:{Task::yunet,Task::sface}) {
    Harness h;h.completed_hardcap(task);h.cooldown_ready();
    h.jump_at=h.clock_calls+2;h.jump_ns=21*ms;
    auto report=h.gate.execute(task,h.now+20*ms,0,ok,nullptr);
    require(report.outcome==Outcome::deadline&&!report.completion.submitted&&!report.result_token,"post-admission TTL recheck prevents submission");
    const auto p=h.snapshot().recovery[static_cast<unsigned>(task)-1].policy;
    require(p.attempts==(task==Task::yunet?1U:0U)&&p.probe_successes==0,"expired admission cannot advance successful probes");
    require(h.snapshot().overruns[static_cast<unsigned>(task)]==1,"21ms withdrawal not a synthetic hardcap");
  }
}
static void checkpoint_wakes_optional_waiter_without_ready() {
  std::atomic<std::uint64_t> now{100*s};std::atomic<bool> watch{false},entered{false};
  std::atomic<unsigned> samples{0};
  NativeLease gate([&] {
    if(watch && ++samples==2)entered=true;
    return now.load();
  },true);
  GateSeed initial;initial.captured_ns=now;
  for(auto& r:initial.recovery) { r.enabled=true;r.policy.captured_ns=now; }
  require(gate.restore_seed(initial),"waiter test fresh seed");
  auto advance=[](void* pointer)->Completion {
    auto& step=*static_cast<std::pair<std::atomic<std::uint64_t>*,std::uint64_t>*>(pointer);
    *step.first+=step.second;return {true,true,0};
  };
  auto primary=[&] {
    std::pair<std::atomic<std::uint64_t>*,std::uint64_t> step{&now,ms};
    return gate.execute(Task::yolo,now+s,now+100*ms,advance,&step);
  };
  primary();std::pair<std::atomic<std::uint64_t>*,std::uint64_t> slow{&now,31*ms};
  gate.execute(Task::sface,now+s,0,advance,&slow);now+=10*s;primary();
  std::pair<std::atomic<std::uint64_t>*,std::uint64_t> quick{&now,ms};
  auto probe=gate.execute(Task::sface,now+5*ms,0,advance,&quick);
  require(probe.result_token!=0,"pending probe before notification wait");
  int result=-9;watch=true;
  std::thread waiter([&] { result=gate.wait_optional(Task::sface,now+s); });
  while(!entered)std::this_thread::yield();
  watch=false;now+=5*ms;GateSeed checkpoint;
  require(gate.checkpoint(checkpoint),"checkpoint drops expired pending and seals");
  waiter.join();require(result==1,"sealed wake cannot advertise optional opportunity");
}
int main() {
  try {
    seed_validation_once();preserve_mixed_latched_unknown_history();cooldown_requires_primary_progress();
    sface_three_post_GIL_acks();expired_post_GIL_result_does_not_advance();pending_isolated_and_immutable();
    primary_late_between_release_and_ack_latches();unsubmitted_round_semantics();
    unknown_completion_fences_and_ACK_cannot_unlock();checkpoint_seals_and_restores_exact_history();
    counter_overflow_fail_closed();notification_wait_owns_no_lease();
    bounded_rounds_and_window_expiry();guard_and_cooldown_primary_failure_latch();source_expired_after_admission_no_false_probe();
    checkpoint_wakes_optional_waiter_without_ready();
    primary_entry_refusals_preserve_period_and_probation();primary_TTL_refusal_before_period_is_not_late();
    primary_wait_deadline_does_not_disappear();preserve_both_current_latched_histories();
    std::cout<<"{\"passed\":true,\"groups\":20,\"scope\":\"native recovery/seed/ACK integration fake callbacks, no VART/device\"}\n";
    return 0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
