"""Configuration-only transaction over the existing v24 guarded normal lifecycle."""
import base64
import contextlib
import types


def reviewed_face():
    candidate,proof=BINDING.verify_binding()
    need(proof['candidate']==PLAN['face_readback'],'current_candidate_binding_changed')
    return proof


def parent_transactions(j):
    for key,expected in PLAN['parent_transactions'].items():
        marker=j.get(key,{})
        need(marker.get('state')=='APPLIED' and marker.get('stage')==BASE_SPEC[key]['stage'],
             'unchanged_parent_transaction_required_'+key)
        tx=c.parse(c.read(Path(marker['stage'])/'transaction.json',marker['transaction_sha256']))
        need(tx.get('applied_spec_sha256')==expected,'unchanged_parent_spec_required_'+key)


def ready_state():
    v=listening_readonly_state();h=v.get('handsfree_dialogue',{});pan=v.get('manual_pan',{})
    r=pan.get('readback') or {}
    need(v.get('playing') is False and pan.get('automatic_following') is False
         and pan.get('state')=='READY' and r.get('flags')==0 and r.get('lease_left_ms')==0
         and type(pan.get('pulse_us')) is int and 500<=pan['pulse_us']<=2500,
         'original_manual_ready_stopped_required')
    preference=c.parse(c.read('/home/root/.local/share/aura-board-business/listening_preference.json'))
    need(preference=={'version':1,'enabled':False} and h.get('enabled') is False
         and h.get('state')=='PAUSED' and h.get('microphone_open') is False,
         'saved_user_pause_required')
    need(h.get('voice_barge_in') is False and h.get('conversation_mode')=='half_duplex',
         'existing_half_duplex_required')
    return v


def exact_new(path,raw):
    path=Path(path)
    if path.exists():need(c.read(path)==raw,'prepared_file_changed')
    else:c.create(path,raw)


