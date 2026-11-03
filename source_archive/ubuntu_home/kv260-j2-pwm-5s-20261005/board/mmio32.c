#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include "bench_config.h"
#ifndef __aarch64__
#error "Build only for AArch64 Linux"
#endif
__attribute__((noinline)) uint32_t mmio_read32(volatile uint32_t *p) {
    uint32_t v=*p;
    __asm__ volatile("dsb sy" ::: "memory");
    return v;
}
__attribute__((noinline)) void mmio_write32(volatile uint32_t *p,uint32_t v) {
    __asm__ volatile("dsb sy" ::: "memory");
    *p=v;
    __asm__ volatile("dsb sy" ::: "memory");
}
static int property_is(const char *path,const char *want) {
    char b[256]={0}; FILE *f=fopen(path,"rb"); if (!f) return 0;
    size_t n=fread(b,1,sizeof(b)-1,f); fclose(f);
    while(n && (b[n-1]=='\0' || b[n-1]=='\n')) b[--n]='\0';
    return strcmp(b,want)==0;
}
static double now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)) return -1;
    return t.tv_sec+t.tv_nsec/1e9;
}
static uint32_t rd(volatile uint32_t *p,unsigned offset) {return mmio_read32(p+offset/4);}
int main(int argc,char **argv) {
    if(argc!=2 || (strcmp(argv[1],"inspect") && strcmp(argv[1],"start") &&
       strcmp(argv[1],"stop") && strcmp(argv[1],"scratch"))) {
        fprintf(stderr,"usage: mmio32 inspect|start|stop|scratch\n"); return 2;
    }
    if(geteuid()!=0 ||
       !property_is("/sys/block/mmcblk1/device/cid","0353445345333247805558c00401a100") ||
       !property_is("/proc/device-tree/fpga-full/firmware-name",BENCH_FIRMWARE_NAME) ||
       !property_is("/sys/class/fpga_manager/fpga0/state","operating")) {
        fprintf(stderr,"Board/image guard failed; no MMIO accessed\n"); return 3;
    }
    int writing=strcmp(argv[1],"inspect")!=0;
    int fd=open("/dev/mem",(writing?O_RDWR:O_RDONLY)|O_SYNC);
    if(fd<0) {perror("open");return 4;}
    volatile uint32_t *p=mmap(NULL,4096,PROT_READ|(writing?PROT_WRITE:0),MAP_SHARED,fd,(off_t)0x80080000ULL);
    if(p==MAP_FAILED) {perror("mmap");close(fd);return 4;}
    int rc=0;
    if(rd(p,0)!=0x50574d54 || rd(p,4)!=0x10000 || rd(p,8)!=BENCH_BUILD_ID ||
       rd(p,20)!=1999980 || rd(p,24)!=149999 || rd(p,32)!=99999001 ||
       rd(p,36)!=BENCH_RUN_FRAMES || rd(p,40)!=1500 || !(rd(p,12)&4)) {
        fprintf(stderr,"PWMT identity/configuration mismatch; no writes performed\n");rc=5;goto finish;
    }
    if(!strcmp(argv[1],"start")) {
        if(rd(p,12)!=4 || rd(p,28)!=0) {rc=6;goto finish;}
        double begin=now(); if(begin<0) {rc=7;goto finish;}
        /* The disassembled function must contain a 32-bit STR, never STRB. */
        mmio_write32(p+0x10/4,0x53544152);
        if(!(rd(p,12)&1)) rc=8;
        const struct timespec delay={.tv_sec=0,.tv_nsec=2000000};
        while(!rc && (rd(p,12)&1)) {
            double t=now(); if(t<0 || t-begin>BENCH_TIMEOUT_SECONDS) {rc=9;break;}
            nanosleep(&delay,NULL);
        }
        mmio_write32(p+0x10/4,0x53544f50);
    } else if(!strcmp(argv[1],"stop")) {
        mmio_write32(p+0x10/4,0x53544f50);
    } else if(!strcmp(argv[1],"scratch")) {
        if(rd(p,12)!=4) {rc=6;goto finish;}
        uint32_t old=rd(p,0x2c);
        const uint32_t patterns[]={0x12345678,0xa55a3cc3};
        for(unsigned i=0;i<2;i++) {
            mmio_write32(p+0x2c/4,patterns[i]);
            if(rd(p,0x2c)!=patterns[i]) {rc=10;break;}
        }
        mmio_write32(p+0x2c/4,old);
        if(rd(p,0x2c)!=old) rc=10;
    }
    if(writing && (rd(p,12)!=4 || rd(p,28)!=0)) rc=11;
    if(!rc) printf("{\"ip_id\":\"0x%x\",\"abi\":\"0x%x\",\"build_id\":\"0x%x\","
      "\"status\":%u,\"period_ticks\":%u,\"pulse_ticks\":%u,\"frames_left\":%u,"
      "\"clock_hz\":%u,\"run_frames\":%u,\"pulse_us\":%u}\n",
      rd(p,0),rd(p,4),rd(p,8),rd(p,12),rd(p,20),rd(p,24),rd(p,28),rd(p,32),rd(p,36),rd(p,40));
    else fprintf(stderr,"32-bit operation failed: %d\n",rc);
finish:
    munmap((void *)p,4096);close(fd);return rc;
}
