cmd_scripts/dtc/checks.o := gcc -Wp,-MMD,scripts/dtc/.checks.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/checks.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/checks.c

source_scripts/dtc/checks.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/checks.c

deps_scripts/dtc/checks.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/dtc.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/util.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/dtc/srcpos.h \

scripts/dtc/checks.o: $(deps_scripts/dtc/checks.o)

$(deps_scripts/dtc/checks.o):
