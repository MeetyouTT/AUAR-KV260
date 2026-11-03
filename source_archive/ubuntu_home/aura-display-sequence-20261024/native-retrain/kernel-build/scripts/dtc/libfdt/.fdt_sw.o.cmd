cmd_scripts/dtc/libfdt/fdt_sw.o := gcc -Wp,-MMD,scripts/dtc/libfdt/.fdt_sw.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/libfdt/fdt_sw.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/fdt_sw.c

source_scripts/dtc/libfdt/fdt_sw.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/fdt_sw.c

deps_scripts/dtc/libfdt/fdt_sw.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/libfdt.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/libfdt_internal.h \

scripts/dtc/libfdt/fdt_sw.o: $(deps_scripts/dtc/libfdt/fdt_sw.o)

$(deps_scripts/dtc/libfdt/fdt_sw.o):
