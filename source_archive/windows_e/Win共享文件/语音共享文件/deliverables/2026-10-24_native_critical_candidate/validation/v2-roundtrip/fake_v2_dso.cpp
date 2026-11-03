// Host-only v2 ABI fixture. Only the owner factory and external ML dependencies
// are fake. Execution, gate, recovery, buffers, ACK and close are candidate code.
#include "fake_runtime.hpp"
#include <atomic>
#include <chrono>
#include <cstring>
#include <thread>

namespace fixture {
std::atomic<std::uint64_t> now{100'000'000'000ULL};
std::atomic<std::uint64_t> delay{1'000'000ULL};
std::atomic<bool> fail{false};
std::atomic<unsigned> destroyed{0}, kind{2}, progress{0};
std::atomic<bool> blocked{false};
class Runner final : public vart::Runner {
 public:
  explicit Runner(unsigned task) : input(task==1?"yunet_input":"sface_input",
      task==1?std::vector<std::int32_t>{1,320,320,3}:std::vector<std::int32_t>{1,112,112,3}) {
    if(task==1) {
      outputs.emplace_back("yunet_40",std::vector<std::int32_t>{1,40,40,51});
      outputs.emplace_back("yunet_20",std::vector<std::int32_t>{1,20,20,34});
      outputs.emplace_back("yunet_10",std::vector<std::int32_t>{1,10,10,34});
      outputs.emplace_back("yunet_5",std::vector<std::int32_t>{1,5,5,51});
    } else outputs.emplace_back("sface_output",std::vector<std::int32_t>{1,128});
  }
  xir::Tensor input;
  std::vector<xir::Tensor> outputs;
  std::vector<const xir::Tensor*> get_input_tensors() override { return {&input}; }
  std::vector<const xir::Tensor*> get_output_tensors() override {
    std::vector<const xir::Tensor*> result;
    for(const auto& output:outputs)result.push_back(&output);
    return result;
  }
  std::pair<std::uint32_t,int> execute_async(const std::vector<vart::TensorBuffer*>& inputs,
      const std::vector<vart::TensorBuffer*>& outputs_) override {
    if(fail.exchange(false))throw std::runtime_error("fake unknown completion");
    now+=delay.load();
    const auto input_=inputs[0]->data();
    for(unsigned i=0;i<outputs_.size();++i) {
      const auto output=outputs_[i]->data();
      std::memset(reinterpret_cast<void*>(output.first),
          *reinterpret_cast<const unsigned char*>(input_.first)+i,output.second);
    }
    return {1,0};
  }
  int wait(int,int) override { return 0; }
};
}  // namespace fixture
std::unique_ptr<vart::Runner> vart::Runner::create_runner(const xir::Subgraph*,const char*) {
  return std::make_unique<fixture::Runner>(fixture::kind);
}

#define aura_native_context_create aura_fixture_disabled_real_context_create
#include "native_bridge.cpp"
#undef aura_native_context_create

namespace fixture {
int detect(void*,const unsigned char*,int,int,int,float* output,int,int,int* count) {
  now+=1'000'000ULL;
  const float values[6]{1,2,3,4,.9F,0};
  std::memcpy(output,values,sizeof(values));*count=1;return 0;
}
void destroy(void*) { ++destroyed; }
}  // namespace fixture
extern "C" {
// Deliberate fake factory: no project/hardware owner lock or library loading.
std::uint64_t aura_native_context_create(int owner_fd,const char*) {
  auto context=std::make_shared<Context>([] { return fixture::now.load(); });
  context->fd=fcntl(owner_fd,F_DUPFD_CLOEXEC,3);
  if(context->fd<0)return 0;
  context->yolo=fixture::detect;context->destroy_yolo=fixture::destroy;
  std::lock_guard<std::mutex> lock(registry_mutex);
  const auto id=next_id++;contexts.emplace(id,context);return id;
}
unsigned aura_fixture_fake_only() { return 2; }
std::uint64_t aura_fixture_now() { return fixture::now; }
void aura_fixture_advance(std::uint64_t ns) { fixture::now+=ns; }
void aura_fixture_delay(std::uint64_t ns) { fixture::delay=ns; }
void aura_fixture_kind(unsigned task) { fixture::kind=task; }
void aura_fixture_fail_next() { fixture::fail=true; }
unsigned aura_fixture_destroyed() { return fixture::destroyed; }
void aura_fixture_block() {
  fixture::progress=0;fixture::blocked=true;
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  fixture::blocked=false;
}
void aura_fixture_try_progress() { if(fixture::blocked)++fixture::progress; }
unsigned aura_fixture_progress() { return fixture::progress; }
}
