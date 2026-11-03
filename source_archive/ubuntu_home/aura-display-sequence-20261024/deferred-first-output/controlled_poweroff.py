"""Pure completion/counter checks for a deliberate physical cold-boot test."""
def validate_checkpoint(document, before, *, current_boot, source_pid, source_birth_ticks,
                        source_process_alive, lock_free, unit):
    if document.get('schema')!='aura-native-protection-checkpoint-2' or \
            document.get('scope')!='final_quiescent_before_native_owner_close':
        raise ValueError('Exact sealed native checkpoint required')
    seed,aux=document['seed'],document['auxiliary']
    if seed['boot_id']!=current_boot or seed['source_pid']!=source_pid or \
            seed['source_birth_ticks']!=source_birth_ticks or seed['checkpoint_kind']!=1:
        raise ValueError('Checkpoint source differs from the stopped owner')
    if seed['fenced'] or aux['fenced'] or aux['active'] or aux['primary_waiting'] or any(aux['pending_result_tokens']):
        raise ValueError('Native completion is unconfirmed or a result is pending')
    if source_process_alive or not lock_free:
        raise ValueError('The native owner has not released its process and lock')
    if unit.get('MainPID')!='0' or unit.get('ExecMainStatus')!='0' or unit.get('Result')!='success':
        raise ValueError('Native service did not stop normally')
    if seed['primary_calls']<before['primary_calls'] or seed['primary_period_overruns']<before['primary_period_overruns']:
        raise ValueError('Primary counters decreased during shutdown')
    for index,task in ((1,'yunet'),(2,'sface')):
        previous=before['optional'][task]
        if seed['admissions'][index]<previous['calls'] or seed['overruns'][index]<previous['overruns']:
            raise ValueError('Optional counters decreased during shutdown')
    if aux['sface_counters']['completed']<before['sface_completed']:
        raise ValueError('SFace completion history decreased')
    return True

"""Prepare a reviewed power-off; --shutdown only after explicit human readiness.

It never cuts power or kills a model owner. Normal service shutdown and an
exact checkpoint must finish before it schedules OS poweroff.
"""
import fcntl,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path

BASE=Path('/home/root/aura-native-coldboot-20261024')
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
SOURCE_BOOT='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def command(argv,timeout=10):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError('Command failed: '+repr(argv)+' '+p.stderr[-500:])
    return p.stdout
