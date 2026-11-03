#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/mman.h>
#include <unistd.h>

static FILE *fake_fopen(const char *,const char *);
static size_t fake_fread(void *,size_t,size_t,FILE *);
static int fake_fclose(FILE *);
static uid_t fake_geteuid(void);
static int fake_open(const char *,int,...);
static int fake_flock(int,int);
static int fake_close(int);
static void *fake_mmap(void *,size_t,int,int,int,off_t);
static int fake_munmap(void *,size_t);
#define VSRV_MMIO_TEST 1
#define fopen fake_fopen
#define fread fake_fread
#define fclose fake_fclose
#define geteuid fake_geteuid
#define open fake_open
#define flock fake_flock
#define close fake_close
#define mmap fake_mmap
#define munmap fake_munmap
#include "vsrv_mmio.c"
#undef fopen
#undef fread
#undef fclose
#undef geteuid
#undef open
#undef flock
#undef close
#undef mmap
#undef munmap

static uint32_t regs[1024];
static unsigned platform_calls,prop_opens,prop_closes,mmio_reads,mmio_writes,ack_reads;
static int bad_prop,bad_platform_at,bad_identity_after_data,seq_mode,nonroot,lock_busy;
static unsigned open_calls,flock_calls,map_calls,close_calls,unmap_calls;
static const char *paths[]={"/proc/sys/kernel/random/boot_id","/sys/block/mmcblk1/device/cid",
    "/proc/device-tree/fpga-full/firmware-name","/sys/class/fpga_manager/fpga0/state"};
static const char *contents[]={"12345678-1234-1234-1234-123456789012\n",
    "0353445345333247805558c00401a100\n",VSRV_FW,"operating\n"};

static FILE *fake_fopen(const char *path,const char *mode) {
    assert(strcmp(mode,"rb")==0);
    for(unsigned i=0;i<4;++i)if(strcmp(path,paths[i])==0) {
        ++prop_opens;return (FILE *)(uintptr_t)(i+1);
    }
    assert(!"unexpected filesystem read");return NULL;
}
static size_t fake_fread(void *buffer,size_t size,size_t count,FILE *file) {
    unsigned index=(unsigned)(uintptr_t)file-1;assert(index<4 && size==1);
    const char *content=((int)index==bad_prop ||
        (index==3 && bad_platform_at>0 && (int)platform_calls>=bad_platform_at))?"wrong":contents[index];
    size_t n=strlen(content);if(n>count)n=count;memcpy(buffer,content,n);return n;
}
static int fake_fclose(FILE *file) {(void)file;++prop_closes;return 0;}
static uid_t fake_geteuid(void) {++platform_calls;return nonroot?1000:0;}
static int fake_open(const char *path,int flags,...) {
    (void)flags;++open_calls;
    if(strcmp(path,"/run/aura-vsrv.lock")==0)return 51;
    if(strcmp(path,"/dev/mem")==0)return 52;
    assert(!"unexpected open");return -1;
}
static int fake_flock(int fd,int flags) {
    assert(fd==51 && flags==(LOCK_EX|LOCK_NB));++flock_calls;
    if(lock_busy){errno=EWOULDBLOCK;return -1;}return 0;
}
static int fake_close(int fd) {assert(fd==51 || fd==52);++close_calls;return 0;}
static void *fake_mmap(void *a,size_t n,int p,int f,int fd,off_t offset) {
    assert(a==NULL && n==4096 && p==(PROT_READ|PROT_WRITE) && f==MAP_SHARED && fd==52 && offset==(off_t)0x80080000ULL);
    ++map_calls;return regs;
}
static int fake_munmap(void *a,size_t n) {assert(a==regs && n==4096);++unmap_calls;return 0;}
uint32_t vsrv_test_mmio_read(volatile uint32_t *p) {
    ptrdiff_t word=p-regs;assert(word>=0 && word<1024);++mmio_reads;
    if(word==0x28/4) {
        ++ack_reads;
        if(seq_mode==2 || (seq_mode==1 && ack_reads==2))++regs[word];
    }
    uint32_t result=regs[word];
    if(word==0x0c/4 && bad_identity_after_data)regs[0]=0;
    return result;
}
void vsrv_test_mmio_write(volatile uint32_t *p,uint32_t value) {
    ptrdiff_t word=p-regs;assert(word>=0 && word<1024);++mmio_writes;regs[word]=value;
    if(word==0x24/4 && value==0x53544f50){regs[0x0c/4]=0;regs[0x30/4]=0;}
}
static void reset(void) {
    memset(regs,0,sizeof(regs));regs[0]=0x56535256;regs[1]=2;regs[2]=VSRV_BUILD_ID;
    regs[0x28/4]=7;regs[0x0c/4]=15;regs[0x2c/4]=1500;regs[0x30/4]=99;
    regs[0x34/4]=111;regs[0x38/4]=222;regs[0x40/4]=1490;regs[0x44/4]=1504;
    platform_calls=prop_opens=prop_closes=mmio_reads=mmio_writes=ack_reads=0;
    open_calls=flock_calls=map_calls=close_calls=unmap_calls=0;
    bad_prop=-1;bad_platform_at=bad_identity_after_data=seq_mode=nonroot=lock_busy=0;
}
static handle local_handle(void) {
    handle h={.fd=52,.lock=51,.p=regs};memcpy(h.boot,contents[0],36);h.boot[36]=0;return h;
}
static void untouched(const uint32_t *output,unsigned count) {
    for(unsigned i=0;i<count;++i)assert(output[i]==0xdeadbeef);
}