def apply_original_configuration():
    boot();j=journal();inactive(j);parent_transactions(j)
    need(j['phase'] in ('NORMAL_CLOSED','AXIS_ORIGINAL_BINDING_INTENT') and not j['guard_removed'],
         'guarded_normal_closed_required')
    need(j['active_root']==EXACT_TARGET,'current_v24_root_required')
    stage=Path(PLAN['stage']);backup=stage/'before'
    need(stage.parent==CONTROL and not stage.is_symlink(),'new_owned_binding_stage_required')
    if not stage.exists():stage.mkdir(mode=0o700)
    if not backup.exists():backup.mkdir(mode=0o700)
    for path in (stage,backup):
        need(path.resolve()==path and path.stat().st_uid==0 and not path.stat().st_mode&0o077,
             'private_binding_stage_required')
    locks=['/run/aura-avatar-ui.lock','/home/root/.local/share/aura-board-business/writer.lock',
           '/home/root/.local/share/aura-board-business/speaker/speaker-writer.lock']
    with contextlib.ExitStack() as stack:
        for path in locks:
            fd=os.open(path,os.O_RDWR|os.O_NOFOLLOW);handle=stack.enter_context(os.fdopen(fd,'r+b'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ownerless(c.show());guarded(j);reviewed_face()
        need(c.parse(c.read('/home/root/.local/share/aura-board-business/listening_preference.json'))=={'version':1,'enabled':False},'pause_changed')
        # Every code/resource component remains the exact v24 version.
        for rel,pin in BASE_SPEC['component_sha256'].items():
            if rel not in PLAN['changed_components']:
                c.read(Path(EXACT_TARGET)/'runtime/aura'/c.relative(rel),pin)
        sys.path.insert(0,str(Path(EXACT_TARGET)/'runtime/aura'))
        from common.board_production_bootstrap import verify_production_bootstrap
        cfg=OLD_GUI['board_business']
        proof=verify_production_bootstrap(Path('/home/root/.local/share/aura-board-business'),
            cfg['bootstrap_receipt'],cfg['bootstrap_receipt_sha256'])
        need(proof['profiles_migration_verified'] is True,'original_bootstrap_receipt_required')
        pending=j.get('axis_original_rebind')
        if pending is None:
            for name,row in PLAN['targets'].items():
                old=c.read(row['path'],row['old_sha256'])
                exact_new(backup/name,old)
            exact_new(backup/'publication-state.json',c.read(STATE))
        else:
            need(pending['state']=='INTENT' and pending['stage']==PLAN['stage']
                 and pending['transaction_sha256']==PLAN['transaction_sha256'],'other_binding_transaction_present')
            for name,row in PLAN['targets'].items():c.read(backup/name,row['old_sha256'])
        for name,row in PLAN['targets'].items():
            raw=base64.b64decode(row['new_base64'],validate=True)
            need(c.sha(raw)==row['new_sha256'],'new_configuration_payload_changed')
            exact_new(stage/name,raw)
        exact_new(stage/'prepared-gui.json',c.encoded(NEW_GUI))
        exact_new(stage/'transaction.json',c.encoded(PLAN['transaction']))
        exact_new(stage/'applied-spec.json',c.encoded(NEW_SPEC))
        if pending is None:
            j.update(phase='AXIS_ORIGINAL_BINDING_INTENT',axis_original_rebind=dict(state='INTENT',
                stage=PLAN['stage'],transaction_sha256=PLAN['transaction_sha256'],
                previous_startup_sha256=BASE_SPEC['startup_sha256']))
            save(j)
        for name,row in PLAN['targets'].items():
            current=c.read(row['path']);pin=c.sha(current)
            need(pin in (row['old_sha256'],row['new_sha256']),'unknown_partial_configuration_refused')
        for name,row in PLAN['targets'].items():
            guarded(j);reviewed_face()
            need(journal()==j,'publication_state_changed_during_binding')
            current=c.read(row['path']);pin=c.sha(current)
            need(pin in (row['old_sha256'],row['new_sha256']),'unknown_configuration_refused')
            if pin==row['old_sha256']:
                atomic(row['path'],base64.b64decode(row['new_base64'],validate=True))
        for name,row in PLAN['targets'].items():c.read(row['path'],row['new_sha256'])
        j.update(phase='NORMAL_CLOSED',target_startup_sha256=NEW_SPEC['startup_sha256'],target_pins=380,
                 axis_original_rebind=dict(j['axis_original_rebind'],state='APPLIED'))
        save(j)
        BINDING_J=BINDING.state()
        BINDING_J.update(original_committed_startup_sha256=NEW_SPEC['startup_sha256'],
            original_committed_manifest_sha256=NEW_SPEC['source_manifest_sha256'],
            original_binding_transaction_sha256=PLAN['transaction_sha256'],
            phase='ORIGINAL_CONFIGURATION_APPLIED_UI_STOPPED')
        BINDING.save(BINDING_J)
    return dict(status='ORIGINAL_CONFIGURATION_APPLIED_UI_STOPPED',changed_components=PLAN['changed_components'],
        component_count=380,python_or_native_sources_changed=False,old_files_backed_up=True,
        startup_sha256=NEW_SPEC['startup_sha256'],manifest_sha256=NEW_SPEC['source_manifest_sha256'])


def binding_applied():
    j=journal();parent_transactions(j)
    item=j.get('axis_original_rebind',{})
    need(item.get('state')=='APPLIED' and item.get('stage')==PLAN['stage']
         and item.get('transaction_sha256')==PLAN['transaction_sha256'],'exact_original_binding_required')
    tx=c.parse(c.read(Path(PLAN['stage'])/'transaction.json',PLAN['transaction_sha256']))
    need(tx['new_spec_sha256']==c.sha(c.encoded(NEW_SPEC)),'new_original_spec_changed')
    need(j['target_startup_sha256']==NEW_SPEC['startup_sha256'],'new_startup_not_committed')
    return j


def dispatch_original():
    boot()
    with open('/run/aura-production-publisher.lock','a') as publisher_lock:
        fcntl.flock(publisher_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if ACTION=='guard':return guard()
        if ACTION=='window-inspect':
            value=window();return dict(status='WINDOW_INSPECTED_NO_CLOSE',window=value['window'],review_token=c.sha(c.encoded(value)))
        if ACTION=='normal-close':return close()
        if ACTION=='apply':return apply_original_configuration()
        binding_applied()
        if ACTION=='start':return start()
        if ACTION=='ready':
            result=ready()
            if result['status']=='PRODUCTION_BOARD_BUSINESS_READY':
                local=BINDING.state();local['phase']='ORIGINAL_ENTRY_READY';BINDING.save(local)
            return result
        raise ValueError('unknown original restoration action')
