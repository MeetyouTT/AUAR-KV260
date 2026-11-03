cmd_scripts/dtc/livetree.o := gcc -Wp,-MMD,scripts/dtc/.livetree.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/livetree.o /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/livetree.c

source_scripts/dtc/livetree.o := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/livetree.c

deps_scripts/dtc/livetree.o := \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/dtc.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/util.h \
  /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/dtc/srcpos.h \

scripts/dtc/livetree.o: $(deps_scripts/dtc/livetree.o)

$(deps_scripts/dtc/livetree.o):
