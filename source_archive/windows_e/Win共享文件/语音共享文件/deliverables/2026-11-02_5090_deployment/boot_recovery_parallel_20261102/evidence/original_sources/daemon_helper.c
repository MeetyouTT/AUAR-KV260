/*
 * Copyright (c) 2021, Xilinx Inc. and Contributors. All rights reserved.
 *
 * SPDX-License-Identifier: MIT
 */

#include <errno.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <unistd.h>
#include <dfx-mgr/accel.h>
#include <dfx-mgr/assert.h>
#include <dfx-mgr/shell.h>
#include <dfx-mgr/model.h>
#include <dfx-mgr/json-config.h>
#include <dfx-mgr/daemon_helper.h>
#include <sys/stat.h>
#include <sys/inotify.h>
#include <fcntl.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <semaphore.h>

struct daemon_config config;
struct watch *active_watch = NULL;
struct basePLDesign *base_designs = NULL;
static int inotifyFd;
/* Protect watches, package metadata and loaded-slot lifetimes together.
 * Internal helpers return borrowed pointers and require state_lock to be held.
 * Public entry points acquire the lock once; inotify read() never holds it.
 */
static pthread_mutex_t state_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned char base_removed[MAX_WATCH];
static int init_status;
platform_info_t platform;
sem_t mutex;
void firmware_dir_walk(void);
static void firmware_dir_walk_locked(void);
static void release_removed_base(struct basePLDesign *base);
static int remove_accel_base(void);

struct watch {
    int wd;
	char name[64];
    char path[WATCH_PATH_LEN];
	char parent_name[64];
    char parent_path[WATCH_PATH_LEN];
};

static struct basePLDesign *findBaseDesign(const char *name)
{
    int i,j;

    for (i = 0; i < MAX_WATCH; i++) {
        if (!base_removed[i] && base_designs[i].base_path[0] != '\0') {
            if(!strcmp(base_designs[i].name, name)) {
                    DFX_DBG("Found base design %s", base_designs[i].name);
                    return &base_designs[i];
			}
            for (j=0;j <10; j++){
                if(!strcmp(base_designs[i].accel_list[j].name, name)) {
                    DFX_DBG("accel %s in base %s", name, base_designs[i].name);
                    return &base_designs[i];
                }
            }
        }
    }
    DFX_ERR("No accel found for %s", name);
    return NULL;
}

static struct basePLDesign *findBaseDesign_path(const char *path)
{
    int i,j;

    for (i = 0; i < MAX_WATCH; i++) {
        if (!base_removed[i] && base_designs[i].base_path[0] != '\0') {
            if(!strcmp(base_designs[i].base_path, path)) {
                    DFX_DBG("Found base design %s", base_designs[i].base_path);
                    return &base_designs[i];
			}
            for (j=0;j <10; j++){
                if(!strcmp(base_designs[i].accel_list[j].path, path)) {
                    DFX_DBG("accel %s in base %s", path, base_designs[i].base_path);
                    return &base_designs[i];
                }
            }
        }
    }
    DFX_ERR("No base design or accel found for %s", path);
    return NULL;
}

/*
 * getRMInfo is a function intended to be able to read the presently
 * loaded RMs. Rename to saveRMinfo()?
 */
static void getRMInfo_locked(void)
{
    FILE *fptr;
    int i;
    struct basePLDesign *base = platform.active_base;

    if(base == NULL || base->slots == NULL) {
        DFX_ERR("No design currently loaded");
        return;
    }

    fptr = fopen("/home/root/rm_info.txt","w");
    if (fptr == NULL) {
        DFX_ERR("Couldn't create /home/root/rm_info.txt");
        return;
    }

    for (i = 0; i < base->num_pl_slots; i++)
        fprintf(fptr, "%d %s\n", i, base->slots[i] ? "used" : "GREY");

    fclose(fptr);
}

/*
 * Update Vitis AI Runtime (VART) env
 */
static void update_env(const char *path)
{
    DIR *dir = opendir(path);
    struct dirent *entry;
    if (!dir)
        return;
    while ((entry = readdir(dir)) != NULL) {
        size_t len = strlen(entry->d_name);
        if (len > 7 &&
            (!strcmp(entry->d_name + len - 7, ".xclbin") ||
             !strcmp(entry->d_name + len - 7, ".XCLBIN"))) {
            FILE *file = fopen("/etc/vart.conf", "w");
            if (!file) {
                DFX_ERR("cannot update /etc/vart.conf");
                break;
            }
            int ret = fprintf(file, "firmware: %s/%s\n", path, entry->d_name);
            int closed = fclose(file);
            if (ret < 0 || closed != 0)
                DFX_ERR("cannot write /etc/vart.conf");
        }
    }
    closedir(dir);
}

