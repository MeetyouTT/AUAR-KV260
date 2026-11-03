/* Real helper and parser; only hardware entry points below are test doubles. */
#define _GNU_SOURCE
#include <assert.h>
#include <limits.h>
#include <poll.h>
#include <stdatomic.h>
#include <sys/types.h>
#include HELPER_FILE

static atomic_int unload_result, base_unload_result, load_calls, unload_calls;
static atomic_int stop_events;
static atomic_ulong event_calls, list_calls;
static char root_dir[512];

void init_accel(acapd_accel_t *accel, acapd_accel_pkg_hd_t *pkg)
{
    memset(accel, 0, sizeof(*accel));
    accel->pkg = pkg;
}

int load_accel(acapd_accel_t *accel, const char *shell, unsigned int async)
{
    assert(shell && !async && accel->pkg && accel->pkg->path);
    assert(!access(accel->pkg->path, F_OK));
    accel->sys_info.fpga_cfg_id = atomic_fetch_add(&load_calls, 1) + 100;
    accel->status = ACAPD_ACCEL_STATUS_INUSE;
    if (!strcmp(accel->type, "PL_DFX"))
        return 0;
    accel->num_ip_devs = 2;
    accel->ip_dev = calloc(2, sizeof(*accel->ip_dev));
    assert(accel->ip_dev);
    for (int i = 0; i < 2; i++) {
        accel->ip_dev[i].dev_name = strdup(i ? "test-config" : "test-uio");
        assert(accel->ip_dev[i].dev_name);
        snprintf(accel->ip_dev[i].path, sizeof(accel->ip_dev[i].path), "/dev/test-%d", i);
        accel->ip_dev[i].id = 80 + i;
    }
    return 0;
}

int remove_accel(acapd_accel_t *accel, unsigned int async)
{
    assert(!async && accel && accel->pkg && accel->pkg->path);
    atomic_fetch_add(&unload_calls, 1);
    int result = atomic_load(&unload_result);
    if (result)
        return result;
    for (int i = 0; i < accel->num_ip_devs; i++)
        free(accel->ip_dev[i].dev_name);
    free(accel->ip_dev);
    accel->ip_dev = NULL;
    accel->status = ACAPD_ACCEL_STATUS_UNLOADED;
    return 0;
}

int remove_base(int id) { assert(id >= 0); return atomic_load(&base_unload_result); }
int dfx_shell_fd_by_name(const char *name) { (void)name; return -1; }
char *dfx_shell_uio_by_name(const char *name) { (void)name; return NULL; }
void dfx_shell_uio_list(char *buf, size_t size) { if (size) buf[0] = 0; }

static int table_count(void)
{
    int count = 0;
    for (int i = 0; i < MAX_WATCH; i++)
        count += active_watch[i].wd >= 0;
    return count;
}

static int kernel_count(void)
{
    char path[128], line[4096];
    snprintf(path, sizeof(path), "/proc/self/fdinfo/%d", inotifyFd);
    FILE *file = fopen(path, "r");
    assert(file);
    int count = 0;
    while (fgets(line, sizeof(line), file))
        count += !strncmp(line, "inotify wd:", 11);
    assert(!fclose(file));
    return count;
}

static void join_path(char *dest, size_t size, const char *parent, const char *name)
{
    int n = snprintf(dest, size, "%s/%s", parent, name);
    assert(n > 0 && n < (int)size);
}

static void write_file(const char *path, const char *text)
{
    FILE *file = fopen(path, "w");
    assert(file && fputs(text, file) >= 0 && !fclose(file));
}

static void make_flat(const char *name)
{
    char dir[512], file[600];
    join_path(dir, sizeof(dir), root_dir, name);
    assert(!mkdir(dir, 0700));
    join_path(file, sizeof(file), dir, "shell.json");
    write_file(file, "{\"shell_type\":\"PL_FLAT\",\"num_pl_slots\":1,\"num_aie_slots\":0}\n");
}

