cmd_scripts/dtc/libfdt/fdt_sw.o := gcc -Wp,-MMD,scripts/dtc/libfdt/.fdt_sw.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/libfdt/fdt_sw.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/fdt_sw.c

source_scripts/dtc/libfdt/fdt_sw.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/fdt_sw.c

deps_scripts/dtc/libfdt/fdt_sw.o := \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/libfdt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/libfdt_internal.h \

scripts/dtc/libfdt/fdt_sw.o: $(deps_scripts/dtc/libfdt/fdt_sw.o)

$(deps_scripts/dtc/libfdt/fdt_sw.o):