static int load_accelerator_locked(const char *accel_name)
{
    int i, ret;
    char path[1024];
    char shell_path[600];
    acapd_accel_t *pl_accel = (acapd_accel_t *)calloc(sizeof(acapd_accel_t), 1);
    acapd_accel_pkg_hd_t *pkg = (acapd_accel_pkg_hd_t *)calloc(sizeof(acapd_accel_pkg_hd_t),1);
    struct basePLDesign *base = findBaseDesign(accel_name);
    slot_info_t *slot = calloc(1, sizeof(*slot));
    accel_info_t *accel_info = NULL;

    if (!slot || !pl_accel || !pkg)
        goto out;

    if(base == NULL) {
        DFX_ERR("No package found for %s", accel_name);
        goto out;
    }
    /* sys_cache_accel() appends '/' in its fixed-size tmp_dir buffer. */
    if (strlen(base->base_path) + 2 > sizeof(pl_accel->sys_info.tmp_dir)) {
        DFX_ERR("base package path is too long");
        goto out;
    }
    sprintf(shell_path,"%s/shell.json",base->base_path);

    /* Flat shell design are treated as with one slot */
    if (!strcmp(base->type,"XRT_FLAT") || !strcmp(base->type,"PL_FLAT")) {
        if (base->slots == NULL)
            base->slots = calloc(base->num_pl_slots + base->num_aie_slots,
                                 sizeof(slot_info_t *));

        if(platform.active_base != NULL && platform.active_base->active > 0) {
            DFX_ERR("Remove previously loaded accelerator, no empty slot");
            goto out;
        }
        if (!base->slots)
            goto out;
        if (platform.active_base && platform.active_base != base &&
            remove_accel_base() != 0)
            goto out;
        sprintf(pkg->name,"%s",accel_name);
        strcpy(slot->path, base->base_path);
        pkg->path = slot->path;
        pkg->type = ACAPD_ACCEL_PKG_TYPE_NONE;
        init_accel(pl_accel, pkg);
        strncpy(pl_accel->sys_info.tmp_dir, pkg->path,
                sizeof(pl_accel->sys_info.tmp_dir) - 1);
        strcpy(pl_accel->type,"XRT_FLAT");
        DFX_PR("load flat shell from %s", pkg->path);
        ret = load_accel(pl_accel, shell_path, 0);
        if (ret < 0){
            DFX_ERR("load_accel %s", accel_name);
            base->active = 0;
            goto out;
        }
		pl_accel->rm_slot = 0;
        base->fpga_cfg_id = pl_accel->sys_info.fpga_cfg_id;
        base->active += 1;
		slot->accel = pl_accel;
		slot->is_aie = 0;
        base->slots[0] = slot;
        platform.active_base = base;

        /* VART libary for SOM desings needs .xclbin path to be written to a file*/
		if(!strcmp(base->type,"XRT_FLAT"))
			update_env(pkg->path);
        return 0;
    }
    for (i = 0; i < 10; i++){
        if(!strcmp(base->accel_list[i].name, accel_name)) {
            accel_info = &base->accel_list[i];
            DFX_DBG("Found accel %s base %s parent %s", accel_info->path, base->base_path, accel_info->parent_path);
        }
    }
    /* For SIHA slotted architecture */
    if(!strcmp(base->type,"PL_DFX")) {
        if (accel_info == NULL)
            goto out;
        if (platform.active_base != NULL && !platform.active_base->active && 
				strcmp(platform.active_base->base_path, accel_info->parent_path)) {
			DFX_PR("All slots for base are empty, loading new base design");
			ret = remove_base(platform.active_base->fpga_cfg_id);
			if (ret != 0)
				goto out;
			struct basePLDesign *previous = platform.active_base;
			free(platform.active_base->slots);
			platform.active_base->slots = NULL;
			platform.active_base = NULL;
			release_removed_base(previous);
		}
		else if(platform.active_base != NULL && platform.active_base->active > 0 && 
				strcmp(platform.active_base->base_path, accel_info->parent_path)) {
            DFX_ERR("Active base design doesn't match this accel base");
            goto out;
        }
        if (platform.active_base == NULL) {
            sprintf(pkg->name,"%s",base->name);
            strcpy(slot->path, base->base_path);
            pkg->path = slot->path;
            pkg->type = ACAPD_ACCEL_PKG_TYPE_NONE;
			if (base->load_base_design) {
				init_accel(pl_accel, pkg);
				strncpy(pl_accel->sys_info.tmp_dir, pkg->path,
						sizeof(pl_accel->sys_info.tmp_dir) - 1);
				strcpy(pl_accel->type,"PL_DFX");
				DFX_PR("load from %s", pkg->path);
				ret = load_accel(pl_accel, shell_path, 0);
				if (ret < 0){
					DFX_ERR("load_accel %s", accel_name);
					base->active = 0;
					goto out;
				}
				DFX_PR("Loaded %s successfully", base->name);
				base->fpga_cfg_id = pl_accel->sys_info.fpga_cfg_id;
			}
			if (base->slots == NULL)
				base->slots = calloc(base->num_pl_slots + base->num_aie_slots,
						sizeof(slot_info_t *));
			platform.active_base = base;
	}
        for (i = 0; i < (base->num_pl_slots + base->num_aie_slots); i++) {
            DFX_DBG("Finding empty slot for %s i %d", accel_name, i);
            if (base->slots[i] == NULL){
                sprintf(path,"%s/%s_slot%d", accel_info->path, accel_info->name,i);
                if (access(path,F_OK) != 0){
                    continue;
                }
				strcpy(slot->name, accel_name);
				if (!strcmp(accel_info->accel_type,"XRT_AIE_DFX")) {
					DFX_ERR("%s: XRT_AIE_DFX unsupported", accel_name);
					goto out;
				}
				slot->is_aie = 0;
                strcpy(pkg->name, accel_name);
                if (strlen(path) + 2 > sizeof(pl_accel->sys_info.tmp_dir)) {
                    DFX_ERR("accelerator package path is too long");
                    goto out;
                }
                /* The slot owns this path until the accelerator is unloaded. */
                strcpy(slot->path, path);
                pkg->path = slot->path;
                pkg->type = ACAPD_ACCEL_PKG_TYPE_NONE;
                init_accel(pl_accel, pkg);
                /* Set rm_slot before load_accel() so isolation for appropriate slot can be applied*/
                pl_accel->rm_slot = i;
                strcpy(pl_accel->type,accel_info->accel_type);
                strncpy(pl_accel->sys_info.tmp_dir, pkg->path,
                        sizeof(pl_accel->sys_info.tmp_dir) - 1);
                DFX_PR("load from %s", pkg->path);
                ret = load_accel(pl_accel, shell_path, 0);
                if (ret < 0){
                    DFX_ERR("load_accel %s", accel_name);
					goto out;
                }
				platform.active_base->active += 1;
				slot->accel = pl_accel;
                base->slots[i] = slot;
                DFX_PR("Loaded %s successfully to slot %d", pkg->name, i);
                return i;
            }
        }
        if (i >= (base->num_pl_slots + base->num_aie_slots))
            DFX_ERR("No empty slot for %s", accel_name);
    }
    else {
        DFX_ERR("Check the supported type of base/accel");
    }
out:
    free(slot);
    free(pl_accel);
    free(pkg);
    return -1;
}

