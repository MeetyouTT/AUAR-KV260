cmd_scripts/dtc/util.o := gcc -Wp,-MMD,scripts/dtc/.util.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/util.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.c

source_scripts/dtc/util.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.c

deps_scripts/dtc/util.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/version_gen.h \

scripts/dtc/util.o: $(deps_scripts/dtc/util.o)

$(deps_scripts/dtc/util.o):
