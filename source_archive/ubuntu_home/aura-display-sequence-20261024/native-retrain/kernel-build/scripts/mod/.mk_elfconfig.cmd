cmd_scripts/mod/mk_elfconfig := gcc -Wp,-MMD,scripts/mod/.mk_elfconfig.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts/mod   -o scripts/mod/mk_elfconfig /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/mod/mk_elfconfig.c   

source_scripts/mod/mk_elfconfig := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/mod/mk_elfconfig.c

deps_scripts/mod/mk_elfconfig := \

scripts/mod/mk_elfconfig: $(deps_scripts/mod/mk_elfconfig)

$(deps_scripts/mod/mk_elfconfig):
