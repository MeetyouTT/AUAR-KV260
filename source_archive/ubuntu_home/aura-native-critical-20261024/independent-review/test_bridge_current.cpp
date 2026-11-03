// Control-flow isolation only. Exact captured bridge source, fake VART/XIR,
// injected registry; no context/model factories or device files are touched.
#include "fake_runtime.hpp"
#include <atomic>
#include <chrono>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>

class FakeRunner final : public vart::Runner {
 public:
  xir::Tensor input{"input",{1,4}}, output{"output",{1,4}};
  bool throw_execute=false;
  std::uint32_t job_id=1;
  int execute_status=0, wait_status=0;
  std::atomic<unsigned> calls{0},waits{0};
  std::atomic<bool> block{false},entered{false},release{false};
  std::vector<const xir::Tensor*> get_input_tensors() override { return {&input}; }
  std::vector<const xir::Tensor*> get_output_tensors() override { return {&output}; }
  std::pair<std::uint32_t,int> execute_async(const std::vector<vart::TensorBuffer*>&,
      const std::vector<vart::TensorBuffer*>& outputs) override {
    ++calls;entered=true;
    if(throw_execute)throw std::runtime_error("injected unknown completion");
    while(block && !release)std::this_thread::sleep_for(std::chrono::microseconds(100));
    auto p=outputs[0]->data();std::memset(reinterpret_cast<void*>(p.first),42,p.second);
    return {job_id,execute_status};
  }
  int wait(int,int) override { ++waits;return wait_status; }
};
std::unique_ptr<vart::Runner> vart::Runner::create_runner(const xir::Subgraph*,const char*) {
  throw std::runtime_error("Factories forbidden in this isolation test");
}

#include "bridge-reviewed-current/native_bridge.cpp"

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
  int execute(const std::int8_t* input,std::int8_t* output,AuraNativeReport& report,
      std::uint64_t ttl=0) {
    AuraBuffer outputs{output,4};
    return aura_native_optional_execute(cid,mid,input,4,&outputs,1,
        ttl ? ttl : aura::NativeLease::monotonic_ns()+1'000'000'000,&report);
  }
};

int main() {
  try {
    unsigned groups=0;
    {
      Fixture f;const std::int8_t in[4]{1,2,3,4};std::int8_t out[4]{};AuraNativeReport report{};
      require(f.execute(in,out,report)==0,"normal completion failed");
      require(out[0]==42 && report.completed==1 && report.submitted==1,"output proof missing");
      require(f.fake->calls==1 && f.fake->waits==1,"execute/wait must each run once");
      ++groups;
    }
    {
      Fixture f;f.fake->throw_execute=true;
      const std::int8_t initial[4]{1,2,3,4},replacement[4]{9,9,9,9};
      std::int8_t out[4]{};AuraNativeReport report{};
      require(f.execute(initial,out,report)==-2,"unknown completion must fence");
      require(f.runner->input_buffers[0]->storage[0]==1,"initial input not copied");
      require(f.execute(replacement,out,report)==-2,"second call must reject fence");
      require(f.runner->input_buffers[0]->storage[0]==1,"fenced storage was overwritten");
      require(out[0]==0 && f.fake->calls==1,"fenced output/native call escaped");
      require(aura_native_runner_close(f.cid,f.mid)==-1,"fenced runner was destroyed");
      require(aura_native_context_close(f.cid)==-1,"fenced owner was closed");
      ++groups;
    }
    {
      Fixture f;const std::int8_t in[4]{1,2,3,4};std::int8_t out[4]{};AuraNativeReport report{};
      require(f.execute(in,out,report,1)==1,"expired source must defer");
      require(f.fake->calls==0 && out[0]==0 && report.submitted==0,"expired source was submitted");
      ++groups;
    }
    {
      Fixture f;f.fake->block=true;
      const std::int8_t initial[4]{1,2,3,4},replacement[4]{9,9,9,9};
      std::int8_t out[4]{},out2[4]{};AuraNativeReport report{},report2{};int status=-99;
      std::thread worker([&]{status=f.execute(initial,out,report);});
      const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);
      while(!f.fake->entered && std::chrono::steady_clock::now()<end)std::this_thread::yield();
      const bool entered=f.fake->entered;
      const int duplicate=f.execute(replacement,out2,report2);
      const bool retained=f.runner->input_buffers[0]->storage[0]==1;
      const int runner_close=aura_native_runner_close(f.cid,f.mid);
      const int owner_close=aura_native_context_close(f.cid);
      f.fake->release=true;worker.join();
      require(entered && duplicate==-1 && retained,"duplicate operation changed active storage");
      require(runner_close==-1 && owner_close==-1,"active close released resources");
      require(status==0 && out[0]==42 && out2[0]==0,"first output was corrupted");
      f.runner.reset();
      require(aura_native_runner_close(f.cid,f.mid)==0,"settled runner should close");
      f.context.reset();
      require(aura_native_context_close(f.cid)==0,"unreferenced empty context should close");
      ++groups;
    }
    {
      Fixture f;f.fake->wait_status=-1;
      const std::int8_t in[4]{1,2,3,4};std::int8_t out[4]{};AuraNativeReport report{};
      require(f.execute(in,out,report)==-2 && out[0]==0,"wait failure must retain unknown completion");
      require(report.submitted==1 && report.completed==0 && report.native_status==-1,"wait failure report differs");
      ++groups;
    }
    {
      Fixture f;f.fake->job_id=std::numeric_limits<std::uint32_t>::max();
      const std::int8_t in[4]{1,2,3,4};std::int8_t out[4]{};AuraNativeReport report{};
      require(f.execute(in,out,report)==-2 && out[0]==0,"oversized job id must fence");
      require(f.fake->waits==0 && report.native_status==EOVERFLOW,"job id was narrowed");
      ++groups;
    }
    std::cout<<"{\"passed\":true,\"groups\":"<<groups
      <<",\"input_retained_after_fence\":true,\"active_close_retained\":true,"
      <<"\"real_vart_or_dpu_calls\":0,\"factories_called\":0,"
      <<"\"scope\":\"captured bridge control flow with fake dependencies and injected registry\"}\n";
    return 0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