int main(void) {
    unsigned passed=0;uint32_t out[32];unsigned offsets[]={0x0c,0x2c};
    reset();handle h=local_handle();
    assert(vsrv_snapshot(&h,out)==0);
    assert(out[0]==0x56535256 && out[1]==2 && out[2]==VSRV_BUILD_ID && out[3]==7 && out[11]==7);
    assert(out[4]==15 && out[5]==1500 && out[6]==99 && out[7]==111 && out[8]==222 && out[9]==1490 && out[10]==1504);
    assert(platform_calls==2 && prop_opens==8 && prop_closes==8 && mmio_writes==0);++passed;

    reset();assert(vsrv_read_many(&h,(unsigned[]){0,4,8},3,out)==0);assert(out[1]==2 && platform_calls==2);++passed;
    reset();assert(vsrv_read_many(&h,offsets,2,out)==0 && out[0]==15 && out[1]==1500);++passed;
    reset();memset(out,0xef,sizeof(out));
    for(unsigned i=0;i<32;++i)out[i]=0xdeadbeef;
    assert(vsrv_read_many(NULL,offsets,2,out)==EINVAL);
    assert(vsrv_read_many(&h,NULL,2,out)==EINVAL);
    assert(vsrv_read_many(&h,offsets,2,NULL)==EINVAL);
    assert(vsrv_read_many(&h,offsets,0,out)==EINVAL);
    assert(vsrv_read_many(&h,offsets,33,out)==EINVAL);
    assert(platform_calls==0 && mmio_reads==0);untouched(out,32);++passed;
    for(unsigned invalid=0;invalid<3;++invalid) {
        reset();unsigned wrong[]={0x24,1,0x48};
        assert(vsrv_read_many(&h,&wrong[invalid],1,out)==EINVAL);
        assert(platform_calls==0 && mmio_reads==0);untouched(out,32);
    }++passed;
    for(int prop=0;prop<4;++prop) {
        reset();bad_prop=prop;
        assert(vsrv_read_many(&h,offsets,2,out)==EPERM);assert(mmio_reads==0);untouched(out,32);
    }++passed;
    reset();nonroot=1;assert(vsrv_snapshot(&h,out)==EPERM && mmio_reads==0);untouched(out,32);++passed;
    reset();regs[0]=0;assert(vsrv_snapshot(&h,out)==EBADMSG);untouched(out,32);++passed;
    reset();regs[1]=1;assert(vsrv_snapshot(&h,out)==EBADMSG);untouched(out,32);++passed;
    reset();regs[2]^=1;assert(vsrv_snapshot(&h,out)==EBADMSG);untouched(out,32);++passed;
    reset();bad_platform_at=2;assert(vsrv_read_many(&h,offsets,2,out)==EPERM);
    assert(platform_calls==2 && mmio_writes==0);untouched(out,32);++passed;
    reset();bad_identity_after_data=1;assert(vsrv_read_many(&h,offsets,2,out)==EBADMSG);untouched(out,32);++passed;
    reset();seq_mode=2;assert(vsrv_read_many(&h,offsets,2,out)==EAGAIN);
    assert(ack_reads==6 && platform_calls==2);untouched(out,32);++passed;
    reset();seq_mode=1;assert(vsrv_read_many(&h,offsets,2,out)==0 && ack_reads==4 && platform_calls==2);++passed;
    reset();uint32_t word;assert(vsrv_read(&h,0x0c,&word)==0 && word==15);
    assert(vsrv_read(&h,0x2c,&word)==0 && word==1500 && platform_calls==2 && prop_opens==8);++passed;
    reset();assert(vsrv_write(&h,0x1c,1504)==0 && regs[0x1c/4]==1504 && platform_calls==1);
    bad_prop=1;assert(vsrv_write(&h,0x1c,1505)==EPERM && regs[0x1c/4]==1504);++passed;
    reset();void *opened=NULL;assert(vsrv_open(h.boot,&opened)==0 && opened!=NULL);
    assert(open_calls==2 && flock_calls==1 && map_calls==1);
    assert(vsrv_close(opened)==0 && unmap_calls==1 && close_calls==2 && mmio_writes==1);++passed;
    reset();lock_busy=1;opened=NULL;assert(vsrv_open(h.boot,&opened)==EWOULDBLOCK && opened==NULL);
    assert(map_calls==0 && open_calls==1 && close_calls==1);++passed;
    printf("HOST_FAKE_FS_MMIO %u checks passed; real filesystem/MMIO calls=0\n",passed);
    return 0;
}
