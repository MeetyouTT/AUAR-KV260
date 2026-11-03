cmd_usr/gen_init_cpio := gcc -Wp,-MMD,usr/.gen_init_cpio.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./usr   -o usr/gen_init_cpio /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/usr/gen_init_cpio.c   

source_usr/gen_init_cpio := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/usr/gen_init_cpio.c

deps_usr/gen_init_cpio := \

usr/gen_init_cpio: $(deps_usr/gen_init_cpio)

$(deps_usr/gen_init_cpio):
