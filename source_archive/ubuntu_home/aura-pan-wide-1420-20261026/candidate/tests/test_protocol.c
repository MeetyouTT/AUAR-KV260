#include <assert.h>
#include <stdio.h>
#include "vsrv_protocol.h"
int main(void) {
    const uint32_t allowed[] = {0x42494e44u,0x52454621u,0x41524d21u,0x434d5421u,0x53544f50u,0x51554945u};
    for (unsigned i=0;i<sizeof(allowed)/sizeof(allowed[0]);i++) assert(vsrv_valid_command(allowed[i]));
    const uint32_t rejected[] = {0,1,0xffffffffu,0x51554944u,0x51554946u,0x53544f51u};
    for (unsigned i=0;i<sizeof(rejected)/sizeof(rejected[0]);i++) assert(!vsrv_valid_command(rejected[i]));
    assert(VSRV_ABI==2 && VSRV_BUILD_ID==0x14202602u);
    puts("VSRV2_NATIVE_PROTOCOL_WHITELIST_PASS_NO_MMIO");
    return 0;
}
