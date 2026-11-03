cmd_scripts/dtc/util.o := gcc -Wp,-MMD,scripts/dtc/.util.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/util.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/util.c

source_scripts/dtc/util.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/util.c

deps_scripts/dtc/util.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/libfdt.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/util.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/version_gen.h \

scripts/dtc/util.o: $(deps_scripts/dtc/util.o)

$(deps_scripts/dtc/util.o):
