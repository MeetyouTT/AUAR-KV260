"""Restore a hash-pinned same-boot protection snapshot before worker startup."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import time


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:raise ValueError('Invalid protection integer: '+name)
    return value


def _finite(value, name, minimum=0.):
    if type(value) not in (int,float) or not math.isfinite(value) or value < minimum:
        raise ValueError('Invalid protection number: '+name)
    return value


def restore_protection(schedule, pin, *, boot_id, clock_ns=time.monotonic_ns):
    """Pinned startup data is authority; incomplete/unconfirmed state never unlocks."""
    if not isinstance(pin,dict) or set(pin)!={'path','sha256'}:
        raise ValueError('Pinned protection handoff required')
    path=Path(pin['path'])
    if not path.is_absolute() or path.is_symlink() or path.resolve()!=path:
        raise ValueError('Protection handoff path redirects')
    raw=path.read_bytes()
    if len(raw)>262144 or hashlib.sha256(raw).hexdigest()!=pin['sha256']:
        raise ValueError('Protection handoff hash mismatch')
    seed=json.loads(raw)
    if seed['schema']!='aura-dpu-protection-handoff-1' or seed['boot']!=boot_id:
        raise ValueError('Protection handoff boot/schema mismatch')
    source_pid=_integer(seed['source_pid'],'source_pid',1)
    _integer(seed['source_birth_ticks'],'source_birth_ticks',1)
    captured=_integer(seed['captured_mono_ns'],'captured_mono_ns',1)
    if captured>clock_ns():raise ValueError('Protection handoff is from the future')
    for name in ('source_unit_sha256','source_manifest_sha256'):
        if not isinstance(seed[name],str) or len(seed[name])!=64 or any(c not in '0123456789abcdef' for c in seed[name]):
            raise ValueError('Protection provenance hash missing')
    old=seed['schedule']
    if old['owner_fenced'] or old.get('owner_fault_reason'):
        raise ValueError('Native owner completion is unconfirmed')
    if old.get('active') is not None or old.get('waiting_primary')!=0:
        raise ValueError('Protection snapshot must be taken while lease is idle')
    if old['budget_ms']!=20. or old['guard_ms']!=5.:
        raise ValueError('Protection budget changed')
    jobs=copy.deepcopy(old['optional'])
    if set(jobs)!={'yunet','sface'}:raise ValueError('Both optional jobs must be preserved')
    diag=old['optional_diagnostics'];events=copy.deepcopy(diag['fault_events'])
    if not diag['enabled'] or diag['diagnostic_errors'] or old['diagnostic_failures']:
        raise ValueError('Fault provenance unavailable')
    primary_calls=_integer(old['primary_calls'],'primary_calls',1)
    primary_overruns=_integer(old['primary_period_overruns'],'primary_overruns')
    clean=all(row.get('disabled') is False and row.get('overruns')==0 for row in jobs.values())
    if not clean and not all(row.get('disabled') is True for row in jobs.values()):
        raise ValueError('Unsupported mixed protection history')
    max_sequence=0
    for kind,code in (('yunet',1),('sface',2)):
        row=jobs[kind]
        if row['disabled'] is not (False if clean else True):raise ValueError('Inconsistent protection mode')
        for key in ('calls','skipped','overruns','budget_exceeded'):_integer(row[key],kind+'.'+key)
        if (not clean and row['overruns']<1) or row['calls']<row['overruns']:raise ValueError('Missing protected fault count')
        _finite(row['maximum_ms'],kind+'.maximum_ms')
        estimate=_finite(row['estimated_budget_ms'],kind+'.estimated_budget_ms')
        if not 20.<=estimate<=30.:raise ValueError('Invalid inherited admission budget')
        faults=[event for event in events if event['task_code']==code]
        if len(faults)!=row['overruns']:raise ValueError('Fault evidence count mismatch')
        sequences=[]
        for event in faults:
            sequence=_integer(event['event_sequence'],'event_sequence',1);sequences.append(sequence)
            max_sequence=max(max_sequence,sequence)
            if (event['native_completed']!=1 or event['native_attempts']!=1 or event['native_status']!=0
                    or event['native_failed'] or event['body_failed'] or event['diagnostic_finished']!=1):
                raise ValueError('Fault native completion is not proven')
            end=_integer(event['lease_release_decision_mono_ns'],'release_ns',1)
            if not event['lease_started_mono_ns']<end<=captured:raise ValueError('Fault outside snapshot')
            if event['hardcap_exceeded'] not in (0,1) or event['guard_exceeded'] not in (0,1):
                raise ValueError('Invalid protection decisions')
            if not event['hardcap_exceeded'] and not event['guard_exceeded']:raise ValueError('No fault decision')
        if len(set(sequences))!=len(sequences):raise ValueError('Duplicate fault evidence')
    legacy=old['yunet_recovery']
    if (legacy['phase']!=('RUNNING' if clean else 'LATCHED') or legacy['faults']!=jobs['yunet']['overruns']
            or legacy['attempts']!=0 or legacy['recoveries']!=0 or legacy['attempts_in_window']!=0
            or legacy['probe_successes']!=0):
        raise ValueError('Unsupported YuNet recovery history; refusing reset')
    last_sface=max((e for e in events if e['task_code']==2),key=lambda e:e['event_sequence']) if not clean else None
    # The legacy SFace path had no automatic recovery: exactly one proven fault
    # gives an unambiguous zero-attempt migration. Other history stays blocked.
    if jobs['sface']['overruns']!=(0 if clean else 1):raise ValueError('Unsupported legacy SFace recovery history')
    feature=seed['feature_inference']
    feature_names=('requests','execution_attempts','completed','features_returned','deferred',
                   'slot_denials','expired_after_admission')
    inherited_feature={name:_integer(feature[name],'feature.'+name) for name in feature_names}
    if not inherited_feature['features_returned']<=inherited_feature['completed']<=inherited_feature['execution_attempts']<=inherited_feature['requests']:
        raise ValueError('Inconsistent inherited feature counters')
    _integer(old['lease_sequence'],'lease_sequence',max_sequence)
    marker=path.with_name(path.name+'.consumed')
    first_use=False
    try:
        fd=os.open(str(marker),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW,0o600)
    except FileExistsError:
        if marker.is_symlink() or marker.read_text().strip()!=pin['sha256']:
            raise ValueError('Protection handoff consumption marker differs')
    else:
        try:
            stamp=(pin['sha256']+'\n').encode()
            if os.write(fd,stamp)!=len(stamp):raise OSError('Partial protection marker write')
            os.fsync(fd)
        finally:os.close(fd)
        first_use=True
    with schedule.condition:
        if (schedule.jobs or schedule.primary_calls or schedule.active is not None
                or schedule._lease_sequence or hasattr(schedule,'protection_handoff')):
            raise ValueError('Protection handoff must precede all workers and leases')
        if schedule.yunet_recovery is None or schedule.sface_recovery is None:
            raise ValueError('Both independent recovery policies required')
        schedule.jobs=jobs
        schedule.inherited_sface_counters=inherited_feature
        schedule.primary_calls=primary_calls;schedule.primary_overruns=primary_overruns
        schedule.next_primary=0.;schedule._last_primary=None
        schedule._lease_sequence=old['lease_sequence']
        policy=schedule.yunet_recovery
        policy.phase=legacy['phase'];policy.reason=legacy['reason'];policy.faults=legacy['faults']
        policy.fault_primary_calls=primary_calls;policy.fault_primary_overruns=primary_overruns
        policy.cooldown_until=legacy['cooldown_until_monotonic_s']
        policy=schedule.sface_recovery
        if not clean:
            policy.fault(last_sface['lease_release_decision_mono_ns']/1e9,completed=True,body_failed=False,
                hardcap=bool(last_sface['hardcap_exceeded']),guard=bool(last_sface['guard_exceeded']),
                primary_calls=primary_calls,primary_overruns=primary_overruns)
        if not first_use:
            policy.phase='LATCHED';policy.reason='uncheckpointed_same_boot_restart'
            schedule.yunet_recovery.phase='LATCHED';schedule.yunet_recovery.reason='uncheckpointed_same_boot_restart'
            schedule.jobs['yunet']['disabled']=schedule.jobs['sface']['disabled']=True
        diagnostics=schedule.diagnostics
        if diagnostics is not None and diagnostics.enabled:
            with diagnostics.lock:
                diagnostics.sequence=old['lease_sequence']
                diagnostics.events.extend(events)
                diagnostics.counters=copy.deepcopy(diag['counters'])
        schedule.protection_handoff={'source_pid':source_pid,'source_birth_ticks':seed['source_birth_ticks'],
            'source_unit_sha256':seed['source_unit_sha256'],'seed_sha256':pin['sha256'],
            'captured_mono_ns':captured,'counter_scope':'schedule and optional diagnostics include pinned predecessor; other process metrics start fresh',
            'inherited_yunet_faults':jobs['yunet']['overruns'],'inherited_sface_faults':jobs['sface']['overruns']}
        schedule.protection_handoff['first_use']=first_use
        schedule.protection_handoff['mode']='clean_same_boot' if clean else 'protected_same_boot'
    return copy.deepcopy(schedule.protection_handoff)
