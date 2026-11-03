"""Copied to the board only for a bounded observed-UI outage test."""
import json,time,subprocess,urllib.request,zlib

def state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)

if __name__=='__main__':
    before=state();pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)
    assert before['portrait_offload']['mode']=='remote'
    assert before['phase']=='IDLE' and before['audio_output_state']=='IDLE_READY' and not before['handsfree_dialogue']['enabled']
    position=before['manual_pan']['pulse_us'];rows=[];local_crc=set();announced=False;local=False;recovered=False
    began=time.monotonic()
    while time.monotonic()-began<30:
        s=state();d=s['avatar_display'];p=s['portrait_offload'];at=time.monotonic()-began
        assert s['phase']=='IDLE' and s['audio_output_state']=='IDLE_READY' and not s.get('error')
        assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue'].get('microphone_open')
        assert s['manual_pan']['pulse_us']==position and s['manual_pan'].get('state') not in ('MOVING','STOPPING')
        assert d['age_ms']<1000,d
        rows.append(dict(at=at,received=d['received'],display_age_ms=d['age_ms'],**p))
        if not announced and len(rows)>=5:print(json.dumps({'event':'REMOTE_READY'}),flush=True);announced=True
        if announced and p['mode']=='local':
            local=True
            if len(rows)%3==0:
                with urllib.request.urlopen('http://127.0.0.1:8783/api/frame',timeout=3) as f:local_crc.add(zlib.crc32(f.read(2_000_000)))
        if local and p['mode']=='remote':recovered=True
        time.sleep(.25)
    offline=[r for r in rows if r['mode']=='local'];assert len(offline)>12
    local_fps=(offline[-1]['received']-offline[0]['received'])/(offline[-1]['at']-offline[0]['at'])
    assert 7.2<=local_fps<=8.8,(local_fps,len(offline))
    assert recovered and len(local_crc)>1
    assert pid==subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)
    print(json.dumps({'status':'PASS','scope':'existing native UI during real owned Windows service outage',
        'local_fallback_observed':local,'local_fallback_fps':local_fps,'changing_local_preview_images':len(local_crc),
        'remote_recovered':recovered,'target_fps_after_recovery':state()['portrait_offload']['target_fps'],
        'max_display_age_ms':max(r['display_age_ms'] for r in rows),'pan_readback_preserved':position,'rows':rows,
        'ui_pid_unchanged':True,'audio_output_state':'IDLE_READY','monitor_enabled':False,
        'physical_speech_played':False,'microphone':False,'motor_command_issued':False}),flush=True)