def prop(unit):
    out=command(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus'])
    return dict(row.split('=',1) for row in out.splitlines() if '=' in row)
def get(port,path):
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as response:return json.load(response)
def atomic(path,value):
    temporary=path.with_name(path.name+'.partial-'+str(os.getpid()))
    with temporary.open('x') as out:json.dump(value,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
    os.replace(temporary,path)
    fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def brief(h):
    s=h['dpu_schedule'];i=h['identity']
    return dict(pid=h['pid'],primary_calls=s['primary_calls'],primary_period_overruns=s['primary_period_overruns'],
        optional={k:{n:v[n] for n in ['calls','overruns']} for k,v in s['optional'].items()},
        sface_completed=i['feature_inference']['completed'],match_counts=i['match_diagnostics']['counts'])

def main():
    assert boot()==SOURCE_BOOT
    meta=json.loads((OPS/'meta.json').read_text());controller=OPS/'boot_ops.py'
    assert sha(controller)==meta['source_pins']['boot_ops.py']
    sys.path.insert(0,str(OPS));from boot_ops import Ops
    ops=Ops(OPS);ops.verify();assert ops.state()['phase']=='ACCEPTED'
    token=sha(Path(__file__))[:16];root=BASE/token;root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if sys.argv[1:]!=['--shutdown']:
        assert not sys.argv[1:] and not (root/'prepared.json').exists()
        h=get(8790,'/health');assert h['pid']==int(prop('aura-camera-ui.service')['MainPID']) and not h['dpu_schedule']['owner_fenced']
        assert h['dpu_schedule']['native_critical'] and h['identity']['ready']
        assert command(['systemctl','is-enabled','aura-camera-ui.service']).strip()=='enabled'
        assert command(['systemctl','is-enabled','aura-avatar-ui.service']).strip()=='enabled'
        cfg=json.loads(Path(meta['candidate_config']).read_text());identity=Path(cfg['identity']['config'])
        assert cfg['native_execution']['allow_new_kernel_boot'] is True
        assert cfg['native_execution']['checkpoint_output']
        assert sha(identity)=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
        db=Path(json.loads(identity.read_text())['database'])
        prepared=dict(scope='PHYSICAL_POWER_CYCLE_PREPARED_NOT_PERFORMED',source_boot=SOURCE_BOOT,
            source_pid=h['pid'],source_birth_ticks=int((Path('/proc')/str(h['pid'])/'stat').read_text().rsplit(')',1)[1].split()[19]),
            controller_sha256=sha(controller),candidate_config=meta['candidate_config'],
            candidate_config_sha256=sha(meta['candidate_config']),identity_config_sha256=sha(identity),
            database_sha256=sha(db),checkpoint_output=cfg['native_execution']['checkpoint_output'],
            before=brief(h),services_enabled=True,prepared_mono_ns=time.monotonic_ns())
        atomic(root/'prepared.json',prepared)
        print(json.dumps({'prepared':True,'root':str(root),'no_service_changes':True,'no_poweroff':True,
            'next_action':'Wait for explicit human physical readiness; normal shutdown and checkpoint precede poweroff'}))
        return
    prepared=json.loads((root/'prepared.json').read_text());assert not (root/'shutdown.json').exists()
    lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert sha(meta['candidate_config'])==prepared['candidate_config_sha256']
    h=get(8790,'/health');assert h['pid']==prepared['source_pid'] and not h['dpu_schedule']['owner_fenced']
    gui=get(8783,'/api/state');assert gui['phase']=='IDLE' and gui['audio_output_state']=='IDLE_READY' and not gui['playing']
    assert gui.get('local_recording',{}).get('state')!='RECORDING'
    assert not gui.get('local_transcription',{}).get('service',{}).get('pending')
    before=brief(h)
    report={'source_boot':SOURCE_BOOT,'before':before,'safe_to_disconnect_power':False,'poweroff_scheduled':False}
    try:
        command(['systemctl','stop','--no-block','aura-avatar-ui.service'])
        until=time.monotonic()+35
        while prop('aura-avatar-ui.service')['MainPID']!='0' and time.monotonic()<until:time.sleep(.2)
        assert prop('aura-avatar-ui.service')['MainPID']=='0','GUI did not stop; no poweroff'
        command(['systemctl','stop','--no-block','aura-camera-ui.service'])
        until=time.monotonic()+20
        while prop('aura-camera-ui.service')['MainPID']!='0' and time.monotonic()<until:time.sleep(.2)
        checkpoint=Path(prepared['checkpoint_output']);document=json.loads(checkpoint.read_text())
        source_alive=(Path('/proc')/str(prepared['source_pid'])).exists()
        free=False
        with open('/run/aura-person-dpu.lock','a+') as owner:
            try:fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
            except BlockingIOError:pass
        validate_checkpoint(document,before,current_boot=SOURCE_BOOT,source_pid=prepared['source_pid'],
            source_birth_ticks=prepared['source_birth_ticks'],source_process_alive=source_alive,
            lock_free=free,unit=prop('aura-camera-ui.service'))
        report.update(checkpoint=document,checkpoint_sha256=sha(checkpoint),safe_to_disconnect_power=True)
        atomic(root/'shutdown.json',report)
        command(['systemd-run','--no-block','--quiet','--unit=aura-cold-poweroff-'+token,
            '--on-active=3s','/bin/systemctl','poweroff','--no-block'])
        report['poweroff_scheduled']=True;atomic(root/'shutdown.json',report)
    except BaseException as exc:
        report['failure']=type(exc).__name__+': '+str(exc);atomic(root/'shutdown.json',report)
        raise
    print(json.dumps({'root':str(root),'safe_to_disconnect_after_OS_halt':True,'poweroff_scheduled':True,
        'checkpoint_sha256':report['checkpoint_sha256'],'model_owner_closed_normally':True}))

if __name__=='__main__':main()
