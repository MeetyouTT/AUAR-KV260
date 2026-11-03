"""Bind the existing original one-shot restoration scripts to the granted phase."""
import datetime, hashlib, importlib.util, json, os, sys
from pathlib import Path

B=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment')
J=B/'joint_acceptance_180s_20261102'; M=B/'maintenance_original_axis_20261101'; L=Path(__file__).parent
GRANT_SHA='7c82dc3670179726e57aa5ed50ff2e818f513d1ac52280f43bfd9e36e5a780ae'
BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
TX='/home/root/aura-5090-recovery-20261102-a6d4a069/axis-wide-idstop-184011-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
g=load(J/'AXIS_WIDE_IDSTOP_PHASE_HANDOFF.json')
assert sha(J/'AXIS_WIDE_IDSTOP_PHASE_HANDOFF.json')==GRANT_SHA
assert g['permission_active'] and g['operator_thread']=='01a19b64-8194-70e3-806b-03fa9a283918'
assert g['status']=='ACTIVE_AXIS_EXCLUSIVE_ORIGINAL_WIDE_AND_ID_STOP_ONLY' and g['boot_id']==BOOT
for field,name in [('CPU_completion_pin','CPU_PROTECTED_STOP_SEAL_RESULT.json'),('CPU_explicit_return_pin','CPU_DEVICE_RETURNED_AFTER_STOP_SEAL.json'),('source_manifest_phase_pin','CPU_RESTORE_PHASE_HANDOFF.json'),('motor_power_off_human_receipt','MOTOR_POWER_OFF_CONFIRMED.json'),('local_original_preparation_pin','AXIS_WIDE_IDSTOP_LOCAL_PREPARED.json')]:
    assert sha(J/name)==g[field]['sha256'],name
cpu=load(J/'CPU_RESTORE_PHASE_HANDOFF.json')
P={'grant_sha256':GRANT_SHA,'boot':BOOT,'tx':TX,'startup':g['startup_sha256'],
   'sealed':g['sealed_identical_final'],'checkpoint':g['genuine_new_final'],
   'history':g['validation_result_board_pin'],'expected':g['expected_history_board_pin'],
   'components':cpu['component_sha256'],'camera':cpu['camera_owner'],
   'units':{a:'aura-original-'+a+'-a6d4-184011-v1.service' for a in ['remove','load','idstop']}}
assert len(P['components'])==380

