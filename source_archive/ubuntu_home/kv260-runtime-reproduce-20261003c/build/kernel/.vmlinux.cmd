cmd_vmlinux := sh /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/link-vmlinux.sh "/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-ld" " -EL  -maarch64elf" "--no-undefined -X -shared -Bsymbolic -z notext  --no-apply-dynamic-relocs --fix-cortex-a53-843419 --build-id=sha1 --orphan-handling=warn";  true

source_vmlinux := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/link-vmlinux.sh

deps_vmlinux := \
    $(wildcard include/config/LTO_CLANG) \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/STACK_VALIDATION) \
    $(wildcard include/config/UNWINDER_ORC) \
    $(wildcard include/config/FTRACE_MCOUNT_USE_OBJTOOL) \
    $(wildcard include/config/VMLINUX_VALIDATION) \
    $(wildcard include/config/FRAME_POINTER) \
    $(wildcard include/config/GCOV_KERNEL) \
    $(wildcard include/config/RETPOLINE) \
    $(wildcard include/config/X86_SMAP) \
    $(wildcard include/config/VMLINUX_MAP) \
    $(wildcard include/config/KALLSYMS_ALL) \
    $(wildcard include/config/KALLSYMS_ABSOLUTE_PERCPU) \
    $(wildcard include/config/KALLSYMS_BASE_RELATIVE) \
    $(wildcard include/config/SHELL) \
    $(wildcard include/config/DEBUG_INFO_BTF) \
    $(wildcard include/config/KALLSYMS) \
    $(wildcard include/config/BPF) \
    $(wildcard include/config/BUILDTIME_TABLE_SORT) \

vmlinux: $(deps_vmlinux)

$(deps_vmlinux):
