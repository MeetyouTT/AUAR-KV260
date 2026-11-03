#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
  uint32_t abi_version, outcome, hardcap, guard, submitted, completed;
  int32_t native_status;
  uint32_t task;
  uint64_t start_ns, native_return_ns, release_decision_ns, after_unlock_ns;
  uint32_t business_ready, result_fresh, recovery_phase, reserved;
  uint64_t result_token;
} AuraNativeReport;
typedef struct {
  uint32_t rank;
  int32_t dims[8];
  int32_t fix_point;
  uint64_t bytes;
  char name[256];
} AuraTensorInfo;
typedef struct { void* data; uint64_t bytes; } AuraBuffer;
// phase: 0 RUNNING, 1 COOLDOWN, 2 PROBATION, 3 LATCHED.
// reason: 0 none, 1 unsafe/unknown, 2 budget exhausted, 3 completed-hardcap,
//         4 primary overrun after fault, 5 primary overrun during probation.
// history_opaque=1 is allowed only for disabled LATCHED state. attempt_times
// and attempt_count then describe only known times; opaque_attempt_count is
// the preserved health-only count and NEVER authorizes recovery.
typedef struct {
  uint32_t enabled, phase, reason, probe_successes;
  uint32_t attempt_count, history_opaque, opaque_attempt_count, reserved;
  uint64_t cooldown_until_ns, fault_primary_calls, fault_primary_overruns;
  uint64_t faults, attempts, recoveries, observed_ns, attempt_times_ns[2];
} AuraRecoveryState;
typedef struct {
  uint32_t abi_version, active, fenced, primary_waiting;
  uint64_t next_primary_ns;
  uint32_t disabled[3], seed_loaded;
  uint32_t active_task, fence_reason, quiesced, checkpoint_kind;
  uint64_t admissions[3], overruns[3];
  uint64_t completed[3], native_failures[3], not_submitted[3];
  uint64_t primary_calls, primary_period_overruns, last_primary_ns;
  uint64_t pending_result_tokens[3];
  AuraRecoveryState recovery[2];
} AuraNativeState;
typedef struct {
  uint32_t abi_version, accepted, business_ready, result_fresh;
  uint32_t recovery_phase, reserved;
  uint64_t result_token;
} AuraNativeAck;
// The C layer verifies boot_id against the running kernel. The upper layer
// validates SHA/provenance, exact quiescent checkpoint and old owner shutdown.
// source_pid=source_birth_ticks=0 denotes explicitly validated fresh startup;
// that form must contain entirely clean counters/policies, never old faults.
typedef struct {
  // kind: 0 fresh, 1 exact quiescent, 2 health prefix (always fenced).
  uint32_t abi_version, struct_size, fenced, checkpoint_kind;
  uint64_t captured_mono_ns, primary_calls, primary_period_overruns, last_primary_ns;
  uint32_t source_pid, reserved2;
  uint64_t source_birth_ticks;
  char boot_id[40], source_manifest_sha256[65], reserved_bytes[7];
  uint64_t admissions[3], overruns[3], completed[3], native_failures[3], not_submitted[3];
  uint32_t disabled[3], reserved3;
  AuraRecoveryState recovery[2];
} AuraNativeSeed;
uint32_t aura_native_abi(void);
// Explicit bounded operator request. 0 accepted, 1 refused without unlock,
// -1 invalid context. Existing ABI structures and counters are unchanged.
int aura_native_request_operator_recovery(uint64_t context,unsigned task,
    uint64_t expected_faults,uint64_t expected_attempts,uint64_t expected_primary_overruns);
uint32_t aura_native_report_size(void);
const char* aura_native_error(void);
// Creation requires the existing owner's /run/aura-person-dpu.lock FD.
// Isolation build/check must not call either context or runner factories.
uint64_t aura_native_context_create(int owner_fd, const char* existing_yolo_library);
int aura_native_context_close(uint64_t context);
// On success the context assumes exclusive ownership. The caller must detach
// its old handle while holding the original owner's lifecycle lock.
int aura_native_adopt_yolo(uint64_t context, void* existing_detector);
int aura_native_snapshot(uint64_t context, AuraNativeState* state);
uint32_t aura_native_state_size(void);
uint32_t aura_native_seed_size(void);
uint32_t aura_native_recovery_size(void);
uint32_t aura_native_ack_size(void);
int aura_native_restore_seed(uint64_t context, const AuraNativeSeed* seed);
// Successful checkpoint seals the source gate against any future execution.
// Refuses active/waiting jobs and unacknowledged unexpired results.
int aura_native_checkpoint(uint64_t context, const char* current_manifest_sha256,
                           AuraNativeSeed* seed);
int aura_native_ack_result(uint64_t context, unsigned task, uint64_t token,
                           unsigned usable, AuraNativeAck* ack);
// 0 scheduling opportunity, 1 timeout/disabled/pending/seed-required,
// -2 fenced, -1 invalid. Wait is bounded to min(until, now+100ms), owns no lease.
int aura_native_wait_optional(uint64_t context, unsigned task, uint64_t until_ns);
int aura_native_announce_primary(uint64_t context, uint64_t deadline_ns);
uint64_t aura_native_runner_create(uint64_t context, unsigned task, const char* xmodel);
int aura_native_runner_close(uint64_t context, uint64_t runner);
int aura_native_tensor_info(uint64_t context, uint64_t runner, unsigned output,
                            unsigned index, AuraTensorInfo* info);
int aura_native_optional_execute(uint64_t context, uint64_t runner,
    const void* input, uint64_t input_bytes, const AuraBuffer* outputs, unsigned count,
    uint64_t source_expires_ns, AuraNativeReport* report);
int aura_native_yolo_execute(uint64_t context,
    const unsigned char* bgr, int width, int height, int stride,
    float* output, int capacity, int class_id, int* count,
    uint64_t source_expires_ns, uint64_t primary_finish_ns, AuraNativeReport* report);
#ifdef __cplusplus
}
#endif
