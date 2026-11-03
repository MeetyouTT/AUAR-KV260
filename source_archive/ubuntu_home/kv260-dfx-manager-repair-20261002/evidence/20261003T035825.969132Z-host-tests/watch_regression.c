/* Exercise the real fixed-source helper; no FPGA, MMIO, daemon or load calls. */
#include <assert.h>
#include <limits.h>
#include <sys/types.h>
#ifndef HELPER_FILE
#error HELPER_FILE must point to the original or repaired daemon_helper.c
#endif
#include HELPER_FILE

static int count_entries(void)
{
    int n = 0;
    for (int i = 0; i < MAX_WATCH; i++)
        n += active_watch[i].wd >= 0;
    return n;
}

static int count_kernel_watches(void)
{
    char path[128], line[4096];
    int n = 0;
    snprintf(path, sizeof(path), "/proc/self/fdinfo/%d", inotifyFd);
    FILE *f = fopen(path, "r");
    assert(f);
    while (fgets(line, sizeof(line), f))
        n += !strncmp(line, "inotify wd:", 11);
    assert(!fclose(f));
    return n;
}

static void reset_table(void)
{
    memset(active_watch, 0, MAX_WATCH * sizeof(*active_watch));
    for (int i = 0; i < MAX_WATCH; i++)
        active_watch[i].wd = -1;
}

static void create_app(const char *root, const char *name)
{
    char path[1024];
    snprintf(path, sizeof(path), "%s/%s", root, name);
    assert(!mkdir(path, 0700));
    snprintf(path, sizeof(path), "%s/%s/shell.json", root, name);
    FILE *f = fopen(path, "wx");
    assert(f);
    assert(fputs("{\"shell_type\":\"PL_FLAT\",\"num_pl_slots\":1,\"num_aie_slots\":0}\n", f) >= 0);
    assert(!fclose(f));
}

static void prepare_fixture(char *root)
{
    const char *names[] = {"k26-starter-kits", "kv260-benchmark-b4096", "dpu41-control", "kv260-benchmark-b4096-m3"};
    assert(!mkdir(root, 0700));
    for (unsigned i = 0; i < sizeof(names) / sizeof(names[0]); i++)
        create_app(root, names[i]);
    config.number_locations = 1;
    config.firmware_locations = calloc(1, sizeof(char *));
    assert(config.firmware_locations);
    config.firmware_locations[0] = root;
    inotifyFd = inotify_init1(IN_NONBLOCK | IN_CLOEXEC);
    assert(inotifyFd >= 0);
}

static void rescan(char *root, int legacy)
{
    prepare_fixture(root);
    int rounds = legacy ? 130 : 10000;
    for (int i = 0; i < rounds; i++) {
        char *listing = listAccelerators();
        assert(listing && strstr(listing, "kv260-benchmark-b4096-m3"));
        free(listing);
        if (!legacy) {
            assert(count_entries() == 5);
            for (int j = 0; j < MAX_WATCH; j++) {
                if (active_watch[j].wd < 0)
                    continue;
                for (int k = j + 1; k < MAX_WATCH; k++)
                    assert(active_watch[k].wd < 0 ||
                           (active_watch[k].wd != active_watch[j].wd &&
                            strcmp(active_watch[k].path, active_watch[j].path)));
            }
        }
    }
    int entries = count_entries(), watches = count_kernel_watches();
    assert(watches == 5);
    if (legacy)
        assert(entries == MAX_WATCH && entries > watches);
    else
        assert(entries == watches);
    fprintf(stderr, "RESULT rescan rounds=%d entries=%d kernel_watches=%d legacy_defect_reproduced=%d\n",
            rounds, entries, watches, legacy);
}

static void lifecycle(char *root)
{
    prepare_fixture(root);
    firmware_dir_walk();
    for (int i = 0; i < 1000; i++) {
        char path[1024], shell[1100];
        snprintf(path, sizeof(path), "%s/lifecycle-probe", root);
        snprintf(shell, sizeof(shell), "%s/shell.json", path);
        create_app(root, "lifecycle-probe");
        firmware_dir_walk();
        assert(count_entries() == 6 && count_kernel_watches() == 6);
        assert(path_to_watch(path));
        remove_base_design(path, root, 1);
        remove_watch(path);
        assert(!path_to_watch(path));
        assert(count_entries() == 5 && count_kernel_watches() == 5);
        assert(!unlink(shell));
        assert(!rmdir(path));
        firmware_dir_walk();
        assert(count_entries() == 5 && count_kernel_watches() == 5);
    }
    fprintf(stderr, "RESULT lifecycle cycles=1000 entries=%d kernel_watches=%d\n",
            count_entries(), count_kernel_watches());
}

