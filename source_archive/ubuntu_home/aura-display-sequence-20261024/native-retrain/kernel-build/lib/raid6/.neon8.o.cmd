cmd_lib/raid6/neon8.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,lib/raid6/.neon8.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include -I./include -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-version.h -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/kconfig.h -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler_types.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/= -Wall -Wundef -Werror=strict-prototypes -Wno-trigraphs -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -Werror=implicit-function-declaration -Werror=implicit-int -Werror=return-type -Wno-format-security -std=gnu89 -DCONFIG_CC_HAS_K_CONSTRAINT=1 -Wno-psabi -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -mbranch-protection=pac-ret+leaf+bti -Wa,-march=armv8.5-a -DARM64_ASM_ARCH='"armv8.5-a"' -DKASAN_SHADOW_SCALE_SHIFT= -fno-delete-null-pointer-checks -Wno-frame-address -Wno-format-truncation -Wno-format-overflow -Wno-address-of-packed-member -O2 -fno-allow-store-data-races -Wframe-larger-than=2048 -fstack-protector-strong -Wimplicit-fallthrough=5 -Wno-main -Wno-unused-but-set-variable -Wno-unused-const-variable -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -g -fpatchable-function-entry=2 -Wdeclaration-after-statement -Wvla -Wno-pointer-sign -Wno-stringop-truncation -Wno-zero-length-bounds -Wno-array-bounds -Wno-stringop-overflow -Wno-restrict -Wno-maybe-uninitialized -fno-strict-overflow -fno-stack-check -fconserve-stack -Werror=date-time -Werror=incompatible-pointer-types -Werror=designated-init -Wno-packed-not-aligned -mstack-protector-guard=sysreg -mstack-protector-guard-reg=sp_el0 -mstack-protector-guard-offset=1016 -ffreestanding -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/lib/raid6 -I ./lib/raid6    -DKBUILD_MODFILE='"lib/raid6/raid6_pq"' -DKBUILD_BASENAME='"neon8"' -DKBUILD_MODNAME='"raid6_pq"' -D__KBUILD_MODNAME=kmod_raid6_pq -c -o lib/raid6/neon8.o lib/raid6/neon8.c

source_lib/raid6/neon8.o := lib/raid6/neon8.c

deps_lib/raid6/neon8.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler_types.h \
    $(wildcard include/config/HAVE_ARCH_COMPILER_H) \
    $(wildcard include/config/CC_HAS_ASM_INLINE) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler_attributes.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-gcc.h \
    $(wildcard include/config/RETPOLINE) \
    $(wildcard include/config/ARCH_USE_BUILTIN_BSWAP) \
    $(wildcard include/config/KCOV) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/asm/compiler.h \
    $(wildcard include/config/CFI_CLANG) \

lib/raid6/neon8.o: $(deps_lib/raid6/neon8.o)

$(deps_lib/raid6/neon8.o):
