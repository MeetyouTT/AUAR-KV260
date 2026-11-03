cmd_scripts/extract-cert := gcc -Wp,-MMD,scripts/.extract-cert.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89       -I ./scripts   -o scripts/extract-cert /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/extract-cert.c   -lcrypto

source_scripts/extract-cert := /home/ghmd/kv260-overlay-repair-20261002/sources/linux-xlnx/scripts/extract-cert.c

deps_scripts/extract-cert := \

scripts/extract-cert: $(deps_scripts/extract-cert)

$(deps_scripts/extract-cert):
