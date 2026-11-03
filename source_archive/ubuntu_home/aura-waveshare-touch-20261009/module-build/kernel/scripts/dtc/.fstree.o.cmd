cmd_scripts/dtc/fstree.o := gcc -Wp,-MMD,scripts/dtc/.fstree.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/fstree.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/fstree.c

source_scripts/dtc/fstree.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/fstree.c

deps_scripts/dtc/fstree.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/dtc.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.h \

scripts/dtc/fstree.o: $(deps_scripts/dtc/fstree.o)

$(deps_scripts/dtc/fstree.o):