static void remove_tree(const char *path)
{
    /* Only paths under the harness's newly created fixture may be removed. */
    assert(!strncmp(path, root_dir, strlen(root_dir)));
    assert(path[strlen(root_dir)] == '/');
    DIR *dir = opendir(path);
    assert(dir);
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, ".."))
            continue;
        char child[1024];
        struct stat info;
        join_path(child, sizeof(child), path, entry->d_name);
        assert(!lstat(child, &info));
        if (S_ISDIR(info.st_mode))
            remove_tree(child);
        else
            assert(!unlink(child));
    }
    assert(!closedir(dir) && !rmdir(path));
}

static void make_multi(void)
{
    char base[512], shell[600], child[512], slot[512], json[600], name[32];
    join_path(base, sizeof(base), root_dir, "multi");
    assert(!mkdir(base, 0700));
    join_path(shell, sizeof(shell), base, "shell.json");
    write_file(shell, "{\"shell_type\":\"PL_DFX\",\"num_pl_slots\":2,\"num_aie_slots\":0}\n");
    for (int i = 0; i < 3; i++) {
        snprintf(name, sizeof(name), "rm%d", i);
        join_path(child, sizeof(child), base, name);
        assert(!mkdir(child, 0700));
        for (int j = 0; j < 2; j++) {
            snprintf(name, sizeof(name), "rm%d_slot%d", i, j);
            join_path(slot, sizeof(slot), child, name);
            assert(!mkdir(slot, 0700));
            join_path(json, sizeof(json), slot, "accel.json");
            write_file(json, "{\"accel_type\":\"SIHA_PL_DFX\"}\n");
        }
    }
}

static void fixture(const char *root)
{
    assert(strlen(root) < sizeof(root_dir));
    strcpy(root_dir, root);
    assert(!mkdir(root_dir, 0700));
    active_watch = calloc(MAX_WATCH, sizeof(*active_watch));
    base_designs = calloc(MAX_WATCH, sizeof(*base_designs));
    assert(active_watch && base_designs);
    for (int i = 0; i < MAX_WATCH; i++)
        active_watch[i].wd = -1;
    config.number_locations = 1;
    config.firmware_locations = calloc(1, sizeof(char *));
    assert(config.firmware_locations);
    config.firmware_locations[0] = root_dir;
    inotifyFd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    assert(inotifyFd >= 0);
    make_flat("official-a"); make_flat("official-b"); make_flat("official-c");
    firmware_dir_walk();
    assert(table_count() == 4 && kernel_count() == 4);
}

static int child_count(const struct basePLDesign *base)
{
    int count = 0;
    for (int i = 0; i < 10; i++)
        count += base->accel_list[i].path[0] != 0;
    return count;
}

#ifdef LEGACY_SOURCE
static void legacy_delete(void)
{
    make_multi();
    firmware_dir_walk();
    struct basePLDesign *base = findBaseDesign("rm0");
    assert(base && child_count(base) == 3);
    int before = kernel_count();
    char path[512];
    join_path(path, sizeof(path), root_dir, "multi");
    remove_base_design(path, root_dir, 1);
    int remaining = child_count(base);
    assert(remaining == 2 && kernel_count() > 4);
    fprintf(stderr, "RESULT legacy-delete reproduced=1 stale_children=%d kernel_before=%d kernel_after=%d\n",
            remaining, before, kernel_count());
}
#else
static void check_consistency(void)
{
    for (int i = 0; i < MAX_WATCH; i++) {
        if (active_watch[i].wd < 0)
            continue;
        assert(memchr(active_watch[i].path, 0, sizeof(active_watch[i].path)));
        for (int j = i + 1; j < MAX_WATCH; j++)
            assert(active_watch[j].wd < 0 ||
                   (active_watch[j].wd != active_watch[i].wd &&
                    strcmp(active_watch[j].path, active_watch[i].path)));
    }
}

static void rescans(void)
{
    for (int i = 0; i < 10000; i++) {
        char *list = listAccelerators();
        assert(list && strstr(list, "official-a") && strstr(list, "official-c"));
        free(list);
        pthread_mutex_lock(&state_lock);
        assert(table_count() == 4 && kernel_count() == 4);
        check_consistency();
        pthread_mutex_unlock(&state_lock);
    }
    fprintf(stderr, "RESULT rescan rounds=10000 entries=4 kernel_watches=4\n");
}

