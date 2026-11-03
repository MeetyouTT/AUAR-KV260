cmd_drivers/spi/spi.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,drivers/spi/.spi.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include -I./include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret+leaf+bti -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wimplicit-fallthrough=5 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -g -fpatchable-function-entry=2 -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1016 -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/spi -I ./drivers/spi    -DKBUILD_MODFILE='"drivers/spi/spi"' -DKBUILD_BASENAME='"spi"' -DKBUILD_MODNAME='"spi"' -D__KBUILD_MODNAME=kmod_spi -c -o drivers/spi/spi.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/spi/spi.c

source_drivers/spi/spi.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/spi/spi.c

deps_drivers/spi/spi.o := \
    $(wildcard include/config/SPI_DYNAMIC) \
    $(wildcard include/config/HAS_DMA) \
    $(wildcard include/config/HIGHMEM) \
    $(wildcard include/config/OF) \
    $(wildcard include/config/ACPI) \
    $(wildcard include/config/SPI_SLAVE) \
    $(wildcard include/config/OF_DYNAMIC) \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/device.h \
    $(wildcard include/config/ENERGY_MODEL) \
    $(wildcard include/config/GENERIC_MSI_IRQ_DOMAIN) \
    $(wildcard include/config/PINCTRL) \
    $(wildcard include/config/GENERIC_MSI_IRQ) \
    $(wildcard include/config/DMA_OPS) \
    $(wildcard include/config/DMA_DECLARE_COHERENT) \
    $(wildcard include/config/DMA_CMA) \
    $(wildcard include/config/SWIOTLB) \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_DEVICE) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_CPU) \
    $(wildcard include/config/ARCH_HAS_SYNC_DMA_FOR_CPU_ALL) \
    $(wildcard include/config/DMA_OPS_BYPASS) \
    $(wildcard include/config/PM_SLEEP) \
    $(wildcard include/config/DEVTMPFS) \
    $(wildcard include/config/SYSFS_DEPRECATED) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dev_printk.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ratelimit.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_NATIVE) \
    $(wildcard include/config/SCHED_INFO) \
    $(wildcard include/config/SCHEDSTATS) \
    $(wildcard include/config/FAIR_GROUP_SCHED) \
    $(wildcard include/config/RT_GROUP_SCHED) \
    $(wildcard include/config/RT_MUTEXES) \
    $(wildcard include/config/UCLAMP_TASK) \
    $(wildcard include/config/UCLAMP_BUCKETS_COUNT) \
    $(wildcard include/config/KMAP_LOCAL) \
    $(wildcard include/config/THREAD_INFO_IN_TASK) \
    $(wildcard include/config/SCHED_CORE) \
    $(wildcard include/config/CGROUP_SCHED) \
    $(wildcard include/config/PREEMPT_NOTIFIERS) \
    $(wildcard include/config/BLK_DEV_IO_TRACE) \
    $(wildcard include/config/PREEMPT_RCU) \
    $(wildcard include/config/TASKS_RCU) \
    $(wildcard include/config/TASKS_TRACE_RCU) \
    $(wildcard include/config/PSI) \
    $(wildcard include/config/MEMCG) \
    $(wildcard include/config/COMPAT_BRK) \
    $(wildcard include/config/CGROUPS) \
    $(wildcard include/config/BLK_CGROUP) \
    $(wildcard include/config/PAGE_OWNER) \
    $(wildcard include/config/EVENTFD) \
    $(wildcard include/config/STACKPROTECTOR) \
    $(wildcard include/config/ARCH_HAS_SCALED_CPUTIME) \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING_GEN) \
    $(wildcard include/config/NO_HZ_FULL) \
    $(wildcard include/config/POSIX_CPUTIMERS) \
    $(wildcard include/config/POSIX_CPU_TIMERS_TASK_WORK) \
    $(wildcard include/config/KEYS) \
    $(wildcard include/config/SYSVIPC) \
    $(wildcard include/config/DETECT_HUNG_TASK) \
    $(wildcard include/config/IO_URING) \
    $(wildcard include/config/AUDIT) \
    $(wildcard include/config/AUDITSYSCALL) \
    $(wildcard include/config/DEBUG_MUTEXES) \
    $(wildcard include/config/TRACE_IRQFLAGS) \
    $(wildcard include/config/UBSAN) \
    $(wildcard include/config/UBSAN_TRAP) \
    $(wildcard include/config/BLOCK) \
    $(wildcard include/config/COMPACTION) \
    $(wildcard include/config/TASK_XACCT) \
    $(wildcard include/config/CPUSETS) \
    $(wildcard include/config/X86_CPU_RESCTRL) \
    $(wildcard include/config/FUTEX) \
    $(wildcard include/config/COMPAT) \
    $(wildcard include/config/PERF_EVENTS) \
    $(wildcard include/config/DEBUG_PREEMPT) \
    $(wildcard include/config/NUMA_BALANCING) \
    $(wildcard include/config/RSEQ) \
    $(wildcard include/config/TASK_DELAY_ACCT) \
    $(wildcard include/config/FAULT_INJECTION) \
    $(wildcard include/config/LATENCYTOP) \
    $(wildcard include/config/KUNIT) \
    $(wildcard include/config/FUNCTION_GRAPH_TRACER) \
    $(wildcard include/config/UPROBES) \
    $(wildcard include/config/BCACHE) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/LIVEPATCH) \
    $(wildcard include/config/SECURITY) \
    $(wildcard include/config/BPF_SYSCALL) \
    $(wildcard include/config/GCC_PLUGIN_STACKLEAK) \
    $(wildcard include/config/X86_MCE) \
    $(wildcard include/config/KRETPROBES) \
    $(wildcard include/config/ARCH_HAS_PARANOID_L1D_FLUSH) \
    $(wildcard include/config/ARCH_TASK_STRUCT_ON_STACK) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/DEBUG_RSEQ) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/sched.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/current.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rculist.h \
    $(wildcard include/config/PROVE_RCU_LIST) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/list.h \
    $(wildcard include/config/DEBUG_LIST) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/poison.h \
    $(wildcard include/config/ILLEGAL_POINTER_VALUE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rcupdate.h \
    $(wildcard include/config/TINY_RCU) \
    $(wildcard include/config/TASKS_RCU_GENERIC) \
    $(wildcard include/config/RCU_STALL_COMMON) \
    $(wildcard include/config/RCU_NOCB_CPU) \
    $(wildcard include/config/TASKS_RUDE_RCU) \
    $(wildcard include/config/TREE_RCU) \
    $(wildcard include/config/DEBUG_OBJECTS_RCU_HEAD) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/PROVE_RCU) \
    $(wildcard include/config/ARCH_WEAK_RELEASE_ACQUIRE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqflags.h \
    $(wildcard include/config/IRQSOFF_TRACER) \
    $(wildcard include/config/PREEMPT_TRACER) \
    $(wildcard include/config/DEBUG_IRQFLAGS) \
    $(wildcard include/config/TRACE_IRQFLAGS_SUPPORT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/irqflags.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/ptrace.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/cpufeature.h \
    $(wildcard include/config/ARM64_PAN) \
    $(wildcard include/config/ARM64_SW_TTBR0_PAN) \
    $(wildcard include/config/ARM64_SVE) \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/hwcap.h \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/jump_label.h \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/HAVE_ARCH_JUMP_LABEL_RELATIVE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/ptrace.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/sve_context.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/percpu.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/preempt.h \
    $(wildcard include/config/PREEMPT_COUNT) \
    $(wildcard include/config/TRACE_PREEMPT_TOGGLE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/preempt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/thread_info.h \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/errno.h \
  arch/arm64/include/generated/uapi/asm/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/errno-base.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/thread_info.h \
    $(wildcard include/config/SHADOW_CALL_STACK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/memory.h \
    $(wildcard include/config/ARM64_VA_BITS) \
    $(wildcard include/config/KASAN_SHADOW_OFFSET) \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/EFI) \
    $(wildcard include/config/ARM_GIC_V3_ITS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sizes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/page-def.h \
    $(wildcard include/config/ARM64_PAGE_SHIFT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mmdebug.h \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/DEBUG_VM_PGFLAGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/SPARSEMEM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pfn.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/stack_pointer.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/percpu.h \
    $(wildcard include/config/HAVE_SETUP_PER_CPU_AREA) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/threads.h \
    $(wildcard include/config/BASE_SMALL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/percpu-defs.h \
    $(wildcard include/config/DEBUG_FORCE_WEAK_PER_CPU) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bottom_half.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/lockdep.h \
    $(wildcard include/config/DEBUG_LOCKING_API_SELFTESTS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/smp.h \
    $(wildcard include/config/UP_LATE_INIT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cpumask.h \
    $(wildcard include/config/CPUMASK_OFFSTACK) \
    $(wildcard include/config/DEBUG_PER_CPU_MAPS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bitmap.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/string.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/string.h \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/smp_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/llist.h \
    $(wildcard include/config/ARCH_HAVE_NMI_SAFE_CMPXCHG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/smp.h \
    $(wildcard include/config/ARM64_ACPI_PARKING_PROTOCOL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/processor.h \
    $(wildcard include/config/KUSER_HELPERS) \
    $(wildcard include/config/ARM64_FORCE_52BIT) \
    $(wildcard include/config/HAVE_HW_BREAKPOINT) \
    $(wildcard include/config/ARM64_PTR_AUTH_KERNEL) \
    $(wildcard include/config/ARM64_TAGGED_ADDR_ABI) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/processor.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/vdso/processor.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/hw_breakpoint.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/virt.h \
    $(wildcard include/config/KVM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/sections.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/sections.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/kasan.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/mte-kasan.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/mte-def.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/pgtable-types.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/pgtable-nop4d.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/pgtable-hwdef.h \
    $(wildcard include/config/ARM64_CONT_PTE_SHIFT) \
    $(wildcard include/config/ARM64_CONT_PMD_SHIFT) \
    $(wildcard include/config/ARM64_VA_BITS_52) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/pointer_auth.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/prctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/random.h \
    $(wildcard include/config/ARCH_RANDOM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/once.h \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/archrandom.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/arm-smccc.h \
    $(wildcard include/config/ARM64) \
    $(wildcard include/config/HAVE_ARM_SMCCC) \
    $(wildcard include/config/ARM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/spectre.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/fpsimd.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/sigcontext.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rcutree.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/wait.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/spinlock.h \
  arch/arm64/include/generated/asm/mmiowb.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/mmiowb.h \
    $(wildcard include/config/MMIOWB) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/spinlock.h \
  arch/arm64/include/generated/asm/qspinlock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/qspinlock.h \
  arch/arm64/include/generated/asm/qrwlock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/qrwlock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rwlock.h \
    $(wildcard include/config/PREEMPT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/spinlock_api_smp.h \
    $(wildcard include/config/INLINE_SPIN_LOCK) \
    $(wildcard include/config/INLINE_SPIN_LOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK) \
    $(wildcard include/config/INLINE_SPIN_TRYLOCK_BH) \
    $(wildcard include/config/UNINLINE_SPIN_UNLOCK) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_BH) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_SPIN_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/GENERIC_LOCKBREAK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rwlock_api_smp.h \
    $(wildcard include/config/INLINE_READ_LOCK) \
    $(wildcard include/config/INLINE_WRITE_LOCK) \
    $(wildcard include/config/INLINE_READ_LOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_LOCK_BH) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_WRITE_LOCK_IRQSAVE) \
    $(wildcard include/config/INLINE_READ_TRYLOCK) \
    $(wildcard include/config/INLINE_WRITE_TRYLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK) \
    $(wildcard include/config/INLINE_READ_UNLOCK_BH) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_BH) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQ) \
    $(wildcard include/config/INLINE_READ_UNLOCK_IRQRESTORE) \
    $(wildcard include/config/INLINE_WRITE_UNLOCK_IRQRESTORE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/wait.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/refcount.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sem.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/sem.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ipc.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/uidgid.h \
    $(wildcard include/config/MULTIUSER) \
    $(wildcard include/config/USER_NS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/highuid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rhashtable-types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mutex.h \
    $(wildcard include/config/MUTEX_SPIN_ON_OWNER) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/osq_lock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/debug_locks.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/workqueue.h \
    $(wildcard include/config/DEBUG_OBJECTS_WORK) \
    $(wildcard include/config/FREEZER) \
    $(wildcard include/config/SYSFS) \
    $(wildcard include/config/WQ_WATCHDOG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/timer.h \
    $(wildcard include/config/DEBUG_OBJECTS_TIMERS) \
    $(wildcard include/config/NO_HZ_COMMON) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ktime.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/time.h \
    $(wildcard include/config/POSIX_TIMERS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/time32.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/timex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/timex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/timex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/arch_timer.h \
    $(wildcard include/config/ARM_ARCH_TIMER_OOL_WORKAROUND) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/clocksource/arm_arch_timer.h \
    $(wildcard include/config/ARM_ARCH_TIMER) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/timecounter.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/timex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/time32.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/time.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/jiffies.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/jiffies.h \
  include/generated/timeconst.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/vdso/ktime.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/timekeeping.h \
    $(wildcard include/config/GENERIC_CMOS_UPDATE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/clocksource_ids.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/debugobjects.h \
    $(wildcard include/config/DEBUG_OBJECTS) \
    $(wildcard include/config/DEBUG_OBJECTS_FREE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/ipc.h \
  arch/arm64/include/generated/uapi/asm/ipcbuf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/ipcbuf.h \
  arch/arm64/include/generated/uapi/asm/sembuf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/sembuf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/shm.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/page.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/personality.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/personality.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/getorder.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/shm.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/hugetlb_encode.h \
  arch/arm64/include/generated/uapi/asm/shmbuf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/shmbuf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/shmparam.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/shmparam.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/plist.h \
    $(wildcard include/config/DEBUG_PLIST) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/hrtimer.h \
    $(wildcard include/config/HIGH_RES_TIMERS) \
    $(wildcard include/config/TIME_LOW_RES) \
    $(wildcard include/config/TIMERFD) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/hrtimer_defs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rbtree.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rbtree_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/seqlock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ww_mutex.h \
    $(wildcard include/config/DEBUG_RT_MUTEXES) \
    $(wildcard include/config/DEBUG_WW_MUTEX_SLOWPATH) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rtmutex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/timerqueue.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/seccomp.h \
    $(wildcard include/config/SECCOMP) \
    $(wildcard include/config/HAVE_ARCH_SECCOMP_FILTER) \
    $(wildcard include/config/SECCOMP_FILTER) \
    $(wildcard include/config/CHECKPOINT_RESTORE) \
    $(wildcard include/config/SECCOMP_CACHE_DEBUG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/seccomp.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/seccomp.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/unistd.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/unistd.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/unistd.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/seccomp.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/unistd.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/nodemask.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/numa.h \
    $(wildcard include/config/NODES_SHIFT) \
    $(wildcard include/config/NUMA_KEEP_MEMINFO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/resource.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/resource.h \
  arch/arm64/include/generated/uapi/asm/resource.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/resource.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/resource.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/latencytop.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/prio.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/signal_types.h \
    $(wildcard include/config/OLD_SIGACTION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/signal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/signal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/signal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/signal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/signal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/signal-defs.h \
  arch/arm64/include/generated/uapi/asm/siginfo.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/siginfo.h \
  arch/arm64/include/generated/uapi/asm/siginfo.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/syscall_user_dispatch.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mm_types_task.h \
    $(wildcard include/config/ARCH_WANT_BATCHED_UNMAP_TLB_FLUSH) \
    $(wildcard include/config/SPLIT_PTLOCK_CPUS) \
    $(wildcard include/config/ARCH_ENABLE_SPLIT_PMD_PTLOCK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/task_io_accounting.h \
    $(wildcard include/config/TASK_IO_ACCOUNTING) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/posix-timers.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/alarmtimer.h \
    $(wildcard include/config/RTC_CLASS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/task_work.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/rseq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kcsan.h \
  arch/arm64/include/generated/asm/kmap_size.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/kmap_size.h \
    $(wildcard include/config/DEBUG_KMAP_LOCAL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/energy_model.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kobject.h \
    $(wildcard include/config/UEVENT_HELPER) \
    $(wildcard include/config/DEBUG_KOBJECT_RELEASE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sysfs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kernfs.h \
    $(wildcard include/config/KERNFS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/err.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/idr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/radix-tree.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/xarray.h \
    $(wildcard include/config/XARRAY_MULTI) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/gfp.h \
    $(wildcard include/config/ZONE_DMA) \
    $(wildcard include/config/ZONE_DMA32) \
    $(wildcard include/config/ZONE_DEVICE) \
    $(wildcard include/config/CONTIG_ALLOC) \
    $(wildcard include/config/CMA) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mmzone.h \
    $(wildcard include/config/FORCE_MAX_ZONEORDER) \
    $(wildcard include/config/MEMORY_ISOLATION) \
    $(wildcard include/config/ZSMALLOC) \
    $(wildcard include/config/SWAP) \
    $(wildcard include/config/TRANSPARENT_HUGEPAGE) \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/PAGE_EXTENSION) \
    $(wildcard include/config/DEFERRED_STRUCT_PAGE_INIT) \
    $(wildcard include/config/HAVE_MEMORYLESS_NODES) \
    $(wildcard include/config/SPARSEMEM_EXTREME) \
    $(wildcard include/config/HAVE_ARCH_PFN_VALID) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pageblock-flags.h \
    $(wildcard include/config/HUGETLB_PAGE) \
    $(wildcard include/config/HUGETLB_PAGE_SIZE_VARIABLE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/page-flags-layout.h \
  include/generated/bounds.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/sparsemem.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mm_types.h \
    $(wildcard include/config/HAVE_ALIGNED_STRUCT_PAGE) \
    $(wildcard include/config/USERFAULTFD) \
    $(wildcard include/config/HAVE_ARCH_COMPAT_MMAP_BASES) \
    $(wildcard include/config/MEMBARRIER) \
    $(wildcard include/config/AIO) \
    $(wildcard include/config/MMU_NOTIFIER) \
    $(wildcard include/config/IOMMU_SUPPORT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/auxvec.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/auxvec.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/auxvec.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rwsem.h \
    $(wildcard include/config/RWSEM_SPIN_ON_OWNER) \
    $(wildcard include/config/DEBUG_RWSEMS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/completion.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/swait.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/uprobes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/uprobes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/debug-monitors.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/esr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/insn.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/probes.h \
    $(wildcard include/config/KPROBES) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/mmu.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/page-flags.h \
    $(wildcard include/config/ARCH_USES_PG_UNCACHED) \
    $(wildcard include/config/MEMORY_FAILURE) \
    $(wildcard include/config/PAGE_IDLE_FLAG) \
    $(wildcard include/config/THP_SWAP) \
    $(wildcard include/config/KSM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/local_lock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/local_lock_internal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/memory_hotplug.h \
    $(wildcard include/config/ARCH_HAS_ADD_PAGES) \
    $(wildcard include/config/HAVE_ARCH_NODEDATA_EXTENSION) \
    $(wildcard include/config/MEMORY_HOTREMOVE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/notifier.h \
    $(wildcard include/config/TREE_SRCU) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/srcu.h \
    $(wildcard include/config/TINY_SRCU) \
    $(wildcard include/config/SRCU) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rcu_segcblist.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/srcutree.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rcu_node_tree.h \
    $(wildcard include/config/RCU_FANOUT) \
    $(wildcard include/config/RCU_FANOUT_LEAF) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/topology.h \
    $(wildcard include/config/USE_PERCPU_NUMA_NODE_ID) \
    $(wildcard include/config/SCHED_SMT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/arch_topology.h \
    $(wildcard include/config/GENERIC_ARCH_TOPOLOGY) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/topology.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/topology.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kobject_ns.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/stat.h \
  arch/arm64/include/generated/uapi/asm/stat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/stat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/compat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/compat.h \
    $(wildcard include/config/COMPAT_FOR_U64_ALIGNMENT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/task_stack.h \
    $(wildcard include/config/STACK_GROWSUP) \
    $(wildcard include/config/DEBUG_STACK_USAGE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/magic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/stat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kref.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/cpufreq.h \
    $(wildcard include/config/CPU_FREQ) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/topology.h \
    $(wildcard include/config/SCHED_DEBUG) \
    $(wildcard include/config/SCHED_MC) \
    $(wildcard include/config/CPU_FREQ_GOV_SCHEDUTIL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/idle.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/sd_flags.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ioport.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/klist.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pm.h \
    $(wildcard include/config/VT_CONSOLE_SLEEP) \
    $(wildcard include/config/PM) \
    $(wildcard include/config/PM_CLK) \
    $(wildcard include/config/PM_GENERIC_DOMAINS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/overflow.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/device/bus.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/device/class.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/device/driver.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/device.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pm_wakeup.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dma-mapping.h \
    $(wildcard include/config/DMA_API_DEBUG) \
    $(wildcard include/config/NEED_DMA_MAP_STATE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dma-direction.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/scatterlist.h \
    $(wildcard include/config/NEED_SG_DMA_LENGTH) \
    $(wildcard include/config/DEBUG_SG) \
    $(wildcard include/config/SGL_ALLOC) \
    $(wildcard include/config/ARCH_NO_SG_CHAIN) \
    $(wildcard include/config/SG_POOL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mm.h \
    $(wildcard include/config/SYSCTL) \
    $(wildcard include/config/HAVE_ARCH_MMAP_RND_BITS) \
    $(wildcard include/config/HAVE_ARCH_MMAP_RND_COMPAT_BITS) \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/MEM_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_USES_HIGH_VMA_FLAGS) \
    $(wildcard include/config/ARCH_HAS_PKEYS) \
    $(wildcard include/config/PPC) \
    $(wildcard include/config/X86) \
    $(wildcard include/config/PARISC) \
    $(wildcard include/config/IA64) \
    $(wildcard include/config/SPARC64) \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_MINOR) \
    $(wildcard include/config/SHMEM) \
    $(wildcard include/config/DEV_PAGEMAP_OPS) \
    $(wildcard include/config/DEVICE_PRIVATE) \
    $(wildcard include/config/PCI_P2PDMA) \
    $(wildcard include/config/MIGRATION) \
    $(wildcard include/config/ARCH_HAS_PTE_SPECIAL) \
    $(wildcard include/config/ARCH_HAS_PTE_DEVMAP) \
    $(wildcard include/config/DEBUG_VM_RB) \
    $(wildcard include/config/PAGE_POISONING) \
    $(wildcard include/config/INIT_ON_ALLOC_DEFAULT_ON) \
    $(wildcard include/config/INIT_ON_FREE_DEFAULT_ON) \
    $(wildcard include/config/DEBUG_PAGEALLOC) \
    $(wildcard include/config/HUGETLBFS) \
    $(wildcard include/config/MAPPING_DIRTY_HELPERS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mmap_lock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/tracepoint-defs.h \
    $(wildcard include/config/TRACEPOINTS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/static_key.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/range.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/percpu-refcount.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bit_spinlock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/shrinker.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/page_ext.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stacktrace.h \
    $(wildcard include/config/STACKTRACE) \
    $(wildcard include/config/ARCH_STACKWALK) \
    $(wildcard include/config/HAVE_RELIABLE_STACKTRACE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stackdepot.h \
    $(wildcard include/config/STACKDEPOT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/page_ref.h \
    $(wildcard include/config/DEBUG_PAGE_REF) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/memremap.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pgtable.h \
    $(wildcard include/config/HIGHPTE) \
    $(wildcard include/config/GUP_GET_PTE_LOW_HIGH) \
    $(wildcard include/config/HAVE_ARCH_TRANSPARENT_HUGEPAGE_PUD) \
    $(wildcard include/config/HAVE_ARCH_SOFT_DIRTY) \
    $(wildcard include/config/ARCH_ENABLE_THP_MIGRATION) \
    $(wildcard include/config/HAVE_ARCH_HUGE_VMAP) \
    $(wildcard include/config/X86_ESPFIX64) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/pgtable.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/proc-fns.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/mte.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bitfield.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/pgtable-prot.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/tlbflush.h \
    $(wildcard include/config/ARM64_WORKAROUND_REPEAT_TLBI) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/fixmap.h \
    $(wildcard include/config/ACPI_APEI_GHES) \
    $(wildcard include/config/ARM_SDE_INTERFACE) \
    $(wildcard include/config/UNMAP_KERNEL_AT_EL0) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/boot.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/fixmap.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/pgtable_uffd.h \
    $(wildcard include/config/HAVE_ARCH_USERFAULTFD_WP) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kasan.h \
    $(wildcard include/config/KASAN_STACK) \
    $(wildcard include/config/KASAN_VMALLOC) \
    $(wildcard include/config/KASAN_INLINE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/huge_mm.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/coredump.h \
    $(wildcard include/config/CORE_DUMP_DEFAULT_ELF_HEADERS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/fs.h \
    $(wildcard include/config/READ_ONLY_THP_FOR_FS) \
    $(wildcard include/config/FS_POSIX_ACL) \
    $(wildcard include/config/CGROUP_WRITEBACK) \
    $(wildcard include/config/IMA) \
    $(wildcard include/config/FILE_LOCKING) \
    $(wildcard include/config/FSNOTIFY) \
    $(wildcard include/config/FS_ENCRYPTION) \
    $(wildcard include/config/FS_VERITY) \
    $(wildcard include/config/EPOLL) \
    $(wildcard include/config/UNICODE) \
    $(wildcard include/config/QUOTA) \
    $(wildcard include/config/FS_DAX) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/wait_bit.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kdev_t.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/kdev_t.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dcache.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rculist_bl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/list_bl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/lockref.h \
    $(wildcard include/config/ARCH_USE_CMPXCHG_LOCKREF) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stringhash.h \
    $(wildcard include/config/DCACHE_WORD_ACCESS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/hash.h \
    $(wildcard include/config/HAVE_ARCH_HASH) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/path.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/list_lru.h \
    $(wildcard include/config/MEMCG_KMEM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/capability.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/capability.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/semaphore.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/fcntl.h \
    $(wildcard include/config/ARCH_32BIT_OFF_T) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/fcntl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/fcntl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/fcntl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/openat2.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/migrate_mode.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/percpu-rwsem.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rcuwait.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/signal.h \
    $(wildcard include/config/SCHED_AUTOGROUP) \
    $(wildcard include/config/BSD_PROCESS_ACCT) \
    $(wildcard include/config/TASKSTATS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/signal.h \
    $(wildcard include/config/PROC_FS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/jobctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/task.h \
    $(wildcard include/config/HAVE_EXIT_THREAD) \
    $(wildcard include/config/ARCH_WANTS_DYNAMIC_TASK_STRUCT) \
    $(wildcard include/config/HAVE_ARCH_THREAD_STRUCT_WHITELIST) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/uaccess.h \
    $(wildcard include/config/SET_FS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/fault-inject-usercopy.h \
    $(wildcard include/config/FAULT_INJECTION_USERCOPY) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/uaccess.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/kernel-pgtable.h \
    $(wildcard include/config/RANDOMIZE_BASE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/extable.h \
    $(wildcard include/config/BPF_JIT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cred.h \
    $(wildcard include/config/DEBUG_CREDENTIALS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/key.h \
    $(wildcard include/config/KEY_NOTIFICATIONS) \
    $(wildcard include/config/NET) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sysctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/sysctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/assoc_array.h \
    $(wildcard include/config/ASSOCIATIVE_ARRAY) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/user.h \
    $(wildcard include/config/WATCH_QUEUE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/percpu_counter.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rcu_sync.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/delayed_call.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/uuid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/uuid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/errseq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ioprio.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/rt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/iocontext.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/ioprio.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/fs_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mount.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/fs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/quota.h \
    $(wildcard include/config/QUOTA_NETLINK_INTERFACE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/dqblk_xfs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dqblk_v1.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dqblk_v2.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dqblk_qtree.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/projid.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/quota.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/nfs_fs_i.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/vmstat.h \
    $(wildcard include/config/VM_EVENT_COUNTERS) \
    $(wildcard include/config/DEBUG_TLBFLUSH) \
    $(wildcard include/config/DEBUG_VM_VMACACHE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/vm_event_item.h \
    $(wildcard include/config/MEMORY_BALLOON) \
    $(wildcard include/config/BALLOON_COMPACTION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/io.h \
  arch/arm64/include/generated/asm/early_ioremap.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/early_ioremap.h \
    $(wildcard include/config/GENERIC_EARLY_IOREMAP) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/io.h \
    $(wildcard include/config/GENERIC_IOMAP) \
    $(wildcard include/config/GENERIC_IOREMAP) \
    $(wildcard include/config/HAS_IOPORT_MAP) \
    $(wildcard include/config/VIRT_TO_BUS) \
    $(wildcard include/config/GENERIC_DEVMEM_IS_ALLOWED) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/pci_iomap.h \
    $(wildcard include/config/PCI) \
    $(wildcard include/config/NO_GENERIC_PCI_IOPORT_MAP) \
    $(wildcard include/config/GENERIC_PCI_IOMAP) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/logic_pio.h \
    $(wildcard include/config/INDIRECT_PIO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/fwnode.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/vmalloc.h \
    $(wildcard include/config/HAVE_ARCH_HUGE_VMALLOC) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/vmalloc.h \
    $(wildcard include/config/PTDUMP_DEBUGFS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mem_encrypt.h \
    $(wildcard include/config/ARCH_HAS_MEM_ENCRYPT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/dmaengine.h \
    $(wildcard include/config/DEBUG_FS) \
    $(wildcard include/config/DMA_ENGINE_RAID) \
    $(wildcard include/config/ASYNC_TX_ENABLE_CHANNEL_SWITCH) \
    $(wildcard include/config/DMA_ENGINE) \
    $(wildcard include/config/RAPIDIO_DMA_ENGINE) \
    $(wildcard include/config/ASYNC_TX_DMA) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/uio.h \
    $(wildcard include/config/ARCH_HAS_COPY_MC) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/uio.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/of_device.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cpu.h \
    $(wildcard include/config/PM_SLEEP_SMP) \
    $(wildcard include/config/PM_SLEEP_SMP_NONZERO_CPU) \
    $(wildcard include/config/HOTPLUG_SMT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/node.h \
    $(wildcard include/config/HMEM_REPORTING) \
    $(wildcard include/config/MEMORY_HOTPLUG_SPARSE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cpuhotplug.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/platform_device.h \
    $(wildcard include/config/SUSPEND) \
    $(wildcard include/config/HIBERNATE_CALLBACKS) \
    $(wildcard include/config/SUPERH) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/of_platform.h \
    $(wildcard include/config/OF_ADDRESS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/mod_devicetable.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/of.h \
    $(wildcard include/config/SPARC) \
    $(wildcard include/config/OF_PROMTREE) \
    $(wildcard include/config/OF_KOBJ) \
    $(wildcard include/config/OF_NUMA) \
    $(wildcard include/config/OF_OVERLAY) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/property.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/of_irq.h \
    $(wildcard include/config/IRQCHIP_XILINX_INTC_MODULE_SUPPORT_EXPERIMENTAL) \
    $(wildcard include/config/PPC32) \
    $(wildcard include/config/PPC_PMAC) \
    $(wildcard include/config/OF_IRQ) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irq.h \
    $(wildcard include/config/GENERIC_IRQ_EFFECTIVE_AFF_MASK) \
    $(wildcard include/config/GENERIC_IRQ_IPI) \
    $(wildcard include/config/IRQ_DOMAIN_HIERARCHY) \
    $(wildcard include/config/GENERIC_IRQ_MIGRATION) \
    $(wildcard include/config/GENERIC_PENDING_IRQ) \
    $(wildcard include/config/HARDIRQS_SW_RESEND) \
    $(wildcard include/config/GENERIC_IRQ_LEGACY) \
    $(wildcard include/config/GENERIC_IRQ_MULTI_HANDLER) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqhandler.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqreturn.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/io.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/slab.h \
    $(wildcard include/config/DEBUG_SLAB) \
    $(wildcard include/config/FAILSLAB) \
    $(wildcard include/config/HAVE_HARDENED_USERCOPY_ALLOCATOR) \
    $(wildcard include/config/SLAB) \
    $(wildcard include/config/SLUB) \
    $(wildcard include/config/SLOB) \
    $(wildcard include/config/CC_IS_GCC) \
    $(wildcard include/config/CLANG_VERSION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/irq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/irq.h \
  arch/arm64/include/generated/asm/irq_regs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/irq_regs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqdesc.h \
    $(wildcard include/config/GENERIC_IRQ_DEBUGFS) \
    $(wildcard include/config/SPARSE_IRQ) \
    $(wildcard include/config/IRQ_DOMAIN) \
    $(wildcard include/config/HANDLE_DOMAIN_IRQ) \
  arch/arm64/include/generated/asm/hw_irq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/hw_irq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqdomain.h \
    $(wildcard include/config/IRQ_DOMAIN_NOMAP) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/clk/clk-conf.h \
    $(wildcard include/config/COMMON_CLK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/spi/spi.h \
    $(wildcard include/config/SPI) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kthread.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/gpio/consumer.h \
    $(wildcard include/config/GPIOLIB) \
    $(wildcard include/config/OF_GPIO) \
    $(wildcard include/config/GPIO_SYSFS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ptp_clock_kernel.h \
    $(wildcard include/config/PTP_1588_CLOCK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pps_kernel.h \
    $(wildcard include/config/NTP_PPS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/pps.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cdev.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/ptp_clock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/skbuff.h \
    $(wildcard include/config/NF_CONNTRACK) \
    $(wildcard include/config/BRIDGE_NETFILTER) \
    $(wildcard include/config/NET_TC_SKB_EXT) \
    $(wildcard include/config/DEBUG_KMAP_LOCAL_FORCE_MAP) \
    $(wildcard include/config/NET_SOCK_MSG) \
    $(wildcard include/config/SKB_EXTENSIONS) \
    $(wildcard include/config/IPV6_NDISC_NODETYPE) \
    $(wildcard include/config/NET_SWITCHDEV) \
    $(wildcard include/config/NET_CLS_ACT) \
    $(wildcard include/config/NET_REDIRECT) \
    $(wildcard include/config/TLS_DEVICE) \
    $(wildcard include/config/NET_SCHED) \
    $(wildcard include/config/NET_RX_BUSY_POLL) \
    $(wildcard include/config/XPS) \
    $(wildcard include/config/NETWORK_SECMARK) \
    $(wildcard include/config/PAGE_POOL) \
    $(wildcard include/config/HAVE_EFFICIENT_UNALIGNED_ACCESS) \
    $(wildcard include/config/NETWORK_PHY_TIMESTAMPING) \
    $(wildcard include/config/XFRM) \
    $(wildcard include/config/MPTCP) \
    $(wildcard include/config/NETFILTER_XT_TARGET_TRACE) \
    $(wildcard include/config/NF_TABLES) \
    $(wildcard include/config/IP_VS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bvec.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/highmem.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/hardirq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/context_tracking_state.h \
    $(wildcard include/config/CONTEXT_TRACKING) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ftrace_irq.h \
    $(wildcard include/config/HWLAT_TRACER) \
    $(wildcard include/config/OSNOISE_TRACER) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/vtime.h \
    $(wildcard include/config/VIRT_CPU_ACCOUNTING) \
    $(wildcard include/config/IRQ_TIME_ACCOUNTING) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/hardirq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/kvm_arm.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/hardirq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/cacheflush.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kgdb.h \
    $(wildcard include/config/HAVE_ARCH_KGDB) \
    $(wildcard include/config/KGDB) \
    $(wildcard include/config/SERIAL_KGDB_NMI) \
    $(wildcard include/config/KGDB_HONOUR_BLOCKLIST) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kprobes.h \
    $(wildcard include/config/KPROBES_SANITY_TEST) \
    $(wildcard include/config/OPTPROBES) \
    $(wildcard include/config/KPROBES_ON_FTRACE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ftrace.h \
    $(wildcard include/config/FUNCTION_TRACER) \
    $(wildcard include/config/DYNAMIC_FTRACE) \
    $(wildcard include/config/HAVE_DYNAMIC_FTRACE_WITH_ARGS) \
    $(wildcard include/config/DYNAMIC_FTRACE_WITH_REGS) \
    $(wildcard include/config/DYNAMIC_FTRACE_WITH_DIRECT_CALLS) \
    $(wildcard include/config/HAVE_DYNAMIC_FTRACE_WITH_DIRECT_CALLS) \
    $(wildcard include/config/STACK_TRACER) \
    $(wildcard include/config/FRAME_POINTER) \
    $(wildcard include/config/FUNCTION_PROFILER) \
    $(wildcard include/config/FTRACE_SYSCALLS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/trace_recursion.h \
    $(wildcard include/config/FTRACE_RECORD_RECURSION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/interrupt.h \
    $(wildcard include/config/IRQ_FORCED_THREADING) \
    $(wildcard include/config/GENERIC_IRQ_PROBE) \
    $(wildcard include/config/IRQ_TIMINGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/trace_clock.h \
  arch/arm64/include/generated/asm/trace_clock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/trace_clock.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kallsyms.h \
    $(wildcard include/config/KALLSYMS_ALL) \
    $(wildcard include/config/KALLSYMS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/buildid.h \
    $(wildcard include/config/STACKTRACE_BUILD_ID) \
    $(wildcard include/config/CRASH_CORE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/module.h \
    $(wildcard include/config/MODULES_TREE_LOOKUP) \
    $(wildcard include/config/MODULE_SIG) \
    $(wildcard include/config/BPF_EVENTS) \
    $(wildcard include/config/DEBUG_INFO_BTF_MODULES) \
    $(wildcard include/config/EVENT_TRACING) \
    $(wildcard include/config/MODULE_UNLOAD) \
    $(wildcard include/config/CONSTRUCTORS) \
    $(wildcard include/config/FUNCTION_ERROR_INJECTION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kmod.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/umh.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/elf.h \
    $(wildcard include/config/ARCH_USE_GNU_PROPERTY) \
    $(wildcard include/config/ARCH_HAVE_ELF_PROT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/elf.h \
    $(wildcard include/config/COMPAT_VDSO) \
  arch/arm64/include/generated/asm/user.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/user.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/elf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/elf-em.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/moduleparam.h \
    $(wildcard include/config/ALPHA) \
    $(wildcard include/config/PPC64) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/rbtree_latch.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/error-injection.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/error-injection.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cfi.h \
    $(wildcard include/config/CFI_CLANG_SHADOW) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/module.h \
    $(wildcard include/config/ARM64_MODULE_PLTS) \
    $(wildcard include/config/ARM64_ERRATUM_843419) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/module.h \
    $(wildcard include/config/HAVE_MOD_ARCH_SPECIFIC) \
    $(wildcard include/config/MODULES_USE_ELF_REL) \
    $(wildcard include/config/MODULES_USE_ELF_RELA) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ptrace.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pid_namespace.h \
    $(wildcard include/config/PID_NS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/nsproxy.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ns_common.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/ptrace.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/ftrace.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compat.h \
    $(wildcard include/config/ARCH_HAS_SYSCALL_WRAPPER) \
    $(wildcard include/config/X86_X32_ABI) \
    $(wildcard include/config/COMPAT_OLD_SIGACTION) \
    $(wildcard include/config/ODD_RT_SIGACTION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/socket.h \
  arch/arm64/include/generated/uapi/asm/socket.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/socket.h \
  arch/arm64/include/generated/uapi/asm/sockios.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/sockios.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/sockios.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/socket.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/if.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/libc-compat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/hdlc/ioctl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/aio_abi.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/syscall_wrapper.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/freelist.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/kprobes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/kprobes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/kgdb.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/cacheflush.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/highmem-internal.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/net.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sockptr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/net.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/textsearch.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/net/checksum.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/checksum.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/in6.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/in6.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/checksum.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/netdev_features.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/clock.h \
    $(wildcard include/config/HAVE_UNSTABLE_SCHED_CLOCK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/net/flow_dissector.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/siphash.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/if_ether.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/splice.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pipe_fs_i.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/if_packet.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/net/flow.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/net/page_pool.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ptr_ring.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/netfilter/nf_conntrack_common.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/netfilter/nf_conntrack_common.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/spi/spi.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/spi/spi-mem.h \
    $(wildcard include/config/SPI_MEM) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/of_gpio.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/gpio/driver.h \
    $(wildcard include/config/GPIO_GENERIC) \
    $(wildcard include/config/GPIOLIB_IRQCHIP) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irqchip/chained_irq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pinctrl/pinctrl.h \
    $(wildcard include/config/GENERIC_PINCONF) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/seq_file.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pinctrl/pinctrl-state.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pinctrl/devinfo.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pinctrl/consumer.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pinctrl/pinconf-generic.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pinctrl/machine.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/gpio.h \
    $(wildcard include/config/ARCH_HAVE_CUSTOM_GPIO_H) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/gpio.h \
    $(wildcard include/config/ARCH_NR_GPIO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pm_runtime.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/pm_domain.h \
    $(wildcard include/config/CPU_IDLE) \
    $(wildcard include/config/PM_GENERIC_DOMAINS_SLEEP) \
    $(wildcard include/config/PM_GENERIC_DOMAINS_OF) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/sched/types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/delay.h \
  arch/arm64/include/generated/asm/delay.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/delay.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/acpi.h \
    $(wildcard include/config/ACPI_DEBUGGER) \
    $(wildcard include/config/LOONGARCH) \
    $(wildcard include/config/ACPI_PROCESSOR_CSTATE) \
    $(wildcard include/config/ACPI_HOTPLUG_CPU) \
    $(wildcard include/config/ACPI_HOTPLUG_IOAPIC) \
    $(wildcard include/config/X86_IO_APIC) \
    $(wildcard include/config/ACPI_WMI) \
    $(wildcard include/config/ACPI_NUMA) \
    $(wildcard include/config/HIBERNATION) \
    $(wildcard include/config/ACPI_HOTPLUG_MEMORY) \
    $(wildcard include/config/ACPI_CONTAINER) \
    $(wildcard include/config/ACPI_GTDT) \
    $(wildcard include/config/ACPI_TABLE_UPGRADE) \
    $(wildcard include/config/ACPI_WATCHDOG) \
    $(wildcard include/config/ACPI_SPCR_TABLE) \
    $(wildcard include/config/ACPI_GENERIC_GSI) \
    $(wildcard include/config/ACPI_LPIT) \
    $(wildcard include/config/ACPI_PPTT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/resource_ext.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acpi.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/platform/acenv.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/platform/acgcc.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/platform/aclinux.h \
    $(wildcard include/config/ACPI_REDUCED_HARDWARE_ONLY) \
    $(wildcard include/config/ACPI_DEBUG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ctype.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acnames.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/actypes.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acexcep.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/actbl.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/actbl1.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/actbl2.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/actbl3.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acrestyp.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/platform/acenvex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/platform/aclinuxex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/platform/acgccex.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acoutput.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acpiosxf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acpixf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acconfig.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acbuffer.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/acpi/acpi_numa.h \
    $(wildcard include/config/ACPI_HMAT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/platform_data/x86/apple.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/trace/events/spi.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/tracepoint.h \
    $(wildcard include/config/HAVE_SYSCALL_TRACEPOINTS) \
    $(wildcard include/config/TRACEPOINT) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/static_call.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/trace/define_trace.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/trace/trace_events.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/trace_events.h \
    $(wildcard include/config/DYNAMIC_EVENTS) \
    $(wildcard include/config/KPROBE_EVENTS) \
    $(wildcard include/config/UPROBE_EVENTS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ring_buffer.h \
    $(wildcard include/config/RING_BUFFER_ALLOW_SWAP) \
    $(wildcard include/config/RING_BUFFER) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/poll.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/poll.h \
  arch/arm64/include/generated/uapi/asm/poll.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/poll.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/eventpoll.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/trace_seq.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/seq_buf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/perf_event.h \
    $(wildcard include/config/CGROUP_PERF) \
    $(wildcard include/config/CPU_SUP_INTEL) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/perf_event.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/bpf_perf_event.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/bpf_perf_event.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/perf_event.h \
  arch/arm64/include/generated/asm/local64.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/local64.h \
  arch/arm64/include/generated/asm/local.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/local.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/irq_work.h \
    $(wildcard include/config/IRQ_WORK) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/irq_work.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/jump_label_ratelimit.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/perf_regs.h \
    $(wildcard include/config/HAVE_PERF_REGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/perf_regs.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cgroup.h \
    $(wildcard include/config/CGROUP_CPUACCT) \
    $(wildcard include/config/SOCK_CGROUP_DATA) \
    $(wildcard include/config/CGROUP_DATA) \
    $(wildcard include/config/CGROUP_BPF) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/cgroupstats.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/taskstats.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/user_namespace.h \
    $(wildcard include/config/INOTIFY_USER) \
    $(wildcard include/config/FANOTIFY) \
    $(wildcard include/config/PERSISTENT_KEYRINGS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kernel_stat.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cgroup-defs.h \
    $(wildcard include/config/CGROUP_NET_CLASSID) \
    $(wildcard include/config/CGROUP_NET_PRIO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/u64_stats_sync.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bpf-cgroup.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bpf.h \
    $(wildcard include/config/BPF_JIT_ALWAYS_ON) \
    $(wildcard include/config/INET) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/bpf.h \
    $(wildcard include/config/BPF_LIRC_MODE2) \
    $(wildcard include/config/EFFICIENT_UNALIGNED_ACCESS) \
    $(wildcard include/config/IP_ROUTE_CLASSID) \
    $(wildcard include/config/BPF_KPROBE_OVERRIDE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/bpf_common.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/file.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sched/mm.h \
    $(wildcard include/config/ARCH_HAS_MEMBARRIER_CALLBACKS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/sync_core.h \
    $(wildcard include/config/ARCH_HAS_SYNC_CORE_BEFORE_USERMODE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/bpfptr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/psi_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/cgroup_subsys.h \
    $(wildcard include/config/CGROUP_DEVICE) \
    $(wildcard include/config/CGROUP_FREEZER) \
    $(wildcard include/config/CGROUP_HUGETLB) \
    $(wildcard include/config/CGROUP_PIDS) \
    $(wildcard include/config/CGROUP_RDMA) \
    $(wildcard include/config/CGROUP_MISC) \
    $(wildcard include/config/CGROUP_DEBUG) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/security.h \
    $(wildcard include/config/SECURITY_NETWORK) \
    $(wildcard include/config/SECURITY_INFINIBAND) \
    $(wildcard include/config/SECURITY_NETWORK_XFRM) \
    $(wildcard include/config/SECURITY_PATH) \
    $(wildcard include/config/SECURITYFS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kernel_read_file.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/trace/perf.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/trace/bpf_probe.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/spi/internals.h \

drivers/spi/spi.o: $(deps_drivers/spi/spi.o)

$(deps_drivers/spi/spi.o):
