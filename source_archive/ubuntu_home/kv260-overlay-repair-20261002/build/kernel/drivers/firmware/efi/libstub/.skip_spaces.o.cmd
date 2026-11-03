cmd_drivers/firmware/efi/libstub/skip_spaces.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,drivers/firmware/efi/libstub/.skip_spaces.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include -I./include -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi -I./include/generated/uapi -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler-version.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kconfig.h -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -mgeneral-regs-only -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret+leaf+bti -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wimplicit-fallthrough=5 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -g -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1016 -fpie -mbranch-protection=none -I/home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt -Os -DDISABLE_BRANCH_PROFILING -include /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/hidden.h -D__NO_FORTIFY -ffreestanding -fno-stack-protector -D__DISABLE_EXPORTS -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/firmware/efi/libstub -I ./drivers/firmware/efi/libstub    -DKBUILD_MODFILE='"drivers/firmware/efi/libstub/skip_spaces"' -DKBUILD_BASENAME='"skip_spaces"' -DKBUILD_MODNAME='"skip_spaces"' -D__KBUILD_MODNAME=kmod_skip_spaces -c -o drivers/firmware/efi/libstub/skip_spaces.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/firmware/efi/libstub/skip_spaces.c

source_drivers/firmware/efi/libstub/skip_spaces.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/firmware/efi/libstub/skip_spaces.c

deps_drivers/firmware/efi/libstub/skip_spaces.o := \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/hidden.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/ctype.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/STACK_VALIDATION) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/compiler_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/rwonce.h \
    $(wildcard include/config/LTO) \
    $(wildcard include/config/AS_HAS_LDAPR) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/asm-generic/rwonce.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kasan-checks.h \
    $(wildcard include/config/KASAN_GENERIC) \
    $(wildcard include/config/KASAN_SW_TAGS) \
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
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/uapi/asm/posix_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/posix_types.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/kcsan-checks.h \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/KCSAN_IGNORE_ATOMICS) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/string.h \
    $(wildcard include/config/BINARY_PRINTF) \
    $(wildcard include/config/FORTIFY_SOURCE) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/errno.h \
  arch/arm64/include/generated/uapi/asm/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/errno.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/asm-generic/errno-base.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/linux/stdarg.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/include/uapi/linux/string.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/arch/arm64/include/asm/string.h \
    $(wildcard include/config/KASAN_HW_TAGS) \
    $(wildcard include/config/ARCH_HAS_UACCESS_FLUSHCACHE) \

drivers/firmware/efi/libstub/skip_spaces.o: $(deps_drivers/firmware/efi/libstub/skip_spaces.o)

$(deps_drivers/firmware/efi/libstub/skip_spaces.o):
