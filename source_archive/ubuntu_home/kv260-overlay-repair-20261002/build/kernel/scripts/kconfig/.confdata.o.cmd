cmd_scripts/kconfig/confdata.o := gcc -Wp,-MMD,scripts/kconfig/.confdata.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/kconfig -c -o scripts/kconfig/confdata.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/confdata.c

source_scripts/kconfig/confdata.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/confdata.c

deps_scripts/kconfig/confdata.o := \
    $(wildcard include/config/FOO) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/expr.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/list.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/kconfig/lkc_proto.h \

scripts/kconfig/confdata.o: $(deps_scripts/kconfig/confdata.o)

$(deps_scripts/kconfig/confdata.o):
