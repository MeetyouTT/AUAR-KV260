cmd_scripts/dtc/fdtoverlay.o := gcc -Wp,-MMD,scripts/dtc/.fdtoverlay.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML  -I ./scripts/dtc -c -o scripts/dtc/fdtoverlay.o /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/fdtoverlay.c

source_scripts/dtc/fdtoverlay.o := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/fdtoverlay.c

deps_scripts/dtc/fdtoverlay.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.h \

scripts/dtc/fdtoverlay.o: $(deps_scripts/dtc/fdtoverlay.o)

$(deps_scripts/dtc/fdtoverlay.o):
