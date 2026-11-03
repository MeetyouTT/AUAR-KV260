// Candidate bridge only. Not installed or connected to the production owner.
#include "native_bridge.h"
#include "native_lease.hpp"
#include "tensor_layout.hpp"
#include <vart/runner.hpp>
#include <vart/tensor_buffer.hpp>
#include <xir/graph/graph.hpp>
#include <xir/graph/subgraph.hpp>
#include <xir/tensor/tensor.hpp>
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <limits>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <sys/file.h>
#include <sys/stat.h>
#include <unordered_map>
#include <unistd.h>
#include <vector>

namespace {
constexpr std::uint64_t fingerprint = 0x101000056010407ULL;
const pid_t module_pid = getpid();
thread_local char last_error[512]{};
void error(const char* text) { std::snprintf(last_error, sizeof(last_error), "%s", text); }
void clear_error() { last_error[0] = 0; }
void same_process() { if (getpid() != module_pid) throw std::runtime_error("Fork-inherited bridge rejected"); }

class OwnedBuffer final : public vart::TensorBuffer {
 public:
  explicit OwnedBuffer(const xir::Tensor* tensor)
      : vart::TensorBuffer(tensor), layout(tensor->get_shape()), storage(layout.bytes()) {
    if (tensor->get_data_type().type != xir::DataType::XINT || tensor->get_data_type().bit_width != 8 ||
        tensor->get_data_size() <= 0 || static_cast<std::size_t>(tensor->get_data_size()) != layout.bytes())
      throw std::invalid_argument("Expected bounded contiguous XINT8 tensor");
  }
  std::pair<std::uint64_t, std::size_t> data(const std::vector<std::int32_t> index = {}) override {
    const auto offset = layout.offset(index);
    return {reinterpret_cast<std::uint64_t>(storage.data() + offset), storage.size() - offset};
  }
  aura::Int8Layout layout;
  std::vector<std::int8_t> storage;
};
struct Runner {
  unsigned task;
  std::unique_ptr<xir::Graph> graph;
  std::unique_ptr<vart::Runner> native;
  std::vector<const xir::Tensor*> inputs, outputs;
  std::vector<std::unique_ptr<OwnedBuffer>> input_buffers, output_buffers;
  std::vector<vart::TensorBuffer*> input_ports, output_ports;
  std::mutex operation;
};
using YoloFunction = int (*)(void*, const unsigned char*, int, int, int, float*, int, int, int*);
using YoloDestroy = void (*)(void*);
struct Context {
  aura::NativeLease gate;
  int fd = -1;
  int gate_fd = -1;
  void* library = nullptr;
  YoloFunction yolo = nullptr;
  YoloDestroy destroy_yolo = nullptr;
  void* detector = nullptr;
  std::mutex yolo_operation;
  std::vector<unsigned char> yolo_input;
  std::array<float, 300 * 6> yolo_output{};
  int yolo_count = 0;
  std::mutex models_mutex;
  std::unordered_map<std::uint64_t, std::shared_ptr<Runner>> models;
  ~Context() {
    if (detector && destroy_yolo) destroy_yolo(detector);
    if (library) dlclose(library);
    if (gate_fd >= 0) close(gate_fd);
    if (fd >= 0) close(fd);
  }
};
std::mutex registry_mutex;
// A fenced context must not run model destructors during static teardown.
// Explicit close is the sole supported teardown; the registry intentionally
// lives until process termination and the OS reclaims its memory.
auto& contexts = *new std::unordered_map<std::uint64_t, std::shared_ptr<Context>>;
std::atomic<std::uint64_t> next_id{1};
std::shared_ptr<Context> context_for(std::uint64_t id) {
  same_process();
  std::lock_guard<std::mutex> lock(registry_mutex);
  const auto found = contexts.find(id);
  if (found == contexts.end()) throw std::invalid_argument("Unknown native context handle");
  return found->second;
}
std::shared_ptr<Runner> runner_for(const std::shared_ptr<Context>& context, std::uint64_t id) {
  std::lock_guard<std::mutex> lock(context->models_mutex);
  const auto found = context->models.find(id);
  if (found == context->models.end()) throw std::invalid_argument("Unknown native runner handle");
  return found->second;
}
bool fenced(Context& context) {
  aura::Snapshot value;
  if (!context.gate.snapshot(value)) throw std::runtime_error("Native context process differs");
  return value.fenced;
}
void export_report(unsigned task, const aura::Report& value, AuraNativeReport* output) {
  *output = AuraNativeReport{1, static_cast<unsigned>(value.outcome), value.hardcap, value.guard,
      value.completion.submitted, value.completion.completed, value.completion.status, task,
      value.start_ns, value.native_return_ns, value.release_decision_ns, value.after_unlock_ns};
}
int outcome_code(const aura::Report& value) {
  if (value.outcome == aura::Outcome::fenced) return -2;
  return value.outcome == aura::Outcome::completed && value.completion.completed &&
      value.completion.status == 0 ? 0 : 1;
}
void tensor_info(const xir::Tensor* tensor, AuraTensorInfo* info) {
  aura::Int8Layout layout(tensor->get_shape());
  const auto name = tensor->get_name();
  if (name.size() >= sizeof(info->name) || !tensor->has_attr("fix_point"))
    throw std::invalid_argument("Tensor metadata exceeds reviewed ABI");
  *info = AuraTensorInfo{};
  info->rank = static_cast<unsigned>(layout.shape().size());
  std::copy(layout.shape().begin(), layout.shape().end(), info->dims);
  info->fix_point = tensor->get_attr<int>("fix_point");
  info->bytes = layout.bytes();
  std::memcpy(info->name, name.c_str(), name.size() + 1);
}
aura::Completion run_optional(void* pointer) {
  auto& runner = *static_cast<Runner*>(pointer);
  auto job = runner.native->execute_async(runner.input_ports, runner.output_ports);
  if (job.second != 0) return {true, false, job.second};
  if (job.first > static_cast<std::uint32_t>(std::numeric_limits<int>::max()))
    return {true, false, EOVERFLOW};
  const auto status = runner.native->wait(static_cast<int>(job.first), -1);
  return {true, status == 0, status};
}
struct YoloJob {
  Context* context;
  void* detector;
  const unsigned char* bgr;
  int width, height, stride;
  float* output;
  int capacity, class_id;
  int* count;
};
aura::Completion run_yolo(void* pointer) {
  auto& j = *static_cast<YoloJob*>(pointer);
  const auto status = j.context->yolo(j.detector, j.bgr, j.width, j.height, j.stride,
      j.output, j.capacity, j.class_id, j.count);
  return {true, status == 0, status};
}
}  // namespace

