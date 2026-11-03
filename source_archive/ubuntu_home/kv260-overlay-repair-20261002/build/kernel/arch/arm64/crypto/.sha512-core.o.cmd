cmd_arch/arm64/crypto/sha512-core.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,arch/arm64/crypto/.sha512-core.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include -I./include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/= -D__ASSEMBLY__ -fno-PIE -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -DKASAN_SHADOW_SCALE_SHIFT= -Wa,-gdwarf-2 -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/crypto -I ./arch/arm64/crypto    -c -o arch/arm64/crypto/sha512-core.o arch/arm64/crypto/sha512-core.S

source_arch/arm64/crypto/sha512-core.o := arch/arm64/crypto/sha512-core.S

deps_arch/arm64/crypto/sha512-core.o := \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \

arch/arm64/crypto/sha512-core.o: $(deps_arch/arm64/crypto/sha512-core.o)

$(deps_arch/arm64/crypto/sha512-core.o):
