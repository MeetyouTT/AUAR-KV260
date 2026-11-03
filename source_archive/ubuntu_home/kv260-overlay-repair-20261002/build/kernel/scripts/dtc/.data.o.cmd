cmd_scripts/dtc/data.o := gcc -Wp,-MMD,scripts/dtc/.data.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/data.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/data.c

source_scripts/dtc/data.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/data.c

deps_scripts/dtc/data.o := \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/dtc.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/util.h \

scripts/dtc/data.o: $(deps_scripts/dtc/data.o)

$(deps_scripts/dtc/data.o):
