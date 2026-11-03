cmd_scripts/dtc/dtc.o := gcc -Wp,-MMD,scripts/dtc/.dtc.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/dtc.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/dtc.c

source_scripts/dtc/dtc.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/dtc.c

deps_scripts/dtc/dtc.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/dtc.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/srcpos.h \

scripts/dtc/dtc.o: $(deps_scripts/dtc/dtc.o)

$(deps_scripts/dtc/dtc.o):
