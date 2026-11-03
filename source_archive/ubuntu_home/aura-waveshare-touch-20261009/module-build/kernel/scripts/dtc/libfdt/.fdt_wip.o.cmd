cmd_scripts/dtc/libfdt/fdt_wip.o := gcc -Wp,-MMD,scripts/dtc/libfdt/.fdt_wip.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/libfdt/fdt_wip.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt_wip.c

source_scripts/dtc/libfdt/fdt_wip.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt_wip.c

deps_scripts/dtc/libfdt/fdt_wip.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_internal.h \

scripts/dtc/libfdt/fdt_wip.o: $(deps_scripts/dtc/libfdt/fdt_wip.o)

$(deps_scripts/dtc/libfdt/fdt_wip.o):
