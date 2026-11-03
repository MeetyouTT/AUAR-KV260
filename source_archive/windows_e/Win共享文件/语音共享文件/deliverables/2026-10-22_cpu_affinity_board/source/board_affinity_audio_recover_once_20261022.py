"""One idle application lifecycle recovery, with protected preferences and a guard."""
import errno,hashlib,json,os,select,subprocess,sys,time,urllib.request
from pathlib import Path

SOURCE=Path(sys._getframe().f_code.co_filename).resolve()
DIGEST=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
ROOT=Path('/home/root/aura-audio-recovery-20261021')/DIGEST[:16]
UNIT='aura-audio-recovery-'+DIGEST[:16]
GUARD=UNIT+'-restore'
CFG=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json')
PREF=Path('/home/root/.local/share/aura/handsfree_dialogue.json')
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def run(args,timeout=10):
    return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=timeout).decode().strip()
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(port,path):
    with OPENER.open('http://127.0.0.1:%d/%s'%(port,path),timeout=3) as r:return json.load(r)
def unit(name):
    return dict(x.split('=',1) for x in run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts']).splitlines())
def camera():
    s=api(8790,'health')
    return {k:s.get(k) for k in ('pid','detected_frames','capture_frames','capture_hz','detection_hz','camera_error','detector_error','observation_age_ms','dpu_schedule')}
def ui():
    s=api(8783,'api/state')
    return {k:s.get(k) for k in ('phase','playing','paused','audio_output_state','local_recording','handsfree_dialogue','voice_barge_in','pending_job','manual_pan')}
def brief_ui(s):
    return {'phase':s['phase'],'playing':s['playing'],'audio_output_state':s['audio_output_state'],
            'recording_state':s['local_recording'].get('state'),'microphone_open':s['handsfree_dialogue'].get('microphone_open'),
            'handsfree_enabled':s['handsfree_dialogue'].get('enabled'),'handsfree_state':s['handsfree_dialogue'].get('state'),
            'barge_in_enabled':s['voice_barge_in'].get('enabled'),'manual_pan_state':s['manual_pan'].get('state')}
def cpu():
    v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));ps={}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            a=(p/'stat').read_text().split(') ')[1].split()
            ps[p.name]=(int(a[11])+int(a[12]),int(a[19]),(p/'comm').read_text().strip())
        except (OSError,IndexError):pass
    return sum(v),v[3]+v[4],ps
def sample(seconds):
    # Bounded journal query; avoid the previous high-rate /dev/kmsg observer.
    text=run(['journalctl','-k','-n','1','--show-cursor','--no-pager'],timeout=6)
    cursor=next(x.split(': ',1)[1] for x in text.splitlines() if x.startswith('-- cursor: '))
    before=cpu();started=time.monotonic();time.sleep(seconds);end=cpu()
    duration=time.monotonic()-started;total=end[0]-before[0];processes=[]
    for pid,v in end[2].items():
        old=before[2].get(pid)
        if old and old[1]==v[1]:processes.append({'pid':int(pid),'name':v[2],
            'cpu_pct_board':100*(v[0]-old[0])/os.sysconf('SC_CLK_TCK')/duration/os.cpu_count()})
    raw=run(['journalctl','-k','--after-cursor='+cursor,'-o','json','--no-pager','-n','5000'],timeout=10)
    rows=[]
    for line in raw.splitlines():
        try:rows.append(json.loads(line))
        except ValueError:pass
    count=sum("HC couldn't access mem fast enough for slot 4 ep 3" in x.get('MESSAGE','') for x in rows)
    return {'seconds':duration,'cpu_pct_board':100*(1-(end[1]-before[1])/float(total)),
        'xhci_warning_count':count,'journal_query_complete':len(rows)<5000,
        'count_scope':'Bounded after-cursor journal window; lower bound if5000 entries reached; no /dev/kmsg reader',
        'processes':sorted(processes,key=lambda x:x['cpu_pct_board'],reverse=True)[:10],
        'camera':camera(),'playback_pcm_status':Path('/proc/asound/card1/pcm0p/sub0/status').read_text().strip()}

def save(value):
    p=ROOT/'result.json';temp=ROOT/'result.tmp';temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(p)
def restore_preference():
    p=ROOT/'handsfree.preference.original'
    if p.exists() and PREF.read_bytes()!=p.read_bytes():
        temp=PREF.with_name(PREF.name+'.audio-recovery-tmp');temp.write_bytes(p.read_bytes());temp.replace(PREF)
def restore():
    if unit('aura-avatar-ui.service')['ActiveState']!='active':
        restore_preference();run(['systemctl','start','--no-block','aura-avatar-ui.service'])

