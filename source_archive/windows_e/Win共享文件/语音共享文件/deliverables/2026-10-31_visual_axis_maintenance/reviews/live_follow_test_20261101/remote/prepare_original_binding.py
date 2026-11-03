# USE_SESSION_COMMON
"""Create fresh configuration for the unchanged original motor and camera producers."""
import copy
current_guard();wide_active();manifest=verify_wide_files()
j=state();assert j['phase']=='FIRST_FACE_TEST_STOPPED'
assert j['first_follow_returncode']==0 and j['direction_qualified'] is True
assert int(systemd()['MainPID'])==j['restored_camera_pid'] and dpu_users()==[j['restored_camera_pid']]
config=BUSINESS/'runtime/aura/config'
manual=document(config/'pan_manual.local.json');face=document(config/'pan_face.local.json')
original=Path(face['release_root']);assert original==Path('/home/root/aura-pan-wide-20261028/control-10282601')
assert digest(original/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
original_manifest=document(original/'deployment-manifest.json')
assert len(original_manifest['files'])==25
assert all(digest(r['destination'])==r['sha256'] for r in original_manifest['files'])
# The fresh status/STOP receipt only qualifies the current platform and output
# off state. It deliberately does not claim a calibrated shaft angle.
sys.path.insert(0,str(RELEASE/'driver'))
from vsrv_driver import VSRVDriver
from vsrv_transport import NativeRegisters
with NativeRegisters(RELEASE/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],BOOT,manifest['runtime_files']) as io:
    device=VSRVDriver(io,0x10282601,BOOT);before=device.status();stopped=device.stop()
assert stopped['flags']==0 and stopped['lease_left_ms']==0
assert stopped==j['current_stopped_readback']
target=ROOT/'original-entry';assert not target.exists();target.mkdir(mode=0o700)
release=target/'manual-release';release.mkdir(mode=0o700)
old_release=Path(manual['release_manifest']);old=document(old_release)
assert old['status']=='USER_RATED_RANGE_VSRV2'
assert old['payload_files']==manifest['payload_files'] and old['runtime_files']==manifest['runtime_files']
old_authority=old_release.parent/old['authorization']['file']
assert digest(old_authority)==old['authorization']['sha256']
authority=copy.deepcopy(document(old_authority))
authority.update(boot_id=BOOT,clearance_confirmed=True,
    user_instruction_quote='原来班上的那个就可以了啊，愿挨板端已经做额转轴跟随',
    scope='reuse already authorized original 500..2500us software scope; no new angle qualification',
    predecessor_authorization=dict(path=str(old_authority),sha256=digest(old_authority)),
    current_user_mount_and_power_confirmation='已上电，现在可以看',physical_calibration_claimed=False)
atomic(release/'authorization.json',authority)
proof=dict(boot_id=BOOT,fdt_sha256=digest('/sys/firmware/fdt'),build_id=0x10282601,
    identity_stop_passed=True,ARM_sent=False,COMMIT_sent=False,before=before,after_stop=stopped,
    external_waveform_verified=False,mechanical_zero_calibrated=False)
atomic(release/'platform-proof.json',proof)
qualified=copy.deepcopy(old);qualified.update(boot_id=BOOT,
    authorization=dict(file='authorization.json',sha256=digest(release/'authorization.json')),
    platform_proof=dict(file='platform-proof.json',sha256=digest(release/'platform-proof.json')))
for name,sha in manifest['payload_files'].items():
    data=read_regular(RELEASE/'driver'/name);assert hashlib.sha256(data).hexdigest()==sha
    with (release/name).open('xb') as f:f.write(data)
    os.chmod(release/name,0o600)
atomic(release/'release.json',qualified)
zone=document(Path(face['arguments']['zone-settings']))
assert zone['board_boot_id']==BOOT and zone['viewport']==[8,112,568,300]
atomic(target/'face-zone-settings.json',zone)
direction=document(ROOT/'current-direction-human.json')
atomic(target/'pan_direction.current.json',direction)
human=dict(authority,boot_id=BOOT,actual_direction_evidence_sha256=digest(target/'pan_direction.current.json'))
atomic(target/'human-evidence.json',human)
face['arguments'].update(context=str(ROOT/'wide-context.json'),
    **{'app-root':str(BUSINESS/'runtime/aura'),'direction-evidence':str(config/'pan_direction.current.json'),
       'human-evidence':str(target/'human-evidence.json'),'zone-settings':str(target/'face-zone-settings.json')})
assert face['release_root']==str(original)
atomic(target/'pan_face.local.json',face)
manual.update(boot_id=BOOT,fdt_sha256=digest('/sys/firmware/fdt'),
    release_manifest=str(release/'release.json'),release_manifest_sha256=digest(release/'release.json'),
    face_follow_config=str(config/'pan_face.local.json'))
atomic(target/'pan_manual.local.json',manual)
# Verify the unchanged active adapter's release guards without opening its MMIO.
sys.path.insert(0,str(BUSINESS/'runtime/aura'))
from board.motion.manual_vsrv import load_release
assert load_release(manual)[0]==release
sys.path.insert(0,str(original))
from face_zone import camera_zone
camera_zone(zone,BOOT)
j.update(phase='ORIGINAL_MOTION_CONFIG_PREPARED',original_configuration_root=str(target),
    original_controller_manifest_sha256=face['manifest_sha256'],current_stopped_readback=stopped);save(j)
print(json.dumps(dict(status=j['phase'],original_controller_root=str(original),controller_files=25,
    original_sources_unchanged=True,manual_release_guards_passed=True,current_boot_and_fdt_bound=True,
    physical_angle_calibrated=False,range_us=[manual['manual_minimum_us'],manual['manual_maximum_us']],
    stage=str(target),candidate_configuration={name:dict(path=str(target/name),sha256=digest(target/name))
        for name in ('pan_manual.local.json','pan_face.local.json','pan_direction.current.json')},
    production_files_written=0,ARM_sent=False,COMMIT_sent=False)))
