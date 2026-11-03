// Exact bridge source control flow against fake VART/XIR, no device access.
#include "fake_runtime.hpp"
#include <atomic>
#include <cstring>
#include <iostream>
#include <thread>
#include <chrono>
#include <stdexcept>

class FakeRunner final : public vart::Runner {
 public:
  xir::Tensor input{"input",{1,4}},output{"output",{1,4}};
  bool throw_execute=false;
  std::atomic<bool> block{false},entered{false},release{false};
  std::vector<const xir::Tensor*> get_input_tensors() override { return {&input}; }
  std::vector<const xir::Tensor*> get_output_tensors() override { return {&output}; }
  std::pair<std::uint32_t,int> execute_async(const std::vector<vart::TensorBuffer*>&,
      const std::vector<vart::TensorBuffer*>& outputs) override {
    entered=true;
    if(throw_execute)throw std::runtime_error("injected unknown native completion");
    while(block && !release)std::this_thread::sleep_for(std::chrono::microseconds(100));
    auto p=outputs[0]->data();std::memset(reinterpret_cast<void*>(p.first),42,p.second);
    return {1,0};
  }
  int wait(int,int) override { return 0; }
};
std::unique_ptr<vart::Runner> vart::Runner::create_runner(const xir::Subgraph*,const char*) {
  return std::make_unique<FakeRunner>();
}

#include "bridge-initial/native_bridge.cpp"

static void require(bool condition,const char* message) {
  if(!condition)throw std::runtime_error(message);
}
struct Fixture {
  std::shared_ptr<Context> context=std::make_shared<Context>();
  std::shared_ptr<Runner> runner=std::make_shared<Runner>();
  FakeRunner* fake=nullptr;
  std::uint64_t cid=900,mid=901;
  Fixture() {
    context->gate.announce_primary(aura::NativeLease::monotonic_ns()+1'000'000'000);
    runner->task=2;runner->native=std::make_unique<FakeRunner>();
    fake=static_cast<FakeRunner*>(runner->native.get());
    runner->inputs=runner->native->get_input_tensors();runner->outputs=runner->native->get_output_tensors();
    runner->input_buffers.emplace_back(std::make_unique<OwnedBuffer>(runner->inputs[0]));
    runner->output_buffers.emplace_back(std::make_unique<OwnedBuffer>(runner->outputs[0]));
    runner->input_ports.push_back(runner->input_buffers[0].get());
    runner->output_ports.push_back(runner->output_buffers[0].get());
    context->models.emplace(mid,runner);contexts.emplace(cid,context);
  }
  ~Fixture() { contexts.clear(); }
  int execute(const std::int8_t* input,std::int8_t* output,AuraNativeReport& report) {
    AuraBuffer outputs{output,4};
    return aura_native_optional_execute(cid,mid,input,4,&outputs,1,
        aura::NativeLease::monotonic_ns()+1'000'000'000,&report);
  }
};
int main() {
  try {
    bool overwrite_reproduced=false;
    {
      Fixture f;f.fake->throw_execute=true;
      const std::int8_t initial[4]{1,2,3,4},replacement[4]{9,9,9,9};
      std::int8_t out[4]{};AuraNativeReport report{};
      require(f.execute(initial,out,report)==-2,"first unknown call must fence");
      require(f.runner->input_buffers[0]->storage[0]==1,"initial input was copied");
      require(f.execute(replacement,out,report)==-2,"subsequent call must be rejected as fenced");
      overwrite_reproduced=f.runner->input_buffers[0]->storage[0]==9;
      require(overwrite_reproduced,"expected pre-fence-copy counterexample changed");
      require(out[0]==0,"unknown output cannot be copied to caller");
      require(aura_native_runner_close(f.cid,f.mid)==-1,"fenced runner close must retain model");
      require(aura_native_context_close(f.cid)==-1,"fenced context close must retain owner");
    }
    std::cout<<"{\"fake_bridge_control_flow_executed\":true,\"unknown_input_overwrite_reproduced\":"
        <<(overwrite_reproduced?"true":"false")<<",\"fenced_close_retained\":true,"
        <<"\"real_vart_or_dpu_calls\":0,\"scope\":\"bridge source with fake dependencies and injected registry only\"}\n";
    return 0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
