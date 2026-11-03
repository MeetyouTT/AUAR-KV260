#define _GNU_SOURCE 1
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

/* A normal CPython extension call holds the GIL throughout this small read.
 * No Py_BEGIN_ALLOW_THREADS and no ctypes wrapper are used. The returned
 * endpoints exclude tuple construction: callers MUST time the full call too.
 * Proc counters are not an atomic snapshot and runtime can lag the CPU clock.
 */
typedef struct {
    PyObject_HEAD
    int fd;
    pid_t pid;
    pid_t tid;
} Probe;

static int read_clock(clockid_t clock, uint64_t *out) {
    struct timespec value;
    if (clock_gettime(clock, &value) < 0) return -1;
    *out = (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
    return 0;
}

static int parse_counters(const char *raw, size_t size, uint64_t value[3]) {
    char buffer[257], *at, *end;
    if (!size || size > 256 || memchr(raw, '\0', size)) return -1;
    memcpy(buffer, raw, size);
    buffer[size] = '\0';
    at = buffer;
    for (int i = 0; i < 3; ++i) {
        while (*at == ' ' || *at == '\t' || *at == '\n') ++at;
        if (*at < '0' || *at > '9') return -1;
        errno = 0;
        unsigned long long parsed = strtoull(at, &end, 10);
        if (errno == ERANGE || end == at) return -1;
        value[i] = (uint64_t)parsed;
        at = end;
    }
    while (*at == ' ' || *at == '\t' || *at == '\n') ++at;
    return *at ? -1 : 0;
}

static PyObject *probe_new(PyTypeObject *type, PyObject *args, PyObject *kw) {
    (void)args; (void)kw;
    Probe *self = (Probe *)type->tp_alloc(type, 0);
    if (self) { self->fd = -1; self->pid = 0; self->tid = 0; }
    return (PyObject *)self;
}

static int probe_init(Probe *self, PyObject *args, PyObject *kw) {
    static char *keywords[] = {NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kw, ":Probe", keywords)) return -1;
    if (self->pid) {
        PyErr_SetString(PyExc_RuntimeError, "Probe cannot be initialized twice");
        return -1;
    }
    int fd = open("/proc/thread-self/schedstat", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) { PyErr_SetFromErrno(PyExc_OSError); return -1; }
    self->fd = fd;
    self->pid = getpid();
    self->tid = (pid_t)syscall(SYS_gettid);
    return 0;
}

static void close_fd(Probe *self) {
    int fd = self->fd;
    self->fd = -1;
    if (fd >= 0) (void)close(fd); /* Never retry close after EINTR on Linux. */
}

static void probe_dealloc(Probe *self) {
    close_fd(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *probe_close(Probe *self, PyObject *unused) {
    (void)unused;
    close_fd(self);
    Py_RETURN_NONE;
}

static PyObject *probe_owner(Probe *self, void *closure) {
    (void)closure;
    return Py_BuildValue("(ii)", (int)self->pid, (int)self->tid);
}

static PyObject *probe_closed(Probe *self, void *closure) {
    (void)closure;
    return PyBool_FromLong(self->fd < 0);
}

static PyObject *probe_sample(Probe *self, PyObject *unused) {
    (void)unused;
    uint64_t wall0, cpu0, wall1, cpu1, counters[3];
    struct rusage usage;
    char buffer[257];
    if (!PyGILState_Check()) {
        PyErr_SetString(PyExc_RuntimeError, "Sampling requires the calling interpreter GIL");
        return NULL;
    }
    if (self->fd < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Probe is closed");
        return NULL;
    }
    if (getpid() != self->pid || (pid_t)syscall(SYS_gettid) != self->tid) {
        PyErr_SetString(PyExc_RuntimeError, "Probe belongs to another process or native thread");
        return NULL;
    }
    if (read_clock(CLOCK_MONOTONIC, &wall0) < 0 ||
        read_clock(CLOCK_THREAD_CPUTIME_ID, &cpu0) < 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    ssize_t size = pread(self->fd, buffer, sizeof(buffer), 0);
    if (size < 0) return PyErr_SetFromErrno(PyExc_OSError);
    if (parse_counters(buffer, (size_t)size, counters) < 0) {
        PyErr_SetString(PyExc_ValueError, "Invalid calling-thread schedstat");
        return NULL;
    }
    if (getrusage(RUSAGE_THREAD, &usage) < 0 ||
        read_clock(CLOCK_THREAD_CPUTIME_ID, &cpu1) < 0 ||
        read_clock(CLOCK_MONOTONIC, &wall1) < 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    return Py_BuildValue("(iKKKKKllKK)", (int)self->tid,
        (unsigned long long)wall0, (unsigned long long)cpu0,
        (unsigned long long)counters[0], (unsigned long long)counters[1],
        (unsigned long long)counters[2], usage.ru_nvcsw, usage.ru_nivcsw,
        (unsigned long long)wall1, (unsigned long long)cpu1);
}

static PyMethodDef probe_methods[] = {
    {"sample", (PyCFunction)probe_sample, METH_NOARGS, "Read this owner's numeric counters while holding the GIL."},
    {"close", (PyCFunction)probe_close, METH_NOARGS, "Close the owned read-only descriptor; idempotent."},
    {NULL, NULL, 0, NULL}
};
static PyGetSetDef probe_properties[] = {
    {"owner", (getter)probe_owner, NULL, "Creating (pid, native tid).", NULL},
    {"closed", (getter)probe_closed, NULL, "Descriptor closed.", NULL},
    {NULL, NULL, NULL, NULL, NULL}
};
static PyTypeObject ProbeType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_aura_schedprobe.Probe",
    .tp_basicsize = sizeof(Probe),
    .tp_dealloc = (destructor)probe_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = "Read-only PID/TID-bound sampler. Not DPU hardware time or GIL attribution.",
    .tp_methods = probe_methods,
    .tp_getset = probe_properties,
    .tp_init = (initproc)probe_init,
    .tp_new = probe_new,
};
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_aura_schedprobe",
    .m_doc = "Numeric Linux thread counters. Endpoints are ordered, not atomic; no device owner.",
    .m_size = -1,
};
PyMODINIT_FUNC PyInit__aura_schedprobe(void) {
    if (PyType_Ready(&ProbeType) < 0) return NULL;
    PyObject *result = PyModule_Create(&module);
    if (!result) return NULL;
    Py_INCREF(&ProbeType);
    if (PyModule_AddObject(result, "Probe", (PyObject *)&ProbeType) < 0) {
        Py_DECREF(&ProbeType); Py_DECREF(result); return NULL;
    }
    return result;
}
