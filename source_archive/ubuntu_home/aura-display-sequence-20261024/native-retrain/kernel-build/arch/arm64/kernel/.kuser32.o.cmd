cmd_arch/arm64/kernel/kuser32.o := /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-gcc -Wp,-MMD,arch/arm64/kernel/.kuser32.o.d  -nostdinc -isystem /home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/x86_64-petalinux-linux/usr/bin/aarch64-xilinx-linux/../../lib/aarch64-xilinx-linux/gcc/aarch64-xilinx-linux/11.2.0/include -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include -I./arch/arm64/include/generated -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include -I./include -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/uapi -I./arch/arm64/include/generated/uapi -I/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi -I./include/generated/uapi -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-version.h -include /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/kconfig.h -D__KERNEL__ -mlittle-endian -DCC_USING_PATCHABLE_FUNCTION_ENTRY -DKASAN_SHADOW_SCALE_SHIFT= -fmacro-prefix-map=/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/= -D__ASSEMBLY__ -fno-PIE -mabi=lp64 -fno-asynchronous-unwind-tables -fno-unwind-tables -DKASAN_SHADOW_SCALE_SHIFT= -Wa,-gdwarf-2 -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/kernel -I ./arch/arm64/kernel    -c -o arch/arm64/kernel/kuser32.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/kernel/kuser32.S

source_arch/arm64/kernel/kuser32.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/kernel/kuser32.S

deps_arch/arm64/kernel/kuser32.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/compiler-version.h \
    $(wildcard include/config/CC_VERSION_TEXT) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/linux/kconfig.h \
    $(wildcard include/config/CPU_BIG_ENDIAN) \
    $(wildcard include/config/BOOGER) \
    $(wildcard include/config/FOO) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/asm/unistd.h \
    $(wildcard include/config/COMPAT) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/uapi/asm/unistd.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi/asm-generic/unistd.h \
    $(wildcard include/config/MMU) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/arch/arm64/include/uapi/asm/bitsperlong.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/asm-generic/bitsperlong.h \
    $(wildcard include/config/64BIT) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/include/uapi/asm-generic/bitsperlong.h \

arch/arm64/kernel/kuser32.o: $(deps_arch/arm64/kernel/kuser32.o)

$(deps_arch/arm64/kernel/kuser32.o):
