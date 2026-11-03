cmd_arch/arm64/lib/clear_user.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,arch/arm64/lib/.clear_user.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include -I./include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/= -D__ASSEMBLY__ -fno-PIE -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -DKASAN_SHADOW_SCALE_SHIFT= -Wa,-gdwarf-2 -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/lib -I ./arch/arm64/lib    -c -o arch/arm64/lib/clear_user.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/lib/clear_user.S

source_arch/arm64/lib/clear_user.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/lib/clear_user.S

deps_arch/arm64/lib/clear_user.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/linkage.h \
    $(wildcard include/config/ARCH_USE_SYM_ANNOTATIONS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler_types.h \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/stringify.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/MODULE_REL_CRCS) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/TRIM_UNUSED_KSYMS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/linkage.h \
    $(wildcard include/config/ARM64_BTI_KERNEL) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/assembler.h \
    $(wildcard include/config/ARM64_RAS_EXTN) \
    $(wildcard include/config/KPROBES) \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
    $(wildcard include/config/KASAN_HW_TAGS) \
    $(wildcard include/config/ARM64_VA_BITS_52) \
    $(wildcard include/config/ARM64_PA_BITS_52) \
    $(wildcard include/config/FUJITSU_ERRATUM_010001) \
    $(wildcard include/config/QCOM_FALKOR_ERRATUM_E1041) \
    $(wildcard include/config/PREEMPTION) \
    $(wildcard include/config/MITIGATE_SPECTRE_BRANCH_HISTORY) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/export.h \
    $(wildcard include/config/64BIT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/asm-offsets.h \
  include/generated/asm-offsets.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/alternative.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/alternative-macros.h \
  arch/arm64/include/generated/asm/cpucaps.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/insn-def.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/asm-bug.h \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
    $(wildcard include/config/GENERIC_BUG) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/brk-imm.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/cpufeature.h \
    $(wildcard include/config/ARM64_PAN) \
    $(wildcard include/config/ARM64_SW_TTBR0_PAN) \
    $(wildcard include/config/ARM64_SVE) \
    $(wildcard include/config/ARM64_CNP) \
    $(wildcard include/config/ARM64_PTR_AUTH) \
    $(wildcard include/config/ARM64_PSEUDO_NMI) \
    $(wildcard include/config/ARM64_MTE) \
    $(wildcard include/config/ARM64_DEBUG_PRIORITY_MASKING) \
    $(wildcard include/config/ARM64_BTI) \
    $(wildcard include/config/ARM64_TLB_RANGE) \
    $(wildcard include/config/ARM64_PA_BITS) \
    $(wildcard include/config/ARM64_HW_AFDBM) \
    $(wildcard include/config/ARM64_AMU_EXTN) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/cputype.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/hwcap.h \
    $(wildcard include/config/COMPAT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/hwcap.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/sysreg.h \
    $(wildcard include/config/BROKEN_GAS_INST) \
    $(wildcard include/config/ARM64_4K_PAGES) \
    $(wildcard include/config/ARM64_16K_PAGES) \
    $(wildcard include/config/ARM64_64K_PAGES) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/bits.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/bits.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/bitsperlong.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/bitsperlong.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/bitsperlong.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kasan-tags.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/debug-monitors.h \
    $(wildcard include/config/HAVE_HW_BREAKPOINT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/errno.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/errno.h \
  arch/arm64/include/generated/uapi/asm/errno.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/errno.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/errno-base.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/types.h \
  arch/arm64/include/generated/uapi/asm/types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/types.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/int-ll64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/asm-generic/int-ll64.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/esr.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/memory.h \
    $(wildcard include/config/ARM64_VA_BITS) \
    $(wildcard include/config/KASAN_SHADOW_OFFSET) \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/EFI) \
    $(wildcard include/config/ARM_GIC_V3_ITS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/sizes.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/page-def.h \
    $(wildcard include/config/ARM64_PAGE_SHIFT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/SPARSEMEM) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/pfn.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/insn.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/build_bug.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/STACK_VALIDATION) \
    $(wildcard include/config/CFI_CLANG) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/rwonce.h \
    $(wildcard include/config/LTO) \
    $(wildcard include/config/AS_HAS_LDAPR) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/rwonce.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/ptrace.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/ptrace.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi/asm/sve_context.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/page.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/getorder.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/pgtable-hwdef.h \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/ARM64_CONT_PTE_SHIFT) \
    $(wildcard include/config/ARM64_CONT_PMD_SHIFT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/thread_info.h \
    $(wildcard include/config/SHADOW_CALL_STACK) \

arch/arm64/lib/clear_user.o: $(deps_arch/arm64/lib/clear_user.o)

$(deps_arch/arm64/lib/clear_user.o):
