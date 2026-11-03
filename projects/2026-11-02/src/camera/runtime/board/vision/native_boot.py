"""Explicit new-kernel counter domain from a pinned sealed v2 checkpoint.

No service/device/model operations. Old monotonic times are validated only in
their archived boot. Current-boot admission is consumed once before restore.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

from board.vision.native_protection import (_boot, _read_pinned, digest, integer,
    make_native_seed, FEATURE_COUNTERS)


MAX_CLOCK = 2**63-1


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _legacy_source(document):
    """Validate archived lower bounds; never turn them into an exact seed."""
    if (document.get('schema') != 'aura-native-legacy-boot-archive-1' or
            document.get('prefix_scope') != 'legacy_health_prefix_lower_bound'):
        raise ValueError('Explicit legacy health-prefix archive required')
    payload = document['legacy_payload']
    if (payload.get('schema') != 'aura-legacy-health-prefix-1' or
            hashlib.sha256(_canonical(payload)).hexdigest() !=
            digest(document['legacy_payload_sha256'], 'legacy_payload_sha256')):
        raise ValueError('Legacy prefix payload or its hash differs')
    boot = _boot(document['source_boot'])
    if payload['boot'] != boot:
        raise ValueError('Legacy prefix source boot differs')
    for name in ('source_pid', 'source_birth_ticks', 'captured_mono_ns'):
        value = integer(document[name], name, maximum=MAX_CLOCK)
        if not value or payload[name] != value:
            raise ValueError('Legacy prefix provenance differs: ' + name)
    for name in ('source_unit_sha256', 'source_manifest_sha256'):
        if digest(document[name], name) != payload[name]:
            raise ValueError('Legacy prefix source hash differs: ' + name)
    manifest = document['source_manifest']
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError('Complete pinned legacy code manifest required')
    for name, value in manifest.items():
        path = Path(name)
        if (not isinstance(name, str) or path.is_absolute() or '..' in path.parts or
                path.suffix != '.py' or str(path) != name):
            raise ValueError('Invalid legacy source manifest path')
        digest(value, 'legacy source file')
    if hashlib.sha256(_canonical(manifest)).hexdigest() != document['source_manifest_sha256']:
        raise ValueError('Legacy source manifest hash differs')
    schedule = payload['schedule']
    if schedule.get('owner_fenced') is not False or schedule.get('owner_fault_reason'):
        raise ValueError('Unknown legacy completion cannot authorize new-boot bootstrap')
    if schedule.get('guard_ms') != 5. or schedule.get('budget_ms') != 20.:
        raise ValueError('Legacy protection constants differ')
    primary = integer(schedule['primary_calls'], 'legacy primary_calls')
    late = integer(schedule['primary_period_overruns'], 'legacy primary_period_overruns')
    if late > primary:raise ValueError('Inconsistent legacy primary counters')
    diagnostics = schedule['optional_diagnostics']
    if (diagnostics.get('enabled') is not True or diagnostics.get('diagnostic_errors') != 0 or
            schedule.get('diagnostic_failures') != 0):
        raise ValueError('Legacy fault completion evidence unavailable')
    events = diagnostics['fault_events']
    if not isinstance(events, list):raise ValueError('Legacy fault event list required')
    policies = []
    overruns = [0]
    all_sequences = set()
    captured = document['captured_mono_ns']
    for kind, code in (('yunet', 1), ('sface', 2)):
        job = schedule['optional'][kind]
        calls = integer(job['calls'], kind+'.calls')
        faults = integer(job['overruns'], kind+'.overruns')
        if faults > calls or type(job['disabled']) is not bool:
            raise ValueError('Invalid legacy optional counters')
        policy = schedule[kind+'_recovery']
        if policy.get('enabled') is not True or policy['phase'] not in ('RUNNING','COOLDOWN','PROBATION','LATCHED'):
            raise ValueError('Independent legacy recovery state required')
        for name in ('faults','attempts','recoveries','probe_successes','attempts_in_window'):
            integer(policy[name], kind+'.'+name)
        if (policy['faults'] != faults or not policy['recoveries'] <= policy['attempts'] <= faults or
                policy['attempts_in_window'] > min(2, policy['attempts']) or policy['probe_successes'] > 3):
            raise ValueError('Inconsistent legacy recovery counters')
        if policy['phase'] in ('COOLDOWN','LATCHED') and not job['disabled']:
            raise ValueError('Blocked legacy policy was not disabled')
        matching = [event for event in events if event.get('task_code') == code]
        if len(matching) != faults:raise ValueError('Legacy fault evidence count differs')
        for event in matching:
            sequence = integer(event['event_sequence'], 'legacy event sequence')
            if not sequence or sequence in all_sequences:
                raise ValueError('Duplicate legacy fault evidence')
            all_sequences.add(sequence)
            start = _time(event['lease_started_mono_ns'], 'legacy lease start', zero=False)
            end = _time(event['lease_release_decision_mono_ns'], 'legacy lease release', zero=False)
            if (not start < end <= captured or event['native_completed'] != 1 or
                    event['native_attempts'] != 1 or event['native_status'] != 0 or
                    event['native_failed'] != 0 or event['body_failed'] != 0 or
                    event['diagnostic_finished'] != 1 or
                    event['hardcap_exceeded'] not in (0,1) or event['guard_exceeded'] not in (0,1) or
                    not (event['hardcap_exceeded'] or event['guard_exceeded'])):
                raise ValueError('Legacy fault native completion was not proven')
        overruns.append(faults)
        policies.append(dict(policy))
    if len(all_sequences) != len(events):raise ValueError('Unclassified legacy fault evidence')
    feature = payload['feature_inference']
    if feature.get('kind') != 'DPU_SFACE_INT8':raise ValueError('Legacy identity domain differs')
    counters = {name: integer(feature[name], 'legacy sface.'+name) for name in FEATURE_COUNTERS}
    if not counters['features_returned'] <= counters['completed'] <= counters['execution_attempts'] <= counters['requests']:
        raise ValueError('Inconsistent legacy SFace counters')
    # Metadata below is ARCHIVE ONLY. It is not a C seed and never goes through
    # restore_seed; no old monotonic timestamp or partial recovery queue is used.
    archive = dict(boot_id=boot, source_pid=document['source_pid'],
        source_birth_ticks=document['source_birth_ticks'], captured_mono_ns=captured,
        source_manifest_sha256=document['source_manifest_sha256'],
        primary_calls=primary, primary_period_overruns=late, overruns=overruns,
        recovery=policies, history_is_lower_bound=True, unknown_tail=True)
    return archive, dict(sface_counters=counters, inherited_optional=schedule['optional'])


def current_boot():
    return _boot(Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def checked_boot(value):
    actual = current_boot()
    if _boot(value) != actual:
        raise ValueError('Supplied boot differs from the running kernel')
    return actual


def _time(value, name, *, zero=True):
    result = integer(value, name, maximum=MAX_CLOCK)
    if not zero and result == 0:raise ValueError('Positive monotonic time required: '+name)
    return result


def _sealed_source(document):
    if (document.get('schema') != 'aura-native-protection-checkpoint-2' or
            document.get('scope') != 'final_quiescent_before_native_owner_close'):
        raise ValueError('New boot requires a sealed v2 business checkpoint')
    seed, auxiliary = document['seed'], document['auxiliary']
    if (seed.get('purpose') != 'final_quiescent_business_checkpoint' or
            seed.get('checkpoint_kind') != 1 or seed.get('abi_version') != 2):
        raise ValueError('Legacy, prefix, maintenance or unsealed source rejected')
    from board.vision.native_binding import Seed, Recovery
    value = make_native_seed(seed, Seed, Recovery)
    _boot(seed['boot_id'])
    digest(document['source_unit_sha256'], 'source_unit_sha256')
    captured = _time(seed['captured_mono_ns'], 'archived captured', zero=False)
    if not value.source_pid or not value.source_birth_ticks:
        raise ValueError('Archived predecessor provenance is incomplete')
    if (auxiliary['active'] != 0 or auxiliary['primary_waiting'] != 0 or auxiliary['fenced'] != 0 or
            auxiliary['pending_result_tokens'] != [0,0,0]):
        raise ValueError('Archived owner was not confirmed quiescent')
    if value.fenced or value.disabled[0] or value.primary_period_overruns > value.primary_calls:
        raise ValueError('Archived native owner state is invalid or fenced')
    if value.admissions[0] > value.primary_calls:
        raise ValueError('Archived primary admissions exceed periods')
    _time(value.last_primary_ns, 'archived last_primary')
    if value.last_primary_ns > captured:raise ValueError('Archived primary timestamp lies in its future')
    for task in range(3):
        if value.completed[task] > value.admissions[task] or value.native_failures[task] > value.admissions[task]:
            raise ValueError('Archived completion exceeds admitted work')
        limit = value.primary_calls if task == 0 else value.admissions[task]
        if value.not_submitted[task] > limit or value.overruns[task] > value.admissions[task]:
            raise ValueError('Archived task counters are inconsistent')
    for index, policy in enumerate(value.recovery):
        if (policy.enabled != 1 or policy.faults < value.overruns[index+1] or
                policy.recoveries > policy.attempts or policy.attempts > policy.faults or
                policy.attempt_count > policy.attempts or policy.opaque_attempt_count > policy.attempts or
                policy.opaque_attempt_count > 2 or policy.probe_successes > 3):
            raise ValueError('Archived recovery counters are invalid')
        observed = _time(policy.observed_ns, 'archived recovery observed')
        cooldown = _time(policy.cooldown_until_ns, 'archived cooldown')
        if observed > captured or (cooldown > captured and cooldown-captured > 10_000_000_000):
            raise ValueError('Archived recovery time lies outside its boot snapshot')
        if (policy.fault_primary_overruns > policy.fault_primary_calls or
                policy.fault_primary_calls > value.primary_calls or
                policy.fault_primary_overruns > value.primary_period_overruns):
            raise ValueError('Archived recovery primary baseline is inconsistent')
        if policy.history_opaque:
            if (policy.phase != 3 or not value.disabled[index+1] or policy.attempt_count or
                    list(policy.attempt_times_ns) != [0,0] or policy.reason in (0,3)):
                raise ValueError('Opaque archived history must remain explicitly LATCHED')
        else:
            if policy.opaque_attempt_count:raise ValueError('Exact history cannot carry an opaque budget')
            times = list(policy.attempt_times_ns)
            for slot, stamp in enumerate(times):
                _time(stamp, 'archived attempt')
                if slot < policy.attempt_count:
                    if not stamp or stamp > observed or (slot and stamp <= times[slot-1]):
                        raise ValueError('Archived attempt time is invalid')
                elif stamp:raise ValueError('Unused archived attempt slot must be zero')
            blocked = policy.phase in (1,3)
            if bool(value.disabled[index+1]) != blocked:
                raise ValueError('Archived disabled flag differs from its policy')
        if policy.phase == 0 and policy.reason != 0:
            raise ValueError('Archived RUNNING reason is invalid')
        if (policy.phase == 0 and policy.faults and (not policy.recoveries or
                policy.probe_successes != 3 or not cooldown or not policy.attempt_count)):
            raise ValueError('Archived recovered RUNNING state is incomplete')
        if policy.phase == 1 and (policy.reason != 3 or not cooldown or policy.probe_successes):
            raise ValueError('Archived COOLDOWN is invalid')
        if policy.phase == 2 and (policy.reason or policy.probe_successes >= 3 or not policy.attempt_count):
            raise ValueError('Archived PROBATION is invalid')
        if (policy.phase == 2 and (not cooldown or not policy.attempts or
                policy.attempt_times_ns[policy.attempt_count-1] < cooldown)):
            raise ValueError('Archived probation precedes its cooldown')
        if policy.phase == 3 and policy.reason in (0,3):
            raise ValueError('Archived LATCHED reason is invalid')
        if not policy.faults and (policy.phase or policy.reason or policy.attempts or
                policy.recoveries or policy.probe_successes or cooldown or
                policy.fault_primary_calls or policy.fault_primary_overruns):
            raise ValueError('Archived clean policy contains hidden fault state')
    counters = auxiliary['sface_counters']
    if set(counters) != set(FEATURE_COUNTERS):raise ValueError('Complete archived SFace counters required')
    for name, item in counters.items():integer(item, 'archived sface.'+name)
    if not counters['features_returned'] <= counters['completed'] <= counters['execution_attempts'] <= counters['requests']:
        raise ValueError('Archived SFace counters are inconsistent')
    return seed, auxiliary


def marker_paths(directory, boot):
    path = Path(directory)
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise ValueError('Explicit nonredirecting new-boot marker directory required')
    return path, path/('kernel-boot-'+_boot(boot)+'.consumed')


def _fresh_seed(boot, now, source_sha):
    policies=[]
    for _ in range(2):
        policies.append(dict(enabled=1,phase=0,reason=0,probe_successes=0,
            attempt_count=0,history_opaque=0,opaque_attempt_count=0,cooldown_until_ns=0,
            fault_primary_calls=0,fault_primary_overruns=0,faults=0,attempts=0,
            recoveries=0,observed_ns=now,attempt_times_ns=[0,0]))
    return dict(abi_version=2,purpose='validated_new_kernel_boot',checkpoint_kind=0,fenced=0,
        captured_mono_ns=now,primary_calls=0,primary_period_overruns=0,last_primary_ns=0,
        source_pid=0,source_birth_ticks=0,boot_id=boot,source_manifest_sha256=source_sha,
        admissions=[0]*3,overruns=[0]*3,completed=[0]*3,native_failures=[0]*3,
        not_submitted=[0]*3,disabled=[0]*3,recovery=policies)


def load_new_boot_checkpoint(pin, *, boot_id, marker_directory, allow_legacy=False):
    boot=checked_boot(boot_id)
    if type(allow_legacy) is not bool:raise ValueError('Legacy bootstrap requires an explicit boolean')
    path, document = _read_pinned(pin)
    legacy = document.get('schema') == 'aura-native-legacy-boot-archive-1'
    if legacy:
        if not allow_legacy:raise ValueError('Legacy bootstrap requires its separate opt-in')
        seed, auxiliary = _legacy_source(document)
    else:
        seed, auxiliary = _sealed_source(document)
    if seed['boot_id'] == boot:
        raise ValueError('Same-boot history cannot enter a fresh counter domain')
    directory, marker = marker_paths(marker_directory, boot)
    if os.path.lexists(str(marker)):
        raise ValueError('This kernel boot already consumed its fresh native counter domain')
    now = _time(time.monotonic_ns(), 'new-boot captured', zero=False)
    fresh = _fresh_seed(boot, now, seed['source_manifest_sha256'])
    if fresh['captured_mono_ns'] > time.monotonic_ns():
        raise ValueError('Fresh counter capture is from the future')
    return dict(seed=fresh,auxiliary={'sface_counters':{n:0 for n in FEATURE_COUNTERS},
        'inherited_optional':{}},document=document,sha256=pin['sha256'],
        source_path=str(path),marker=str(marker),marker_directory=str(directory),
        legacy_new_kernel_boot=legacy,
        new_kernel_boot=True,archive_seed=seed,archive_auxiliary=auxiliary,
        archive_counters={'primary_calls':seed['primary_calls'],
            'primary_period_overruns':seed['primary_period_overruns'],
            'overruns':list(seed['overruns']),
            'history_is_lower_bound':legacy,'unknown_tail':legacy,
            'recovery':[dict(faults=p['faults'],attempts=p['attempts'],recoveries=p['recoveries'],
                phase=p['phase'],reason=p['reason'],history_opaque=(True if legacy else p['history_opaque']))
                for p in seed['recovery']],
            'sface_counters':dict(auxiliary['sface_counters'])})


def _controlled_directory(path):
    path=Path(path)
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise ValueError('New-boot state path redirects')
    if not path.parent.is_dir():raise ValueError('New-boot parent directory must already exist')
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:pass
    info=path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('New-boot directory must be owned by the effective UID with mode0700')
    _fsync_directory(path.parent)
    return path


def _fsync_directory(path):
    fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def commit_new_boot(loaded):
    """Archive first, consume once, then permit caller's native restore/adopt."""
    boot=checked_boot(loaded['seed']['boot_id'])
    if (not loaded.get('new_kernel_boot') or loaded['seed']['purpose'] != 'validated_new_kernel_boot' or
            loaded['archive_seed']['boot_id'] == boot):
        raise ValueError('Explicit different-kernel startup required')
    now=_time(time.monotonic_ns(),'current time',zero=False)
    if not 0 < loaded['seed']['captured_mono_ns'] <= now:
        raise ValueError('New-boot seed capture is not in the current kernel domain')
    _, current_document=_read_pinned({'path':loaded['source_path'],'sha256':loaded['sha256']})
    legacy = current_document.get('schema') == 'aura-native-legacy-boot-archive-1'
    if legacy != bool(loaded.get('legacy_new_kernel_boot')):
        raise ValueError('Archive mode changed after validation')
    old_seed,_=(_legacy_source(current_document) if legacy else _sealed_source(current_document))
    expected=_fresh_seed(boot,loaded['seed']['captured_mono_ns'],old_seed['source_manifest_sha256'])
    if (current_document != loaded['document'] or old_seed != loaded['archive_seed'] or
            loaded['seed'] != expected):
        raise ValueError('Pinned archive or clean new-boot seed changed after validation')
    directory,marker=marker_paths(loaded['marker_directory'],boot)
    if str(marker) != loaded['marker']:raise ValueError('New-boot marker identity changed')
    directory=_controlled_directory(directory)
    archive_dir=_controlled_directory(directory/'archive')
    archive=archive_dir/(boot+'-'+loaded['sha256']+'.json')
    document={'schema':'aura-native-previous-kernel-archive-1','current_boot':boot,
        'source_boot':loaded['archive_seed']['boot_id'],'source_checkpoint_sha256':loaded['sha256'],
        'source_checkpoint_path':loaded['source_path'],
        'source_manifest_sha256':loaded['archive_seed']['source_manifest_sha256'],
        'history_is_lower_bound':legacy,'unknown_tail':legacy,
        'counter_scope':'Previous kernel history is archived; no old monotonic times or counters enter the new running domain',
        'checkpoint':loaded['document']}
    raw=(json.dumps(document,sort_keys=True,separators=(',',':'))+'\n').encode()
    if len(raw)>262144:raise ValueError('New-boot archive exceeds bound')
    archive_sha=hashlib.sha256(raw).hexdigest()
    temporary=archive.with_name(archive.name+'.partial-'+str(os.getpid()))
    try:
        fd=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
        try:
            if os.write(fd,raw)!=len(raw):raise OSError('Incomplete previous-kernel archive write')
            os.fsync(fd)
        finally:os.close(fd)
        try:os.link(str(temporary),str(archive),follow_symlinks=False)
        except FileExistsError:
            if archive.is_symlink() or archive.read_bytes()!=raw:
                raise ValueError('Previous-kernel archive differs')
    finally:
        if temporary.exists() and not temporary.is_symlink():temporary.unlink()
    _fsync_directory(archive_dir)
    record={'schema':'aura-native-current-kernel-consumption-1','boot':boot,
        'source_checkpoint_sha256':loaded['sha256'],'archive_path':str(archive),
        'archive_sha256':archive_sha,'captured_mono_ns':loaded['seed']['captured_mono_ns']}
    stamp=(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode()
    fd=os.open(str(marker),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
    try:
        # Never remove this marker, including on partial write/fsync failure.
        if os.write(fd,stamp)!=len(stamp):raise OSError('Incomplete current-kernel marker write')
        os.fsync(fd)
    finally:os.close(fd)
    _fsync_directory(directory)
    loaded['archive_path']=str(archive);loaded['archive_sha256']=archive_sha
    loaded['boot_consumption_committed']=True
