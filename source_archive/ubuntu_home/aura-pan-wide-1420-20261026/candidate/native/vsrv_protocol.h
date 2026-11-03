#ifndef AURA_VSRV_PROTOCOL_H
#define AURA_VSRV_PROTOCOL_H
#include <stdint.h>
#define VSRV_ABI 2u
#ifndef VSRV_BUILD_ID
#define VSRV_BUILD_ID 0x14202602u
#endif
#if VSRV_BUILD_ID == 0
#error An assigned candidate build identity is required
#endif
#define VSRV_FW "aura-visual-servo-b4096-wide1420-v1.bit.bin"
#define VSRV_QUIESCE 0x51554945u
static inline int vsrv_valid_command(uint32_t value) {
    return value == 0x42494e44u || value == 0x52454621u || value == 0x41524d21u ||
           value == 0x434d5421u || value == 0x53544f50u || value == VSRV_QUIESCE;
}
#endif
