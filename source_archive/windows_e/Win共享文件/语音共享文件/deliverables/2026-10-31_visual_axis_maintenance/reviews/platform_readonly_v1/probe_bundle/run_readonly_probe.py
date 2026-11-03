"""Fixed v24 inventory probe: reads files and existing camera health only.

No checked Python file is imported or run. No device nodes, MMIO, model client,
service control, process signals, binding writes or filesystem writes are used.
Only the main window may run the generated script on the board.
"""
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import stat
import sys
import time

POLICY_SHA256 = '272276d46b27c80fa2cd8f3ac9c531eb3fc35970e2facdb59b2f839b553f8bf3'
SCHEMA = 'aura-axis-platform-readonly-1'


def tri_all(values):
    values = list(values)
    return False if False in values else None if None in values else True


def equal_if_read(value, expected):
    return None if value is None else value == expected


class FileReader:
    """Open only allowlisted regular files for reading, with a byte budget."""
    def __init__(self, policy):
        self.policy = policy
        self.allowed = set(policy['os_paths'].values()) | {policy['startup_path']}
        self.allowed.update(row['path'] for row in policy['files'])
        self.allowed.update(row['path'] for row in policy['manual_driver_files'])
        for owner in policy['owners']:
            self.allowed.update('/proc/%d/%s' % (owner['pid'], name) for name in ('stat', 'cmdline'))
        self.used = 0

    def _read(self, path, limit, digest_only=False, expected_size=None):
        if path not in self.allowed:
            return 'FORBIDDEN_PATH', None, 0
        descriptor = None
        try:
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode):
                return 'NOT_REGULAR', None, 0
            if expected_size is not None and info.st_size != expected_size:
                return 'SIZE_MISMATCH', None, 0
            flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
            descriptor = os.open(path, flags)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                return 'NOT_REGULAR', None, 0
            size, chunks, digest = 0, [], hashlib.sha256()
            while True:
                remaining = min(limit - size, self.policy['limits']['total_bytes'] - self.used)
                if remaining < 0:
                    return 'BYTE_LIMIT', None, size
                raw = os.read(descriptor, min(65536, remaining + 1))
                if not raw:
                    return 'OK', digest.hexdigest() if digest_only else b''.join(chunks), size
                size += len(raw)
                self.used += len(raw)
                if size > limit or self.used > self.policy['limits']['total_bytes']:
                    return 'BYTE_LIMIT', None, size
                if digest_only:
                    digest.update(raw)
                else:
                    chunks.append(raw)
        except OSError:
            return 'UNAVAILABLE', None, 0
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def read(self, path, limit):
        return self._read(path, limit)

    def digest(self, path, expected_size=None):
        return self._read(path, self.policy['limits']['per_file_bytes'], True, expected_size)


def get_health(policy):
    source = policy['camera_health']
    if (source['host'], source['port'], source['path']) != ('127.0.0.1', 8790, '/health'):
        return 'POLICY_REJECTED', None
    connection = http.client.HTTPConnection('127.0.0.1', 8790,
        timeout=policy['limits']['health_timeout_s'])
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        limit = policy['limits']['health_bytes']
        raw = response.read(limit + 1)
        if response.status != 200:
            return 'HTTP_NOT_OK', None
        if len(raw) > limit:
            return 'BYTE_LIMIT', None
        value = json.loads(raw)
        return ('OK', value) if isinstance(value, dict) else ('INVALID_JSON', None)
    except (OSError, ValueError, http.client.HTTPException):
        return 'UNAVAILABLE', None
    finally:
        connection.close()


def small(reader, path, limit=65536):
    code, value, _ = reader.read(path, limit)
    return value if code == 'OK' else None


def digest(reader, path, size=None):
    code, value, _ = reader.digest(path, size)
    return value if code == 'OK' else None


