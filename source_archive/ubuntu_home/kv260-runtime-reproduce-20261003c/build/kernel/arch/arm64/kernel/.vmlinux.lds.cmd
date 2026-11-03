cmd_arch/arm64/kernel/vmlinux.lds := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -E -Wp,-MMD,arch/arm64/kernel/.vmlinux.lds.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include -I./include -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h -include /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/=     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel -I ./arch/arm64/kernel -P -Uarm64 -D__ASSEMBLY__ -DLINKER_SCRIPT -o arch/arm64/kernel/vmlinux.lds /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vmlinux.lds.S

source_arch/arm64/kernel/vmlinux.lds := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/vmlinux.lds.S

deps_arch/arm64/kernel/vmlinux.lds := \
    $(wildcard include/config/KVM) \
    $(wildcard include/config/HIBERNATION) \
    $(wildcard include/config/UNMAP_KERNEL_AT_EL0) \
    $(wildcard include/config/EFI) \
    $(wildcard include/config/RELR) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/hyp_image.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/vmlinux.lds.h \
    $(wildcard include/config/LD_DEAD_CODE_DATA_ELIMINATION) \
    $(wildcard include/config/LTO_CLANG) \
    $(wildcard include/config/HOTPLUG_CPU) \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/FTRACE_MCOUNT_RECORD) \
    $(wildcard include/config/FUNCTION_TRACER) \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/KPROBES) \
    $(wildcard include/config/FUNCTION_ERROR_INJECTION) \
    $(wildcard include/config/EVENT_TRACING) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/FTRACE_SYSCALLS) \
    $(wildcard include/config/BPF_EVENTS) \
    $(wildcard include/config/SERIAL_EARLYCON) \
    $(wildcard include/config/SECURITY) \
    $(wildcard include/config/TIMER_OF) \
    $(wildcard include/config/IRQCHIP) \
    $(wildcard include/config/COMMON_CLK) \
    $(wildcard include/config/OF_RESERVED_MEM) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/CPU_IDLE) \
    $(wildcard include/config/ACPI) \
    $(wildcard include/config/THERMAL) \
    $(wildcard include/config/DTPM) \
    $(wildcard include/config/CFI_CLANG) \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/CONSTRUCTORS) \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/UNWINDER_ORC) \
    $(wildcard include/config/PM_TRACE) \
    $(wildcard include/config/PRINTK_INDEX) \
    $(wildcard include/config/BLK_DEV_INITRD) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
    $(wildcard include/config/GCOV_KERNEL) \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KCSAN) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/cache.h \
    $(wildcard include/config/KASAN_SW_TAGS) \
    $(wildcard include/config/KASAN_HW_TAGS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/cputype.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/kernel-pgtable.h \
    $(wildcard include/config/ARM64_4K_PAGES) \
    $(wildcard include/config/PGTABLE_LEVELS) \
    $(wildcard include/config/RANDOMIZE_BASE) \
    $(wildcard include/config/ARM64_16K_PAGES) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/pgtable-hwdef.h \
    $(wildcard include/config/ARM64_CONT_PTE_SHIFT) \
    $(wildcard include/config/ARM64_CONT_PMD_SHIFT) \
    $(wildcard include/config/ARM64_PA_BITS_52) \
    $(wildcard include/config/ARM64_PA_BITS) \
    $(wildcard include/config/ARM64_VA_BITS_52) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/memory.h \
    $(wildcard include/config/ARM64_VA_BITS) \
    $(wildcard include/config/KASAN_SHADOW_OFFSET) \
    $(wildcard include/config/KASAN) \
    $(wildcard include/config/VMAP_STACK) \
    $(wildcard include/config/DEBUG_VIRTUAL) \
    $(wildcard include/config/ARM_GIC_V3_ITS) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/vdso/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/uapi/linux/const.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/sizes.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/page-def.h \
    $(wildcard include/config/ARM64_PAGE_SHIFT) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/memory_model.h \
    $(wildcard include/config/FLATMEM) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/SPARSEMEM) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/pfn.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/sparsemem.h \
    $(wildcard include/config/ARM64_64K_PAGES) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/page.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/asm-generic/getorder.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/image.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/include/asm/image.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/arch/arm64/kernel/image-vars.h \
    $(wildcard include/config/ARM64_PSEUDO_NMI) \

arch/arm64/kernel/vmlinux.lds: $(deps_arch/arm64/kernel/vmlinux.lds)

$(deps_arch/arm64/kernel/vmlinux.lds):
