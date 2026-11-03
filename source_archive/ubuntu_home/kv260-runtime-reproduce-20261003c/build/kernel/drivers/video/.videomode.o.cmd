cmd_drivers/video/videomode.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,drivers/video/.videomode.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include -I./include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret+leaf+bti -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wimplicit-fallthrough=5 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -g -fpatchable-function-entry=2 -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1016 -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/video -I ./drivers/video    -DKBUILD_MODFILE='"drivers/video/videomode"' -DKBUILD_BASENAME='"videomode"' -DKBUILD_MODNAME='"videomode"' -D__KBUILD_MODNAME=kmod_videomode -c -o drivers/video/videomode.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/video/videomode.c

source_drivers/video/videomode.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/video/videomode.c

deps_drivers/video/videomode.o := \
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
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/errno.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/errno.h \
  arch/arm64/include/generated/uapi/asm/errno.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/errno.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/errno-base.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/MODULE_REL_CRCS) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/TRIM_UNUSED_KSYMS) \
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
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/video/display_timing.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/bitops.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/bits.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/bits.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/build_bug.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/typecheck.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/kernel.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/sysinfo.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/bitops.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/builtin-__ffs.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/builtin-ffs.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/builtin-__fls.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/builtin-fls.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/ffz.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/fls64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/find.h \
    $(wildcard include/config/GENERIC_FIND_FIRST_BIT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/sched.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/hweight.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/arch_hweight.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/const_hweight.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/atomic.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/atomic.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/atomic.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/barrier.h \
    $(wildcard include/config/ARM64_PSEUDO_NMI) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/barrier.h \
    $(wildcard include/config/SMP) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/cmpxchg.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/lse.h \
    $(wildcard include/config/ARM64_LSE_ATOMICS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/atomic_ll_sc.h \
    $(wildcard include/config/CC_HAS_K_CONSTRAINT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/stringify.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/atomic/atomic-long.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/atomic/atomic-instrumented.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/instrumented.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/instrumented-atomic.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/lock.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/instrumented-lock.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/non-atomic.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/le.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/byteorder.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/byteorder/little_endian.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/byteorder/little_endian.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/swab.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/swab.h \
  arch/arm64/include/generated/uapi/asm/swab.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/swab.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/byteorder/generic.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/video/videomode.h \

drivers/video/videomode.o: $(deps_drivers/video/videomode.o)

$(deps_drivers/video/videomode.o):