def owner_context(policy, reader):
    raw = small(reader, policy['os_paths']['boot'], 128)
    boot = raw.strip().decode('ascii', errors='replace') if raw is not None else None
    startup = digest(reader, policy['startup_path'])
    owners, details = [], []
    for owner in policy['owners']:
        raw = small(reader, '/proc/%d/stat' % owner['pid'])
        birth = None
        if raw is not None:
            try:
                birth = int(raw.rsplit(b')', 1)[1].split()[19])
            except (ValueError, IndexError):
                pass
        command = digest(reader, '/proc/%d/cmdline' % owner['pid'])
        matches = tri_all((equal_if_read(birth, owner['birth_ticks']),
                           equal_if_read(command, owner['command_sha256'])))
        owners.append(dict(index=len(owners), matches=matches))
        details.append((birth, command))
    critical = []
    for role in ('GUI_FOLLOW_BEFORE', 'GUI_MANUAL_CONFIG', 'EFFECTIVE_GUI_CONFIG'):
        row = next(row for row in policy['files'] if row['role'] == role)
        value = digest(reader, row['path'], row['bytes'])
        critical.append((value, row['sha256']))
    owners_match = tri_all([equal_if_read(boot, policy['boot_id'])] + [row['matches'] for row in owners])
    matches = tri_all([equal_if_read(boot, policy['boot_id']),
        equal_if_read(startup, policy['startup_sha256'])] + [row['matches'] for row in owners]
        + [equal_if_read(a, b) for a, b in critical])
    return dict(matches=matches, owners_match=owners_match, owners=owners,
        startup_matches=equal_if_read(startup, policy['startup_sha256']),
        token=(boot, startup, tuple(details), tuple(a for a, _ in critical)))


def platform_snapshot(policy, reader):
    paths = policy['os_paths']
    return dict(firmware=small(reader, paths['firmware'], 4096),
        fpga_state=small(reader, paths['fpga_state'], 256),
        vart=small(reader, paths['vart']), fdt=digest(reader, paths['fdt']),
        board_cid=small(reader, paths['board_cid'], 256))


def platform_projection(policy, raw):
    firmware = raw['firmware']
    firmware_kind = 'UNKNOWN' if firmware is None else 'OTHER'
    for kind, name in policy['firmware_names'].items():
        if firmware is not None and firmware.rstrip(b'\0\n') == name.encode():
            firmware_kind = kind
    vart, vart_kind = raw['vart'], 'UNKNOWN' if raw['vart'] is None else 'OTHER'
    for kind, line in policy['vart_lines'].items():
        if vart is not None and vart.split() == line.encode().split():
            vart_kind = kind
    return dict(firmware_kind=firmware_kind, vart_kind=vart_kind,
        fpga_operating=None if raw['fpga_state'] is None else raw['fpga_state'].strip() == b'operating',
        vart_exact_wide=None if vart is None else vart == policy['vart_lines']['WIDE_V1'].encode(),
        board_cid_matches=None if raw['board_cid'] is None else raw['board_cid'].strip() == policy['board_cid'].encode())


def fingerprint(reader, row, expected=None):
    code, value, size = reader.digest(row['path'], row.get('bytes'))
    expected = row['sha256'] if expected is None else expected
    return dict(index=row['index'], role=row.get('role', 'MANUAL_DRIVER_FILE'),
        state=('MATCH' if value == expected else 'MISMATCH') if code == 'OK' else code,
        bytes_read=size)


def bound_json(policy, reader, row, state):
    if state['state'] != 'MATCH':
        return None
    raw = small(reader, row['path'], policy['limits']['json_bytes'])
    if raw is None or hashlib.sha256(raw).hexdigest() != row['sha256']:
        state['state'] = 'CHANGED_DURING_READ'
        return None
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except ValueError:
        return None