def main():
    out={'recurrence':'MCP01 warning persisted after aborted affinity short trial and original restoration; one audio-closed original-camera restart then original audio reopen; causal test not root-cause proof','complete':False,'phase':'PREFLIGHT','root':str(ROOT),'source_sha256':DIGEST}
    save(out);stopped=False
    try:
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        assert boot=='215c4292-ce84-4828-9827-83c32ba66564','Boot changed'
        assert digest(CFG)=='6c47003c4d020066a3ba4c9daa8f905101d633c4cf507951bea3ac3ca86a161d','Runtime configuration changed'
        c=json.loads(CFG.read_text());runtime=Path(c['runtime'])
        marker=json.loads(Path(c['display_recovery_marker']).read_text())
        assert not c.get('startup_display_retrain',False) or all(marker.get(k)==v for k,v in {'boot_id':boot,'output':c['output'],'mode':c['mode'],'edid_sha256':c['edid_sha256']}.items()),'Would trigger display off/on'
        state=ui();assert state['phase']=='IDLE' and not state['playing'] and not state['paused'] and state['pending_job'] is None
        assert state['local_recording']['state']=='IDLE' and not state['local_recording']['can_stop']
        assert not state['manual_pan'].get('automatic_following') and state['manual_pan'].get('pulse_us') is None
        out['ui_before']=brief_ui(state);out['camera_before']=camera()
        out['units_before']={n:unit(n) for n in ('aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service')}
        paths=[CFG,CFG.parent/'launcher.py',Path('/etc/systemd/system/aura-camera-ui.service'),Path('/lib/systemd/system/xserver-nodm.service'),Path('/etc/default/xserver-nodm')]
        paths+=list(runtime.glob('avatar*settings.json'))
        paths+=list(Path('/etc/systemd/system/aura-avatar-ui.service.d').glob('*.conf'))
        out['protected_before']={str(p):digest(p) for p in paths}
        (ROOT/'handsfree.preference.original').write_bytes(PREF.read_bytes());out['preference_sha_before']=digest(PREF)
        out['before']=sample(8);out['phase']='BEFORE_STOP';save(out)
        state=ui();assert state['phase']=='IDLE' and not state['playing'] and state['pending_job'] is None and not state['local_recording']['can_stop']
        run(['systemd-run','--unit='+GUARD,'--on-active=240s','/usr/bin/python3','-B',str(SOURCE),'--restore'])
        stopped=True;run(['systemctl','stop','aura-avatar-ui.service'],timeout=35)
        out['phase']='AUDIO_CLOSED';save(out)
        out['stopped']=sample(3)
        assert out['stopped']['playback_pcm_status']=='closed','Owned audio did not close'
        # Controlled recovery-order experiment: no active playback/capture;
        # reset disabled YuNet while the original application audio is closed.
        camera_unit=Path('/etc/systemd/system/aura-camera-ui.service')
        assert digest(camera_unit)=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
        camera_before=unit('aura-camera-ui.service')['MainPID']
        run(['systemctl','restart','--no-block','aura-camera-ui.service'])
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            try:
                cam=api(8790,'health')
                if (str(cam['pid'])!=camera_before and cam.get('identity',{}).get('face_targets',{}).get('backend')=='DPU_YUNET_INT8'
                        and not cam['camera_error'] and not cam['detector_error']):break
            except Exception:pass
            time.sleep(.4)
        else:raise RuntimeError('Camera did not recover before restarting audio')
        out['explicit_camera_restart_while_audio_closed']={'before_pid':int(camera_before),'after_pid':cam['pid']}
        assert digest(camera_unit)=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'

        restore_preference()
        out['phase']='STARTING_ORIGINAL_APP';save(out)
        run(['systemctl','start','--no-block','aura-avatar-ui.service'])
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            try:
                current=ui()
                if unit('aura-avatar-ui.service')['ActiveState']=='active' and current['audio_output_state']=='IDLE_READY':break
            except Exception:pass
            time.sleep(1)
        else:raise RuntimeError('Original application audio not ready in 120 seconds')
        time.sleep(5);out['ui_after']=brief_ui(ui());out['after']=sample(8)
        out['units_after']={n:unit(n) for n in out['units_before']}
        out['protected_after']={str(p):digest(p) for p in paths}
        out['preference_sha_after']=digest(PREF)
        assert out['protected_after']==out['protected_before'],'Protected file changed'
        assert out['preference_sha_after']==out['preference_sha_before'],'Monitoring preference changed'
        for n in ('xserver-nodm.service',):assert out['units_after'][n]==out['units_before'][n],n+' changed'
        assert out['after']['camera']['pid']==cam['pid']
        assert out['after']['camera']['detected_frames']>cam['detected_frames']
        assert not out['after']['camera']['camera_error'] and not out['after']['camera']['detector_error']
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
        out['complete']=True;out['phase']='RESTORED_AND_SAMPLED'
        out['warning_recovered_in_short_sample']=out['after']['xhci_warning_count']==0 and out['after']['journal_query_complete']
    except Exception as e:
        out['phase']='FAILED';out['error']=type(e).__name__+': '+str(e)
    finally:
        if stopped:
            try:restore()
            except Exception as e:out['restore_error']=type(e).__name__+': '+str(e)
        if unit('aura-avatar-ui.service')['ActiveState']=='active':
            run(['systemctl','stop',GUARD+'.timer'],timeout=10)
            out['guard_timer_active']=unit(GUARD+'.timer')['ActiveState']
        save(out)
    print(json.dumps(out),flush=True)

if '--restore' in sys.argv:restore();print(json.dumps({'restore_attempted':True}))
elif '--recover' in sys.argv:main()
else:
    ROOT.mkdir(parents=True,exist_ok=True)
    assert not (ROOT/'result.json').exists(),'Recovery already attempted; inspect existing evidence'
    run(['systemd-run','--unit='+UNIT,'--property=RuntimeMaxSec=180','/usr/bin/python3','-B',str(SOURCE),'--recover'])
    print(json.dumps({'started':True,'unit':UNIT,'result':str(ROOT/'result.json')}))
