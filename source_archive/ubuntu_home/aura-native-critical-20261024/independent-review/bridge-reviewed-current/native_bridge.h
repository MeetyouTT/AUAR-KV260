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
} AuraNativeReport;
typedef struct {
  uint32_t rank;
  int32_t dims[8];
  int32_t fix_point;
  uint64_t bytes;
  char name[256];
} AuraTensorInfo;
typedef struct { void* data; uint64_t bytes; } AuraBuffer;
uint32_t aura_native_abi(void);
uint32_t aura_native_report_size(void);
const char* aura_native_error(void);
// Creation requires the existing owner's /run/aura-person-dpu.lock FD.
// Isolation build/check must not call either context or runner factories.
uint64_t aura_native_context_create(int owner_fd, const char* existing_yolo_library);
int aura_native_context_close(uint64_t context);
int aura_native_announce_primary(uint64_t context, uint64_t deadline_ns);
uint64_t aura_native_runner_create(uint64_t context, unsigned task, const char* xmodel);
int aura_native_runner_close(uint64_t context, uint64_t runner);
int aura_native_tensor_info(uint64_t context, uint64_t runner, unsigned output,
                            unsigned index, AuraTensorInfo* info);
int aura_native_optional_execute(uint64_t context, uint64_t runner,
    const void* input, uint64_t input_bytes, const AuraBuffer* outputs, unsigned count,
    uint64_t source_expires_ns, AuraNativeReport* report);
int aura_native_yolo_execute(uint64_t context, void* existing_detector,
    const unsigned char* bgr, int width, int height, int stride,
    float* output, int capacity, int class_id, int* count,
    uint64_t source_expires_ns, uint64_t primary_finish_ns, AuraNativeReport* report);
#ifdef __cplusplus
}
#endif