static void boundaries(void)
{
    add_to_watch(10, "first", "/probe/first", "", "/probe");
    add_to_watch(20, "second", "/probe/second", "", "/probe");
    active_watch[0].wd = -1; /* A free slot occurs before the matching entry. */
    active_watch[0].path[0] = 0;
    add_to_watch(20, "second", "/probe/second", "", "/probe");
    assert(count_entries() == 1);
    add_to_watch(21, "second", "/probe/second", "", "/probe");
    assert(count_entries() == 1 && get_watch(21));
    add_to_watch(21, "renamed", "/probe/renamed", "", "/probe");
    assert(count_entries() == 1 && path_to_watch("/probe/renamed"));
    reset_table();
    for (int i = 0; i < MAX_WATCH; i++) {
        char path[64];
        snprintf(path, sizeof(path), "/probe/item-%d", i);
        add_to_watch(1000 + i, "item", path, "", "/probe");
    }
    assert(count_entries() == MAX_WATCH);
    add_to_watch(1000, "item", "/probe/item-0", "", "/probe");
    assert(count_entries() == MAX_WATCH); /* Re-registration succeeds even when full. */
    errno = 0;
    add_to_watch(5000, "overflow", "/probe/overflow", "", "/probe");
    assert(errno == ENOSPC && count_entries() == MAX_WATCH);
    reset_table();
    errno = 0;
    add_to_watch(-1, "bad", "/probe/bad", "", "/probe");
    assert(errno == EINVAL && count_entries() == 0);
    errno = 0;
    add_to_watch(1, NULL, "/probe/bad", "", "/probe");
    assert(errno == EINVAL && count_entries() == 0);
    char name[64], path[WATCH_PATH_LEN], longpath[WATCH_PATH_LEN + 1];
    memset(name, 'n', sizeof(name) - 1); name[sizeof(name) - 1] = 0;
    memset(path, 'p', sizeof(path) - 1); path[sizeof(path) - 1] = 0;
    add_to_watch(1, name, path, name, path);
    assert(count_entries() == 1);
    struct watch *w = get_watch(1);
    assert(w && !strcmp(w->path, path) && !strcmp(w->parent_name, name));
    memset(longpath, 'x', sizeof(longpath) - 1); longpath[sizeof(longpath) - 1] = 0;
    errno = 0;
    add_to_watch(2, "long", longpath, "", "/probe");
    assert(errno == ENAMETOOLONG && count_entries() == 1);
    remove_watch(path);
    assert(count_entries() == 0 && !path_to_watch(path));
    fprintf(stderr, "RESULT boundaries passed=1 capacity=%d\n", MAX_WATCH);
}

static void *registrations(void *arg)
{
    (void)arg;
    for (int i = 0; i < 10000; i++)
        add_to_watch(42, "shared", "/probe/shared", "", "/probe");
    return NULL;
}

static void concurrent_registrations(void)
{
    pthread_t threads[8];
    for (int i = 0; i < 8; i++)
        assert(!pthread_create(&threads[i], NULL, registrations, NULL));
    for (int i = 0; i < 8; i++)
        assert(!pthread_join(threads[i], NULL));
    assert(count_entries() == 1 && get_watch(42));
    fprintf(stderr, "RESULT concurrent threads=8 calls=80000 entries=1\n");
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    active_watch = calloc(MAX_WATCH, sizeof(*active_watch));
    base_designs = calloc(MAX_WATCH, sizeof(*base_designs));
    assert(active_watch && base_designs);
    reset_table();
    inotifyFd = -1;
    if (!strcmp(argv[1], "legacy")) rescan(argv[2], 1);
    else if (!strcmp(argv[1], "rescan")) rescan(argv[2], 0);
    else if (!strcmp(argv[1], "lifecycle")) lifecycle(argv[2]);
    else if (!strcmp(argv[1], "boundaries")) boundaries();
    else if (!strcmp(argv[1], "concurrent")) concurrent_registrations();
    else abort();
    if (inotifyFd >= 0) assert(!close(inotifyFd));
    free(config.firmware_locations);
    free(active_watch);
    free(base_designs);
    return 0;
}
