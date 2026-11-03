cmd_scripts/kconfig/symbol.o := gcc -Wp,-MMD,scripts/kconfig/.symbol.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/kconfig -c -o scripts/kconfig/symbol.o /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/symbol.c

source_scripts/kconfig/symbol.o := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/symbol.c

deps_scripts/kconfig/symbol.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/expr.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/list.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc_proto.h \

scripts/kconfig/symbol.o: $(deps_scripts/kconfig/symbol.o)

$(deps_scripts/kconfig/symbol.o):