static void parent_cleanup(void)
{
    char path[512], neighbor[512], replacement[512];
    make_flat("multi-neighbor");
    join_path(path, sizeof(path), root_dir, "multi");
    join_path(neighbor, sizeof(neighbor), root_dir, "multi-neighbor");
    join_path(replacement, sizeof(replacement), root_dir, "replacement");
    firmware_dir_walk();
    for (int cycle = 0; cycle < 200; cycle++) {
        make_multi();
        firmware_dir_walk();
        pthread_mutex_lock(&state_lock);
        struct basePLDesign *base = findBaseDesign("rm0");
        assert(base && child_count(base) == 3);
        assert(table_count() == 15 && kernel_count() == 15);
        remove_base_design(path, root_dir, 1);
        assert(!base->base_path[0] && !base->slots && child_count(base) == 0);
        assert(table_count() == 5 && kernel_count() == 5 && path_to_watch(neighbor));
        pthread_mutex_unlock(&state_lock);
        remove_tree(path);
        make_flat("replacement");
        firmware_dir_walk();
        pthread_mutex_lock(&state_lock);
        assert(findBaseDesign("replacement") == base && child_count(base) == 1);
        assert(!strcmp(base->accel_list[0].name, "replacement"));
        remove_base_design(replacement, root_dir, 1);
        pthread_mutex_unlock(&state_lock);
        remove_tree(replacement);
    }
    fprintf(stderr, "RESULT parent-delete cycles=200 children=3 descendants=6 remaining_watches=5 slot_reuse=passed\n");
}

static void active_lifecycle(void)
{
    char path[512], shell[600];
    assert(load_accelerator("official-a") == 0);
    struct basePLDesign *base = platform.active_base;
    slot_info_t *slot = base->slots[0];
    assert(slot->accel->pkg->path == slot->path);
    assert(getFD(0, "test-uio") == 80);
    int fds[2];
    assert(dfx_getFDs(0, fds) == 0 && fds[0] == 80 && fds[1] == 81);
    assert(getFD(-1, "test-uio") == -1 && dfx_getFDs(200, fds) == -1);
    assert(remove_accelerator(255) == -1 && remove_accelerator(-2) == -1);
    char *snapshot = get_accel_uio_by_name(0, "test-uio");
    assert(snapshot && !strcmp(snapshot, "/dev/test-0"));
    join_path(path, sizeof(path), root_dir, "official-a");
    join_path(shell, sizeof(shell), path, "shell.json");
    write_file(shell, "{\"shell_type\":\"PL_DFX\",\"num_pl_slots\":200}\n");
    char *list = listAccelerators();
    assert(base->num_pl_slots == 1 && !strcmp(base->type, "PL_FLAT") && base->slots[0] == slot);
    free(list);
    remove_tree(path);
    list = listAccelerators();
    assert(!strstr(list, "official-a") && platform.active_base == base && base->slots[0] == slot);
    free(list);
    make_flat("official-a");
    list = listAccelerators();
    assert(!strstr(list, "official-a")); free(list);
    atomic_store(&unload_result, -EIO);
    assert(remove_accelerator(0) == -EIO && platform.active_base == base && base->slots[0] == slot);
    atomic_store(&unload_result, ACAPD_ACCEL_INPROGRESS);
    assert(remove_accelerator(0) == ACAPD_ACCEL_INPROGRESS && base->active == 1);
    atomic_store(&unload_result, 0);
    assert(remove_accelerator(0) == 0 && !platform.active_base && !base->base_path[0]);
    assert(!strcmp(snapshot, "/dev/test-0"));
    list = listAccelerators();
    assert(strstr(list, "official-a")); free(list);
    make_multi(); firmware_dir_walk();
    assert(load_accelerator("rm0") == 0 && load_accelerator("rm1") == 1);
    base = platform.active_base;
    assert(base->slots[0]->accel->pkg->path == base->slots[0]->path);
    assert(base->slots[1]->accel->pkg->path == base->slots[1]->path);
    join_path(path, sizeof(path), root_dir, "multi");
    remove_tree(path); firmware_dir_walk();
    assert(platform.active_base == base && base->active == 2);
    assert(remove_accelerator(0) == 0 && remove_accelerator(1) == 0);
    assert(platform.active_base == base && base->active == 0);
    atomic_store(&base_unload_result, -EIO);
    assert(remove_accelerator(-1) == -EIO && platform.active_base == base);
    atomic_store(&base_unload_result, 0);
    assert(remove_accelerator(-1) == 0 && !platform.active_base && !base->base_path[0]);
    fprintf(stderr, "RESULT active-lifecycle flat=passed dfx=passed unload_failure_preserved=passed tls_snapshot=passed\n");
}

