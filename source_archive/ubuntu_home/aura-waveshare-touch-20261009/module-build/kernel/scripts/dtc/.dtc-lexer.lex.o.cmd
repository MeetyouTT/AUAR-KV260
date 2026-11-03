cmd_scripts/dtc/dtc-lexer.lex.o := gcc -Wp,-MMD,scripts/dtc/.dtc-lexer.lex.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89     -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt -DNO_YAML -I /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc -I ./scripts/dtc -c -o scripts/dtc/dtc-lexer.lex.o scripts/dtc/dtc-lexer.lex.c

source_scripts/dtc/dtc-lexer.lex.o := scripts/dtc/dtc-lexer.lex.c

deps_scripts/dtc/dtc-lexer.lex.o := \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/dtc.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/libfdt_env.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/libfdt/fdt.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/util.h \
  /home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/scripts/dtc/srcpos.h \
  scripts/dtc/dtc-parser.tab.h \

scripts/dtc/dtc-lexer.lex.o: $(deps_scripts/dtc/dtc-lexer.lex.o)

$(deps_scripts/dtc/dtc-lexer.lex.o):
