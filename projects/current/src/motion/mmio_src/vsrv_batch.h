#ifndef AURA_VSRV_BATCH_H
#define AURA_VSRV_BATCH_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* count 1..32; readable offsets only. errno-style result, output unchanged on failure. */
int vsrv_read_many(void *opaque,const unsigned *offsets,unsigned count,uint32_t *results);
/* ID ABI BUILD ACK FLAGS WIDTH LEASE SESSION EPOCH REFERENCE TARGET ACK */
int vsrv_snapshot(void *opaque,uint32_t *results);
#ifdef __cplusplus
}
#endif
#endif