static int
remove_accel_base(void)
{
	struct basePLDesign *base = platform.active_base;
	int ret = -1;

	if (!base)
		DFX_PR("No base");
	else if (strcmp(base->type, "PL_DFX"))
		DFX_PR("Invalid base type: %s", base->type);
	else if (base->active)
		DFX_PR("Can't remove active base PL design: %s", base->name);
	else {
		DFX_PR("Unload base: %s", base->name);
		ret = remove_base(base->fpga_cfg_id);
		if (ret == 0) {
			free(base->slots);
			base->slots = NULL;
			platform.active_base = NULL;
			release_removed_base(base);
		}
	}
	return ret;
}

static int remove_accelerator_locked(int slot)
{
	struct basePLDesign *base = platform.active_base;
	acapd_accel_t *accel;
	int ret;

	/* slot -1 means remove base PL design */
	if (slot == -1)
		return remove_accel_base();

	if (!base || !base->slots || slot < 0 ||
	    slot >= base->num_pl_slots + base->num_aie_slots || !base->slots[slot]) {
		DFX_ERR("No Accel or invalid slot %d", slot);
		return -1;
	}
	if (base->slots[slot]->is_aie){
		free(base->slots[slot]);
		base->slots[slot] = NULL;
		platform.active_base->active -= 1;
		return 0;
	}
	accel = base->slots[slot]->accel;
	DFX_PR("Removing accel %s from slot %d", accel->pkg->name, slot);

	ret = remove_accel(accel, 0);
	if (ret != 0)
		return ret;
	free(accel->pkg);
	free(accel);
	free(base->slots[slot]);
	base->slots[slot] = NULL;
	platform.active_base->active -= 1;
	if (base->active == 0 &&
	    (!strcmp(base->type, "PL_FLAT") || !strcmp(base->type, "XRT_FLAT"))) {
		platform.active_base = NULL;
		release_removed_base(base);
	}
	return ret;
}

void sendBuff(uint64_t size)
{
    DFX_PR("buffer size %lu", size);
    //sendBuffer(size, socket_d);
}
void allocBuffer(uint64_t size)
{
    DFX_PR("buffer size %lu", size);
    allocateBuffer(size);
}
void freeBuff(uint64_t pa)
{
    DFX_DBG("free buffer PA %lu", pa);
    freeBuffer(pa);
}

static int getFD_locked(int slot, char *name)
{
	struct basePLDesign *base = platform.active_base;
	if(base == NULL || base->slots == NULL){
		DFX_ERR("No active design");
		return -1;
	}
	if (slot < 0 || slot >= base->num_pl_slots || !base->slots[slot] || !name)
		return -1;

	acapd_accel_t *accel = base->slots[slot]->accel;
	if (accel == NULL){
		DFX_ERR("No Accel in slot %d", slot);
		return -1;
	}
	for (int i = 0; i < accel->num_ip_devs; i++)
		if (strstr(accel->ip_dev[i].dev_name, name))
			return accel->ip_dev[i].id;

	// Check if the name matches one of the shell devices
	return dfx_shell_fd_by_name(name);
}

static int dfx_getFDs_locked(int slot, int *fd)
{
    struct basePLDesign *base = platform.active_base;
    if (!base || !base->slots || slot < 0 || slot >= base->num_pl_slots ||
        !base->slots[slot] || !fd) {
        DFX_ERR("No active design");
        return -1;
    }
    acapd_accel_t *accel = base->slots[slot]->accel;
    if (accel == NULL || 2 * slot + 1 >= accel->num_ip_devs) {
        DFX_ERR("No Accel in slot %d", slot);
        return -1;
    }
    fd[0] = accel->ip_dev[2*slot].id;
    fd[1] = accel->ip_dev[2*slot+1].id;
    DFX_PR("Daemon slot %d accel_config %d d_hls %d",
                    slot, fd[0], fd[1]);
    return 0;
}

