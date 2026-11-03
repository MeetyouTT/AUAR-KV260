// Host-only cross-language ABI fixture. All XIR/VART symbols are fakes.
// This is NEVER a target-board library and must not be shipped as one.
#include "fake_runtime.hpp"
#include <atomic>
#include <chrono>
#include <cstring>
#include <thread>

namespace fixture {
std::atomic<bool> fail{false};
std::atomic<unsigned> destroyed{0};
std::atomic<bool> blocking{false};
std::atomic<unsigned> concurrent_progress{0};
class Runner final : public vart::Runner {
 public:
  xir::Tensor input{"sface_input", {1,112,112,3}};
  xir::Tensor output{"sface_output", {1,128}};
  std::vector<const xir::Tensor*> get_input_tensors() override { return {&input}; }
  std::vector<const xir::Tensor*> get_output_tensors() override { return {&output}; }
  std::pair<std::uint32_t,int> execute_async(const std::vector<vart::TensorBuffer*>& inputs,
      const std::vector<vart::TensorBuffer*>& outputs) override {
    if (fail.exchange(false)) throw std::runtime_error("fake unconfirmed execute");
    const auto source = inputs[0]->data();
    const auto target = outputs[0]->data();
    std::memset(reinterpret_cast<void*>(target.first),
        *reinterpret_cast<const unsigned char*>(source.first), target.second);
    return {1,0};
  }
  int wait(int,int) override { return 0; }
};
}  // namespace fixture
std::unique_ptr<vart::Runner> vart::Runner::create_runner(const xir::Subgraph*, const char*) {
  return std::make_unique<fixture::Runner>();
}

// Only the hardware-owner factory is replaced. All remaining C ABI calls,
// resource handling, buffers, gate and execution are the actual candidate.
#define aura_native_context_create aura_fixture_disabled_real_context_create
#include "native_bridge.cpp"
#undef aura_native_context_create

namespace fixture {
int detect(void*, const unsigned char*, int, int, int, float* output, int, int, int* count) {
  const float row[6]{1,2,3,4,0.9F,0};
  std::memcpy(output, row, sizeof(row));*count=1;return 0;
}
void destroy(void*) { ++destroyed; }
}  // namespace fixture
extern "C" {
std::uint64_t aura_native_context_create(int fd, const char*) {
  auto context=std::make_shared<Context>();
  context->fd=fcntl(fd,F_DUPFD_CLOEXEC,3);
  if(context->fd<0)return 0;
  context->yolo=fixture::detect;context->destroy_yolo=fixture::destroy;
  std::lock_guard<std::mutex> lock(registry_mutex);
  const auto id=next_id++;contexts.emplace(id,context);return id;
}
unsigned aura_fixture_fake_only() { return 1; }
unsigned aura_fixture_destroyed() { return fixture::destroyed; }
void aura_fixture_fail_next() { fixture::fail=true; }
void aura_fixture_block() {
  fixture::concurrent_progress=0;
  fixture::blocking=true;
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  fixture::blocking=false;
}
void aura_fixture_try_progress() {
  if(fixture::blocking.load())++fixture::concurrent_progress;
}
unsigned aura_fixture_progress() { return fixture::concurrent_progress; }
}
