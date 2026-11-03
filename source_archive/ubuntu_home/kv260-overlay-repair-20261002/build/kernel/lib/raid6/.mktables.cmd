cmd_lib/raid6/mktables := gcc -Wp,-MMD,lib/raid6/.mktables.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./lib/raid6   -o lib/raid6/mktables /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/lib/raid6/mktables.c   

source_lib/raid6/mktables := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/lib/raid6/mktables.c

deps_lib/raid6/mktables := \

lib/raid6/mktables: $(deps_lib/raid6/mktables)

$(deps_lib/raid6/mktables):