void getShellFD()
{
    //get_shell_fd(socket_d);
}
void getClockFD()
{
    //get_shell_clock_fd(socket_d);
}

/*
 * list_accel_uio  list uio device name and its path
 *
 * Note: dev_name + path < 80 char, see: acapd_device_t
 * and device_name limits in json. Reduce buf sise by
 * one line (80 char) to prevent buffer overrun.
 */
static void
list_accel_uio_locked(int slot, char *buf, size_t sz)
{
	struct basePLDesign *base = platform.active_base;
	acapd_accel_t *accel;
	char *end;
	char *p = buf;
	int i;

	if (!buf || sz < 80) {
		if (buf && sz)
			buf[0] = '\0';
		return;
	}
	end = buf + sz - 80;

	if(base == NULL || base->slots == NULL)
		p += sprintf(p, "No active design\n");
	else if (slot < 0 || slot >= base->num_pl_slots || !base->slots[slot])
		p += sprintf(p, "slot %d is not used or invalid\n", slot);
	else if ( (accel = base->slots[slot]->accel) == NULL)
		p += sprintf(p, "No Accel in slot %d\n", slot);
	if (p != buf)
		return;

	for (i = 0; i < accel->num_ip_devs && p < end; i++) {
		char *dname = accel->ip_dev[i].dev_name;
		if (dname)
			p += sprintf(p, "%-30s %s\n", dname,
					accel->ip_dev[i].path);
	}
	dfx_shell_uio_list(p, end - p);
}

static char *
get_accel_uio_by_name_locked(int slot, const char *name)
{
	struct basePLDesign *base = platform.active_base;
	acapd_accel_t *accel;

	// NULL if no active design, slot is not used or invalid
	if(!base || !base->slots || !name || slot < 0 || slot >= base->num_pl_slots ||
	   !base->slots[slot])
		return NULL;

	accel = base->slots[slot]->accel;
	if (!accel)
		return NULL;

	for (int i = 0; i < accel->num_ip_devs; i++)
		if (strstr(accel->ip_dev[i].dev_name, name))
			return accel->ip_dev[i].path;

	// Check if the name matches one of the shell devices
	return dfx_shell_uio_by_name(name);
}

static char *listAccelerators_locked(void)
{
    int i,j;
	unsigned int slot;
    char msg[4 * (2 * UINT8_MAX) + 512];
	char res[8*1024];

	memset(res,0, sizeof(res));
	firmware_dir_walk_locked();
 
    sprintf(msg,"%32s%20s%32s%20s%20s%20s\n\n","Accelerator","Accel_type","Base","Base_type","#slots(PL+AIE)","Active_slot");
	strcat(res,msg);
    for (i = 0; i < MAX_WATCH; i++) {
        if (!base_removed[i] && base_designs[i].base_path[0] != '\0' && base_designs[i].num_pl_slots > 0) {
            for (j = 0; j < 10; j++) {
                if (base_designs[i].accel_list[j].path[0] != '\0') {
					char s[20];

					/* Internally flat shell is treated as one slot to make the code generic and save info of the active design */
					if (!strcmp(base_designs[i].type,"XRT_FLAT") || !strcmp(base_designs[i].type,"PL_FLAT"))
						sprintf(s,"(%d+%d)", 0, base_designs[i].num_aie_slots);
					else
						sprintf(s,"(%d+%d)", base_designs[i].num_pl_slots,base_designs[i].num_aie_slots);

                    if (base_designs[i].active) {
                        char active_slots[4 * (2 * UINT8_MAX) + 1] = "";
                        char tmp[5];
                        for(slot = 0; slot < (base_designs[i].num_pl_slots +  base_designs[i].num_aie_slots); slot++) {
							if (base_designs[i].slots[slot] != NULL && base_designs[i].slots[slot]->is_aie &&
									!strcmp(base_designs[i].slots[slot]->name,base_designs[i].accel_list[j].name)){
                                    sprintf(tmp,"%d,",slot);
                                    strcat(active_slots,tmp);
							}
                            else if (base_designs[i].slots[slot] != NULL && !base_designs[i].slots[slot]->is_aie &&
										!strcmp(base_designs[i].slots[slot]->accel->pkg->name,base_designs[i].accel_list[j].name)){
                                    sprintf(tmp,"%d,",slot);
                                    strcat(active_slots,tmp);
                            }
                        }
                        if (strcmp(active_slots, ""))
                            sprintf(msg,"%32s%20s%32s%20s%20s%20s\n",base_designs[i].accel_list[j].name,
										base_designs[i].accel_list[j].accel_type, base_designs[i].name,
										base_designs[i].type, s,active_slots);
                        else
                            sprintf(msg,"%32s%20s%32s%20s%20s%20d\n",base_designs[i].accel_list[j].name,
										base_designs[i].accel_list[j].accel_type,base_designs[i].name,
                                                    base_designs[i].type, s,-1);
						if (strlen(res) + strlen(msg) >= sizeof(res))
							return strdup(res);
						strcat(res,msg);
                    }
                    else {
                        sprintf(msg,"%32s%20s%32s%20s%20s%20d\n",base_designs[i].accel_list[j].name,
							base_designs[i].accel_list[j].accel_type,base_designs[i].name,
																base_designs[i].type, s,-1);
						if (strlen(res) + strlen(msg) >= sizeof(res))
							return strdup(res);
						strcat(res,msg);
                    }
                }
            }
        }
    }
	return strdup(res);
}