static void drain_events(void)
{
    char buffer[16384] __attribute__((aligned(8)));
    for (;;) {
        ssize_t count = read(inotifyFd, buffer, sizeof(buffer));
        if (count < 0 && errno == EINTR)
            continue;
        if (count < 0 && errno == EAGAIN)
            return;
        assert(count > 0);
        for (char *p = buffer; p < buffer + count;) {
            struct inotify_event *event = (struct inotify_event *)p;
            assert(sizeof(*event) + event->len <= (size_t)(buffer + count - p));
            process_firmware_event(event);
            atomic_fetch_add(&event_calls, 1);
            p += sizeof(*event) + event->len;
        }
    }
}

static void synthetic_event(int wd, uint32_t mask, const char *name)
{
    unsigned char storage[sizeof(struct inotify_event) + 256] __attribute__((aligned(8))) = {0};
    struct inotify_event *event = (struct inotify_event *)storage;
    event->wd = wd;
    event->mask = mask;
    if (name) {
        event->len = strlen(name) + 1;
        assert(event->len <= 256);
        strcpy(event->name, name);
    }
    process_firmware_event(event);
}

static void events_and_moves(void)
{
    char stage[512], arrived[512], renamed[512];
    drain_events();
    make_flat("staged.dpkg-new");
    join_path(stage, sizeof(stage), root_dir, "staged.dpkg-new");
    join_path(arrived, sizeof(arrived), root_dir, "arrived");
    join_path(renamed, sizeof(renamed), root_dir, "renamed");
    assert(!rename(stage, arrived));
    drain_events();
    assert(findBaseDesign("arrived") && table_count() == 5 && kernel_count() == 5);
    assert(!rename(arrived, renamed));
    drain_events();
    assert(findBaseDesign("renamed") && !path_to_watch(arrived));
    assert(table_count() == 5 && kernel_count() == 5);
    synthetic_event(INT_MAX, IN_CLOSE_WRITE, "accel.json");
    synthetic_event(-1, IN_CLOSE_WRITE, "shell.json");
    struct watch *watch = path_to_watch(renamed);
    assert(watch);
    synthetic_event(watch->wd, IN_CLOSE_WRITE, "shell.json");
    assert(findBaseDesign("renamed"));
    remove_tree(renamed);
    synthetic_event(-1, IN_Q_OVERFLOW, NULL);
    assert(!findBaseDesign("renamed") && table_count() == 4 && kernel_count() == 4);
    fprintf(stderr, "RESULT events moved_in=passed rename=passed unknown_wd=passed queue_overflow_reconcile=passed real_events=%lu\n",
            atomic_load(&event_calls));
}

static void flat_lifecycle(void)
{
    char path[512];
    join_path(path, sizeof(path), root_dir, "probe");
    for (int i = 0; i < 1000; i++) {
        make_flat("probe");
        drain_events();
        assert(findBaseDesign("probe") && table_count() == 5 && kernel_count() == 5);
        remove_tree(path);
        drain_events();
        assert(!path_to_watch(path) && table_count() == 4 && kernel_count() == 4);
    }
    fprintf(stderr, "RESULT lifecycle cycles=1000 entries=4 kernel_watches=4 real_events=%lu\n",
            atomic_load(&event_calls));
}

