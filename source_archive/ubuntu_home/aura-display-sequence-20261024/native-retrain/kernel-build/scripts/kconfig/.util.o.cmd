cmd_scripts/kconfig/util.o := gcc -Wp,-MMD,scripts/kconfig/.util.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/kconfig -c -o scripts/kconfig/util.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/util.c

source_scripts/kconfig/util.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/util.c

deps_scripts/kconfig/util.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/expr.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/list.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc_proto.h \

scripts/kconfig/util.o: $(deps_scripts/kconfig/util.o)

$(deps_scripts/kconfig/util.o):
