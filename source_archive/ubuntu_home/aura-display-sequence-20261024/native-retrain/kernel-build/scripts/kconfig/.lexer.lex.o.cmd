cmd_scripts/kconfig/lexer.lex.o := gcc -Wp,-MMD,scripts/kconfig/.lexer.lex.o.d -Wall -Wmissing-prototypes -Wstrict-prototypes -O2 -fomit-frame-pointer -std=gnu89      -I /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig -I ./scripts/kconfig -c -o scripts/kconfig/lexer.lex.o scripts/kconfig/lexer.lex.c

source_scripts/kconfig/lexer.lex.o := scripts/kconfig/lexer.lex.c

deps_scripts/kconfig/lexer.lex.o := \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc.h \
    $(wildcard include/config/prefix) \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/expr.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/list.h \
  /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/scripts/kconfig/lkc_proto.h \
  scripts/kconfig/parser.tab.h \

scripts/kconfig/lexer.lex.o: $(deps_scripts/kconfig/lexer.lex.o)

$(deps_scripts/kconfig/lexer.lex.o):
