cmd_arch/arm64/kernel/vdso/vgettimeofday.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,arch/arm64/kernel/vdso/.vgettimeofday.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include -I./include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret+leaf+bti -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wimplicit-fallthrough=5 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -g -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1016 -fno-common -fno-builtin -fno-stack-protector -ffixed-x18 -DDISABLE_BRANCH_PROFILING -DBUILD_VDSO -O2 -mcmodel=tiny -fasynchronous-unwind-tables -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/lib/vdso/gettimeofday.c -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vdso -I ./arch/arm64/kernel/vdso    -DKBUILD_MODFILE='"arch/arm64/kernel/vdso/vgettimeofday"' -DKBUILD_BASENAME='"vgettimeofday"' -DKBUILD_MODNAME='"vgettimeofday"' -D__KBUILD_MODNAME=kmod_vgettimeofday -c -o arch/arm64/kernel/vdso/vgettimeofday.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vdso/vgettimeofday.c

source_arch/arm64/kernel/vdso/vgettimeofday.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vdso/vgettimeofday.c

deps_arch/arm64/kernel/vdso/vgettimeofday.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler_types.h \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler_attributes.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-gcc.h \
    $(wildcard include/config/RETPOLINE) \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
    $(wildcard include/config/KCOV) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/compiler.h \
    $(wildcard include/config/CFI_CLANG) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/lib/vdso/gettimeofday.c \
    $(wildcard include/config/TIME_NS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/datapage.h \
    $(wildcard include/config/ARCH_HAS_VDSO_DATA) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/STACK_VALIDATION) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler_types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/rwonce.h \
    $(wildcard include/config/LTO) \
    $(wildcard include/config/AS_HAS_LDAPR) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/rwonce.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/types.h \
  arch/arm64/include/generated/uapi/asm/types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/int-ll64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/int-ll64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/bitsperlong.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitsperlong.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/bitsperlong.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/posix_types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/stddef.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/stddef.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/posix_types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/posix_types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/time.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/time_types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/errno-base.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/bits.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/clocksource.h \
    $(wildcard include/config/GENERIC_GETTIMEOFDAY) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/limits.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/vdso/clocksource.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/ktime.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/jiffies.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/param.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/param.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/time64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/math64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/processor.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/vdso/processor.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/time.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/time32.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/vdso/gettimeofday.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/barrier.h \
    $(wildcard include/config/ARM64_PSEUDO_NMI) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/barrier.h \
    $(wildcard include/config/SMP) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/unistd.h \
    $(wildcard include/config/COMPAT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/unistd.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/unistd.h \
    $(wildcard include/config/MMU) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/helpers.h \

arch/arm64/kernel/vdso/vgettimeofday.o: $(deps_arch/arm64/kernel/vdso/vgettimeofday.o)

$(deps_arch/arm64/kernel/vdso/vgettimeofday.o):
