cmd_scripts/module.lds := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -E -Wp,-MMD,scripts/.module.lds.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include -I./include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/=     -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts -I ./scripts -P -Uarm64 -D__ASSEMBLY__ -DLINKER_SCRIPT -o scripts/module.lds /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/module.lds.S

source_scripts/module.lds := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/module.lds.S

deps_scripts/module.lds := \
    $(wildcard include/config/CFI_CLANG) \
    $(wildcard include/config/LTO_CLANG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/module.lds.h \
    $(wildcard include/config/ARM64_MODULE_PLTS) \
    $(wildcard include/config/KASAN_SW_TAGS) \

scripts/module.lds: $(deps_scripts/module.lds)

$(deps_scripts/module.lds):
