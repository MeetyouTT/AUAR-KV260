"""Isolated metadata call-through to the EXISTING reviewed CPU history adapter.

No archive traversal, Native restore, marker commit, service control or new
counter implementation lives here. Cold/live-chain checks call its unchanged
original_modules/_sealed_source/validate_chain APIs. Same-boot checks call its
unchanged complete main() with a genuine CPU normal-stop expected pin.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import stat
import sys
import types

ADAPTER_SHA = '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9'


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(pin):
    path = Path(pin['path'])
    require(path.is_absolute() and not path.is_symlink() and path.resolve() == path, 'Pinned public path redirects')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size <= 1048576, 'Public input shape')
        raw = stream.read(1048577)
        after = os.fstat(stream.fileno())
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            and digest(raw) == pin['sha256'], 'Pinned public input changed')
    return raw


def execute_request(adapter, request, request_sha, actual_boot):
    """Metadata orchestration only; adapter is the exact separately pinned CPU source."""
    require(request['schema'] == 'aura-original-history-gate-request-1'
            and request['boot_id'] == actual_boot, 'History request/current boot differs')
    kind = request['kind']
    history = request['history_expected']
    snapshot = adapter.Snapshot()
    if kind == 'same_boot_resume':
        expected_pin = request['normal_stop_expected_pin']
        expected = snapshot.pinned(expected_pin)
        expected_history = {key: expected['history'][key] for key in ('head', 'archive_count', 'archives', 'legacy_pin')}
        require(expected['boot_id'] == actual_boot and expected['checkpoint_pin'] == request['checkpoint_pin']
                and expected['camera_owner'] == request['source_owner'] and expected_history == history,
                'Same-boot proof is not bound to the exact final/owner/history')
        previous_argv = sys.argv
        output = io.StringIO()
        try:
            sys.argv = ['original_cpu_full_history', '--expected', expected_pin['path'], '--expected-sha256', expected_pin['sha256']]
            with contextlib.redirect_stdout(output):
                adapter.main()  # Existing real stop/bounds/source/reader/archive guard, unchanged.
        finally:
            sys.argv = previous_argv
        original = json.loads(output.getvalue())
        require(original['schema'] == 'aura-fresh-final-history-validation-1'
                and original['status'] == 'ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED'
                and original['checkpoint_pin'] == request['checkpoint_pin']
                and original['source_owner'] == request['source_owner']
                and original['expected_sha256'] == expected_pin['sha256']
                and original['original_load_business_checkpoint_called'] is True
                and original['complete_ordered_history_verified'] is True
                and original['all_required_current_boot_cumulative_lower_bounds_checked'] is True,
                'Original complete same-boot validation did not succeed')
        records = original['archives']
    else:
        require(kind in {'cold_predecessor', 'running_archive_chain'}, 'Unknown history route')
        protection, boot_module = adapter.original_modules(snapshot)
        if kind == 'cold_predecessor':
            pin = request['checkpoint_pin']
            require(Path(pin['path']) == adapter.CHECKPOINT, 'Original checkpoint path differs')
            document = snapshot.pinned(pin)
            seed, auxiliary = boot_module._sealed_source(document)
            adapter.optional_shape(auxiliary, protection)
            source = request['source_owner']
            require(seed['boot_id'] == request['source_boot'] != actual_boot
                    and seed['source_pid'] == source['pid'] and seed['source_birth_ticks'] == int(source['birth_ticks'])
                    and seed['source_manifest_sha256'] == request['source_manifest_sha256']
                    and document['source_unit_sha256'] == adapter.SOURCE_UNIT, 'Original cold predecessor provenance differs')
            _, marker = boot_module.marker_paths(request['new_boot_marker_directory'], actual_boot)
            require(not os.path.lexists(marker), 'Current kernel domain is already consumed')
        else:
            # validate_chain consumes only this actual boot/head metadata. This
            # is NOT a checkpoint/seed, is never persisted as one, and is never
            # passed to any Native restoration or counter-construction API.
            document = {'seed': {'boot_id': actual_boot}, 'previous_kernel_history': history['head']}
        records = adapter.validate_chain(document, history, snapshot, protection, boot_module)
        original = None
    snapshot.unchanged()
    require(records == history['archives'] and len(records) == history['archive_count'], 'Original complete ordered history differs')
    return dict(schema='aura-original-history-gate-result-1', request_sha256=request_sha, kind=kind,
                boot_id=actual_boot, adapter_sha256=ADAPTER_SHA, checkpoint_pin=request.get('checkpoint_pin'),
                history_expected=history, complete_ordered_history_verified=True, original_calls_only=True,
                original_same_boot_result=original, checkpoint_or_marker_written=False,
                native_context_created=False, model_or_device_opened=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--request-sha256', required=True)
    args = parser.parse_args()
    require(platform.system() == 'Linux' and platform.machine() == 'aarch64' and os.geteuid() == 0
            and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'Fresh board -B -I -S process required')
    request_pin = dict(path=args.request, sha256=args.request_sha256)
    request_raw = read_pin(request_pin)
    request = json.loads(request_raw)
    adapter_pin = request['adapter_pin']
    require(adapter_pin['sha256'] == ADAPTER_SHA, 'Reviewed CPU adapter revision differs')
    source = read_pin(adapter_pin)
    namespace = dict(__name__='existing_cpu_readonly_history_adapter', __file__=adapter_pin['path'])
    exec(compile(source, adapter_pin['path'], 'exec', dont_inherit=True), namespace)
    result = execute_request(types.SimpleNamespace(**namespace), request, args.request_sha256,
                             Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    require(read_pin(request_pin) == request_raw and read_pin(adapter_pin) == source, 'History call inputs changed')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
