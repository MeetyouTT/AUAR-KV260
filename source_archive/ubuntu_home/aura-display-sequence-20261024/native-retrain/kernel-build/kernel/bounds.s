	.arch armv8-a
	.file	"bounds.c"
// GNU C89 (GCC) version 11.2.0 (aarch64-xilinx-linux)
//	compiled by GNU C version 11.2.0, GMP version 6.2.1, MPFR version 4.1.0, MPC version 1.2.1, isl version none
// GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
// options passed: -mbranch-protection=none -mlittle-endian -mgeneral-regs-only -mabi=lp64 -mbranch-protection=pac-ret+leaf+bti -O2 -std=gnu90 -fno-strict-aliasing -fno-common -fshort-wchar -fno-PIE -fno-asynchronous-unwind-tables -fno-unwind-tables -fno-delete-null-pointer-checks -fno-allow-store-data-races -fstack-protector-strong -fno-omit-frame-pointer -fno-optimize-sibling-calls -fno-stack-clash-protection -fpatchable-function-entry=2 -fno-strict-overflow -fstack-check=no -fconserve-stack
	.text
	.section	.text.startup,"ax",@progbits
	.align	2
	.p2align 4,,11
	.global	main
	.type	main, %function
main:
	hint	34 // bti c
	.section	__patchable_function_entries,"awo",@progbits,main
	.align	3
	.8byte	.LPFE1
	.section	.text.startup
.LPFE1:
	nop	
	nop	
	hint	25 // paciasp
// /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c:19: 	DEFINE(NR_PAGEFLAGS, __NR_PAGEFLAGS);
#APP
// 19 "/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c" 1
	
.ascii "->NR_PAGEFLAGS 23 __NR_PAGEFLAGS"	//
// 0 "" 2
// /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c:20: 	DEFINE(MAX_NR_ZONES, __MAX_NR_ZONES);
// 20 "/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c" 1
	
.ascii "->MAX_NR_ZONES 3 __MAX_NR_ZONES"	//
// 0 "" 2
// /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c:22: 	DEFINE(NR_CPUS_BITS, ilog2(CONFIG_NR_CPUS));
// 22 "/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c" 1
	
.ascii "->NR_CPUS_BITS 4 ilog2(CONFIG_NR_CPUS)"	//
// 0 "" 2
// /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c:24: 	DEFINE(SPINLOCK_SIZE, sizeof(spinlock_t));
// 24 "/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c" 1
	
.ascii "->SPINLOCK_SIZE 4 sizeof(spinlock_t)"	//
// 0 "" 2
// /home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877/linux/kernel/bounds.c:28: }
#NO_APP
	mov	w0, 0	//,
	hint	29 // autiasp
	ret	
	.size	main, .-main
	.ident	"GCC: (GNU) 11.2.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align	3
	.word	4
	.word	16
	.word	5
	.string	"GNU"
	.word	3221225472
	.word	4
	.word	3
	.align	3