COUNTERS = {
    'capture_frames': ('capture_frames',), 'person_detection_frames': ('detected_frames',),
    'identity_processed': ('identity', 'processed'),
    'face_detector_processed': ('identity', 'face_targets', 'processed'),
    'face_worker_faults': ('identity', 'face_targets', 'worker_faults'),
    'primary_calls': ('dpu_schedule', 'primary_calls'),
    'primary_period_overruns': ('dpu_schedule', 'primary_period_overruns'),
    'yunet_native_failures': ('dpu_schedule', 'optional', 'yunet', 'native_failures'),
    'sface_native_failures': ('dpu_schedule', 'optional', 'sface', 'native_failures'),
}


def at(value, path):
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def count(value):
    return value if type(value) is int and 0 <= value < 2**53 else None


def presence(value):
    return bool(value) if isinstance(value, str) else None


def health_projection(policy, samples):
    camera = next(row for row in policy['owners'] if row['role'] == 'CAMERA')
    contexts, values = [], []
    for code, value in samples:
        context = None
        if code == 'OK' and isinstance(value, dict):
            service, epoch = value.get('service_epoch'), value.get('camera_epoch')
            if (type(value.get('pid')) is int and value['pid'] == camera['pid']
                    and value.get('board_boot_id') == policy['boot_id']
                    and all(isinstance(s, str) and 1 <= len(s) <= 96 for s in (service, epoch))):
                context = (service, epoch)
        contexts.append(context)
        values.append(value)
    if None in contexts or contexts[0] != contexts[1]:
        return dict(status='HEALTH_CONTEXT_UNVERIFIED', identity_ready=None, identity_backend='UNKNOWN',
            identity_error_present=None, counters=None, deltas=None)
    first, last = values
    counters, deltas = {}, {}
    for name, path in COUNTERS.items():
        a, b = count(at(first, path)), count(at(last, path))
        counters[name] = b
        deltas[name] = b - a if a is not None and b is not None and b >= a else None
    ready, backend = at(last, ('identity', 'ready')), at(last, ('identity', 'backend'))
    return dict(status='HEALTH_CONTEXT_MATCHED',
        identity_ready=ready if type(ready) is bool else None,
        identity_backend='DPU_SFACE_INT8' if backend == 'DPU_SFACE_INT8' else 'UNKNOWN' if backend is None else 'OTHER',
        identity_error_present=presence(at(last, ('identity', 'error'))),
        camera_error_present=presence(last.get('camera_error')),
        detector_error_present=presence(last.get('detector_error')),
        counters=counters, deltas=deltas)