COMMON=r'''
import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
def psha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pshow(n,props):
    r=subprocess.run(['systemctl','show',n,'--property='+props],capture_output=True,text=True,timeout=5)
    assert r.returncode==0,(n,r.stderr)
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def same_owner(v):
    p=Path('/proc')/str(v['pid'])
    try:return (p/'stat').read_text().rsplit(')',1)[1].split()[19]==str(v['birth_ticks']) and psha(p/'cmdline')==v['command_sha256']
    except (FileNotFoundError,ProcessLookupError):return False
def phase_check(full=False):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==P['boot']
    cp=Path(P['checkpoint']['path']); raw=cp.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==P['checkpoint']['sha256']
    assert Path(P['sealed']['path']).read_bytes()==raw
    assert not os.path.lexists(str(cp)+'.native-consumed-'+P['checkpoint']['sha256'])
    for name in ['history','expected']:assert psha(P[name]['path'])==P[name]['sha256'],name
    history=json.loads(Path(P['history']['path']).read_bytes())
    assert history['status']=='ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED' and history['archive_count']==19
    assert history['expected_sha256']==P['expected']['sha256'] and history['checkpoint_pin']['sha256']==P['checkpoint']['sha256']
    assert history['complete_ordered_history_verified'] and history['all_required_current_boot_cumulative_lower_bounds_checked']
    base=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
    assert psha(base/'startup/config.json')==P['startup']
    if full:
        assert json.loads((base/'startup/config.json').read_bytes())['component_sha256']==P['components']
        for name,digest in P['components'].items():assert psha(base/'runtime/aura'/name)==digest,name
        root=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154')
        assert psha(root/'deployment-manifest.json')=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
        manifest=json.loads((root/'deployment-manifest.json').read_bytes());assert len(manifest['files'])==25
        for f in manifest['files']:
            fpath=Path(f['destination']);fpath.relative_to(root)
            assert psha(fpath)==f['sha256'] and fpath.stat().st_size==f['bytes']
    services={n:pshow(n,'MainPID,ActiveState,SubState,Job,Result') for n in ['aura-camera-ui.service','aura-avatar-ui.service']}
    assert all(v=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':'','Result':'success'} for v in services.values()),services
    assert not same_owner(P['camera'])
    jobs=subprocess.run(['systemctl','list-jobs','--no-legend','--no-pager'],capture_output=True,text=True,timeout=5)
    assert jobs.returncode==0 and not jobs.stdout.strip(),jobs.stdout
    owners=[];unreadable=[];daemons=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            maps=(proc/'maps').read_text(); targets=[]
            for fd in (proc/'fd').iterdir():
                try:targets.append(str(fd.readlink()))
                except FileNotFoundError:continue
            if any(x in maps for x in ('libvart','libaura_native_operator','libvsrv.so')) or any(t.startswith(('/dev/dri/renderD','/dev/dpu')) or t=='/dev/mem' for t in targets):owners.append(int(proc.name))
            try:
                exe=str((proc/'exe').readlink())
                if exe=='/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd':
                    daemons.append({'pid':int(proc.name),'birth_ticks':(proc/'stat').read_text().rsplit(')',1)[1].split()[19], 'command_sha256':psha(proc/'cmdline'),'executable_sha256':psha(proc/'exe')})
            except FileNotFoundError:pass
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:
            if proc.exists():unreadable.append(int(proc.name))
    assert not owners and not unreadable,(owners,unreadable)
    assert psha('/usr/bin/dfx-mgr-client')=='a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7'
    assert len(daemons)==1 and daemons[0]['executable_sha256']=='369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd',daemons
    if 'daemon' in P:assert daemons[0]==P['daemon']
    return {'boot_id':P['boot'],'daemon':daemons[0],'services':services,'no_pending_jobs':True,'hardware_owners':owners,'unreadable_alive':unreadable,'checkpoint_sha256':P['checkpoint']['sha256'],'checkpoint_unconsumed':True,'source380_and_controller25_verified':full}
def platform_snapshot():
    root=Path('/sys/kernel/config/device-tree/overlays'); overlays=[]
    if root.exists():
        for e in root.iterdir():
            if e.is_dir():overlays.append({'name':e.name,'status':(e/'status').read_text().strip() if (e/'status').exists() else None})
    fw=Path('/proc/device-tree/fpga-full/firmware-name')
    return {'firmware':fw.read_bytes().rstrip(b'\0').decode() if fw.exists() else None,'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),'vart':Path('/etc/vart.conf').read_text(),'fdt_sha256':psha('/sys/firmware/fdt'),'overlays':overlays,'render_devices':[{'name':e.name,'device':str((e/'device').resolve())} for e in Path('/sys/class/drm').glob('renderD*')]}
'''

def save_new(path,data):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(data);f.flush();os.fsync(f.fileno())

def rebind(source):
    text=(M/source).read_text(encoding='utf-8')
    text=text.replace('903cfade-b93c-48fa-804e-379be1967313',BOOT).replace('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1',TX)
    text=text.replace('c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471',P['checkpoint']['sha256']).replace('0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f',P['startup'])
    for a in ['remove','load','idstop']:text=text.replace('aura-original-'+a+'-903c-v1.service',P['units'][a])
    text=text.replace("(TX/('native-final-'+CP_SHA+'.json')).read_bytes()","Path(P['sealed']['path']).read_bytes()").replace("(TX/('native-final-'+SHA+'.json')).read_bytes()","Path(P['sealed']['path']).read_bytes()")
    d=P.get('daemon')
    if d:
        text=text.replace('/proc/1121','/proc/'+str(d['pid'])).replace("=='1516'","=="+repr(str(d['birth_ticks']))).replace("'daemon_pid':1121","'daemon_pid':"+str(d['pid'])).replace("'daemon_birth_ticks':1516","'daemon_birth_ticks':"+str(d['birth_ticks']))
        text=text.replace('eba390fe164718811ee931534079ab55a51a95b5e8092c7600dcf730346d7088',d['command_sha256'])
    text=text.replace("assert not Path('/proc/1333').exists()","assert not same_owner(P['camera'])")
    return text

