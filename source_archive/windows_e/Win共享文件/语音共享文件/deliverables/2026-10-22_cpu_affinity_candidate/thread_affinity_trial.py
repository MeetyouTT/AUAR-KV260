"""Opt-in, current-thread-only affinity experiment with a startup barrier.

No function in this module passes another PID or TID to sched_setaffinity.
The caller must use the pinned launcher; this module does not own any device.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import threading
import time


class AffinityFailure(RuntimeError):
    pass


def checked_policy(value, available):
    required = {'camera-detection', 'camera-face-targets', 'camera-live-preview', 'camera-identity'}
    if not isinstance(value, dict) or set(value) != {'expected_process_cpus', 'roles'}:
        raise ValueError('Explicit expected_process_cpus and roles are required')

    def cpus(items):
        if (not isinstance(items, list) or not items
                or any(type(n) is not int or n < 0 or n > 4095 for n in items)
                or len(set(items)) != len(items)):
            raise ValueError('CPU masks must be nonempty unique integer arrays')
        return frozenset(items)

    expected = cpus(value['expected_process_cpus'])
    if expected != frozenset(available):
        raise ValueError('Available CPU mask differs from the explicit experiment policy')
    roles = value['roles']
    if not isinstance(roles, dict) or set(roles) != required:
        raise ValueError('Only the four reviewed dual-model thread roles are supported')
    masks = {role: cpus(items) for role, items in roles.items()}
    if any(not mask <= expected for mask in masks.values()):
        raise ValueError('Requested CPU outside the process-allowed mask')
    inference = set().union(*(mask for role, mask in masks.items()
                              if role in {'camera-detection', 'camera-face-targets'}))
    preparation = set().union(*(mask for role, mask in masks.items()
                                if role not in {'camera-detection', 'camera-face-targets'}))
    if inference & preparation:
        raise ValueError('This experiment requires disjoint inference and preparation masks')
    return masks


def _starttime(path):
    # comm in /proc/*/stat can itself contain parentheses and spaces.
    body = Path(path).read_text().rsplit(')', 1)[1].split()
    return int(body[19])  # field 22, with the pid/comm fields removed


def current_identity():
    pid = os.getpid()
    tid = threading.get_native_id()
    status = Path('/proc/thread-self/status').read_text().splitlines()
    tgid = int(next(line.split()[1] for line in status if line.startswith('Tgid:')))
    status_tid = int(next(line.split()[1] for line in status if line.startswith('Pid:')))
    if tgid != pid or status_tid != tid:
        raise AffinityFailure('Calling thread does not belong to the recorded process')
    return {'pid': pid, 'tid': tid, 'process_starttime': _starttime('/proc/self/stat'),
            'thread_starttime': _starttime('/proc/thread-self/stat')}


class Journal:
    def __init__(self, directory):
        self.lock = threading.Lock()
        self.path = Path(directory) / ('affinity-%s.jsonl' % os.getpid())
        self.fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)

    def __call__(self, value):
        data = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
        if len(data) > 8192:
            raise AffinityFailure('Affinity journal entry exceeded its bound')
        with self.lock:
            if os.write(self.fd, data) != len(data):
                raise AffinityFailure('Affinity journal write was incomplete')

    def close(self):
        with self.lock:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None


class AffinityTrial:
    def __init__(self, masks, journal, *, startup_timeout=8., shutdown_timeout=3.,
                 get_affinity=os.sched_getaffinity, set_affinity=os.sched_setaffinity,
                 identity=current_identity, fatal=os._exit, clock=time.monotonic):
        self.masks = {role: frozenset(mask) for role, mask in masks.items()}
        self.journal = journal
        self.get_affinity, self.set_affinity = get_affinity, set_affinity
        self.identity, self.fatal, self.clock = identity, fatal, clock
        self.owner = identity()
        self.condition = threading.Condition()
        self.startup_timeout, self.shutdown_timeout = startup_timeout, shutdown_timeout
        self.deadline = None
        self.active = set()
        self.seen = {}
        self.committed = False
        self.failure = None
        self.aborting = False
        self.closed = False

    def _emit(self, event, role=None, identity=None, **fields):
        self.journal(dict(event=event, mono=self.clock(), role=role,
                          identity=identity or self.owner, **fields))

    def _fail(self, code):
        with self.condition:
            if self.failure is None:
                self.failure = str(code)
            self.condition.notify_all()

    def _same_process(self, identity):
        return (identity['pid'] == self.owner['pid']
                and identity['process_starttime'] == self.owner['process_starttime'])

    def _abort_after_restoration(self):
        with self.condition:
            if self.aborting:
                return
            self.aborting = True
            until = self.clock() + self.shutdown_timeout
            while self.active:
                remaining = until - self.clock()
                if remaining <= 0:
                    break
                self.condition.wait(remaining)
            remaining_roles = sorted(self.active)
        try:
            self._emit('ABORT_OWNED_PROCESS', reason=self.failure,
                       scopes_still_active=remaining_roles, exit_code=70)
        finally:
            # Only the calling experiment process; never pkill or another PID.
            self.fatal(70)

    def reject(self, code):
        self._fail(code)
        self._abort_after_restoration()

    @contextmanager
    def role(self, name):
        identity = None
        old = None
        attempted = registered = False
        try:
            identity = self.identity()
            if not self._same_process(identity):
                raise AffinityFailure('Process identity changed')
            with self.condition:
                if self.closed or self.failure or name not in self.masks or name in self.seen:
                    raise AffinityFailure('Unexpected, repeated or closed thread role')
                if self.deadline is None:
                    self.deadline = self.clock() + self.startup_timeout
                self.active.add(name)
                self.seen[name] = 'ENTERING'
                registered = True
            old = frozenset(self.get_affinity(0))
            requested = self.masks[name]
            if not old or not requested or not requested <= old:
                raise AffinityFailure('Current thread CPU mask no longer permits the policy')
            self._emit('APPLY_BEGIN', name, identity, old_cpus=sorted(old),
                       requested_cpus=sorted(requested))
            attempted = True
            self.set_affinity(0, requested)
            actual = frozenset(self.get_affinity(0))
            if actual != requested or self.identity() != identity:
                raise AffinityFailure('Applied affinity or calling thread identity differs')
            self._emit('APPLIED', name, identity, old_cpus=sorted(old), actual_cpus=sorted(actual))
            with self.condition:
                self.seen[name] = 'APPLIED'
                if set(self.seen) == set(self.masks) and all(s == 'APPLIED' for s in self.seen.values()):
                    self._emit('ALL_ROLES_COMMITTED', roles=sorted(self.seen))
                    self.committed = True
                    self.condition.notify_all()
                while not self.committed and not self.failure:
                    remaining = self.deadline - self.clock()
                    if remaining <= 0:
                        self._fail('Required thread startup deadline expired')
                        break
                    self.condition.wait(remaining)
                if self.failure:
                    raise AffinityFailure(self.failure)
            yield
        except AffinityFailure as exc:
            self._fail(str(exc))
        except Exception as exc:
            # A failure before the barrier is an affinity transaction failure.
            # After admission, original target exceptions retain their behavior.
            if not self.committed:
                self._fail('Affinity startup failed: ' + type(exc).__name__)
            else:
                raise
        finally:
            if attempted:
                try:
                    if self.identity() != identity:
                        raise AffinityFailure('Identity changed before current-thread restoration')
                    self.set_affinity(0, old)
                    restored = frozenset(self.get_affinity(0))
                    if restored != old:
                        raise AffinityFailure('Original CPU mask could not be restored exactly')
                    self._emit('RESTORED', name, identity, original_cpus=sorted(old),
                               actual_cpus=sorted(restored))
                except Exception as exc:
                    self._fail('Affinity restoration failed: ' + type(exc).__name__)
            if registered:
                with self.condition:
                    self.active.discard(name)
                    self.seen[name] = 'EXITED'
                    self.condition.notify_all()
            if self.failure:
                self._abort_after_restoration()

    def close(self):
        with self.condition:
            self.closed = True
            if not self.committed:
                self._fail('Pinned entrypoint returned before all configured roles started')
            until = self.clock() + self.shutdown_timeout
            while self.active and not self.failure:
                remaining = until - self.clock()
                if remaining <= 0:
                    self._fail('Pinned entrypoint returned with live affinity scopes')
                    break
                self.condition.wait(remaining)
        if self.failure:
            self._abort_after_restoration()
        else:
            self._emit('CLOSED', roles_exited=sorted(self.seen))
