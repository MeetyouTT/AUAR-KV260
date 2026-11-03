# USE_SESSION_COMMON
# USE_CAMERA_BINDING_RULES
"""Renew metadata only after proving exact consumed shutdown history and the unchanged original gallery/model."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='ORIGINAL_MOTION_CONFIG_PREPARED'
original=Path('/home/root/aura-board-owner-candidate-20261030/private-pin-bebd3e7d-229296-jpeg-aba-20261031/face_gallery_readback.local.json')
assert digest(original)=='dc6071426041e3589f3c3eb42fe32ee9b82aca5d6d6d26bf0ac58832cdd5f446'
baseline=document(original)
for path,sha in baseline['source_sha256'].items():
    assert path!=baseline['database'] and not path.endswith(('.sqlite','.sqlite3','.db'))
    assert digest(path)==sha
assert not (Path('/proc')/str(j['camera_pid'])).exists()
proc=Path('/proc')/str(j['restored_camera_pid'])
assert digest(proc/'cmdline')==j['restored_camera_command_sha256']
birth=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]);assert birth==j['restored_camera_birth']
assert dpu_users()==[j['restored_camera_pid']] and int(systemd()['MainPID'])==j['restored_camera_pid']
closed=document(CHECKPOINT)
assert digest(CHECKPOINT)==j['checkpoint_sha256'] and closed['seed']==j['checkpoint_seed']
assert closed['auxiliary']==j['checkpoint_auxiliary'] and closed['source_unit_sha256']=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
marker=CHECKPOINT.with_name(CHECKPOINT.name+'.native-consumed-'+j['checkpoint_sha256'])
assert read_regular(marker)==(j['checkpoint_sha256']+'\n').encode()
audit=document(OPS/'pan-face-edge-v5/native-operator-v1'/('recovery-audit-'+str(j['restored_camera_pid'])+'.json'))
assert audit['exact_seed_before_operator_request']==closed['seed'] and audit['checkpoint_sha256']==j['checkpoint_sha256']
runpath=OPS/('native-run-'+BOOT+'-'+str(j['restored_camera_pid']))/'config.json'
new_runtime=document(runpath);old_runtime=document(baseline['camera_config'])
h=get_json(8790,'/health');handoff=h['dpu_schedule']['protection_handoff']
assert h['pid']==j['restored_camera_pid'] and h['identity']['ready'] is True
assert h['camera_error']==h['detector_error']==h['identity']['error']==''
assert handoff['seed_sha256']==j['checkpoint_sha256'] and handoff['source_pid']==j['camera_pid']
assert int(handoff['source_birth_ticks'])==j['camera_birth'] and h['dpu_schedule']['owner_fenced'] is False
assert h['dpu_schedule']['primary_calls']>=closed['seed']['primary_calls']
assert h['dpu_schedule']['primary_period_overruns']>=closed['seed']['primary_period_overruns']
identity=document(baseline['identity_config'])
assert identity['database']==baseline['database'] and identity['model_id']==baseline['model_id']
candidate=binding_candidate(baseline,old_runtime,new_runtime,boot=BOOT,old_pid=j['camera_pid'],old_birth=j['camera_birth'],
    new_pid=j['restored_camera_pid'],new_birth=birth,command_sha=j['restored_camera_command_sha256'],
    new_runtime_path=str(runpath),new_runtime_sha=digest(runpath),checkpoint_sha=j['checkpoint_sha256'],model_id=h['identity']['model_id'])
second=get_json(8790,'/health')
assert all(second[k]==h[k] for k in ('pid','board_boot_id','service_epoch','camera_epoch'))
assert digest(proc/'cmdline')==candidate['camera_cmdline_sha256']
private=ROOT/'camera-binding';assert not private.exists();private.mkdir(mode=0o700)
atomic(private/'face_gallery_readback.local.json',candidate)
proof=dict(schema='aura-current-camera-binding-proof-1',boot=BOOT,
    previous_owner=dict(pid=j['camera_pid'],birth=j['camera_birth']),
    current_owner=dict(pid=j['restored_camera_pid'],birth=birth,command_sha256=candidate['camera_cmdline_sha256']),
    previous_readback=dict(path=str(original),sha256=digest(original)),
    candidate=dict(path=str(private/'face_gallery_readback.local.json'),sha256=digest(private/'face_gallery_readback.local.json')),
    native_checkpoint_sha256=j['checkpoint_sha256'],native_checkpoint_seed_preserved=True,consumption_marker_verified=True,
    original_source_pin_count=len(baseline['source_sha256']),candidate_source_pin_count=len(candidate['source_sha256']),
    service_epoch=h['service_epoch'],camera_epoch=h['camera_epoch'],runtime_sha256=digest(runpath),
    model_id_unchanged=True,gallery_selection_unchanged=True,original_runtime_changed_only_seed=True,
    primary_period_overruns=h['dpu_schedule']['primary_period_overruns'],database_opened=False,templates_exported=False)
atomic(private/'proof.json',proof)
j.update(phase='ORIGINAL_CONFIG_AND_CAMERA_BINDING_PREPARED',camera_readback=proof['candidate'],
    camera_binding_proof_sha256=digest(private/'proof.json'));save(j)
print(json.dumps(dict(status=j['phase'],face_readback=proof['candidate'],proof_sha256=j['camera_binding_proof_sha256'],
    camera_owner=proof['current_owner'],original_source_pin_count=proof['original_source_pin_count'],
    candidate_source_pin_count=proof['candidate_source_pin_count'],native_checkpoint_consumption_verified=True,
    same_gallery_and_model=True,primary_period_overruns=proof['primary_period_overruns'],
    database_opened=False,templates_exported=False,production_written=False)))
