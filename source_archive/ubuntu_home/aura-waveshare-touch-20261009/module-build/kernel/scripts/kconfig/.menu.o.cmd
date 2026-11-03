cmd_scripts/kconfig/menu.o := gcc -Wp,-MMD,scripts/kconfig/.menu.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/kconfig -c -o scripts/kconfig/menu.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/menu.c

source_scripts/kconfig/menu.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/menu.c

deps_scripts/kconfig/menu.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/expr.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/list.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/lkc_proto.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/internal.h \

scripts/kconfig/menu.o: $(deps_scripts/kconfig/menu.o)

$(deps_scripts/kconfig/menu.o):
