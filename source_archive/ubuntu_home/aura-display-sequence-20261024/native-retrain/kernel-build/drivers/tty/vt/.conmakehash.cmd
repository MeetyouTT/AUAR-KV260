cmd_drivers/tty/vt/conmakehash := gcc -Wp,-MMD,drivers/tty/vt/.conmakehash.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./drivers/tty/vt   -o drivers/tty/vt/conmakehash /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/drivers/tty/vt/conmakehash.c   

source_drivers/tty/vt/conmakehash := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/drivers/tty/vt/conmakehash.c

deps_drivers/tty/vt/conmakehash := \

drivers/tty/vt/conmakehash: $(deps_drivers/tty/vt/conmakehash)

$(deps_drivers/tty/vt/conmakehash):
