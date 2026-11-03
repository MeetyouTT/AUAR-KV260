cmd_arch/arm64/kernel/vdso/vdso.lds := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -E -Wp,-MMD,arch/arm64/kernel/vdso/.vdso.lds.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include -I./include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/=    -P -C -Uarm64 -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vdso -I ./arch/arm64/kernel/vdso -P -Uarm64 -D__ASSEMBLY__ -DLINKER_SCRIPT -o arch/arm64/kernel/vdso/vdso.lds /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vdso/vdso.lds.S

source_arch/arm64/kernel/vdso/vdso.lds := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vdso/vdso.lds.S

deps_arch/arm64/kernel/vdso/vdso.lds := \
    $(wildcard include/config/TIME_NS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/page.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/page-def.h \
    $(wildcard include/config/ARM64_PAGE_SHIFT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/getorder.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/vdso.h \
    $(wildcard include/config/COMPAT_VDSO) \

arch/arm64/kernel/vdso/vdso.lds: $(deps_arch/arm64/kernel/vdso/vdso.lds)

$(deps_arch/arm64/kernel/vdso/vdso.lds):
