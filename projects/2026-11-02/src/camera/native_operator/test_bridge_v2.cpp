// Exact candidate C ABI control flow, fake XIR/VART/YOLO only. No factories for
// hardware owners, no dlopen, no project lock file or device calls occur.
#include "fake_runtime.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
struct Control { std::uint64_t* now=nullptr;std::uint64_t delay=1'000'000;bool unknown=false; };
static Control* factory_control=nullptr;
class FakeRunner final : public vart::Runner {
 public:
  xir::Tensor input{"sface_input",{1,112,112,3}},output{"sface_output",{1,128}};
  Control* control=factory_control;
  std::vector<const xir::Tensor*> get_input_tensors() override { return {&input}; }
  std::vector<const xir::Tensor*> get_output_tensors() override { return {&output}; }
  std::pair<std::uint32_t,int> execute_async(const std::vector<vart::TensorBuffer*>& inputs,
      const std::vector<vart::TensorBuffer*>& outputs) override {
    if(control->unknown)throw std::runtime_error("fake unconfirmed completion");
    *control->now+=control->delay;
    auto target=outputs[0]->data();auto source=inputs[0]->data();
    std::memset(reinterpret_cast<void*>(target.first),*reinterpret_cast<unsigned char*>(source.first),target.second);
    return {1,0};
  }
  int wait(int,int) override { return 0; }
};
std::unique_ptr<vart::Runner> vart::Runner::create_runner(const xir::Subgraph*,const char*) {
  return std::make_unique<FakeRunner>();
}
#include "native_bridge.cpp"
static constexpr std::uint64_t ms=1'000'000,s=1'000'000'000;
static void require(bool condition,const char* message) { if(!condition)throw std::runtime_error(message); }
struct FakeDetector { std::uint64_t* now;unsigned destroyed=0; };
static int fake_yolo(void* pointer,const unsigned char*,int,int,int,float* output,int,int,int* count) {
  auto& value=*static_cast<FakeDetector*>(pointer);*value.now+=ms;
  output[0]=1;output[1]=2;output[2]=3;output[3]=4;output[4]=.9F;output[5]=0;*count=1;return 0;
}
static void destroy_yolo(void* pointer) { ++static_cast<FakeDetector*>(pointer)->destroyed; }
struct Fixture {
  std::uint64_t now=100*s;
  Control control{&now};FakeDetector detector{&now};
  std::shared_ptr<Context> context=std::make_shared<Context>([this] { return now; });
  std::uint64_t id=next_id++,model=0;
  Fixture() { context->yolo=fake_yolo;context->destroy_yolo=destroy_yolo;contexts.emplace(id,context); }
  ~Fixture() { contexts.erase(id);context.reset(); }
  AuraNativeSeed seed() const {
    AuraNativeSeed result{};result.abi_version=2;result.struct_size=sizeof(result);result.captured_mono_ns=now;
    std::ifstream stream("/proc/sys/kernel/random/boot_id");std::string boot;std::getline(stream,boot);
    std::memcpy(result.boot_id,boot.c_str(),37);result.recovery[0].enabled=result.recovery[1].enabled=1;return result;
  }
  void initialize() { auto input=seed();require(aura_native_restore_seed(id,&input)==0,"C restore clean seed"); }
  void adopt() { require(aura_native_adopt_yolo(id,&detector)==0,"C adopt YOLO"); }
  void create() {
    factory_control=&control;model=aura_native_runner_create(id,2,"fake-only.not-a-model");
    require(model!=0,"C create fake SFace");
  }
  AuraNativeReport primary() {
    unsigned char bgr[3]{};float output[96]{};int count=0;AuraNativeReport report{};
    require(aura_native_yolo_execute(id,bgr,1,1,3,output,16,0,&count,now+s,now+100*ms,&report)==0,"C primary success");
    require(count==1&&output[0]==1,"C primary copied confirmed result");return report;
  }
  AuraNativeReport optional(unsigned char value=42) {
    std::vector<unsigned char> input(112*112*3,value);unsigned char output[128]{};
    AuraBuffer port{output,128};AuraNativeReport report{};
    require(aura_native_optional_execute(id,model,input.data(),input.size(),&port,1,now+s,&report)==0,"C optional confirmed");
    require(output[0]==value&&output[127]==value,"C raw outputs available before business ACK");return report;
  }
  AuraNativeState state() {
    AuraNativeState output{};require(aura_native_snapshot(id,&output)==0,"C snapshot");return output;
  }
};
static void abi_and_boot_seed_gate() {
  require(aura_native_abi()==2&&aura_native_report_size()==88&&aura_native_state_size()==432&&
      aura_native_seed_size()==520&&aura_native_recovery_size()==104&&aura_native_ack_size()==32,"C ABI exact struct sizes");
  Fixture f;require(aura_native_adopt_yolo(f.id,&f.detector)==-1,"cannot adopt before seed");
  auto seed=f.seed();seed.boot_id[0]=seed.boot_id[0]=='a'?'b':'a';
  require(aura_native_restore_seed(f.id,&seed)==-1,"different kernel boot rejected");
  seed=f.seed();seed.recovery[0].attempts=1;
  require(aura_native_restore_seed(f.id,&seed)==-1,"fresh form cannot smuggle nonzero history");
  f.initialize();require(aura_native_restore_seed(f.id,&seed)==-1,"seed replay cannot reset");
  f.adopt();f.create();auto state=f.state();require(state.seed_loaded&&state.active_task==3,"C state initialized and idle");
}
static void raw_output_three_ack_and_pending_close() {
  Fixture f;f.initialize();f.adopt();f.create();f.primary();f.control.delay=31*ms;
  auto fault=f.optional();require(fault.hardcap&&!fault.guard&&!fault.business_ready,"C hardcap protected");
  f.now+=10*s;f.primary();f.control.delay=ms;
  for(unsigned i=1;i<=3;++i) {
    auto probe=f.optional();require(probe.result_token&&!probe.business_ready&&probe.completed,"pre-ACK completed not ready");
    require(aura_native_runner_close(f.id,f.model)==-1,"cannot close runner with live result token");
    require(aura_native_context_close(f.id)==-1,"cannot close owner with live runner/token");
    AuraNativeAck ack{};
    require(aura_native_ack_result(f.id,2,probe.result_token,1,&ack)==0&&ack.accepted,"C result ACK consumed");
    require(ack.business_ready==(i==3),"only third C ACK business ready");
    require(aura_native_ack_result(f.id,2,probe.result_token,1,&ack)==1&&!ack.accepted,"C ACK replay rejected");
  }
  auto state=f.state();require(state.recovery[1].recoveries==1&&state.completed[2]==4,"C complete/recovery separate counters");
  require(aura_native_runner_close(f.id,f.model)==0,"runner closes after ACK");
  f.context.reset();require(aura_native_context_close(f.id)==0,"confirmed idle owner closes");
  require(f.detector.destroyed==1,"YOLO object destroyed exactly once");
}
static void exact_C_checkpoint_and_frozen_source() {
  Fixture f;f.initialize();f.adopt();f.create();f.primary();f.optional();
  AuraNativeSeed checkpoint{};std::string sha(64,'a');
  require(aura_native_checkpoint(f.id,sha.c_str(),&checkpoint)==0,"C exact checkpoint");
  require(checkpoint.checkpoint_kind==1&&checkpoint.source_pid==static_cast<unsigned>(getpid())&&
      checkpoint.source_birth_ticks&&checkpoint.completed[2]==1,"source provenance and counters");
  require(f.state().quiesced,"C source sealed");
  Fixture target;target.now=f.now;
  require(aura_native_restore_seed(target.id,&checkpoint)==0,"C checkpoint restoration");
  require(target.state().completed[2]==1&&target.state().primary_calls==1,"C inherited counters not reset");
  target.adopt();target.create();target.primary();target.optional();
  require(target.state().completed[2]==2&&target.state().primary_calls==2,"C new epoch appends counts");
}
static void prefix_cannot_become_executable_exact_seed() {
  Fixture f;auto seed=f.seed();seed.checkpoint_kind=2;seed.source_pid=getpid();seed.source_birth_ticks=1;
  std::memset(seed.source_manifest_sha256,'a',64);
  require(aura_native_restore_seed(f.id,&seed)==-1,"unfenced prefix rejected");
  seed.fenced=1;seed.disabled[1]=seed.disabled[2]=1;
  for(auto& r:seed.recovery) { r.phase=3;r.reason=1;r.history_opaque=1; }
  require(aura_native_restore_seed(f.id,&seed)==0,"prefix can only preserve fenced evidence");
  require(f.state().fenced&&f.state().checkpoint_kind==2,"prefix never ready");
  require(aura_native_adopt_yolo(f.id,&f.detector)==-1,"fenced prefix cannot adopt model owner");
}
static void unknown_C_native_retained_and_ACK_denied() {
  Fixture f;f.initialize();f.adopt();f.create();f.primary();f.control.unknown=true;
  std::vector<unsigned char> input(112*112*3,1);unsigned char output[128]{};AuraBuffer port{output,128};AuraNativeReport report{};
  require(aura_native_optional_execute(f.id,f.model,input.data(),input.size(),&port,1,f.now+s,&report)==-2,"C unknown fences");
  require(!report.result_token&&!report.business_ready&&output[0]==0,"unknown no token/output publication");
  AuraNativeAck ack{};require(aura_native_ack_result(f.id,2,1,1,&ack)==-2&&!ack.accepted,"C ACK cannot clear unknown");
  require(aura_native_runner_close(f.id,f.model)==-1&&aura_native_context_close(f.id)==-1,"C unknown owner and buffers retained");
}
int main() {
  try {
    abi_and_boot_seed_gate();raw_output_three_ack_and_pending_close();exact_C_checkpoint_and_frozen_source();
    prefix_cannot_become_executable_exact_seed();unknown_C_native_retained_and_ACK_denied();
    std::cout<<"{\"passed\":true,\"groups\":5,\"scope\":\"exact C ABI v2 with fake VART/XIR/YOLO and injected registry, real device/model calls0\"}\n";
    return 0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
