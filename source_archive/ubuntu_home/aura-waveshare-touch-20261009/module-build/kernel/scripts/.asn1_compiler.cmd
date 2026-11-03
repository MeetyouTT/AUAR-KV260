cmd_scripts/asn1_compiler := gcc -Wp,-MMD,scripts/.asn1_compiler.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89      -I/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include -I ./scripts   -o scripts/asn1_compiler /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/asn1_compiler.c   

source_scripts/asn1_compiler := /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/asn1_compiler.c

deps_scripts/asn1_compiler := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/asn1_ber_bytecode.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/include/linux/asn1.h \

scripts/asn1_compiler: $(deps_scripts/asn1_compiler)

$(deps_scripts/asn1_compiler):