static int add_to_watch(int wd, const char *name, const char *path,
                         const char *parent_name, const char *parent_path)
{
    struct watch entry = {0};
    int i, free_slot = -1, slot = -1;

    /* Repeated inotify_add_watch() calls can return an existing descriptor. */
    if (wd < 0 || !name || !path || !parent_name || !parent_path) {
        errno = EINVAL;
        DFX_ERR("invalid watch");
        return -1;
    }
    if (strlen(name) >= sizeof(entry.name) ||
        strlen(path) >= sizeof(entry.path) ||
        strlen(parent_name) >= sizeof(entry.parent_name) ||
        strlen(parent_path) >= sizeof(entry.parent_path)) {
        errno = ENAMETOOLONG;
        DFX_ERR("watch metadata is too long");
        return -1;
    }
    entry.wd = wd;
    strcpy(entry.name, name);
    strcpy(entry.path, path);
    strcpy(entry.parent_name, parent_name);
    strcpy(entry.parent_path, parent_path);

    for (i = 0; i < MAX_WATCH; i++) {
        if (active_watch[i].wd == -1) {
            if (free_slot == -1)
                free_slot = i;
        } else if (active_watch[i].wd == wd ||
                   !strcmp(active_watch[i].path, path)) {
            slot = i;
            break;
        }
    }
    if (slot == -1)
        slot = free_slot;
    if (slot != -1)
        active_watch[slot] = entry;
    if (slot != -1)
        return 0;
    errno = ENOSPC;
    DFX_ERR("no room to add more watch");
    return -1;
}

static struct watch *get_watch(int wd)
{
    int i;
    if (wd < 0)
        return NULL;
    for (i = 0; i < MAX_WATCH; i++) {
        if (active_watch[i].wd == wd)
            return &active_watch[i];
    }
    return NULL;
}
static struct watch* path_to_watch(const char *path)
{
	int i;
	for(i=0; i < MAX_WATCH; i++){
		if(active_watch[i].wd >= 0 && !strcmp(path,active_watch[i].path))
			return &active_watch[i];
	}
	return NULL;
}
static void remove_watch(const char *path)
{
    int i;
    for (i = 0; i < MAX_WATCH; i++) {
        if (active_watch[i].wd >= 0 && strcmp(active_watch[i].path, path) == 0){
			inotify_rm_watch(inotifyFd, active_watch[i].wd);
			memset(&active_watch[i], 0, sizeof(active_watch[i]));
			active_watch[i].wd = -1;
        }
    }
}
static accel_info_t *add_accel_to_base(struct basePLDesign *base, const char *name,
                                     const char *path, const char *parent_path)
{
    int j, free_slot = -1;

    if (!base || !name || !path || !parent_path ||
        strlen(name) >= sizeof(base->accel_list[0].name) ||
        strlen(path) >= sizeof(base->accel_list[0].path) ||
        strlen(parent_path) >= sizeof(base->accel_list[0].parent_path)) {
        return NULL;
    }

    for (j = 0; j < 10; j++) {
        if (!strcmp(base->accel_list[j].path, path)) {
			DFX_DBG("%s already exists", path);
            return &base->accel_list[j];
        }
        if (base->accel_list[j].path[0] == '\0' && free_slot == -1)
            free_slot = j;
    }
    if (free_slot == -1) {
        errno = ENOSPC;
        return NULL;
    }
    j = free_slot;
    DFX_DBG("adding %s to base %s", path, parent_path);
    memset(&base->accel_list[j], 0, sizeof(base->accel_list[j]));
    strcpy(base->accel_list[j].name, name);
    strcpy(base->accel_list[j].path, path);
    strcpy(base->accel_list[j].parent_path, parent_path);
    base->accel_list[j].wd = -1;
    return &base->accel_list[j];
}


/* Directory and package helpers below require state_lock. */
static int path_is_within(const char *path, const char *root)
{
    size_t len = strlen(root);
    return !strncmp(path, root, len) &&
           (path[len] == '\0' || path[len] == '/');
}

static int d_name_filter(const char *name)
{
    return strlen(name) >= sizeof(((struct watch *)0)->name) ||
           !strcmp(name, ".") || !strcmp(name, "..");
}

static int add_directory_watch(const char *name, const char *path,
                               const char *parent_name, const char *parent_path)
{
    int wd;
    if (d_name_filter(name) || strlen(path) >= WATCH_PATH_LEN ||
        strlen(parent_path) >= WATCH_PATH_LEN) {
        errno = ENAMETOOLONG;
        return -1;
    }
    wd = inotify_add_watch(inotifyFd, path, IN_ALL_EVENTS);
    if (wd < 0)
        return -1;
    if (add_to_watch(wd, name, path, parent_name, parent_path) < 0) {
        int saved_errno = errno;
        inotify_rm_watch(inotifyFd, wd);
        errno = saved_errno;
        return -1;
    }
    return wd;
}

