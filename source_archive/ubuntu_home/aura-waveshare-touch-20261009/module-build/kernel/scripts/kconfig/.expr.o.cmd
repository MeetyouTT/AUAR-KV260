cmd_scripts/kconfig/expr.o := gcc -Wp,-MMD,scripts/kconfig/.expr.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/kconfig -c -o scripts/kconfig/expr.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/expr.c

source_scripts/kconfig/expr.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/expr.c

deps_scripts/kconfig/expr.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/expr.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/list.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/kconfig/lkc_proto.h \

scripts/kconfig/expr.o: $(deps_scripts/kconfig/expr.o)

$(deps_scripts/kconfig/expr.o):
