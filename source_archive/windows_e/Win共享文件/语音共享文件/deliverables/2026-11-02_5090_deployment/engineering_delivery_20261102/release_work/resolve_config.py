from common import *
import re, itertools
M=load(B/'visual_artifact_fix_20261102/release/fresh_expected_after.json')
ref=M['component_sha256']
def enc(v,ascii=True):
    return (json.dumps(v,sort_keys=True,ensure_ascii=ascii,indent=2)+'\n').encode('utf8')
def restore(d,h,file,label,ascii):
    raw=enc(d,ascii)
    if hashlib.sha256(raw).hexdigest()!=h:return False
    file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
    print('SHA MATCH',label,file.name)
    return True
for p in (B/'other_components_20261102').rglob('startup*.json'):
    j=load(p)
    if 'runtime' not in j or 'component_sha256' not in j:continue
    j['component_sha256']=ref
    if restore(j,M['startup_sha256'],ROOT/'board/config/startup.snapshot.json',str(p.relative_to(B)),True):break
d=B/'maintenance_original_axis_20261101'
initial=load(B/'axis_follow_restore/original_sources/ac1522c826c1__pan_direction.current.json')
pool={hashlib.sha256(enc(initial,False)).hexdigest():initial}
for p in (P/'deliverables/2026-10-31_visual_axis_maintenance').rglob('*direction*.json'):
    try:
        v=load(p)
        if 'axis_camera_mirrored_control_polarity' in v:pool[sha(p)]=v
    except (ValueError,OSError):pass
for src in [d/'reconnect_original_axis_config.py', d/'binding_refresh_20261102/apply.py']:
    code=src.read_text(encoding='utf8')
    boot=re.search(r"^BOOT='([^']+)'",code,re.M)[1]
    base=re.search(r"^BASE=Path\('([^']+)'\)",code,re.M)[1]
    tx=base+'/'+re.search(r"^TX=BASE/'([^']+)'",code,re.M)[1]
    original='/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura/config/pan_direction.current.json'
    msg=re.search(r"authorization.update\(boot_id=BOOT,user_instruction_quote='([^']+)'",code)[1]
    for h,prev in list(pool.items()):
        cur=dict(prev)
        cur.update(boot_id=boot,qualification_basis='User-directed reuse of previously human-confirmed polarity on unchanged camera/axis installation',source='Current user restoration instruction and original human-confirmed mapping',current_boot_motion_measured=False,user_instruction_quote=msg,predecessor_direction=dict(path=tx+'/direction.predecessor.json',original_path=original,sha256=h,boot_id=prev['boot_id']))
        for k in ('trial_sha256','pulse_sequence_us','physical_return_stop_observed','command_return_stop_verified','user_quote'):cur.pop(k,None)
        cur['corrected_mapping_live_acceptance']='PENDING_CURRENT_USER_OBSERVATION'
        pool[hashlib.sha256(enc(cur,False)).hexdigest()]=cur
        if restore(cur,ref['config/pan_direction.current.json'],ROOT/'src/software/config/pan_direction.current.json',src.name,False):sys.exit(0)
print('direction remaining. variants:',len(pool))
