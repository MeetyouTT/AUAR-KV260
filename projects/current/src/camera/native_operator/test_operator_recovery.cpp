#include "native_lease_v2.hpp"
#include <iostream>
#include <stdexcept>
using namespace aura;
constexpr std::uint64_t ms=1'000'000,s=1'000'000'000;
static void check(bool v,const char* why) {if(!v)throw std::runtime_error(why);}
struct H {
 std::uint64_t now=1000*s;
 NativeLease gate{[this]{return now;},true};
 H(NativeRecovery::Reason reason=NativeRecovery::Reason::recovery_budget_exhausted,bool opaque=false,bool young=false) {
  GateSeed seed;seed.captured_ns=now;seed.primary_calls=1000;seed.primary_period_overruns=10;
  seed.last_primary_ns=now-ms;seed.admissions={1000,0,40};seed.completed={1000,0,40};seed.overruns[2]=3;seed.disabled[2]=true;
  for(auto& r:seed.recovery) {r.enabled=true;r.policy.captured_ns=now;}
  auto& r=seed.recovery[1];auto& p=r.policy.state;r.history_opaque=opaque;
  p.phase=NativeRecovery::Phase::latched;p.reason=reason;p.faults=3;p.attempts=2;p.recoveries=2;
  p.observed_ns=900*s;p.cooldown_until_ns=400*s;p.fault_primary_calls=500;p.fault_primary_overruns=3;
  if(opaque)r.opaque_attempt_count=2;
  else {p.attempt_count=2;p.attempt_times={100*s,young?900*s:200*s};}
  check(gate.restore_seed(seed),"restore old history");
 }
 static Completion work(void* ptr) {auto& h=*static_cast<H*>(ptr);h.now+=ms;return {true,true,0};}
 void primary(bool late=false) {check(gate.execute(Task::yolo,now+s,late?now-ms:now+100*ms,work,this).outcome!=Outcome::fenced,"primary");}
 void healthy() {for(unsigned i=0;i<210;++i) {now+=150*ms;primary();}}
 Snapshot snapshot() {Snapshot out;check(gate.snapshot(out),"snapshot");return out;}
 bool request(std::uint64_t faults=3,std::uint64_t attempts=2,std::uint64_t primary=10) {
  return gate.request_operator_recovery(Task::sface,faults,attempts,primary);
 }
};
int main() {
 try {
  {
   H h;check(!h.request(),"wait healthy interval");h.healthy();
   check(!h.request(4),"fault CAS");check(!h.request(3,3),"attempt CAS");check(!h.request(3,2,9),"primary CAS");
   auto before=h.snapshot().recovery[1].policy;check(h.request(),"explicit aged operator request");
   auto after=h.snapshot();const auto& p=after.recovery[1].policy;
   check(p.phase==NativeRecovery::Phase::cooldown&&after.disabled[2],"still disabled in cooldown");
   check(p.faults==before.faults&&p.attempts==before.attempts&&p.recoveries==before.recoveries&&
         p.attempt_times==before.attempt_times&&p.attempt_count==before.attempt_count,"history retained exactly");
   check(p.fault_primary_overruns==10&&p.fault_primary_calls==after.primary_calls,"auditable new healthy baseline");
   check(!h.request(),"no replay");h.now+=10*s;h.primary();
   for(unsigned i=0;i<3;++i) {
    auto r=h.gate.execute(Task::sface,h.now+s,0,H::work,&h);
    check(r.completion.completed&&r.result_token,"real qualified probe");
    auto a=h.gate.acknowledge(Task::sface,r.result_token,true);
    check(a.accepted&&a.business_ready==(i==2),"three ACK readiness");
   }
   auto final=h.snapshot().recovery[1].policy;
   check(final.faults==3&&final.attempts==3&&final.recoveries==3,"totals only add actual work");
  }
  {H h;h.now+=31*s;h.primary();check(!h.request(),"elapsed time without primary progress refused");}
  {H h(NativeRecovery::Reason::unsafe_or_unknown_completion);h.healthy();check(!h.request(),"unsafe latch never reopened");}
  {H h(NativeRecovery::Reason::unsafe_or_unknown_completion,true);h.healthy();check(!h.request(),"opaque history refused");}
  {H h(NativeRecovery::Reason::recovery_budget_exhausted,false,true);h.healthy();check(!h.request(),"newest prior attempt must age");}
  {H h;h.healthy();h.primary(true);check(!h.request(3,2,11),"primary miss resets healthy observation");h.healthy();check(h.request(3,2,11),"new actual healthy interval may qualify");}
  {H h;h.healthy();h.now+=s;check(!h.request(),"stale last primary refused");}
  {H h;h.healthy();check(!h.gate.request_operator_recovery(Task::yolo,3,2,10),"never reopen primary");}
  std::cout<<"{\"passed\":true,\"groups\":8,\"scope\":\"operator request guards; counters and three probes\"}\n";
 } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