def run_probe(policy, reader, fetch_health, clock=time.monotonic):
    began = clock()
    result = dict(schema=SCHEMA, status='READONLY_INCOMPLETE', observations_valid=False,
        motion_qualified=False, before_owners_match=None, after_owners_match=None,
        before_context_matches=None, after_context_matches=None,
        same_owner_context=None, platform_stable=None, platform=None,
        files=None, manual_driver_files=None, bindings=None, health=None,
        current_stopped_reference_us=None, current_direction_qualified=None,
        physical_angle_degrees=None, current_identity_threshold=None,
        driver_build_register_readback=None, listening_state='NOT_READ_BY_THIS_PROBE',
        service_or_binding_write_sent=False, motion_driver_imported=False)
    before = owner_context(policy, reader)
    result['before_owners_match'] = before['owners_match']
    result['before_context_matches'] = before['matches']
    if before['matches'] is not True:
        result['status'] = 'CONTEXT_MISMATCH' if before['matches'] is False else 'CONTEXT_UNAVAILABLE'
        return result
    platform_before = platform_snapshot(policy, reader)
    samples = [fetch_health(policy)]
    files = [fingerprint(reader, row) for row in policy['files']]
    documents = {}
    for row, state in zip(policy['files'], files):
        if row['parse_json']:
            documents[row['role']] = bound_json(policy, reader, row, state)
    manual_driver = []
    release = documents.get('MANUAL_RELEASE_MANIFEST')
    payload = release.get('payload_files') if isinstance(release, dict) else None
    names = {row['name'] for row in policy['manual_driver_files']}
    valid_payload = (isinstance(payload, dict) and set(payload) == names and
        all(isinstance(v, str) and len(v) == 64 and set(v) <= set('0123456789abcdef') for v in payload.values()))
    for row in policy['manual_driver_files']:
        manual_driver.append(fingerprint(reader, row, payload[row['name']]) if valid_payload else
            dict(index=row['index'], role='MANUAL_DRIVER_FILE', state='MANIFEST_UNVERIFIED', bytes_read=0))
    samples.append(fetch_health(policy))
    platform_after = platform_snapshot(policy, reader)
    after = owner_context(policy, reader)
    result['after_owners_match'] = after['owners_match']
    result['after_context_matches'] = after['matches']
    result['same_owner_context'] = after['matches'] is True and before['token'] == after['token']
    if result['same_owner_context'] is not True:
        result['status'] = 'CONTEXT_CHANGED'
        return result
    pairs = [(platform_before[k], platform_after[k]) for k in platform_before]
    result['platform_stable'] = (False if any(a != b for a, b in pairs if a is not None and b is not None)
        else None if any(a is None or b is None for a, b in pairs) else True)
    if result['platform_stable'] is False:
        result['status'] = 'PLATFORM_CHANGED'
        return result
    manual = documents.get('GUI_MANUAL_CONFIG') or {}
    direction = documents.get('EFFECTIVE_DIRECTION') or {}
    face = documents.get('EFFECTIVE_FACE_CONFIG') or {}
    result.update(observations_valid=True, platform=platform_projection(policy, platform_after),
        files=files, manual_driver_files=manual_driver,
        bindings=dict(manual_boot_matches_current=equal_if_read(manual.get('boot_id'), policy['boot_id']),
            manual_fdt_matches_current=equal_if_read(platform_after['fdt'], manual['fdt_sha256'])
                if isinstance(manual.get('fdt_sha256'), str) else None,
            direction_boot_matches_current=equal_if_read(direction.get('boot_id'), policy['boot_id']),
            effective_face_release_reference_matches=equal_if_read(face.get('manifest_sha256'),
                next(row['sha256'] for row in policy['files'] if row['role'] == 'CONTROLLER_MANIFEST'))),
        health=health_projection(policy, samples))
    complete = (result['platform_stable'] is True and result['health']['status'] == 'HEALTH_CONTEXT_MATCHED'
        and all(row['state'] in ('MATCH', 'MISMATCH', 'SIZE_MISMATCH') for row in files + manual_driver))
    result['status'] = 'READONLY_OBSERVED' if complete else 'READONLY_INCOMPLETE'
    result['elapsed_ms'] = round(max(0., clock() - began) * 1000, 3)
    return result


def read_policy(path):
    descriptor = None
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return None
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0))
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            return None
        chunks, size = [], 0
        while size <= 262144:
            raw = os.read(descriptor, min(65536, 262145 - size))
            if not raw:
                return b''.join(chunks)
            size += len(raw)
            chunks.append(raw)
        return None
    except OSError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def main():
    try:
        path = Path(__file__).with_name('probe_policy.json')
        raw = read_policy(path)
        if raw is None:
            print(json.dumps(dict(schema=SCHEMA, status='POLICY_UNAVAILABLE', motion_qualified=False)))
            return 2
        if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
            print(json.dumps(dict(schema=SCHEMA, status='POLICY_MISMATCH', motion_qualified=False)))
            return 2
        policy = json.loads(raw)
        if os.name != 'posix' or os.uname().machine != 'aarch64':
            print(json.dumps(dict(schema=SCHEMA, status='UNSUPPORTED_HOST', motion_qualified=False)))
            return 2
        result = run_probe(policy, FileReader(policy), get_health)
        print(json.dumps(result, allow_nan=False, separators=(',', ':')))
        return 0
    except KeyboardInterrupt:
        print(json.dumps(dict(schema=SCHEMA, status='READONLY_INTERRUPTED', motion_qualified=False)))
        return 2
    except Exception:
        print(json.dumps(dict(schema=SCHEMA, status='READONLY_FAILED', motion_qualified=False)))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