static void remove_watch_tree(const char *path)
{
    int i;
    /* Copy: path may itself point into a watch that is about to be cleared. */
    char root[MAX_PATH_SIZE];
    snprintf(root, sizeof(root), "%s", path);
    for (i = 0; i < MAX_WATCH; i++)
        if (active_watch[i].wd >= 0 &&
            path_is_within(active_watch[i].path, root)) {
            char child[WATCH_PATH_LEN];
            strcpy(child, active_watch[i].path);
            remove_watch(child);
        }
}

static void reset_base(struct basePLDesign *base)
{
    int j;
    size_t index = base - base_designs;
    free(base->slots);
    memset(base, 0, sizeof(*base));
    base->wd = -1;
    for (j = 0; j < 10; j++)
        base->accel_list[j].wd = -1;
    base_removed[index] = 0;
}

static void release_removed_base(struct basePLDesign *base)
{
    if (base_removed[base - base_designs] && base != platform.active_base)
        reset_base(base);
}

static void add_base_design(const char *name, const char *path,
                            const char *parent, int wd)
{
    int i;
    if (strlen(name) >= sizeof(base_designs[0].name) ||
        strlen(path) >= sizeof(base_designs[0].base_path) ||
        strlen(parent) >= sizeof(base_designs[0].parent_path))
        return;
    for (i = 0; i < MAX_WATCH; i++)
        if (!strcmp(base_designs[i].base_path, path)) {
            /* A removed but loaded base keeps its identity until unload. */
            if (!base_removed[i])
                base_designs[i].wd = wd;
            return;
        }
    for (i = 0; i < MAX_WATCH; i++)
        if (!base_designs[i].base_path[0]) {
            reset_base(&base_designs[i]);
            strcpy(base_designs[i].name, name);
            strcpy(base_designs[i].base_path, path);
            strcpy(base_designs[i].parent_path, parent);
            base_designs[i].wd = wd;
            return;
        }
    errno = ENOSPC;
    DFX_ERR("no room to add more base designs");
}

static void remove_base_design(const char *path, const char *parent, int is_base)
{
    int i, j;
    char removed_path[MAX_PATH_SIZE];
    (void)parent;
    snprintf(removed_path, sizeof(removed_path), "%s", path);
    remove_watch_tree(removed_path);
    for (i = 0; i < MAX_WATCH; i++) {
        struct basePLDesign *base = &base_designs[i];
        if (!base->base_path[0])
            continue;
        if (is_base && !strcmp(base->base_path, removed_path)) {
            /* Loaded slots and pkg->path can still refer to this record. */
            base_removed[i] = 1;
            base->wd = -1;
            memset(base->accel_list, 0, sizeof(base->accel_list));
            for (j = 0; j < 10; j++)
                base->accel_list[j].wd = -1;
            release_removed_base(base);
            return;
        }
        if (!is_base)
            for (j = 0; j < 10; j++)
                if (base->accel_list[j].path[0] &&
                    path_is_within(base->accel_list[j].path, removed_path)) {
                    memset(&base->accel_list[j], 0, sizeof(base->accel_list[j]));
                    base->accel_list[j].wd = -1;
                }
    }
}

/* The vendor package layout supports two directory levels below a base. */
static void parse_packages(struct basePLDesign *base, char *fname, char *path)
{
    DIR *dir1, *dir2;
    struct dirent *d1, *d2;
    char first[WATCH_PATH_LEN], second[WATCH_PATH_LEN];
    char filename[WATCH_PATH_LEN + 16];
    struct stat info;
    accel_info_t *accel;

    if (!base || base_removed[base - base_designs])
        return;
    if (!strcmp(base->type, "XRT_FLAT") || !strcmp(base->type, "PL_FLAT")) {
        strcpy(base->accel_list[0].name, base->name);
        strcpy(base->accel_list[0].path, base->base_path);
        strcpy(base->accel_list[0].parent_path, base->base_path);
        strcpy(base->accel_list[0].accel_type, base->type);
        return;
    }
    dir1 = opendir(path);
    if (!dir1)
        return;
    while ((d1 = readdir(dir1)) != NULL) {
        if (d1->d_type != DT_DIR || d_name_filter(d1->d_name))
            continue;
        if (snprintf(first, sizeof(first), "%s/%s", path, d1->d_name) >= (int)sizeof(first))
            continue;
        if (add_directory_watch(d1->d_name, first, fname, path) < 0)
            continue;
        snprintf(filename, sizeof(filename), "%s/accel.json", first);
        if (!stat(filename, &info) && S_ISREG(info.st_mode) &&
            strlen(first) + sizeof("/accel.json") <= WATCH_PATH_LEN) {
            accel = add_accel_to_base(base, d1->d_name, first, path);
            if (accel)
                initAccel(accel, first);
            continue;
        }
        dir2 = opendir(first);
        if (!dir2)
            continue;
        while ((d2 = readdir(dir2)) != NULL) {
            if (d2->d_type != DT_DIR || d_name_filter(d2->d_name))
                continue;
            if (snprintf(second, sizeof(second), "%s/%s", first, d2->d_name) >= (int)sizeof(second))
                continue;
            /* initAccel() has its own 256-byte JSON filename buffer. */
            if (strlen(second) + sizeof("/accel.json") > WATCH_PATH_LEN)
                continue;
            if (add_directory_watch(d2->d_name, second, d1->d_name, first) < 0)
                continue;
            snprintf(filename, sizeof(filename), "%s/accel.json", second);
            if (!stat(filename, &info) && S_ISREG(info.st_mode)) {
                accel = add_accel_to_base(base, d1->d_name, first, path);
                if (accel)
                    initAccel(accel, second);
            }
        }
        closedir(dir2);
    }
    closedir(dir1);
}

