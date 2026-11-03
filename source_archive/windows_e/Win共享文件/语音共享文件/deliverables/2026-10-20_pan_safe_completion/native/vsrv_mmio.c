#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mman.h>
#include <unistd.h>
#include "vsrv_protocol.h"
#ifndef __aarch64__
#error Build only for AArch64 Linux
#endif
typedef struct {int fd,lock; volatile uint32_t *p; char boot[37];} handle;
__attribute__((noinline)) uint32_t mmio_read32(volatile uint32_t *p) {
    uint32_t v=*p; __asm__ volatile("dsb sy" ::: "memory"); return v;
}
__attribute__((noinline)) void mmio_write32(volatile uint32_t *p,uint32_t v) {
    __asm__ volatile("dsb sy" ::: "memory"); *p=v;
    __asm__ volatile("dsb sy" ::: "memory");
}
static int prop(const char *path,const char *want) {
    char b[256]={0}; FILE *f=fopen(path,"rb"); if(!f)return 0;
    size_t n=fread(b,1,sizeof(b)-1,f); fclose(f);
    while(n && (b[n-1]=='\n' || b[n-1]=='\0'))b[--n]='\0';
    return !strcmp(b,want);
}
static int platform(const char *boot) {
    return geteuid()==0 && prop("/proc/sys/kernel/random/boot_id",boot) &&
      prop("/sys/block/mmcblk1/device/cid","0353445345333247805558c00401a100") &&
      prop("/proc/device-tree/fpga-full/firmware-name",VSRV_FW) &&
      prop("/sys/class/fpga_manager/fpga0/state","operating");
}
static int identity(handle *h) {
    return mmio_read32(h->p)==0x56535256u && mmio_read32(h->p+1)==VSRV_ABI &&
        mmio_read32(h->p+2)==VSRV_BUILD_ID;
}
static int readable(unsigned o) {return o<=0x44 && o!=0x24 && !(o&3);}
static int writable(unsigned o) {
    return o==0x10 || o==0x14 || o==0x18 || o==0x1c || o==0x20 || o==0x24 || o==0x3c;
}
int vsrv_open(const char *boot,void **result) {
    *result=NULL;
    if(!boot || strlen(boot)!=36 || !platform(boot))return EPERM;
    handle *h=calloc(1,sizeof(*h)); if(!h)return ENOMEM;
    h->fd=-1;h->lock=-1;h->p=MAP_FAILED;memcpy(h->boot,boot,37);
    h->lock=open("/run/aura-vsrv.lock",O_RDWR|O_CREAT|O_CLOEXEC|O_NOFOLLOW,0600);
    if(h->lock<0)goto fail;
    if(flock(h->lock,LOCK_EX|LOCK_NB))goto fail;
    h->fd=open("/dev/mem",O_RDWR|O_SYNC|O_CLOEXEC); if(h->fd<0)goto fail;
    h->p=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_SHARED,h->fd,(off_t)0x80080000ULL);
    if(h->p==MAP_FAILED)goto fail;
    if(!identity(h)){errno=EBADMSG;goto fail;}
    *result=h;return 0;
fail:;
    int error=errno;
    if(h->p!=MAP_FAILED)munmap((void*)h->p,4096);
    if(h->fd>=0)close(h->fd);
    if(h->lock>=0)close(h->lock);
    free(h);return error;
}
int vsrv_read(void *opaque,unsigned offset,uint32_t *result) {
    handle *h=opaque;if(!h || !readable(offset) || !result)return EINVAL;
    if(!platform(h->boot))return EPERM;
    *result=mmio_read32(h->p+offset/4);return 0;
}
int vsrv_write(void *opaque,unsigned offset,uint32_t value) {
    handle *h=opaque;if(!h || !writable(offset))return EINVAL;
    if(offset==0x24 && !vsrv_valid_command(value))return EINVAL;
    if(!platform(h->boot) || !identity(h))return EPERM;
    mmio_write32(h->p+offset/4,value);return 0;
}
int vsrv_close(void *opaque) {
    handle *h=opaque;if(!h)return EINVAL;int result=EPERM;
    if(platform(h->boot) && identity(h)) {
        mmio_write32(h->p+0x24/4,0x53544f50);
        result=((mmio_read32(h->p+0x0c/4)&15) || mmio_read32(h->p+0x30/4))?EIO:0;
    }
    munmap((void*)h->p,4096);close(h->fd);close(h->lock);free(h);return result;
}
