cmd_lib/raid6/mktables := gcc -Wp,-MMD,lib/raid6/.mktables.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./lib/raid6   -o lib/raid6/mktables /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/lib/raid6/mktables.c   

source_lib/raid6/mktables := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/lib/raid6/mktables.c

deps_lib/raid6/mktables := \

lib/raid6/mktables: $(deps_lib/raid6/mktables)

$(deps_lib/raid6/mktables):
