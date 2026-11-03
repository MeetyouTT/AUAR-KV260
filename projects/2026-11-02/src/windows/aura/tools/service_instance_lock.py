"""Cooperative process-lifetime lock; stdlib only, no model or service actions.

Use one stable, local lockfile for every revision of the service. Never unlink
the file while any instance may run: Unix locks follow the opened inode.
"""
import errno
import os
from pathlib import Path
import stat
import threading


class ServiceAlreadyRunning(RuntimeError):
    """Another cooperating instance holds this service's lock."""


def _lock_fd(fd, *, platform=None):
    if (platform or os.name) == 'nt':
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        # The CRT explicitly permits locking beyond EOF. No sentinel write,
        # metadata overwrite or truncation is needed, even for an empty file.
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_fd(fd, *, platform=None):
    if (platform or os.name) == 'nt':
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


class ServiceInstanceLock:
    """Fail immediately on contention, holding only our own open lockfile.

    Acquire before ModelHost/ASR/TTS construction, keep through server shutdown.
    No PID files are trusted; process exit also releases the OS-owned lock.
    Existing non-cooperating service versions still require a port/ownership
    check before any startup GPU operation.
    """
    def __init__(self, path):
        self.path = Path(path)
        self._fd = None
        self._pid = None
        self._guard = threading.RLock()

    @property
    def held(self):
        with self._guard:
            return self._fd is not None and self._pid == os.getpid()

    def acquire(self):
        with self._guard:
            if self._fd is not None:
                raise RuntimeError('Service instance lock is already acquired')
            if self.path.is_symlink():
                raise ValueError('Use an owned regular lockfile, not a symlink')
            flags = os.O_CREAT | os.O_RDWR | getattr(os, 'O_BINARY', 0)
            flags |= getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(self.path, flags, 0o600)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ValueError('Service lockfile must be a regular file')
                os.set_inheritable(fd, False)
                try:
                    _lock_fd(fd)
                except OSError as exc:
                    if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK) or getattr(exc, 'winerror', None) == 33:
                        raise ServiceAlreadyRunning('Service instance lock is held: ' + str(self.path)) from None
                    raise
            except BaseException:
                os.close(fd)
                raise
            self._fd, self._pid = fd, os.getpid()
            return self

    def release(self):
        with self._guard:
            fd, pid = self._fd, self._pid
            self._fd = self._pid = None
            if fd is None:
                return
            try:
                # A forked child must not explicitly unlock the parent's
                # shared open-file description. It may close its own copy.
                if pid == os.getpid():
                    _unlock_fd(fd)
            finally:
                os.close(fd)

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass
