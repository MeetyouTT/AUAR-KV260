"""Explicit camera startup/shutdown wiring for the native candidate."""
import hashlib
import json
import copy
from pathlib import Path

from board.vision.native_binding import NativeContext
from board.vision.native_protection import (consume_checkpoint, digest, load_business_checkpoint,
    checkpoint_document, write_checkpoint, FEATURE_COUNTERS)
from board.vision.native_schedule import NativeDpuSchedule
from board.vision.native_yolo import NativeYoloOwner


def configuration(config):
    value = config.get('native_execution')
    if value is None:return None
    keys = {'library','library_sha256','seed','source_manifest','source_manifest_sha256',
            'source_unit_sha256','checkpoint_output'}
    optional = {'allow_new_kernel_boot','allow_legacy_new_kernel_boot','new_boot_marker_directory'}
    if not isinstance(value,dict) or not keys <= set(value) or set(value)-keys-optional:
        raise ValueError('Explicit complete native execution configuration required')
    allow_new_boot=value.get('allow_new_kernel_boot',False)
    if type(allow_new_boot) is not bool:
        raise ValueError('New kernel boot requires an explicit boolean opt-in')
    legacy_new_boot=value.get('allow_legacy_new_kernel_boot',False)
    if type(legacy_new_boot) is not bool or (legacy_new_boot and not allow_new_boot):
        raise ValueError('Legacy new-boot opt-in also requires the new-boot opt-in')
    if allow_new_boot:
        if 'new_boot_marker_directory' not in value:
            raise ValueError('Explicit new-boot marker directory required')
        from board.vision.native_boot import marker_paths
        # Path validation does not create directories or consume the boot.
        marker_paths(value['new_boot_marker_directory'],'00000000-0000-0000-0000-000000000000')
    elif 'new_boot_marker_directory' in value:
        raise ValueError('New-boot marker directory requires the opt-in')
    for name in ('library_sha256','source_manifest_sha256','source_unit_sha256'):
        digest(value[name],name)
    for name in ('library','source_manifest','checkpoint_output'):
        path = Path(value[name])
        if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
            raise ValueError('Explicit nonredirecting native path required: '+name)
    if config.get('detector_backend') != 'dpu_yolox':
        raise ValueError('Native execution requires the original YOLO DPU owner')
    if config.get('optional_admission_floor_ms') != 30:
        raise ValueError('Native execution preserves the conservative 30ms admission floor')
    if not config.get('yunet_dpu_recovery') or not config.get('sface_dpu_recovery'):
        raise ValueError('Independent native recovery policies are mandatory')
    for task in ('yunet','sface'):
        limit = config.get(task+'_slot_wait_ms',0)
        if type(limit) is not int or not 0<=limit<=100:
            raise ValueError('Native notification waits remain in 0..100ms')
    return value


def verify_runtime_manifest(native, root):
    path = Path(native['source_manifest'])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != native['source_manifest_sha256']:
        raise ValueError('Native runtime manifest SHA mismatch')
    value = json.loads(raw)
    if value.get('schema') != 'aura-native-python-source-2' or not isinstance(value.get('files'),dict):
        raise ValueError('Native runtime source manifest schema differs')
    root = Path(root).resolve()
    actual = {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in root.rglob('*.py') if not p.is_symlink()}
    if actual != value['files']:
        raise ValueError('Native camera source closure differs from the pinned manifest')


def preflight(config, *, boot_id, root):
    native = configuration(config)
    if native is None:return None
    verify_runtime_manifest(native,root)
    if config.get('tracking',{}).get('backend') == 'bytetrack_numpy':
        from board.vision.person_bytetrack import verify_sources
        verify_sources(config['tracking'])
    from board.vision.native_boot import checked_boot, load_new_boot_checkpoint
    from board.vision.native_protection import _read_pinned
    actual_boot=checked_boot(boot_id)
    _,document=_read_pinned(native['seed'])
    source_boot=(document.get('seed') or {}).get('boot_id') or document.get('source_boot')
    if source_boot == actual_boot:
        loaded=load_business_checkpoint(native['seed'],boot_id=actual_boot)
    else:
        if not native.get('allow_new_kernel_boot',False):
            raise ValueError('Different kernel boot requires explicit native opt-in')
        loaded=load_new_boot_checkpoint(native['seed'],boot_id=actual_boot,
            marker_directory=native['new_boot_marker_directory'],
            allow_legacy=native.get('allow_legacy_new_kernel_boot',False))
    if loaded['document']['source_unit_sha256'] != native['source_unit_sha256']:
        raise ValueError('Predecessor unit provenance differs')
    return loaded


def attach(config, state, original, loaded):
    """Run after original fixed-input YOLO checks, before any business worker."""
    native = configuration(config)
    if native is None:raise ValueError('Native attachment not configured')
    if loaded is None:raise ValueError('Validated exact native checkpoint required before attachment')
    if loaded.get('new_kernel_boot'):
        # Archive and consume this boot before any native context restoration
        # or adoption. Failures leave the marker consumed, never a new budget.
        from board.vision.native_boot import commit_new_boot
        commit_new_boot(loaded)
    context = NativeContext(original,native['library'],native['library_sha256'])
    try:
        context.restore_seed(loaded['seed'])
        if not loaded.get('new_kernel_boot'):consume_checkpoint(loaded)
        context.adopt_yolo()
        aux = loaded['auxiliary']
        schedule = NativeDpuSchedule(context,
            yunet_slot_wait_ms=config.get('yunet_slot_wait_ms',0),
            sface_slot_wait_ms=config.get('sface_slot_wait_ms',0),
            inherited_optional=aux.get('inherited_optional'),
            inherited_sface_counters=aux['sface_counters'],
            diagnostics=state.pipeline_metrics.optional_diagnostics)
        schedule.protection_handoff = dict(mode='native_exact_same_boot',
            seed_sha256=loaded['sha256'],source_pid=loaded['seed']['source_pid'],
            source_birth_ticks=loaded['seed']['source_birth_ticks'],
            counter_scope='exact sealed native predecessor counters plus current execution',
            first_use=True)
        if loaded['document'].get('previous_kernel_history') is not None:
            schedule.protection_handoff['previous_kernel_history'] = copy.deepcopy(
                loaded['document']['previous_kernel_history'])
        if loaded.get('new_kernel_boot'):
            schedule.protection_handoff.update(mode='native_new_kernel_boot',
                source_boot=loaded['archive_seed']['boot_id'],current_boot=loaded['seed']['boot_id'],
                source_pid=loaded['archive_seed']['source_pid'],
                source_birth_ticks=loaded['archive_seed']['source_birth_ticks'],
                source_manifest_sha256=loaded['archive_seed']['source_manifest_sha256'],
                archive_path=loaded['archive_path'],archive_sha256=loaded['archive_sha256'],
                previous_kernel_counters=loaded['archive_counters'],
                current_counter_domain='new kernel; counters start at zero; old fault/recovery history remains archived',
                counter_scope='Current kernel counters only; previous_kernel_counters are the separate archived predecessor domain')
            schedule.protection_handoff['previous_kernel_history'] = dict(
                archive_path=loaded['archive_path'], archive_sha256=loaded['archive_sha256'],
                source_boot=loaded['archive_seed']['boot_id'],
                source_checkpoint_sha256=loaded['sha256'],
                history_is_lower_bound=bool(loaded.get('legacy_new_kernel_boot')),
                scope='Persistent archive links predecessor history; not part of current counters')
        owner = NativeYoloOwner(original,context,schedule)
        owner.pipeline_metrics = state.pipeline_metrics
        return owner,schedule
    except BaseException as original_error:
        if context.quarantined:
            # The native call or its Python bookkeeping may have completed;
            # retaining the original owner is part of that uncertain outcome.
            context._retain(original, original_error, 'native startup failed after uncertain operation')
        else:
            try:
                context.close()
            except BaseException as close_error:
                # Cleanup refusal/unknown outcome must not replace the actual
                # startup failure or lose its sole owner/lifecycle references.
                context._retain(original, original_error, close_error,
                    'native startup cleanup was not confirmed')
        raise


def shutdown(config, state, owner):
    """Call only after camera/identity workers joined and their runners closed."""
    native = configuration(config)
    if native is None:return None
    counters = getattr(state.dpu_schedule,'inherited_sface_counters',{})
    if state.identity is not None:
        health = state.identity.health()
        current = health.get('feature_inference') or {}
        if all(name in current for name in FEATURE_COUNTERS):counters=current
    if not all(name in counters for name in FEATURE_COUNTERS):
        raise RuntimeError('Final SFace counters unavailable; refusing a partial native checkpoint')
    seed = owner.native_context.checkpoint(native['source_manifest_sha256'])
    snapshot = owner.native_context.snapshot()
    document = checkpoint_document(snapshot,native_seed=seed,
        source_unit_sha256=native['source_unit_sha256'],sface_counters=counters,
        inherited_optional={task:state.dpu_schedule.optional_status(task) for task in ('yunet','sface')})
    if state.dpu_schedule.protection_handoff.get('previous_kernel_history') is not None:
        # Carry one hash-linked archive reference, without recursively copying
        # history on every same-boot restart. Its archive contains the prior
        # sealed checkpoint and therefore the preceding boot's link as well.
        document['previous_kernel_history'] = copy.deepcopy(
            state.dpu_schedule.protection_handoff['previous_kernel_history'])
    try:
        return write_checkpoint(native['checkpoint_output'],document)
    finally:
        owner.close()
