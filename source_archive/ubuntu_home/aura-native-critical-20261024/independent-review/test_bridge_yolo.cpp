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

#include "bridge-yolo-reviewed/native_bridge.cpp"

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

int optional_regressions() {
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
      f.runner.reset();f.context.reset();
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
      // Drop fixture references so close is rejected by the actual in-flight
      // operation references, rather than by an unrelated test-held ref.
      f.runner.reset();f.context.reset();
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

struct FakeYolo {
  std::atomic<bool> entered{false}, block{false}, release{false};
  std::atomic<unsigned> calls{0}, destroyed{0};
  int status=0;
  const unsigned char* observed_input=nullptr;
  float* observed_output=nullptr;
  int* observed_count=nullptr;
};
int fake_yolo(void* detector,const unsigned char* input,int width,int height,int stride,
    float* output,int capacity,int class_id,int* count) {
  auto& model=*static_cast<FakeYolo*>(detector);
  if(width!=2 || height!=2 || stride!=6 || capacity!=1 || class_id!=0)
    throw std::runtime_error("YOLO arguments changed");
  ++model.calls;model.observed_input=input;model.observed_output=output;model.observed_count=count;
  model.entered=true;
  while(model.block && !model.release)std::this_thread::sleep_for(std::chrono::microseconds(100));
  for(unsigned i=0;i<6;++i)output[i]=static_cast<float>(i);
  *count=1;
  return model.status;
}
void fake_yolo_destroy(void* detector) { ++static_cast<FakeYolo*>(detector)->destroyed; }
struct YoloFixture {
  std::shared_ptr<Context> context=std::make_shared<Context>();
  FakeYolo model;
  static constexpr std::uint64_t cid=1000;
  YoloFixture() {
    context->yolo=fake_yolo;context->destroy_yolo=fake_yolo_destroy;
    contexts.emplace(cid,context);
    require(aura_native_adopt_yolo(cid,&model)==0,"YOLO adoption failed");
  }
  ~YoloFixture() { contexts.clear();context.reset(); }
  int execute(const unsigned char* input,float* output,int& count,AuraNativeReport& report) {
    const auto now=aura::NativeLease::monotonic_ns();
    return aura_native_yolo_execute(cid,input,2,2,8,output,1,0,&count,
        now+1'000'000'000,now+500'000'000,&report);
  }
};
int main() {
  try {
    require(optional_regressions()==0,"optional regression failed after lifecycle change");
    unsigned groups=0;
    {
      YoloFixture f;const unsigned char input[16]{1,2,3,4,5,6,99,99,7,8,9,10,11,12,99,99};
      float output[6]{};int count=0;AuraNativeReport report{};
      require(f.execute(input,output,count,report)==0,"owned YOLO execution failed");
      require(count==1 && output[5]==5 && f.model.calls==1,"YOLO output not confirmed");
      require(f.model.observed_input!=input && f.model.observed_output!=output &&
          f.model.observed_count!=&count,"YOLO retained a caller-owned pointer");
      require(f.context->yolo_input.size()==12 && f.context->yolo_input[6]==7 &&
          f.context->yolo_input[11]==12,"padded BGR row copy changed");
      AuraNativeState state{};
      require(aura_native_snapshot(f.cid,&state)==0 && state.abi_version==1 &&
          state.admissions[0]==1 && !state.active && !state.fenced,"native state export differs");
      require(aura_native_state_size()==sizeof(AuraNativeState),"state ABI size differs");
      ++groups;
    }
    {
      YoloFixture f;f.model.status=-1;
      const unsigned char input[16]{1},replacement[16]{9};
      float output[6]{};int count=0;AuraNativeReport report{};
      require(f.execute(input,output,count,report)==-2,"unknown YOLO completion must fence");
      const auto* pointer=f.context->yolo_input.data();
      require(f.execute(replacement,output,count,report)==-2,"fenced YOLO must reject");
      require(f.context->yolo_input.data()==pointer && f.context->yolo_input[0]==1 &&
          f.model.calls==1 && count==0 && output[0]==0,"unknown YOLO storage changed");
      auto* retained_context=f.context.get();f.context.reset();
      require(aura_native_context_close(f.cid)==-1 && retained_context->detector==&f.model &&
          f.model.destroyed==0,"unknown detector was destroyed");
      ++groups;
    }
    {
      YoloFixture f;require(aura_native_adopt_yolo(f.cid,&f.model)==-1,"duplicate adoption allowed");
      require(f.context->detector==&f.model && f.model.destroyed==0,"duplicate adoption damaged ownership");
      f.context.reset();
      require(aura_native_context_close(f.cid)==0 && f.model.destroyed==1,"settled detector was not destroyed once");
      ++groups;
    }
    {
      YoloFixture f;f.model.block=true;
      const unsigned char input[16]{1},replacement[16]{9};
      float output[6]{},out2[6]{};int count=0,count2=0;AuraNativeReport report{},report2{};int status=-99;
      std::thread worker([&]{status=f.execute(input,output,count,report);});
      const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(2);
      while(!f.model.entered && std::chrono::steady_clock::now()<end)std::this_thread::yield();
      const bool entered=f.model.entered;
      const int duplicate=f.execute(replacement,out2,count2,report2);
      auto* retained_context=f.context.get();f.context.reset();
      const int close=aura_native_context_close(f.cid);
      f.model.release=true;worker.join();
      require(entered && duplicate==-1 && close==-1 && status==0 && count==1 && count2==0,
          "concurrent YOLO execute/close corrupted ownership");
      require(f.model.calls==1 && retained_context->yolo_input[0]==1,"concurrent YOLO copied an input");
      ++groups;
    }
    std::cout<<"{\"passed\":true,\"yolo_groups\":"<<groups
      <<",\"optional_groups_rerun\":6,\"real_vart_or_dpu_calls\":0,\"factories_called\":0,"
      <<"\"scope\":\"captured adopted-YOLO lifecycle plus optional control flow with fake dependencies\"}\n";
    return 0;
  } catch(const std::exception& error) { std::cerr<<error.what()<<'\n';return 1; }
}