static void refresh_base(struct basePLDesign *base)
{
    char filename[MAX_PATH_SIZE + 16];
    if (!base || base_removed[base - base_designs])
        return;
    /* shell.json edits must not change the bounds of a live slots array. */
    if (base != platform.active_base) {
        free(base->slots);
        base->slots = NULL;
        snprintf(filename, sizeof(filename), "%s/shell.json", base->base_path);
        if (initBaseDesign(base, filename) != 0)
            return;
    }
    parse_packages(base, base->name, base->base_path);
}

static struct basePLDesign *base_for_path(const char *path)
{
    int i;
    for (i = 0; i < MAX_WATCH; i++)
        if (!base_removed[i] && base_designs[i].base_path[0] &&
            path_is_within(path, base_designs[i].base_path))
            return &base_designs[i];
    return NULL;
}

static int path_disappeared(const char *path)
{
    struct stat info;
    return stat(path, &info) < 0 && (errno == ENOENT || errno == ENOTDIR);
}

static void firmware_dir_walk_locked(void)
{
    int i, j, k, wd;
    struct dirent *entry;
    /* Also reconcile missed deletions after an inotify queue overflow. */
    for (i = 0; i < MAX_WATCH; i++) {
        struct basePLDesign *base = &base_designs[i];
        if (!base_removed[i] && base->base_path[0] && path_disappeared(base->base_path))
            remove_base_design(base->base_path, base->parent_path, 1);
        if (base_removed[i] || !base->base_path[0])
            continue;
        for (j = 0; j < 10; j++)
            if (base->accel_list[j].path[0] && path_disappeared(base->accel_list[j].path))
                remove_base_design(base->accel_list[j].path, base->base_path, 0);
    }
    for (i = 0; i < MAX_WATCH; i++)
        if (active_watch[i].wd >= 0 && path_disappeared(active_watch[i].path))
            remove_watch_tree(active_watch[i].path);

    for (k = 0; k < config.number_locations; k++) {
        char *fwdir = config.firmware_locations[k];
        DIR *dir = opendir(fwdir);
        if (!dir)
            continue;
        if (!path_to_watch(fwdir) &&
            add_directory_watch("", fwdir, "", "") < 0) {
            closedir(dir);
            continue;
        }
        while ((entry = readdir(dir)) != NULL) {
            char path[WATCH_PATH_LEN];
            if (entry->d_type != DT_DIR || d_name_filter(entry->d_name) ||
                strstr(entry->d_name, ".dpkg-new"))
                continue;
            if (snprintf(path, sizeof(path), "%s/%s", fwdir, entry->d_name) >= (int)sizeof(path))
                continue;
            wd = add_directory_watch(entry->d_name, path, "", fwdir);
            if (wd < 0)
                continue;
            add_base_design(entry->d_name, path, fwdir, wd);
            refresh_base(findBaseDesign_path(path));
        }
        closedir(dir);
    }
}

void firmware_dir_walk(void)
{
    pthread_mutex_lock(&state_lock);
    firmware_dir_walk_locked();
    pthread_mutex_unlock(&state_lock);
}

static void process_firmware_event_locked(const struct inotify_event *event)
{
    struct watch *found;
    struct watch parent;
    struct basePLDesign *base;
    char path[WATCH_PATH_LEN];
    int wd;

    if (event->mask & IN_Q_OVERFLOW) {
        firmware_dir_walk_locked();
        return;
    }
    found = get_watch(event->wd);
    if (!found)
        return;
    parent = *found; /* Deletion may invalidate the original watch entry. */
    if (event->mask & IN_IGNORED) {
        memset(found, 0, sizeof(*found));
        found->wd = -1;
        return;
    }
    if (event->mask & (IN_DELETE_SELF | IN_MOVE_SELF)) {
        base = base_for_path(parent.path);
        if (base && !strcmp(base->base_path, parent.path))
            remove_base_design(parent.path, parent.parent_path, 1);
        else
            remove_base_design(parent.path, parent.parent_path, 0);
        /* If a firmware root disappears, retire each base under it too. */
        if (!parent.parent_path[0])
            firmware_dir_walk_locked();
        return;
    }
    if (!event->len)
        return;
    if (event->mask & IN_ISDIR) {
        if (d_name_filter(event->name) || strstr(event->name, ".dpkg-new") ||
            snprintf(path, sizeof(path), "%s/%s", parent.path, event->name) >= (int)sizeof(path))
            return;
        if (event->mask & (IN_DELETE | IN_MOVED_FROM)) {
            remove_base_design(path, parent.path, !parent.parent_path[0]);
            return;
        }
        if (event->mask & (IN_CREATE | IN_MOVED_TO)) {
            wd = add_directory_watch(event->name, path, parent.name, parent.path);
            if (wd < 0)
                return;
            if (!parent.parent_path[0])
                add_base_design(event->name, path, parent.path, wd);
            refresh_base(base_for_path(path));
        }
        return;
    }
    if (!(event->mask & (IN_CLOSE_WRITE | IN_MOVED_TO)))
        return;
    base = base_for_path(parent.path);
    if (!base)
        return;
    if (!strcmp(event->name, "shell.json") && !strcmp(base->base_path, parent.path))
        refresh_base(base);
    else if (!strcmp(event->name, "accel.json"))
        parse_packages(base, base->name, base->base_path);
}