extern "C" {
std::uint32_t aura_native_abi() { return 1; }
std::uint32_t aura_native_report_size() { return sizeof(AuraNativeReport); }
const char* aura_native_error() { return last_error; }
std::uint64_t aura_native_context_create(int owner_fd, const char* yolo_library) {
  clear_error();
  try {
    same_process();
    if (!yolo_library || !*yolo_library) throw std::invalid_argument("Pinned existing YOLO library required");
    struct stat actual{}, expected{};
    if (fstat(owner_fd, &actual) != 0 || stat("/run/aura-person-dpu.lock", &expected) != 0 ||
        actual.st_dev != expected.st_dev || actual.st_ino != expected.st_ino)
      throw std::invalid_argument("Existing DPU owner's lock FD required");
    std::lock_guard<std::mutex> lock(registry_mutex);
    if (!contexts.empty()) throw std::runtime_error("Exactly one native context per owner process");
    auto context = std::make_shared<Context>();
    context->fd = fcntl(owner_fd, F_DUPFD_CLOEXEC, 3);
    if (context->fd < 0 || flock(context->fd, LOCK_EX | LOCK_NB) != 0)
      throw std::runtime_error("DPU owner lock is not held by the supplied descriptor");
    // A second copy of this DSO must not create a second arbitration gate
    // around the same inherited owner FD. Keep a separate process-wide token.
    context->gate_fd = open("/run/aura-person-native-gate.lock", O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600);
    struct stat gate_stat{};
    if (context->gate_fd < 0 || fstat(context->gate_fd, &gate_stat) != 0 || !S_ISREG(gate_stat.st_mode) ||
        flock(context->gate_fd, LOCK_EX | LOCK_NB) != 0)
      throw std::runtime_error("A native arbitration gate already exists for the owner");
    context->library = dlopen(yolo_library, RTLD_NOW | RTLD_LOCAL);
    if (!context->library) throw std::runtime_error("Pinned YOLO library cannot be loaded");
    context->yolo = reinterpret_cast<YoloFunction>(dlsym(context->library, "aura_yolox_detect"));
    context->destroy_yolo = reinterpret_cast<YoloDestroy>(dlsym(context->library, "aura_yolox_destroy"));
    if (!context->yolo || !context->destroy_yolo)
      throw std::runtime_error("YOLO C ABI functions unavailable");
    const auto id = next_id++;
    contexts.emplace(id, context);
    return id;
  } catch (const std::exception& exc) { error(exc.what()); return 0; }
  catch (...) { error("Unknown native context creation failure"); return 0; }
}
std::uint32_t aura_native_state_size() { return sizeof(AuraNativeState); }
int aura_native_snapshot(std::uint64_t id, AuraNativeState* output) {
  clear_error();
  try {
    if (!output) throw std::invalid_argument("Native state pointer required");
    aura::Snapshot state;
    if (!context_for(id)->gate.snapshot(state)) throw std::runtime_error("Native context process differs");
    *output = AuraNativeState{};
    output->abi_version = 1;
    output->active = state.active;
    output->fenced = state.fenced;
    output->primary_waiting = state.primary_waiting;
    output->next_primary_ns = state.next_primary_ns;
    for (unsigned i = 0; i < 3; ++i) {
      output->disabled[i] = state.disabled[i];
      output->admissions[i] = state.admissions[i];
      output->overruns[i] = state.overruns[i];
    }
    return 0;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
}
int aura_native_adopt_yolo(std::uint64_t id, void* detector) {
  clear_error();
  try {
    auto context = context_for(id);
    std::unique_lock<std::mutex> lock(context->yolo_operation, std::try_to_lock);
    if (!lock.owns_lock() || !detector || context->detector || fenced(*context))
      throw std::runtime_error("YOLO adoption requires a quiescent unbound native context");
    context->detector = detector;
    return 0;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
}
int aura_native_context_close(std::uint64_t id) {
  clear_error();
  try {
    same_process();
    std::lock_guard<std::mutex> registry_lock(registry_mutex);
    const auto found = contexts.find(id);
    if (found == contexts.end()) throw std::invalid_argument("Unknown native context");
    auto context = found->second;
    std::lock_guard<std::mutex> models_lock(context->models_mutex);
    aura::Snapshot value;context->gate.snapshot(value);
    if (context.use_count() != 2 || !context->models.empty() || value.active || value.primary_waiting || value.fenced)
      throw std::runtime_error("Native context is busy or completion unconfirmed; retained");
    contexts.erase(found);
    return 0;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
}
int aura_native_announce_primary(std::uint64_t id, std::uint64_t deadline_ns) {
  clear_error();
  try { return context_for(id)->gate.announce_primary(deadline_ns) ? 0 : -1; }
  catch (const std::exception& exc) { error(exc.what()); return -1; }
}
std::uint64_t aura_native_runner_create(std::uint64_t id, unsigned task, const char* model) {
  clear_error();
  try {
    auto context = context_for(id);
    if (!model || !*model || (task != 1 && task != 2) || fenced(*context))
      throw std::invalid_argument("Enabled optional runner and pinned xmodel required");
    {
      std::unique_lock<std::mutex> lifecycle(context->yolo_operation, std::try_to_lock);
      if (!lifecycle.owns_lock() || !context->detector)
        throw std::runtime_error("Idle adopted YOLO required before optional runners are enabled");
    }
    std::lock_guard<std::mutex> lock(context->models_mutex);
    for (const auto& item : context->models) if (item.second->task == task)
      throw std::runtime_error("Runner already exists for this optional task");
    auto runner = std::make_shared<Runner>();runner->task = task;
    runner->graph = xir::Graph::deserialize(model);
    const xir::Subgraph* selected = nullptr;
    for (const auto* sub : runner->graph->get_root_subgraph()->get_children()) {
      if (sub->has_attr("device") && sub->get_attr<std::string>("device") == "DPU") {
        if (selected) throw std::invalid_argument("Exactly one DPU partition required");
        selected = sub;
      }
    }
    if (!selected || !selected->has_attr("dpu_fingerprint") ||
        selected->get_attr<std::uint64_t>("dpu_fingerprint") != fingerprint)
      throw std::invalid_argument("DPU fingerprint differs from pinned architecture");
    runner->native = vart::Runner::create_runner(selected, "run");
    runner->inputs = runner->native->get_input_tensors();
    runner->outputs = runner->native->get_output_tensors();
    const std::vector<std::int32_t> expected = task == 1 ? std::vector<std::int32_t>{1,320,320,3} :
                                                       std::vector<std::int32_t>{1,112,112,3};
    if (runner->inputs.size() != 1 || runner->inputs[0]->get_shape() != expected ||
        runner->outputs.size() != (task == 1 ? 4U : 1U))
      throw std::invalid_argument("Unexpected optional model ports");
    for (auto* tensor : runner->inputs) {
      runner->input_buffers.emplace_back(std::make_unique<OwnedBuffer>(tensor));
      runner->input_ports.push_back(runner->input_buffers.back().get());
    }
    for (auto* tensor : runner->outputs) {
      runner->output_buffers.emplace_back(std::make_unique<OwnedBuffer>(tensor));
      runner->output_ports.push_back(runner->output_buffers.back().get());
    }
    const auto model_id = next_id++;context->models.emplace(model_id, runner);return model_id;
  } catch (const std::exception& exc) { error(exc.what()); return 0; }
  catch (...) { error("Unknown native runner creation failure"); return 0; }
}
int aura_native_runner_close(std::uint64_t id, std::uint64_t model_id) {
  clear_error();
  try {
    auto context = context_for(id);
    std::lock_guard<std::mutex> lock(context->models_mutex);
    if (fenced(*context)) throw std::runtime_error("Unconfirmed native completion; model buffers retained");
    auto found = context->models.find(model_id);
    if (found == context->models.end()) throw std::invalid_argument("Unknown runner");
    if (found->second.use_count() != 1) throw std::runtime_error("Native runner still referenced by an operation");
    context->models.erase(found);return 0;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
}
int aura_native_tensor_info(std::uint64_t id, std::uint64_t model_id, unsigned output,
                            unsigned index, AuraTensorInfo* info) {
  clear_error();
  try {
    if (!info || output > 1) throw std::invalid_argument("Tensor ABI output invalid");
    auto runner = runner_for(context_for(id), model_id);
    const auto& tensors = output ? runner->outputs : runner->inputs;
    if (index >= tensors.size()) throw std::out_of_range("Tensor port outside model");
    tensor_info(tensors[index], info);return 0;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
}
int aura_native_optional_execute(std::uint64_t id, std::uint64_t model_id,
    const void* input, std::uint64_t input_bytes, const AuraBuffer* outputs, unsigned count,
    std::uint64_t source_expires_ns, AuraNativeReport* report) {
  clear_error();
  if (report) *report = AuraNativeReport{};
  try {
    if (!input || !outputs || !report) throw std::invalid_argument("Native tensor pointers required");
    auto context = context_for(id);auto runner = runner_for(context, model_id);
    std::unique_lock<std::mutex> operation(runner->operation, std::try_to_lock);
    if (!operation.owns_lock()) throw std::runtime_error("Same model runner already active");
    if (fenced(*context)) {
      aura::Report retained;retained.outcome = aura::Outcome::fenced;
      export_report(runner->task, retained, report);
      error("Native completion unconfirmed; owned tensor storage retained unchanged");
      return -2;
    }
    if (input_bytes != runner->input_buffers[0]->storage.size() || count != runner->output_buffers.size())
      throw std::invalid_argument("Native model byte count mismatch");
    for (unsigned i = 0; i < count; ++i)
      if (!outputs[i].data || outputs[i].bytes != runner->output_buffers[i]->storage.size())
        throw std::invalid_argument("Native output capacity mismatch");
    // Stable owned storage survives unknown completion. Allocation/copies are
    // outside the native gate; tensor order comes from Runner, never XIR sets.
    std::memcpy(runner->input_buffers[0]->storage.data(), input, static_cast<std::size_t>(input_bytes));
    const auto result = context->gate.execute(static_cast<aura::Task>(runner->task), source_expires_ns,
        0, run_optional, runner.get());
    export_report(runner->task, result, report);
    const auto code = outcome_code(result);
    if (code == 0)
      for (unsigned i = 0; i < count; ++i)
        std::memcpy(outputs[i].data, runner->output_buffers[i]->storage.data(), static_cast<std::size_t>(outputs[i].bytes));
    return code;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
  catch (...) { error("Unknown optional bridge error"); return -1; }
}
int aura_native_yolo_execute(std::uint64_t id, const unsigned char* bgr,
    int width, int height, int stride, float* output, int capacity, int class_id, int* count,
    std::uint64_t source_expires_ns, std::uint64_t primary_finish_ns, AuraNativeReport* report) {
  clear_error();
  if (report) *report = AuraNativeReport{};
  if (count) *count = 0;
  try {
    if (!bgr || !output || !count || !report || width <= 0 || width > 4096 ||
        height <= 0 || height > 4096 || stride < width * 3 || capacity < 1 || capacity > 300 || class_id != 0)
      throw std::invalid_argument("Original YOLO C ABI arguments invalid");
    auto context = context_for(id);
    std::unique_lock<std::mutex> operation(context->yolo_operation, std::try_to_lock);
    if (!operation.owns_lock() || !context->detector)
      throw std::runtime_error("Adopted YOLO detector required and must be idle");
    if (fenced(*context)) {
      aura::Report retained;retained.outcome = aura::Outcome::fenced;
      export_report(0, retained, report);
      error("Unconfirmed native completion; YOLO detector and storage retained unchanged");
      return -2;
    }
    // Own all storage that an unknown native job might still reference.
    // Allocation/copy is before gate acquisition, and never occurs after fence.
    const auto row_bytes = static_cast<std::size_t>(width) * 3;
    context->yolo_input.resize(row_bytes * static_cast<std::size_t>(height));
    for (int row = 0; row < height; ++row)
      std::memcpy(context->yolo_input.data() + row_bytes * row,
          bgr + static_cast<std::size_t>(stride) * row, row_bytes);
    context->yolo_count = 0;
    YoloJob job{context.get(), context->detector, context->yolo_input.data(), width, height,
        width * 3, context->yolo_output.data(), capacity, class_id, &context->yolo_count};
    const auto result = context->gate.execute(aura::Task::yolo, source_expires_ns, primary_finish_ns, run_yolo, &job);
    export_report(0, result, report);
    const auto code = outcome_code(result);
    if (code == 0) {
      if (context->yolo_count < 0 || context->yolo_count > capacity)
        throw std::runtime_error("Confirmed YOLO result has invalid output count");
      *count = context->yolo_count;
      std::memcpy(output, context->yolo_output.data(), static_cast<std::size_t>(*count) * 6 * sizeof(float));
    }
    return code;
  } catch (const std::exception& exc) { error(exc.what()); return -1; }
  catch (...) { error("Unknown YOLO bridge error"); return -1; }
}
}  // extern C
