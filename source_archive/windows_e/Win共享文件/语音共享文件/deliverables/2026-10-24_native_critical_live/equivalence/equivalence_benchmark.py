"""Exclusive maintenance equivalence bench; never stops/starts any service.

Import is inert: it loads no board module, model, CDLL, camera or database.
Real execution requires an explicit plan and an inactive production camera.
Raw outputs stay in memory; JSON contains metadata, equality/counts and clocks.
"""
import argparse
import ctypes as C
from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import signal
import struct
import subprocess
import sys
import time
import uuid


SCHEMA = 'aura-native-equivalence-maintenance-1'
SERVICE = 'aura-camera-ui.service'
CASES = ('zero', 'public_prng_260')
_UNSAFE_HOLD = {}


class Blocked(RuntimeError):
    pass


class StopBenchmark(RuntimeError):
    pass


class UnsafeRetained(RuntimeError):
    native_execution_unknown = True


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned(pin):
    if not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}:
        raise Blocked('Explicit path/SHA256 pin required')
    digest = pin['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise Blocked('Lowercase SHA256 required')
    path = Path(pin['path'])
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or sha256(path) != digest:
        raise Blocked('Pinned artifact missing, redirected or changed')
    return path.resolve()


def validate_plan(plan):
    if plan.get('schema') != SCHEMA or plan.get('purpose') != 'isolated_model_equivalence':
        raise Blocked('Explicit isolated maintenance scope required')
    if str(uuid.UUID(plan['expected_boot_id'])) != plan['expected_boot_id']:
        raise Blocked('Canonical expected boot ID required')
    if plan.get('camera_service') != SERVICE:
        raise Blocked('Only the project production camera service is supported')
    if plan.get('cases') != list(CASES):
        raise Blocked('Exactly the two public synthetic cases are required')
    if plan.get('primary_period_ns') != 100_000_000:
        raise Blocked('The maintenance primary deadline must remain 100ms')
    if plan.get('yolo_geometry') != [640, 480, 1920]:
        raise Blocked('Pinned public BGR geometry required')
    specs = plan.get('models', [])
    if [s.get('task') for s in specs] != ['yunet', 'sface']:
        raise Blocked('Both optional models in a fixed order are required')
    for spec in specs:
        if set(spec) - {'task', 'model', 'model_sha256', 'manifest', 'manifest_sha256', 'source_ttl_ns'}:
            raise Blocked('Only model pins and existing source TTL belong in a benchmark model spec')
        if type(spec.get('source_ttl_ns')) is not int or not 0 < spec['source_ttl_ns'] <= 1_000_000_000:
            raise Blocked('Explicit bounded existing source TTL required')
    config = plan.get('yolo_owner_config', {})
    if set(config) - {'model', 'model_sha256', 'model_config_sha256', 'native_library',
                      'native_sha256', 'classes', 'score_threshold', 'person_nms_iou', 'arch_fingerprint'}:
        raise Blocked('Only the original YOLO constructor configuration is allowed')
    if (config.get('classes') != ['person'] or config.get('score_threshold') not in (.1, .3) or
            config.get('person_nms_iou', .45) != .45 or
            config.get('arch_fingerprint') != '0x101000056010407'):
        raise Blocked('Original person-only YOLO configuration required')


class SystemGuard:
    def __init__(self, plan):
        self.plan = plan

    def check(self):
        if os.geteuid() != 0:
            raise Blocked('Real maintenance execution requires the board owner account')
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if boot != self.plan['expected_boot_id']:
            raise Blocked('Kernel boot changed')
        run = subprocess.run(['systemctl', 'show', SERVICE, '--property=LoadState',
            '--property=ActiveState', '--property=SubState', '--property=MainPID'],
            capture_output=True, text=True, timeout=5)
        fields = dict(line.split('=', 1) for line in run.stdout.splitlines() if '=' in line)
        if run.returncode or any(fields.get(k) != v for k, v in {
                'LoadState': 'loaded', 'ActiveState': 'inactive', 'SubState': 'dead', 'MainPID': '0'}.items()):
            raise Blocked('Production camera must already be inactive with MainPID=0')
        return {'boot_id': boot, 'camera_service': SERVICE, 'active_state': 'inactive', 'main_pid': 0}


class Journal:
    def __init__(self, directory):
        self.directory = Path(directory)

    def write(self, value):
        target = self.directory / 'checkpoint.json'
        temporary = self.directory / 'checkpoint.tmp'
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n');handle.flush();os.fsync(handle.fileno())
        os.replace(temporary, target)


def public_bytes(count, case):
    if case == 'zero':
        return bytes(count)
    if case != 'public_prng_260':
        raise Blocked('Private/unknown input source refused')
    rng = random.Random(260)
    return bytes(rng.randrange(256) for _ in range(count))


def byte_count(meta):
    size = 1
    dims = meta.get('dims')
    if meta.get('dtype') != 'xint8' or not isinstance(dims, list) or not 1 <= len(dims) <= 8 or dims[0] != 1:
        raise StopBenchmark('Unexpected INT8 metadata')
    for value in dims:
        if type(value) is not int or value <= 0:
            raise StopBenchmark('Invalid tensor dimension')
        size *= value
    if size > 64 * 1024 ** 2:
        raise StopBenchmark('Tensor exceeds reviewed buffer bounds')
    return size


def compare_bytes(left, right):
    if set(left) != set(right):
        raise StopBenchmark('Output tensor names differ')
    rows = []
    for name in sorted(left):
        a, b = left[name], right[name]
        if not isinstance(a, bytes) or not isinstance(b, bytes) or len(a) != len(b):
            raise StopBenchmark('Output byte counts differ')
        differences = sum(x != y for x, y in zip(a, b))
        rows.append({'tensor': name, 'compared_bytes': len(a), 'differing_bytes': differences,
                     'byte_equal': differences == 0})
    return rows


def yolo_bytes(rows):
    if len(rows) > 16 or any(len(row) != 6 or not all(math.isfinite(float(v)) for v in row) for row in rows):
        raise StopBenchmark('Original YOLO output contract differs')
    return b''.join(struct.pack('<6f', *row) for row in rows)


@dataclass
class LegacyResult:
    outputs: dict
    wall_ns: int


class LegacyRaw:
    """PinnedRunner's exact native runner, with caller-owned raw INT8 buffers."""
    def __init__(self, pinned_runner, numpy):
        self.pinned = pinned_runner
        self.np = numpy
        self.inputs = [self.meta(t) for t in pinned_runner.inputs]
        self.outputs = [self.meta(t) for t in pinned_runner.outputs]
        self.pending = None

    @staticmethod
    def meta(tensor):
        return {'name': tensor.name, 'dims': list(tensor.dims), 'dtype': str(tensor.dtype),
                'fix_point': tensor.get_attr('fix_point')}

    def execute_raw(self, source):
        np = self.np
        data = np.frombuffer(source, dtype=np.int8).copy().reshape(self.inputs[0]['dims'])
        outputs = [np.empty(tuple(m['dims']), dtype=np.int8) for m in self.outputs]
        self.pending = (data, outputs)
        began = time.monotonic_ns()
        try:
            job = self.pinned.runner.execute_async([data], outputs)
            status = self.pinned.runner.wait(job)
            if status != 0:
                raise UnsafeRetained('Legacy VART wait did not confirm completion')
        except BaseException as exc:
            raise UnsafeRetained('Legacy VART completion unconfirmed; resources retained') from exc
        wall = time.monotonic_ns() - began
        # wait(status=0) is proven before CPU conversion or possible validation.
        self.pending = None
        return LegacyResult({m['name']: a.tobytes() for m, a in zip(self.outputs, outputs)}, wall)

    def close(self):
        if self.pending is not None:
            raise UnsafeRetained('Legacy in-flight buffers cannot be destroyed')
        self.pinned.close()


class RealDependencies:
    def __init__(self, plan):
        self.plan = plan
        artifacts = plan['artifacts']
        self.pins = {name: pinned(pin) for name, pin in artifacts.items()}
        for key in ('legacy', 'candidate'):
            row = plan['source_sets'][key]
            root = Path(row['root']).resolve(strict=True)
            manifest = json.loads(pinned(row['manifest']).read_text())['files']
            actual = {str(p.relative_to(root)) for p in root.rglob('*.py')}
            if set(manifest) != actual:
                raise Blocked('Complete source closure differs from pinned manifest')
            for relative, digest in manifest.items():
                if Path(relative).is_absolute() or '..' in Path(relative).parts:
                    raise Blocked('Invalid source closure path')
                path = root / relative
                if path.is_symlink() or not path.is_file() or sha256(path) != digest:
                    raise Blocked('Pinned Python source closure changed')
            row['resolved_root'] = str(root)
        legacy = Path(plan['source_sets']['legacy']['resolved_root'])
        candidate = Path(plan['source_sets']['candidate']['resolved_root'])
        for name, expected in {'legacy_yolo': legacy / 'board/vision/yolo_dpu.py',
                'legacy_runtime': legacy / 'board/vision/dpu_vision_runtime.py',
                'candidate_binding': candidate / 'board/vision/native_binding.py',
                'candidate_protection': candidate / 'board/vision/native_protection.py'}.items():
            if self.pins[name] != expected:
                raise Blocked('An execution module is outside the reviewed complete source closure')
        for spec in plan['models']:
            for key in ('model', 'manifest'):
                pinned({'path': spec[key], 'sha256': spec[key + '_sha256']})
        owner = plan['yolo_owner_config']
        for key in ('model', 'native_library'):
            pinned({'path': owner[key], 'sha256': owner['native_sha256' if key == 'native_library' else 'model_sha256']})
        pinned({'path': str(Path(owner['model']).with_suffix('.prototxt')),
                'sha256': owner['model_config_sha256']})
        self.loaded = False

    def load(self):
        if any(name == 'board' or name.startswith('board.') or name == 'common' or name.startswith('common.')
               for name in sys.modules):
            raise Blocked('The benchmark must start in a fresh Python interpreter')
        sys.path[:0] = [self.plan['source_sets']['candidate']['resolved_root'],
                        self.plan['source_sets']['legacy']['resolved_root']]
        try:
            self.binding = importlib.import_module('board.vision.native_binding')
            self.protection = importlib.import_module('board.vision.native_protection')
        except (ImportError, SyntaxError) as exc:
            raise Blocked('Candidate native v2 Python modules are incomplete') from exc
        for module, key in [(self.binding, 'candidate_binding'), (self.protection, 'candidate_protection')]:
            if Path(module.__file__).resolve() != self.pins[key]:
                raise Blocked('Imported candidate module differs from its pin')
        if (not hasattr(self.binding, 'NativeContext') or not hasattr(self.binding, 'NativeRunner') or
                not all(hasattr(self.binding.NativeContext, n) for n in
                    ('restore_seed', 'confirm_result', 'adopt_yolo', 'execute_yolo', 'snapshot', 'close')) or
                not hasattr(self.binding.NativeRunner, 'execute_encoded')):
            raise Blocked('Required native v2 API has not been implemented')
        if not hasattr(self.protection, 'isolated_maintenance_seed'):
            raise Blocked('Explicit isolated maintenance seed helper is missing')
        # Query only constant ABI/sizeof functions before constructing the old
        # owner or any model. A missing v2 API is BLOCKED, not a fake success.
        try:
            self.abi_library = C.CDLL(str(self.pins['bridge']))
            probe = self.binding.NativeContext.__new__(self.binding.NativeContext)
            probe.native = self.abi_library
            probe._configure()
            for function, expected in [('abi', 2), ('report_size', C.sizeof(self.binding.Report)),
                    ('state_size', C.sizeof(self.binding.State)), ('seed_size', C.sizeof(self.binding.Seed)),
                    ('recovery_size', C.sizeof(self.binding.Recovery)), ('ack_size', C.sizeof(self.binding.Ack))]:
                if getattr(self.abi_library, 'aura_native_' + function)() != expected:
                    raise Blocked('Candidate native library is not the matching complete v2 ABI')
        except (AttributeError, OSError) as exc:
            raise Blocked('Candidate native v2 API is unavailable before model creation') from exc
        self.yolo_module = self._module('equivalence_legacy_yolo', self.pins['legacy_yolo'])
        self.runtime = self._module('equivalence_legacy_runtime', self.pins['legacy_runtime'])
        import numpy
        self.np = numpy
        self.loaded = True

    @staticmethod
    def _module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def owner(self):
        return self.yolo_module.DpuYoloX(self.plan['yolo_owner_config'])

    def legacy_yolo(self, owner, bgr):
        source = (C.c_ubyte * len(bgr)).from_buffer_copy(bgr)
        output, count = (C.c_float * (16 * 6))(), C.c_int()
        owner._equivalence_pending = (source, output, count)
        began = time.monotonic_ns()
        try:
            with owner.lock:
                status = owner.native.aura_yolox_detect(owner.handle, source, 640, 480, 1920,
                    output, 16, 0, C.byref(count))
            if status != 0:
                raise UnsafeRetained('Original YOLO library did not confirm successful completion')
        except BaseException as exc:
            raise UnsafeRetained('Original YOLO native call is unconfirmed') from exc
        wall = time.monotonic_ns() - began
        owner._equivalence_pending = None
        if not 0 <= count.value <= 16:
            raise StopBenchmark('Original YOLO count differs from fixed capacity')
        rows = tuple(tuple(output[i * 6:i * 6 + 6]) for i in range(count.value))
        return rows, wall

    def context(self, owner):
        return self.binding.NativeContext(owner, self.pins['bridge'], self.plan['artifacts']['bridge']['sha256'])

    def maintenance_seed(self, now):
        return self.protection.isolated_maintenance_seed(boot_id=self.plan['expected_boot_id'],
            captured_mono_ns=now,
            production_snapshot_sha256=self.plan['artifacts']['production_snapshot']['sha256'])

    def legacy(self, owner, spec):
        return LegacyRaw(self.runtime.PinnedRunner(spec['model'], spec['manifest'], owner), self.np)

    def native_runner(self, context, spec):
        return self.binding.NativeRunner(context, spec['task'], spec['model'], spec['model_sha256'],
            spec['manifest'], spec['manifest_sha256'])


class Benchmark:
    def __init__(self, plan, dependencies, guard, journal, clock=time.monotonic_ns):
        self.plan, self.dependencies, self.guard, self.journal, self.clock = plan, dependencies, guard, journal, clock
        self.owner = self.context = None
        self.legacy_runners, self.native_runners, self.inputs = [], [], {}
        self.report = {'schema': SCHEMA, 'purpose': 'isolated_model_equivalence',
            'input_scope': 'public_synthetic_only', 'accuracy_evaluated': False,
            'utilization_or_speedup_evaluated': False, 'service_actions_performed': False,
            'passed': False, 'unsafe': False, 'cleanup_confirmed': False,
            'pairs': [], 'primary_anchors': 0, 'completed_calls': {'legacy_yolo': 0, 'native_yolo': 0,
                'legacy_optional': 0, 'native_optional': 0}, 'halt_reason': None}
        self.stage = 'preflight'

    def checkpoint(self, stage, *, unconfirmed=False, unsafe=False):
        self.stage = stage
        self.journal.write({'schema': SCHEMA, 'stage': stage,
            'completion_unconfirmed': unconfirmed, 'unsafe': unsafe,
            'owner_must_remain_alive': unsafe or unconfirmed,
            'monotonic_ns': self.clock()})

    def invoke(self, stage, callback):
        self.checkpoint(stage, unconfirmed=True)
        try:
            result = callback()
        except BaseException as exc:
            if (getattr(exc, 'native_execution_unknown', False) or
                    getattr(self.context, 'quarantined', False) or not isinstance(exc, (ValueError, Blocked, StopBenchmark))):
                raise UnsafeRetained('A native call result is unconfirmed') from exc
            self.checkpoint(stage + ':rejected_before_submission')
            raise
        self.checkpoint(stage + ':confirmed')
        return result

    @staticmethod
    def clean_state(state):
        if state.get('abi_version') != 2 or state.get('seed_loaded') != 1 or state.get('fenced') or state.get('active'):
            raise StopBenchmark('Native v2 seed was not accepted in a quiescent context')
        for name in ('admissions', 'overruns', 'completed', 'native_failures', 'not_submitted', 'disabled'):
            if state.get(name) != [0, 0, 0]:
                raise StopBenchmark('Maintenance seed is not a separate clean counter domain')
        if state.get('primary_calls') or state.get('primary_period_overruns'):
            raise StopBenchmark('Maintenance seed contains prior production activity')
        for recovery in state.get('recovery', []):
            if any(recovery.get(k) for k in ('phase', 'faults', 'attempts', 'recoveries', 'attempt_count', 'history_opaque')):
                raise StopBenchmark('Maintenance seed would alter prior protection history')
        if len(state.get('recovery', [])) != 2:
            raise StopBenchmark('Independent recovery domains are required')

    def check_execution(self, execution):
        r = execution.report
        self.report['last_native_report'] = dict(r)
        if (r.get('outcome') == 5 or (r.get('submitted') and
                (not r.get('completed') or r.get('native_status') != 0))):
            raise UnsafeRetained('Native completion report is unconfirmed')
        if r.get('hardcap') or r.get('guard'):
            raise StopBenchmark('Native cap/guard protection fired; no further cases are allowed')
        if not execution.native_usable:
            raise StopBenchmark('Native admission/result/TTL refused; no retry is allowed')
        return execution

    def retain_unsafe(self, reason):
        # Establish process-lifetime references BEFORE fallible filesystem I/O.
        self.report['passed'] = False
        self.report['unsafe'] = True
        self.report['halt_reason'] = reason
        _UNSAFE_HOLD[id(self)] = self
        try:
            self.checkpoint(self.stage + ':UNSAFE_HOLD', unconfirmed=True, unsafe=True)
        except BaseException:
            self.report['unsafe_marker_write_failed'] = True
        return self.report

    def new_yolo(self, case, *, anchor=False):
        now = self.clock()
        result = self.invoke('native_yolo:' + case, lambda: self.context.execute_yolo(self.inputs['yolo'][case],
            width=640, height=480, stride=1920, source_expires_ns=now + 1_000_000_000,
            primary_finish_ns=now + self.plan['primary_period_ns']))
        self.check_execution(result)
        self.report['completed_calls']['native_yolo'] += 1
        if anchor:self.report['primary_anchors'] += 1
        if self.context.snapshot().get('primary_period_overruns'):
            raise StopBenchmark('The maintenance primary deadline was missed')
        return result

    def run(self):
        validate_plan(self.plan)
        self.report['preflight'] = self.guard.check()
        # Generate public inputs before any submission/TTL interval.
        self.inputs['yolo'] = {case: public_bytes(640 * 480 * 3, case) for case in CASES}
        try:
            self.owner = self.invoke('original_owner_create', self.dependencies.owner)
            # Original library baseline doubles as startup self-check. No raw
            # original detector handle is used again after ownership adoption.
            yolo_old = {}
            for case in CASES:
                self.guard.check()
                yolo_old[case] = self.invoke('legacy_yolo:' + case,
                    lambda case=case: self.dependencies.legacy_yolo(self.owner, self.inputs['yolo'][case]))
                yolo_bytes(yolo_old[case][0])
                self.report['completed_calls']['legacy_yolo'] += 1
            self.context = self.invoke('native_context_create', lambda: self.dependencies.context(self.owner))
            seed = self.dependencies.maintenance_seed(self.clock())
            if seed.get('purpose') != 'isolated_model_equivalence':
                raise StopBenchmark('Only a separate maintenance seed may be used')
            self.invoke('restore_maintenance_seed', lambda: self.context.restore_seed(seed))
            self.clean_state(self.context.snapshot())
            self.invoke('adopt_original_yolo', self.context.adopt_yolo)
            for case in CASES:
                self.guard.check()
                result = self.new_yolo(case)
                old_rows, old_wall = yolo_old[case]
                equal = yolo_bytes(old_rows) == yolo_bytes(result.outputs)
                self.report['pairs'].append({'task': 'yolo', 'case': case,
                    'legacy_count': len(old_rows), 'native_count': len(result.outputs), 'byte_equal': equal,
                    'compared_output_bytes': len(yolo_bytes(old_rows)), 'legacy_wall_ns': old_wall,
                    'native_call_returned_ns': result.returned_mono_ns,
                    'native_lease_ns': result.report['release_decision_ns'] - result.report['start_ns']})
                if not equal:raise StopBenchmark('YOLO raw row/count equality failed')
            for spec in self.plan['models']:
                old = self.invoke('legacy_runner_create:' + spec['task'], lambda spec=spec: self.dependencies.legacy(self.owner, spec))
                self.legacy_runners.append(old)
                new = self.invoke('native_runner_create:' + spec['task'], lambda spec=spec: self.dependencies.native_runner(self.context, spec))
                self.native_runners.append(new)
                if (old.inputs != new.inputs or {m['name']: m for m in old.outputs} != {m['name']: m for m in new.outputs} or
                        len({m['name'] for m in old.outputs}) != len(old.outputs)):
                    raise StopBenchmark('Raw old/new tensor interfaces differ')
                size = byte_count(old.inputs[0])
                for case in CASES:
                    source = public_bytes(size, case)
                    self.inputs[(spec['task'], case)] = source
                    self.guard.check()
                    # A bounded, reported real primary call establishes a real
                    # 100ms schedule window. Never invent an unlimited deadline.
                    # Complete the legacy reference before opening the next
                    # real primary window; reference work is not new-path
                    # execution occupancy and must not spend its admission gap.
                    baseline = self.invoke('legacy_optional:' + spec['task'] + ':' + case,
                        lambda source=source: old.execute_raw(source))
                    self.report['completed_calls']['legacy_optional'] += 1
                    self.new_yolo('zero', anchor=True)
                    now = self.clock()
                    result = self.invoke('native_optional:' + spec['task'] + ':' + case,
                        lambda source=source: new.execute_encoded(source, source_expires_ns=now + spec['source_ttl_ns']))
                    self.check_execution(result)
                    self.report['completed_calls']['native_optional'] += 1
                    result = self.invoke('native_ack:' + spec['task'] + ':' + case,
                        lambda result=result: self.context.confirm_result(result))
                    self.check_execution(result)
                    if not result.usable:
                        raise StopBenchmark('Maintenance result remains in probation or unavailable')
                    native = {m['name']: raw for m, raw in zip(new.outputs, result.outputs)}
                    if len(result.outputs) != len(new.outputs):raise StopBenchmark('Native raw output count differs')
                    for meta in old.outputs:
                        if len(baseline.outputs[meta['name']]) != byte_count(meta):
                            raise StopBenchmark('Legacy raw output byte count differs')
                    compared = compare_bytes(baseline.outputs, native)
                    self.report['pairs'].append({'task': spec['task'], 'case': case,
                        'input_bytes': size, 'public_seed': 260 if case != 'zero' else None,
                        'raw_tensors': compared, 'byte_equal': all(row['byte_equal'] for row in compared),
                        'legacy_execute_wait_ns': baseline.wall_ns,
                        'native_lease_ns': result.report['release_decision_ns'] - result.report['start_ns'],
                        'native_returned_mono_ns': result.returned_mono_ns})
                    if not all(row['byte_equal'] for row in compared):
                        raise StopBenchmark('Raw INT8 tensor equality failed')
            self.report['passed'] = True
        except UnsafeRetained:
            return self.retain_unsafe('completion_unconfirmed_resources_retained')
        except (StopBenchmark, Blocked) as exc:
            self.report['halt_reason'] = str(exc)
        except BaseException:
            # Outside an invoke means no new native call was submitted. Existing
            # resources are nevertheless preserved if the binding is uncertain.
            if getattr(self.context, 'quarantined', False):
                return self.retain_unsafe('binding_quarantined_resources_retained')
            self.report['halt_reason'] = 'cpu_validation_or_interruption'
        try:
            for runner in reversed(self.native_runners):
                self.invoke('native_runner_close', runner.close)
            for runner in reversed(self.legacy_runners):
                self.invoke('legacy_runner_close', runner.close)
            if self.context is not None:self.invoke('native_context_close', self.context.close)
            if self.owner is not None and getattr(self.owner, 'ownership', None) is not None:
                self.invoke('original_owner_close', self.owner.close)
            self.report['cleanup_confirmed'] = True
            self.checkpoint('finished_confirmed_idle')
        except BaseException:
            return self.retain_unsafe('cleanup_unconfirmed_resources_retained')
        return self.report


def hold_unsafe_owner():
    # A SIGTERM timeout must not silently discard unconfirmed buffers and free
    # the project owner lock. Root must inspect the marker and contain it.
    def keep_resources(_signal, _frame):
        sys.stderr.write('UNSAFE: owner retained; automatic termination refused\n');sys.stderr.flush()
    signal.signal(signal.SIGTERM, keep_resources)
    signal.signal(signal.SIGINT, keep_resources)
    while True:
        signal.pause()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--execute-maintenance', action='store_true')
    args = parser.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text())
    validate_plan(plan)
    guard = SystemGuard(plan)
    guard.check()
    dependencies = RealDependencies(plan)
    if not args.execute_maintenance:
        print(json.dumps({'pins_and_service_preconditions_passed': True, 'execution_readiness_verified': False,
                          'candidate_library_loaded': False, 'models_loaded': False,
                          'services_changed': False, 'scope': 'read-only pins/preconditions only'}))
        return 0
    target = Path(args.output_directory)
    target.mkdir(mode=0o750, parents=False, exist_ok=False)
    dependencies.load()
    # Handle cancellation through Python containment/cleanup, including the
    # interval between detecting uncertainty and entering the permanent hold.
    def cancel_or_hold(_signal, _frame):
        if _UNSAFE_HOLD:
            return
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, cancel_or_hold)
    signal.signal(signal.SIGINT, cancel_or_hold)
    benchmark = Benchmark(plan, dependencies, guard, Journal(target))
    report = benchmark.run()
    if report['unsafe']:
        try:
            (target / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            sys.stderr.write('UNSAFE: check result/checkpoint; process retains the sole owner\n');sys.stderr.flush()
        finally:
            hold_unsafe_owner()
    (target / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Blocked as error:
        print(json.dumps({'blocked': True, 'reason': str(error), 'models_loaded': False,
                          'services_changed': False}))
        raise SystemExit(2)
