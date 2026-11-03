"""One-source forward/rollback adapter over the frozen guarded normal GUI lifecycle."""
import base64
import contextlib
import stat


def reviewed_face():
    candidate,proof=BINDING.verify_binding()
    need(proof['candidate']==PLAN['face_readback'],'current_camera_binding_changed')
    return proof


def parent_transactions(j):
    for key,expected in PLAN['parent_transactions'].items():
        marker=j.get(key,{})
        need(marker.get('state') in expected.get('allowed_states',['APPLIED'])
             and marker.get('stage')==expected['stage'],'parent_marker_changed_'+key)
        transaction=c.parse(c.read(Path(marker['stage'])/'transaction.json',marker['transaction_sha256']))
        need(transaction.get(expected['field'])==expected['spec_sha256'],'parent_spec_changed_'+key)


def ready_state():
    v=listening_readonly_state();h=v.get('handsfree_dialogue',{});pan=v.get('manual_pan',{});r=pan.get('readback') or {}
    need(v.get('phase')=='IDLE' and v.get('playing') is False and v.get('pending_job') is None,
         'idle_no_active_job_required')
    need(h.get('enabled') is False and h.get('state')=='PAUSED' and h.get('microphone_open') is False
         and h.get('conversation_entered') is False and h.get('voice_barge_in') is False
         and h.get('conversation_mode')=='half_duplex','paused_no_conversation_required')
    need(c.parse(c.read('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False},
         'saved_pause_changed')
    need(pan.get('automatic_following') is False and pan.get('state')=='READY'
         and r.get('flags')==0 and r.get('lease_left_ms')==0 and r.get('active') is False and r.get('armed') is False,
         'closed_motion_output_required')
    avatar=v.get('avatar_display',{})
    need(v.get('ui_page')=='main' and avatar.get('visible') is True and avatar.get('frame_scheduling_active') is True
         and avatar.get('target_fps')==16,'main_page_visible_original_16fps_required')
    need(v.get('runtime_faults',{}).get('count')==0,'gui_runtime_fault_present')
    return v


def state():return ready_state()


def expected_owners():
    root=source();j=journal();parent_transactions(j);u,sup,child=owner(root)
    if DIRECTION=='forward':
        for role,actual in [('supervisor',sup),('gtk',child)]:
            expected=PLAN['expected_before_owners'][role]
            need(c.same(actual,dict(pid=expected['pid'],birth=str(expected['birth_ticks']),
                                   cmdline_sha256=expected['command_sha256'])),'reviewed_owner_changed_'+role)
    elif j.get('guard_removed') is True and j.get('phase')=='COMMITTED':
        need(c.same(sup,j['final_supervisor']) and c.same(child,j['final_child']),'committed_candidate_owner_changed')
    else:
        # A failed controlled start may not have reached the final owner journal.
        # Its exact root/startup/source closure, current parent/child command lines,
        # and publisher target must still match before obtaining a fresh WM proof.
        need(j.get('target')==EXACT_TARGET and j.get('target_startup_sha256')==BASE_SPEC['startup_sha256']
             and j.get('phase') in ('GUARDED','STARTING','START_INTENT','POSTCHECK_FAILED_GUARDED'),
             'known_guarded_candidate_start_required')
    return u,sup,child


def exact_new(path,raw):
    path=Path(path)
    if path.exists():need(c.read(path)==raw,'prepared_file_changed')
    else:c.create(path,raw)


def validate_snapshot(current,*,first_apply):
    need(set(current)==set(PLAN['targets']),'exact_three_target_snapshot_required')
    for name,pin in current.items():
        row=PLAN['targets'][name]
        allowed=(row['old_sha256'],row['new_sha256'])
        need(pin in allowed,'unknown_transaction_payload_'+name)
        if first_apply and not PLAN['allow_known_mixed_on_first_apply']:
            need(pin==row['old_sha256'],'forward_initial_source_changed_'+name)


def atomic_preserve_mode(path,raw):
    path=Path(path);info=path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022,'safe_root_owned_target_required')
    tmp=path.with_name(path.name+'.single-projection-'+str(os.getpid()))
    c.create(tmp,raw);os.chmod(tmp,stat.S_IMODE(info.st_mode),follow_symlinks=False)
    os.replace(str(tmp),str(path))
    fd=os.open(str(path.parent),os.O_DIRECTORY|os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def apply_one_source():
    boot();j=journal();inactive(j);parent_transactions(j)
    phases=('NORMAL_CLOSED','SINGLE_PROJECTION_INTENT')
    if DIRECTION=='rollback':phases+=('STARTING','START_INTENT','POSTCHECK_FAILED_GUARDED')
    need(j['phase'] in phases and not j['guard_removed'],
         'guarded_normal_close_required')
    need(j['active_root']==EXACT_TARGET,'production_root_changed')
    stage=Path(PLAN['stage']);backup=stage/'before';marker_key=PLAN['marker']
    need(stage.parent==CONTROL and stage.resolve()==stage and not stage.is_symlink(),'owned_transaction_stage_required')
    for path in (stage,backup):
        if not path.exists():path.mkdir(mode=0o700)
        need(path.resolve()==path and path.stat().st_uid==0 and not path.stat().st_mode&0o077,'private_stage_required')
    locks=['/run/aura-avatar-ui.lock','/home/root/.local/share/aura-board-business/writer.lock',
           '/home/root/.local/share/aura-board-business/speaker/speaker-writer.lock']
    with contextlib.ExitStack() as stack:
        for path in locks:
            fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW);handle=stack.enter_context(os.fdopen(fd,'r+b'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ownerless(c.show());guarded(j);reviewed_face()
        need(c.parse(c.read('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False},'pause_changed')
        for relative,pin in BASE_SPEC['component_sha256'].items():
            if relative!=PLAN['changed_source']:c.read(Path(EXACT_TARGET)/'runtime/aura'/c.relative(relative),pin)
        sys.path.insert(0,str(Path(EXACT_TARGET)/'runtime/aura'))
        from common.board_production_bootstrap import verify_production_bootstrap
        cfg=GUI['board_business']
        proof=verify_production_bootstrap(Path('/home/root/.local/share/aura-board-business'),cfg['bootstrap_receipt'],cfg['bootstrap_receipt_sha256'])
        need(proof['profiles_migration_verified'] is True,'original_bootstrap_receipt_required')
        pending=j.get(marker_key)
        need(pending is None or (pending.get('state')=='INTENT' and pending.get('stage')==PLAN['stage']
             and pending.get('transaction_sha256')==PLAN['transaction_sha256']),'different_or_completed_transaction_refused')
        current={name:c.sha(c.read(row['path'])) for name,row in PLAN['targets'].items()}
        validate_snapshot(current,first_apply=pending is None)
        if pending is None:
            for name,row in PLAN['targets'].items():exact_new(backup/name,c.read(row['path'],current[name]))
            exact_new(backup/'payload-pins.json',c.encoded(current))
            exact_new(backup/'publication-state.json',c.read(STATE))
        else:
            saved=c.parse(c.read(backup/'payload-pins.json',pending['backup_pins_sha256']))
            validate_snapshot(saved,first_apply=False)
            for name,pin in saved.items():c.read(backup/name,pin)
            c.read(backup/'publication-state.json',pending['backup_journal_sha256'])
        for name,row in PLAN['targets'].items():
            raw=base64.b64decode(row['new_base64'],validate=True)
            need(c.sha(raw)==row['new_sha256'],'prepared_payload_changed')
            exact_new(stage/name,raw)
        exact_new(stage/'transaction.json',c.encoded(PLAN['transaction']))
        exact_new(stage/'applied-spec.json',c.encoded(NEW_SPEC))
        if pending is None:
            j[marker_key]=dict(state='INTENT',stage=PLAN['stage'],transaction_sha256=PLAN['transaction_sha256'],
                               backup_pins_sha256=c.sha(c.read(backup/'payload-pins.json')),
                               backup_journal_sha256=c.sha(c.read(backup/'publication-state.json')),
                               previous_startup_sha256=BASE_SPEC['startup_sha256'])
            j['phase']='SINGLE_PROJECTION_INTENT';save(j)
        for name,row in PLAN['targets'].items():
            guarded(j);reviewed_face();need(journal()==j,'journal_changed_during_transaction')
            pin=c.sha(c.read(row['path']));need(pin in (row['old_sha256'],row['new_sha256']),'unknown_partial_target_refused')
            if pin==row['old_sha256']:atomic_preserve_mode(row['path'],base64.b64decode(row['new_base64'],validate=True))
        for name,row in PLAN['targets'].items():c.read(row['path'],row['new_sha256'])
        j[marker_key]=dict(j[marker_key],state='APPLIED')
        j.update(phase='NORMAL_CLOSED',target_startup_sha256=NEW_SPEC['startup_sha256'],target_pins=380)
        save(j)
    return dict(status='ONE_SOURCE_APPLIED_GUI_STOPPED',direction=DIRECTION,changed_source=PLAN['changed_source'],
                unchanged_components=379,startup_sha256=NEW_SPEC['startup_sha256'],manifest_sha256=NEW_SPEC['source_manifest_sha256'],
                configuration_sha256=NEW_SPEC['configuration_sha256'],camera_unchanged=True,forced_action=False)


def applied():
    j=journal();parent_transactions(j);marker=j.get(PLAN['marker'],{})
    need(marker.get('state')=='APPLIED' and marker.get('stage')==PLAN['stage']
         and marker.get('transaction_sha256')==PLAN['transaction_sha256'],'exact_applied_transaction_required')
    tx=c.parse(c.read(Path(marker['stage'])/'transaction.json',marker['transaction_sha256']))
    need(tx['applied_spec_sha256']==c.sha(c.encoded(NEW_SPEC)),'applied_spec_changed')
    need(j['target_startup_sha256']==NEW_SPEC['startup_sha256'],'publisher_target_startup_changed')
    return j


def dispatch_single_projection():
    boot()
    with open('/run/aura-production-publisher.lock','a') as publisher:
        fcntl.flock(publisher,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if ACTION in ('inspect','guard','window-inspect','normal-close'):
            expected_owners();ready_state()
        if ACTION=='inspect':
            return dict(status='READ_ONLY_READY_FOR_REVIEW',direction=DIRECTION,startup_sha256=SPEC['startup_sha256'],
                        camera_owner=SPEC['camera_owner'],component_pins=380,changed_source=PLAN['changed_source'])
        if ACTION=='guard':return guard()
        if ACTION=='window-inspect':
            proof=window();return dict(status='WINDOW_INSPECTED_NO_CLOSE',window=proof['window'],review_token=c.sha(c.encoded(proof)))
        if ACTION=='normal-close':return close()
        if ACTION=='apply':return apply_one_source()
        applied()
        if ACTION=='start':return start()
        if ACTION=='ready':
            result=ready()
            if result.get('status')=='PRODUCTION_BOARD_BUSINESS_READY':
                _,sup,child=owner(Path(EXACT_TARGET));result.update(supervisor=sup,gtk=child,
                    startup_sha256=NEW_SPEC['startup_sha256'],source_manifest_sha256=NEW_SPEC['source_manifest_sha256'])
            return result
        raise ValueError('unknown single projection action')