static void boundaries(void)
{
    assert(!close(inotifyFd));
    inotifyFd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    assert(inotifyFd >= 0);
    pthread_mutex_lock(&state_lock);
    memset(active_watch, 0, MAX_WATCH * sizeof(*active_watch));
    for (int i = 0; i < MAX_WATCH; i++) active_watch[i].wd = -1;
    assert(add_to_watch(-1, "bad", "/bad", "", "") == -1 && errno == EINVAL);
    assert(add_to_watch(1, NULL, "/bad", "", "") == -1 && errno == EINVAL);
    char name[64], path[WATCH_PATH_LEN], longpath[WATCH_PATH_LEN + 1];
    memset(name, 'n', sizeof(name) - 1); name[sizeof(name) - 1] = 0;
    memset(path, 'p', sizeof(path) - 1); path[sizeof(path) - 1] = 0;
    memset(longpath, 'p', sizeof(longpath) - 1); longpath[sizeof(longpath) - 1] = 0;
    assert(!add_to_watch(1, name, path, name, path));
    assert(add_to_watch(2, "long", longpath, "", "") == -1 && errno == ENAMETOOLONG);
    memset(active_watch, 0, MAX_WATCH * sizeof(*active_watch));
    for (int i = 0; i < MAX_WATCH; i++) active_watch[i].wd = -1;
    for (int i = 0; i < MAX_WATCH; i++) {
        snprintf(path, sizeof(path), "/fake/item-%d", i);
        assert(!add_to_watch(1000 + i, "item", path, "", "/fake"));
    }
    assert(!add_to_watch(1000, "item", "/fake/item-0", "", "/fake"));
    assert(table_count() == MAX_WATCH);
    assert(add_to_watch(5000, "new", "/fake/new", "", "/fake") == -1 && errno == ENOSPC);
    assert(add_directory_watch("", root_dir, "", "") == -1 && errno == ENOSPC);
    assert(kernel_count() == 0); /* No orphan kernel watch when metadata is full. */
    struct basePLDesign *base = &base_designs[10];
    for (int i = 0; i < 10; i++) {
        snprintf(name, sizeof(name), "child%d", i);
        snprintf(path, sizeof(path), "/fake/base/child%d", i);
        assert(add_accel_to_base(base, name, path, "/fake/base"));
    }
    memset(&base->accel_list[0], 0, sizeof(base->accel_list[0]));
    assert(add_accel_to_base(base, "child9", "/fake/base/child9", "/fake/base") == &base->accel_list[9]);
    assert(add_accel_to_base(base, "new", "/fake/base/new", "/fake/base") == &base->accel_list[0]);
    assert(!add_accel_to_base(base, "extra", "/fake/base/extra", "/fake/base") && errno == ENOSPC);
    pthread_mutex_unlock(&state_lock);
    assert(!get_accel_uio_by_name(-1, "test-uio") && !get_accel_uio_by_name(0, NULL));
    char tiny[1] = {'x'};
    list_accel_uio(-1, tiny, sizeof(tiny));
    assert(tiny[0] == 0);
    fprintf(stderr, "RESULT boundaries watch_capacity=500 accel_capacity=10 no_orphan_watch=passed invalid_slots=passed\n");
}

static void list_capacity(void)
{
    for (int i = 0; i < 60; i++) {
        char name[32]; snprintf(name, sizeof(name), "extra-app-%02d", i); make_flat(name);
    }
    char *list = listAccelerators();
    assert(list && strlen(list) < 8192 && strlen(list) > 7000);
    fprintf(stderr, "RESULT list-capacity packages=63 bytes=%zu bounded=passed\n", strlen(list));
    free(list);
}

static void *event_worker(void *arg)
{
    (void)arg;
    while (!atomic_load(&stop_events)) {
        struct pollfd descriptor = {.fd = inotifyFd, .events = POLLIN};
        int ret = poll(&descriptor, 1, 10);
        assert(ret >= 0 || errno == EINTR);
        if (ret > 0)
            drain_events();
    }
    drain_events();
    return NULL;
}

