cmd_scripts/kconfig/preprocess.o := gcc -Wp,-MMD,scripts/kconfig/.preprocess.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/kconfig -c -o scripts/kconfig/preprocess.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/preprocess.c

source_scripts/kconfig/preprocess.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/preprocess.c

deps_scripts/kconfig/preprocess.o := \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/list.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/expr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/lkc_proto.h \

scripts/kconfig/preprocess.o: $(deps_scripts/kconfig/preprocess.o)

$(deps_scripts/kconfig/preprocess.o):