def unit_pin(action):
    r=load(L/(action+'_READ.json')) if (L/(action+'_READ.json')).exists() else load(L/(action+'_SUBMIT.json'))
    s=r.get('unit_snapshot') or r['unit']
    assert s.get('InvocationID') and int(s.get('ExecMainPID','0'))>0,'Only observe the same submitted action until its actual identity is known'
    return s

action=sys.argv[1]
if action=='preflight':
    assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(g['may_begin_before_host_utc'])
    code="fresh=phase_check(True)\nfresh['platform']=platform_snapshot()\nassert fresh['platform']['firmware']=='kv260-benchmark-b4096.bit.bin'\ntx=Path(P['tx']);assert tx.parent.resolve()==tx.parent and not tx.parent.is_symlink()\ntx.mkdir(mode=0o700)\nraw=(json.dumps({'phase_grant_sha256':P['grant_sha256'],'fresh':fresh},sort_keys=True,indent=2)+'\\n').encode()\nfd=os.open(tx/'phase-binding.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)\nwith os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())\nprint(json.dumps(fresh))\n"
    result_name='PREFLIGHT'
else:
    pre=load(L/'PREFLIGHT.json');P['daemon']=pre['daemon']
    if action in ['remove','load','idstop']:
        if action=='load':assert load(L/'remove_READ.json')['status']=='REMOVE_CONFIRMED_AND_ACTUAL_PLATFORM_UNLOADED'
        if action=='idstop':assert load(L/'load_READ.json')['status']=='LOAD_CONFIRMED_ORIGINAL_WIDE_PLATFORM_ACTIVE'
        code=rebind('launch_original_'+action+'.py')
        result_name=action+'_SUBMIT'
    elif action in ['read_remove','read_load']:
        a=action.removeprefix('read_');code=rebind('read_original_'+a+'_result.py');result_name=a+'_READ'
    elif action=='read_idstop':
        code=rebind('verify_idstop_start_camera.py').split("intent={'schema':'aura-original-camera-start-intent-1'")[0]
        code+="\nfresh=phase_check(True)\nprint(json.dumps({'status':'ORIGINAL_WIDE_AND_ID_STOP_ONLY_PASS','unit':state,'report':report,'report_sha256':hashlib.sha256(report_bytes).hexdigest(),'context':context,'fresh_final_state':fresh,'platform':platform_snapshot(),'ARM_sent':False,'COMMIT_sent':False,'BIND_sent':False,'REFERENCE_sent':False,'camera_or_GUI_started':False}))\n"
        result_name='idstop_READ'
    elif action=='final_audit':
        code=r'''
import base64
fresh=phase_check(True);tx=Path(P['tx']);actions={}
props='LoadState,Job,ActiveState,SubState,InvocationID,MainPID,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,ExecMainCode,ExecMainStatus,Result,Type,Restart,RemainAfterExit,KillMode,SendSIGKILL,RuntimeMaxUSec,TimeoutStartUSec,TimeoutStopUSec,ExecStart,StandardInput,StandardOutput,StandardError'
for a,unit in P['units'].items():
    s=pshow(unit,props)
    assert s['MainPID']=='0' and s['ActiveState']=='active' and s['SubState']=='exited' and not s['Job']
    assert s['ExecMainCode']=='1' and s['ExecMainStatus']=='0' and s['Result']=='success'
    assert int(s['ExecMainExitTimestampMonotonic'])>int(s['ExecMainStartTimestampMonotonic'])>0
    assert s['Type']=='exec' and s['Restart']=='no' and s['RemainAfterExit']=='yes' and s['KillMode']=='process' and s['SendSIGKILL']=='no'
    assert all(s[k]=='infinity' for k in ['RuntimeMaxUSec','TimeoutStartUSec','TimeoutStopUSec'])
    assert s['StandardInput']=='null' and s['StandardOutput']=='append' and s['StandardError']=='append'
    stdout=(tx/(a+'.stdout.raw')).read_bytes();stderr=(tx/(a+'.stderr.raw')).read_bytes()
    assert len(stdout)<=65536 and not stderr
    intent=json.loads((tx/(a+'-intent.json')).read_bytes())
    assert intent['unit']==unit and intent['boot_id']==P['boot']
    actions[a]={'unit':s,'intent':intent,'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':base64.b64encode(stderr).decode(),'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(stderr).hexdigest()}
assert base64.b64decode(actions['remove']['stdout_base64'])==b'remove from slot 0 returns: 0 (Ok)\n'
assert base64.b64decode(actions['load']['stdout_base64'])==b'aura-visual-servo-b4096-wide-v1: loaded to slot 0\n'
report=json.loads((tx/'id-stop.json').read_bytes());assert report['identity_stop_passed']
assert all(report[k] is False for k in ['ARM_sent','COMMIT_sent','BIND_sent','REFERENCE_sent'])
assert report['after_stop']['flags']==0 and report['after_stop']['lease_left_ms']==0
context=json.loads((tx/'wide-context.json').read_bytes());platform=platform_snapshot()
assert context['boot_id']==P['boot'] and context['fdt_sha256']==platform['fdt_sha256']
assert platform['firmware']==context['firmware_name']=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert platform['fpga_state']=='operating' and platform['vart']=='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
print(json.dumps({'status':'ORIGINAL_SUPERVISION_AND_STOP_FINAL_AUDIT_PASS','fresh':fresh,'platform':platform,'context':context,'actions':actions,'checkpoint_consumed':False,'services_started':False,'motion_requested':False}))
'''
        result_name='FINAL_AUDIT'
    else:raise ValueError(action)
    for a,old_inv,old_pid in [('remove','2f576a41a8f44a34b173cbca8305a82a','79180'),('load','990d648e43ee4a9fb5cf9f6066ba2156','79397'),('idstop','06d7005d93534d09ba36356a5322f91d','79696')]:
        if old_inv in code:
            pin=unit_pin(a);code=code.replace(old_inv,pin['InvocationID']).replace("'"+old_pid+"'",repr(pin['ExecMainPID']))
    if action in ['remove','load','idstop']:code='phase_check()\n'+code
