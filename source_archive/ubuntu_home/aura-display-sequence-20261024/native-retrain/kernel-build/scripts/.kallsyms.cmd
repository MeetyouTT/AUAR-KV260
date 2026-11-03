cmd_scripts/kallsyms := gcc -Wp,-MMD,scripts/.kallsyms.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts   -o scripts/kallsyms /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kallsyms.c   

source_scripts/kallsyms := /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kallsyms.c

deps_scripts/kallsyms := \

scripts/kallsyms: $(deps_scripts/kallsyms)

$(deps_scripts/kallsyms):
