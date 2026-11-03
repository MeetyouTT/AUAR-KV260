cmd_scripts/kconfig/parser.tab.o := gcc -Wp,-MMD,scripts/kconfig/.parser.tab.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89      -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig -I ./scripts/kconfig -c -o scripts/kconfig/parser.tab.o scripts/kconfig/parser.tab.c

source_scripts/kconfig/parser.tab.o := scripts/kconfig/parser.tab.c

deps_scripts/kconfig/parser.tab.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/expr.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/list.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc_proto.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/internal.h \

scripts/kconfig/parser.tab.o: $(deps_scripts/kconfig/parser.tab.o)

$(deps_scripts/kconfig/parser.tab.o):