prefix='import json\nP=json.loads('+repr(json.dumps(P,separators=(',',':')))+')\n'+COMMON+'\n'
script=prefix+code
compile(script,'<original-phase-'+action+'>','exec')
save_new(L/(result_name+'.prepared.py'),script)
host_intent={'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase_grant_sha256':GRANT_SHA,'action':action,'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'only_original_entrypoints':True}
save_new(L/(result_name+'_HOST_INTENT.json'),json.dumps(host_intent,indent=2)+'\n')
transport=Path('E:/Win共享文件/语音共享文件/deliverables/2026-10-18_board_dialogue/board_ssh.py')
assert sha(transport)=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('strict_axis_phase_transport',transport);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
try:
    raw=mod.ssh('python3 -B -',script,timeout=55)
    if isinstance(raw,bytes):raw=raw.decode('utf-8')
    value=json.loads(raw)
    save_new(L/(result_name+'.json'),json.dumps(value,ensure_ascii=False,indent=2)+'\n')
except BaseException as e:
    save_new(L/(result_name+'_HOST_ERROR.json'),json.dumps({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'error_type':type(e).__name__,'error':str(e),'mutating_action_must_not_be_resent':action in ['remove','load','idstop']},ensure_ascii=False,indent=2)+'\n')
    raise
print(json.dumps(value,ensure_ascii=False,indent=2))