static void *list_worker(void *arg)
{
    (void)arg;
    for (int i = 0; i < 2000; i++) {
        char *list = listAccelerators();
        assert(list && strstr(list, "official-a") && strstr(list, "official-c"));
        free(list);
        char *path = get_accel_uio_by_name(0, "test-uio");
        if (path) assert(!strcmp(path, "/dev/test-0"));
        atomic_fetch_add(&list_calls, 1);
        pthread_mutex_lock(&state_lock);
        check_consistency();
        pthread_mutex_unlock(&state_lock);
    }
    return NULL;
}

static void *directory_worker(void *arg)
{
    long id = (long)arg;
    char name[32], renamed_name[32], first[512], second[512];
    snprintf(name, sizeof(name), "hot-%ld", id);
    snprintf(renamed_name, sizeof(renamed_name), "moved-%ld", id);
    join_path(first, sizeof(first), root_dir, name);
    join_path(second, sizeof(second), root_dir, renamed_name);
    for (int i = 0; i < 300; i++) {
        make_flat(name);
        assert(!rename(first, second));
        remove_tree(second);
    }
    return NULL;
}

static void *runtime_worker(void *arg)
{
    (void)arg;
    for (int i = 0; i < 1000; i++) {
        assert(load_accelerator("official-a") == 0);
        char *snapshot = get_accel_uio_by_name(0, "test-uio");
        assert(snapshot && !strcmp(snapshot, "/dev/test-0"));
        assert(remove_accelerator(0) == 0 && !strcmp(snapshot, "/dev/test-0"));
    }
    return NULL;
}

static void concurrency(void)
{
    pthread_t events, readers[4], writers[2], runtime;
    assert(!pthread_create(&events, NULL, event_worker, NULL));
    for (long i = 0; i < 4; i++) assert(!pthread_create(&readers[i], NULL, list_worker, (void *)i));
    for (long i = 0; i < 2; i++) assert(!pthread_create(&writers[i], NULL, directory_worker, (void *)i));
    assert(!pthread_create(&runtime, NULL, runtime_worker, NULL));
    for (int i = 0; i < 2; i++) assert(!pthread_join(writers[i], NULL));
    assert(!pthread_join(runtime, NULL));
    for (int i = 0; i < 4; i++) assert(!pthread_join(readers[i], NULL));
    atomic_store(&stop_events, 1);
    assert(!pthread_join(events, NULL));
    firmware_dir_walk();
    check_consistency();
    assert(!platform.active_base && table_count() == 4 && kernel_count() == 4);
    int bases = 0;
    for (int i = 0; i < MAX_WATCH; i++) bases += base_designs[i].base_path[0] != 0;
    assert(bases == 3);
    fprintf(stderr, "RESULT concurrent threads=8 lists=%lu directory_cycles=600 simulated_load_unload=1000 events=%lu entries=4 kernel_watches=4\n",
            atomic_load(&list_calls), atomic_load(&event_calls));
}
#endif

int main(int argc, char **argv)
{
    assert(argc == 3);
    fixture(argv[2]);
#ifdef LEGACY_SOURCE
    assert(!strcmp(argv[1], "legacy-delete")); legacy_delete();
#else
    if (!strcmp(argv[1], "rescan")) rescans();
    else if (!strcmp(argv[1], "parent-delete")) parent_cleanup();
    else if (!strcmp(argv[1], "active-lifecycle")) active_lifecycle();
    else if (!strcmp(argv[1], "events")) events_and_moves();
    else if (!strcmp(argv[1], "lifecycle")) flat_lifecycle();
    else if (!strcmp(argv[1], "boundaries")) boundaries();
    else if (!strcmp(argv[1], "list-capacity")) list_capacity();
    else if (!strcmp(argv[1], "concurrent")) concurrency();
    else abort();
#endif
    assert(!close(inotifyFd));
    for (int i = 0; i < MAX_WATCH; i++)
        free(base_designs[i].slots);
    free(active_watch); free(base_designs); free(config.firmware_locations);
    return 0;
}
