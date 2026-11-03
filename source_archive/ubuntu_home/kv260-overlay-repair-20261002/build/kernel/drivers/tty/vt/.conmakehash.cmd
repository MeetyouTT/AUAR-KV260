cmd_drivers/tty/vt/conmakehash := gcc -Wp,-MMD,drivers/tty/vt/.conmakehash.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./drivers/tty/vt   -o drivers/tty/vt/conmakehash /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/tty/vt/conmakehash.c   

source_drivers/tty/vt/conmakehash := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/drivers/tty/vt/conmakehash.c

deps_drivers/tty/vt/conmakehash := \

drivers/tty/vt/conmakehash: $(deps_drivers/tty/vt/conmakehash)

$(deps_drivers/tty/vt/conmakehash):
