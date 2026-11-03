"""Bounded, one-boot Xserver start deferral. No modeset, AUX or firmware writes."""
import hashlib,json,os,re,subprocess,sys,time,urllib.request
from pathlib import Path
from policy import choose_boot,readiness

SOURCE_BOOT='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
source=Path(sys._getframe().f_code.co_filename).resolve()
token=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
root=Path('/home/root/aura-display-sequence-20261024/deferred')/token
override=Path('/etc/systemd/system/xserver-nodm.service.d')/('zzzzzz-late-first-output-'+token+'.conf')
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(path,value):
    temp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temp.open('x') as out:json.dump(value,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
    os.replace(temp,path)
def command(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=8)
    if p.returncode:raise RuntimeError('Command failed: '+repr(args)+' '+p.stderr[-400:])
    return p.stdout
def mainpid(unit):return int(command(['systemctl','show',unit,'-p','MainPID','--value']).strip())
def scanout():
    p=Path('/sys/kernel/debug/dri/0/state')
    raw=p.read_text() if p.exists() else ''
    lines=[line.strip() for line in raw.splitlines() if any(k in line for k in ['format=','size=','crtc-pos=','mode:']) or line.strip().startswith(('enable=','active='))]
    active=any(re.match(r'^\s*(?:enable|active)=1\s*$',line) for line in raw.splitlines())
    return {'state_available':bool(raw),'active':active,'lines':lines,
        'fb_nodes':[p.name for p in Path('/sys/class/graphics').glob('fb*') if re.match(r'^fb[0-9]+$',p.name)]}
def camera():
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with op.open('http://127.0.0.1:8790/health',timeout=1) as response:h=json.load(response)
        s=h.get('dpu_schedule') or {}
        return dict(ready=not h.get('camera_error') and not h.get('detector_error') and h.get('detected_frames',0)>=5
            and bool(s.get('native_critical')) and not s.get('owner_fenced'),pid=h['pid'],detected=h['detected_frames'])
    except Exception as e:return {'ready':False,'unavailable':type(e).__name__}
def payload():
    return ('[Service]\nExecStartPre=/usr/bin/python3 -B '+str(source)+' --wait\nTimeoutStartSec=120\n').encode()
def prepare():
    assert boot()==SOURCE_BOOT;root.mkdir(parents=True,exist_ok=False,mode=0o700)
    assert Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation').read_text().strip()=='N'
    assert not scanout()['fb_nodes'],'Do not claim late first scanout with an early fbdev client'
    assert camera()['ready']
    units={unit:mainpid(unit) for unit in ['xserver-nodm.service','aura-avatar-ui.service','aura-camera-ui.service']}
    assert all(units.values())
    unit_path=Path(command(['systemctl','show','xserver-nodm.service','-p','FragmentPath','--value']).strip())
    assert unit_path.is_absolute() and unit_path.is_file(),'Actual Xserver unit file required'
    value={'source_boot':SOURCE_BOOT,'target_boot':None,'phase':'PREPARED','minimum_uptime':60,'maximum_wait':90,
        'source_sha256':sha(source),'override':str(override),'override_sha256':hashlib.sha256(payload()).hexdigest(),
        'original_units':units,'protected':{str(p):sha(p) for p in [Path('/boot/uEnv.txt'),Path('/etc/X11/xorg.conf'),unit_path]},
        'scope':'One later kernel boot; only postpone the first Xserver start; no physical HDMI equivalence claimed'}
    atomic(root/'plan.json',value)
    print(json.dumps({'prepared':True,'root':str(root),'no_service_change':True,'proposed_override':payload().decode()}))
def arm():
    assert boot()==SOURCE_BOOT;plan=json.loads((root/'plan.json').read_text());assert plan['phase']=='PREPARED'
    assert sha(source)==plan['source_sha256']
    for p,pin in plan['protected'].items():assert sha(p)==pin
    assert not override.exists() and not override.is_symlink();override.parent.mkdir(parents=True,exist_ok=True)
    with override.open('xb') as out:out.write(payload());out.flush();os.fsync(out.fileno())
    command(['systemctl','daemon-reload'])
    assert all(mainpid(u)==pid for u,pid in plan['original_units'].items()),'Running processes changed unexpectedly'
    plan['phase']='ARMED';atomic(root/'plan.json',plan)
    print(json.dumps({'armed':True,'current_display_unchanged':True,'root':str(root)}))
def wait_once():
    plan=json.loads((root/'plan.json').read_text());now_boot=boot();choice=choose_boot(plan['source_boot'],now_boot,plan['target_boot'])
    if choice.startswith('UNCHANGED'):return
    if plan.get('phase') not in ['ARMED','WAITING_FIRST_XSERVER','COMPLETE']:return
    assert sha(source)==plan['source_sha256']
    for p,pin in plan['protected'].items():assert sha(p)==pin
    if choice=='CLAIM_NEW_BOOT':
        plan['target_boot']=now_boot;plan['phase']='WAITING_FIRST_XSERVER';atomic(root/'plan.json',plan)
    elif plan.get('phase') in ['COMPLETE','REMOVED']:return
    start=time.monotonic();rows=[];outcome='FALLBACK_ERROR'
    try:
        while True:
            uptime=float(Path('/proc/uptime').read_text().split()[0]);display=scanout();health=camera()
            row={'mono_ns':time.monotonic_ns(),'uptime':uptime,'elapsed':time.monotonic()-start,
                 'display':display,'camera':health};rows.append(row)
            outcome=readiness(uptime=uptime,elapsed=row['elapsed'],scanout_active=display['active'],
                camera_ready=health['ready'],minimum_uptime=plan['minimum_uptime'],maximum_wait=plan['maximum_wait'])
            if outcome=='READY_FOR_FIRST_XSERVER_OUTPUT' and not display['state_available']:
                outcome='FALLBACK_SCANOUT_STATE_UNAVAILABLE'
            if outcome!='WAIT':break
            time.sleep(1)
    finally:
        report={'boot':now_boot,'outcome':outcome,'samples':rows,'elapsed_seconds':time.monotonic()-start,
            'display_start_allowed':True,'modeset_commands':0,'aux_transactions':0,
            'limits':'Linux scanout state only; autonomous bridge/bootloader behavior is not controlled'}
        atomic(root/('report-'+now_boot+'.json'),report)
        plan['phase']='COMPLETE';plan['outcome']=outcome;atomic(root/'plan.json',plan)
def remove():
    plan=json.loads((root/'plan.json').read_text())
    if override.exists():
        assert not override.is_symlink() and sha(override)==plan['override_sha256']
        override.unlink();command(['systemctl','daemon-reload'])
    plan['phase']='REMOVED';atomic(root/'plan.json',plan)
    print(json.dumps({'removed':True,'service_restarted':False}))
def main():
    args=sys.argv[1:]
    if not args:prepare()
    elif args==['--arm']:arm()
    elif args==['--wait']:wait_once()
    elif args==['--remove']:remove()
    else:raise ValueError('Explicit prepare, arm, wait or remove required')
if __name__=='__main__':
    if sys.argv[1:]==['--wait']:
        try:main()
        except BaseException as exc:
            # Failure is observable and must not permanently block the display.
            try:atomic(root/('wait-fallback-'+boot()+'.json'),{'failure':type(exc).__name__,'display_start_allowed':True})
            except BaseException:pass
        raise SystemExit(0)
    main()
