cmd_lib/uuid.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,lib/.uuid.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include -I./include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret+leaf+bti -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wimplicit-fallthrough=5 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -g -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1016 -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/lib -I ./lib    -DKBUILD_MODFILE='"lib/uuid"' -DKBUILD_BASENAME='"uuid"' -DKBUILD_MODNAME='"uuid"' -D__KBUILD_MODNAME=kmod_uuid -c -o lib/uuid.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/lib/uuid.c

source_lib/uuid.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/lib/uuid.c

deps_lib/uuid.o := \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_types.h \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_attributes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-gcc.h \
    $(wildcard include/config/RETPOLINE) \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
    $(wildcard include/config/KCOV) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/compiler.h \
    $(wildcard include/config/CFI_CLANG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kernel.h \
    $(wildcard include/config/PREEMPT_VOLUNTARY) \
    $(wildcard include/config/PREEMPT_DYNAMIC) \
    $(wildcard include/config/PREEMPT_) \
    $(wildcard include/config/DEBUG_ATOMIC_SLEEP) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/MMU) \
    $(wildcard include/config/PROVE_LOCKING) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/FTRACE_MCOUNT_RECORD) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stdarg.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/align.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/const.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/const.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/const.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/limits.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/limits.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/types.h \
  arch/arm64/include/generated/uapi/asm/types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/int-ll64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/int-ll64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/bitsperlong.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitsperlong.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/bitsperlong.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/posix_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stddef.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/stddef.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/posix_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/posix_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/limits.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stringify.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/MODULE_REL_CRCS) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/TRIM_UNUSED_KSYMS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/STACK_VALIDATION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/rwonce.h \
    $(wildcard include/config/LTO) \
    $(wildcard include/config/AS_HAS_LDAPR) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/rwonce.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/linkage.h \
    $(wildcard include/config/ARM64_BTI_KERNEL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bitops.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bits.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/bits.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/build_bug.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/typecheck.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/kernel.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/sysinfo.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/bitops.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/builtin-__ffs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/builtin-ffs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/builtin-__fls.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/builtin-fls.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/ffz.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/fls64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/find.h \
    $(wildcard include/config/GENERIC_FIND_FIRST_BIT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/sched.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/hweight.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/arch_hweight.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/const_hweight.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/atomic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/atomic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/atomic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/barrier.h \
    $(wildcard include/config/ARM64_PSEUDO_NMI) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/barrier.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/cmpxchg.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/lse.h \
    $(wildcard include/config/ARM64_LSE_ATOMICS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/atomic_ll_sc.h \
    $(wildcard include/config/CC_HAS_K_CONSTRAINT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/atomic/atomic-arch-fallback.h \
    $(wildcard include/config/GENERIC_ATOMIC64) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/atomic/atomic-long.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/atomic/atomic-instrumented.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/instrumented.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/instrumented-atomic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/lock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/instrumented-lock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/non-atomic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/le.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/byteorder.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/byteorder/little_endian.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/byteorder/little_endian.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/swab.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/swab.h \
  arch/arm64/include/generated/uapi/asm/swab.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/swab.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/byteorder/generic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bitops/ext2-atomic-setbit.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kstrtox.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/log2.h \
    $(wildcard include/config/ARCH_HAS_ILOG2_U32) \
    $(wildcard include/config/ARCH_HAS_ILOG2_U64) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/math.h \
  arch/arm64/include/generated/asm/div64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/div64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/minmax.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/panic.h \
    $(wildcard include/config/PANIC_TIMEOUT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/printk.h \
    $(wildcard include/config/MESSAGE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_DEFAULT) \
    $(wildcard include/config/CONSOLE_LOGLEVEL_QUIET) \
    $(wildcard include/config/EARLY_PRINTK) \
    $(wildcard include/config/PRINTK) \
    $(wildcard include/config/PRINTK_INDEX) \
    $(wildcard include/config/DYNAMIC_DEBUG) \
    $(wildcard include/config/DYNAMIC_DEBUG_CORE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/init.h \
    $(wildcard include/config/STRICT_KERNEL_RWX) \
    $(wildcard include/config/STRICT_MODULE_RWX) \
    $(wildcard include/config/LTO_CLANG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kern_levels.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cache.h \
    $(wildcard include/config/ARCH_HAS_CACHE_LINE_SIZE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/cache.h \
    $(wildcard include/config/KASAN_HW_TAGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/cputype.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/sysreg.h \
    $(wildcard include/config/BROKEN_GAS_INST) \
    $(wildcard include/config/ARM64_PA_BITS_52) \
    $(wildcard include/config/ARM64_4K_PAGES) \
    $(wildcard include/config/ARM64_16K_PAGES) \
    $(wildcard include/config/ARM64_64K_PAGES) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kasan-tags.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/alternative.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/alternative-macros.h \
  arch/arm64/include/generated/asm/cpucaps.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/insn-def.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ratelimit_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/param.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/param.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/param.h \
    $(wildcard include/config/HZ) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/param.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/spinlock_types.h \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/spinlock_types_raw.h \
    $(wildcard include/config/DEBUG_SPINLOCK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/spinlock_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/qspinlock_types.h \
    $(wildcard include/config/NR_CPUS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/qrwlock_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/lockdep_types.h \
    $(wildcard include/config/PROVE_RAW_LOCK_NESTING) \
    $(wildcard include/config/PREEMPT_LOCK) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/LOCK_STAT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rwlock_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/once_lite.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/static_call_types.h \
    $(wildcard include/config/HAVE_STATIC_CALL) \
    $(wildcard include/config/HAVE_STATIC_CALL_INLINE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ctype.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/errno.h \
  arch/arm64/include/generated/uapi/asm/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/errno-base.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/uuid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/uuid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/string.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/string.h \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/random.h \
    $(wildcard include/config/ARCH_RANDOM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bug.h \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/BUG_ON_DATA_CORRUPTION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/bug.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/asm-bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/brk-imm.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/bug.h \
    $(wildcard include/config/BUG) \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/instrumentation.h \
    $(wildcard include/config/DEBUG_ENTRY) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/list.h \
    $(wildcard include/config/DEBUG_LIST) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/once.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/jump_label.h \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/random.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/ioctl.h \
  arch/arm64/include/generated/uapi/asm/ioctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/ioctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/ioctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqnr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/irqnr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/prandom.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/percpu.h \
    $(wildcard include/config/NEED_PER_CPU_EMBED_FIRST_CHUNK) \
    $(wildcard include/config/NEED_PER_CPU_PAGE_FIRST_CHUNK) \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/preempt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/thread_info.h \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/GENERIC_ENTRY) \
    $(wildcard include/config/HAVE_ARCH_WITHIN_STACK_FRAMES) \
    $(wildcard include/config/HARDENED_USERCOPY) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/restart_block.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/time64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/math64.h \
    $(wildcard include/config/ARCH_SUPPORTS_INT128) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/math64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/time64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/time.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/time_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/current.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/thread_info.h \
    $(wildcard include/config/ARM64_SW_TTBR0_PAN) \
    $(wildcard include/config/SHADOW_CALL_STACK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/memory.h \
    $(wildcard include/config/ARM64_VA_BITS) \
    $(wildcard include/config/KASAN_SHADOW_OFFSET) \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/EFI) \
    $(wildcard include/config/ARM_GIC_V3_ITS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sizes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/page-def.h \
    $(wildcard include/config/ARM64_PAGE_SHIFT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/SPARSEMEM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pfn.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/stack_pointer.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cpumask.h \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/threads.h \
    $(wildcard include/config/BASE_SMALL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bitmap.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/smp_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/smp.h \
    $(wildcard include/config/ARM64_ACPI_PARKING_PROTOCOL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/percpu.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/percpu.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/archrandom.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/arm-smccc.h \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/HAVE_ARM_SMCCC) \
    $(wildcard include/config/ARM) \
    $(wildcard include/config/ARM64_SVE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/cpufeature.h \
    $(wildcard include/config/ARM64_PAN) \
    $(wildcard include/config/ARM64_CNP) \
    $(wildcard include/config/ARM64_PTR_AUTH) \
    $(wildcard include/config/ARM64_MTE) \
    $(wildcard include/config/ARM64_DEBUG_PRIORITY_MASKING) \
    $(wildcard include/config/ARM64_BTI) \
    $(wildcard include/config/ARM64_TLB_RANGE) \
    $(wildcard include/config/ARM64_PA_BITS) \
    $(wildcard include/config/ARM64_HW_AFDBM) \
    $(wildcard include/config/ARM64_AMU_EXTN) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/hwcap.h \
    $(wildcard include/config/COMPAT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/hwcap.h \

lib/uuid.o: $(deps_lib/uuid.o)

$(deps_lib/uuid.o):
