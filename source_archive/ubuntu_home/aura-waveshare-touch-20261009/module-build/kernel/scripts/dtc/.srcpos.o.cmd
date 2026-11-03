cmd_scripts/dtc/srcpos.o := gcc -Wp,-MMD,scripts/dtc/.srcpos.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/srcpos.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/srcpos.c

source_scripts/dtc/srcpos.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/srcpos.c

deps_scripts/dtc/srcpos.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/dtc.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/srcpos.h \

scripts/dtc/srcpos.o: $(deps_scripts/dtc/srcpos.o)

$(deps_scripts/dtc/srcpos.o):
