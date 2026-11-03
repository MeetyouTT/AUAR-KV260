cmd_certs/system_certificates.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,certs/.system_certificates.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include -I./include -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-version.h -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/= -D__ASSEMBLY__ -fno-PIE -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -DKASAN_SHADOW_SCALE_SHIFT= -Wa,-gdwarf-2 -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/certs -I ./certs    -c -o certs/system_certificates.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/certs/system_certificates.S

source_certs/system_certificates.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/certs/system_certificates.S

deps_certs/system_certificates.o := \
    $(wildcard include/config/MODULE_SIG) \
    $(wildcard include/config/IMA_APPRAISE_MODSIG) \
    $(wildcard include/config/MODULES) \
    $(wildcard include/config/SYSTEM_EXTRA_CERTIFICATE) \
    $(wildcard include/config/SYSTEM_EXTRA_CERTIFICATE_SIZE) \
    $(wildcard include/config/64BIT) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/export.h \
    $(wildcard include/config/MODVERSIONS) \
    $(wildcard include/config/MODULE_REL_CRCS) \
    $(wildcard include/config/HAVE_ARCH_PREL32_RELOCATIONS) \
    $(wildcard include/config/TRIM_UNUSED_KSYMS) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/init.h \
    $(wildcard include/config/STRICT_KERNEL_RWX) \
    $(wildcard include/config/STRICT_MODULE_RWX) \
    $(wildcard include/config/LTO_CLANG) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler.h \
    $(wildcard include/config/TRACE_BRANCH_PROFILING) \
    $(wildcard include/config/PROFILE_ALL_BRANCHES) \
    $(wildcard include/config/STACK_VALIDATION) \
    $(wildcard include/config/CFI_CLANG) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler_types.h \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/asm/rwonce.h \
    $(wildcard include/config/LTO) \
    $(wildcard include/config/AS_HAS_LDAPR) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/asm-generic/rwonce.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/types.h \
    $(wildcard include/config/HAVE_UID16) \
    $(wildcard include/config/UID16) \
    $(wildcard include/config/ARCH_DMA_ADDR_T_64BIT) \
    $(wildcard include/config/PHYS_ADDR_T_64BIT) \
    $(wildcard include/config/ARCH_32BIT_USTAT_F_TINODE) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi/linux/types.h \
  arch/arm64/include/generated/uapi/asm/types.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi/asm-generic/types.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/asm-generic/int-ll64.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi/asm-generic/int-ll64.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/uapi/asm/bitsperlong.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/asm-generic/bitsperlong.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi/asm-generic/bitsperlong.h \

certs/system_certificates.o: $(deps_certs/system_certificates.o)

$(deps_certs/system_certificates.o):