static void process_firmware_event(const struct inotify_event *event)
{
    pthread_mutex_lock(&state_lock);
    process_firmware_event_locked(event);
    pthread_mutex_unlock(&state_lock);
}

#define BUF_LEN (10 * (sizeof(struct inotify_event) + NAME_MAX + 1))
static void *threadFunc(void *unused)
{
    char buf[BUF_LEN] __attribute__((aligned(8)));
    int j;
    ssize_t count;
    char *p;
    (void)unused;

    pthread_mutex_lock(&state_lock);
    active_watch = calloc(MAX_WATCH, sizeof(*active_watch));
    base_designs = calloc(MAX_WATCH, sizeof(*base_designs));
    init_status = 0;
    if (!active_watch || !base_designs) {
        init_status = -ENOMEM;
        goto initialized;
    }
    for (j = 0; j < MAX_WATCH; j++) {
        active_watch[j].wd = -1;
        base_designs[j].wd = -1;
    }
    inotifyFd = inotify_init1(IN_CLOEXEC);
    if (inotifyFd < 0) {
        init_status = -errno;
        goto initialized;
    }
    firmware_dir_walk_locked();
initialized:
    pthread_mutex_unlock(&state_lock);
    sem_post(&mutex);
    if (init_status)
        return NULL;

    for (;;) {
        /* A blocking read must leave client requests free to acquire state_lock. */
        count = read(inotifyFd, buf, sizeof(buf));
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0) {
            DFX_ERR("read() from inotify failed");
            return NULL;
        }
        for (p = buf; p + sizeof(struct inotify_event) <= buf + count; ) {
            struct inotify_event *event = (struct inotify_event *)p;
            size_t size = sizeof(*event) + event->len;
            if (size > (size_t)(buf + count - p))
                break;
            process_firmware_event(event);
            p += size; /* An unknown/deleted wd must not discard the rest of a batch. */
        }
    }
}

/* Only these entry points expose shared state to the request thread. */
int load_accelerator(const char *name)
{
    int ret;
    if (!name || !name[0])
        return -1;
    pthread_mutex_lock(&state_lock);
    ret = load_accelerator_locked(name);
    pthread_mutex_unlock(&state_lock);
    return ret;
}

int remove_accelerator(int slot)
{
    int ret;
    pthread_mutex_lock(&state_lock);
    ret = remove_accelerator_locked(slot);
    pthread_mutex_unlock(&state_lock);
    return ret;
}

char *listAccelerators(void)
{
    char *result;
    pthread_mutex_lock(&state_lock);
    result = listAccelerators_locked();
    pthread_mutex_unlock(&state_lock);
    return result;
}

void getRMInfo(void)
{
    pthread_mutex_lock(&state_lock);
    getRMInfo_locked();
    pthread_mutex_unlock(&state_lock);
}

int getFD(int slot, char *name)
{
    int ret;
    pthread_mutex_lock(&state_lock);
    ret = getFD_locked(slot, name);
    pthread_mutex_unlock(&state_lock);
    return ret;
}

int dfx_getFDs(int slot, int *fd)
{
    int ret;
    pthread_mutex_lock(&state_lock);
    ret = dfx_getFDs_locked(slot, fd);
    pthread_mutex_unlock(&state_lock);
    return ret;
}

void list_accel_uio(int slot, char *buf, size_t size)
{
    pthread_mutex_lock(&state_lock);
    list_accel_uio_locked(slot, buf, size);
    pthread_mutex_unlock(&state_lock);
}

char *get_accel_uio_by_name(int slot, const char *name)
{
    /* Preserve the existing borrowed-string API without leaking a slot pointer.
     * Valid until this thread's next call; callers must not free the result.
     */
    static __thread char snapshot[MAX_PATH_SIZE];
    char *path;
    pthread_mutex_lock(&state_lock);
    path = get_accel_uio_by_name_locked(slot, name);
    if (path) {
        if (strlen(path) >= sizeof(snapshot))
            path = NULL;
        else {
            strcpy(snapshot, path);
            path = snapshot;
        }
    }
    pthread_mutex_unlock(&state_lock);
    return path;
}

int dfx_init(void)
{
    pthread_t thread;
    int ret;
    strcpy(config.defaul_accel_name, "");
    strcpy(platform.boardName, "Xilinx board");
    if (sem_init(&mutex, 0, 0) < 0)
        return -errno;
    parse_config(CONFIG_PATH, &config);
    ret = pthread_create(&thread, NULL, threadFunc, NULL);
    if (ret) {
        sem_destroy(&mutex);
        return -ret;
    }
    pthread_detach(thread);
    do {
        ret = sem_wait(&mutex);
    } while (ret < 0 && errno == EINTR);
    if (ret < 0)
        return -errno;
    sem_destroy(&mutex);
    if (init_status)
        return init_status;
    if (config.defaul_accel_name[0])
        load_accelerator(config.defaul_accel_name);
    return 0;
}
