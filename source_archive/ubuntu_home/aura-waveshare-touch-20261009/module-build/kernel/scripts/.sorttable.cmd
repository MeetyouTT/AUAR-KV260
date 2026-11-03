cmd_scripts/sorttable := gcc -Wp,-MMD,scripts/.sorttable.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89      -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/tools/include -I ./scripts   -o scripts/sorttable /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/sorttable.c   

source_scripts/sorttable := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/sorttable.c

deps_scripts/sorttable := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/tools/include/tools/be_byteshift.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/tools/include/tools/le_byteshift.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/sorttable.h \

scripts/sorttable: $(deps_scripts/sorttable)

$(deps_scripts/sorttable):
