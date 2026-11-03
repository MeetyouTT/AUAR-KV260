"""Read-only same-request metadata window, coordinated through local receipts."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(REPAIR))
import probe
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import KEY

EXTRA=r'''
def token(value):
 if not isinstance(value,str) or not value:return None
 return hashlib.sha256(value.encode()).hexdigest()
trans=state.get('local_transcription',{})
request=token(trans.get('request_id'))
ack=dialogue.get('last_playback_ack') or {}
route=dialogue.get('last_voice_route') or {}
renderer=state.get('avatar_renderer',{})
observed={key:out[key] for key in ('observed_mono','startup_sha256','board_boot_id','phase','playing','listening',
 'latency','prepare_latency','audio_output','producer_diagnostics','stream_diagnostics','runtime_faults','capture_performance','last_capture_failure')}
observed.update(request_token=request,capture_token=token(trans.get('capture_id')),transcription_state=stage(trans.get('state')),
 transcript_characters=len(trans.get('text') or ''),ack_request_token=token(ack.get('request_id')),
 ack_committed=ack.get('committed') is True,
 ack_matches_current_request=bool(request and request==token(ack.get('request_id'))),
 route_generation=route.get('generation') if type(route.get('generation')) is int else None,
 renderer_faults=runtime_faults(renderer.get('worker_faults')),
 native=scalar(state.get('avatar_display',{})),capture_counts=scalar(state.get('safe_capture_diagnostics',{}).get('counters',{})))
print(json.dumps(dict(kind='sample',**observed)),flush=True)
'''
remote='import hashlib,http.client,json,time\nSOURCE='+repr(probe.REMOTE.replace('print(json.dumps(out))',EXTRA))+r'''
EXPECTED='90f6c6c40f6501362aa77483235a7260a212de6e3357615311bdaa5cc193ebbe'
BOOT='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
deadline=time.monotonic()+60
while time.monotonic()<deadline:
 exec(SOURCE)
 assert out['startup_sha256']==EXPECTED and out['board_boot_id']==BOOT
 h=out['listening']
 if out['phase']=='IDLE' and not out['playing'] and h.get('enabled') is True and h.get('microphone_open') is True and h.get('state')=='WAITING_SPEECH':break
 time.sleep(1)
else:raise RuntimeError('LIVE_WINDOW_WAITING_FOR_LISTENING')
connection=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
try:
 connection.request('GET','/health');response=connection.getresponse();raw=response.read(262145)
 assert response.status==200 and len(raw)<=262144
 health=json.loads(raw)
finally:connection.close()
assert health['role']=='model_inference_only' and health['backend']['tts_ready'] is True
start=time.monotonic()
print(json.dumps(dict(kind='ready',status='READY',observed_mono=start,deadline_mono=start+180,
 startup_sha256=EXPECTED,boot_id=BOOT,listening_enabled=True,microphone_open=True,
 native_visible=state.get('avatar_display',{}).get('visible') is True,
 model_inference_ready=True,tts_ready=True,duration_seconds=180,interval_seconds=1,
 request_ids_exported_as_hashes=True,raw_audio_or_dialogue_text_saved=False)),flush=True)
while time.monotonic()<start+180:
 began=time.monotonic();cpu=time.process_time()
 exec(SOURCE)
 assert out['startup_sha256']==EXPECTED and out['board_boot_id']==BOOT
 print(json.dumps(dict(kind='probe_cost',wall_ms=(time.monotonic()-began)*1000,cpu_ms=(time.process_time()-cpu)*1000)),flush=True)
 time.sleep(max(0.,1.-(time.monotonic()-began)))
print(json.dumps(dict(kind='complete',observed_mono=time.monotonic(),status='WINDOW_COMPLETE')),flush=True)
'''

if __name__=='__main__':
    suffix=str(time.time_ns())
    evidence=HERE/('metadata_'+suffix+'.jsonl')
    rows=[]
    command=['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes',
        '-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4','root@192.168.50.2','python3 -B -']
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,encoding='utf8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    process.stdin.write(remote);process.stdin.close()
    with evidence.open('x',encoding='utf8') as stream:
        for line in process.stdout:
            row=json.loads(line);rows.append(row);stream.write(json.dumps(row,ensure_ascii=True)+'\n');stream.flush()
            if row.get('kind')=='ready':
                receipt=dict(row,evidence_path=str(evidence),instruction_owner_chat='01a191ec-d0c3-77d0-904f-86e6cc9b2cb3',
                    measured_acoustic_first_sound=False,physical_speech_end_timestamp_available=False,
                    submit_absolute_timestamp_available=False,host_prefill_decode_same_request_available=False)
                (HERE/'READY.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
                print(json.dumps({'status':'READY','receipt':str(HERE/'READY.json'),'evidence':str(evidence)}),flush=True)
    code=process.wait(timeout=10)
    error=process.stderr.read()
    result=dict(status='WINDOW_COMPLETE' if code==0 and any(x.get('kind')=='complete' for x in rows) else 'WINDOW_INCOMPLETE',
        evidence_path=str(evidence),samples=sum(x.get('kind')=='sample' for x in rows),exit_code=code,
        stderr_present=bool(error),private_text_or_pcm_saved=False,
        correlation_rule='Use the hashed current request and matching complete playback ACK. Treat latency observed before request transition/reset as ambiguous.',
        physical_speech_end_and_acoustic_first_sound_measured=False)
    (HERE/'RESULT_HANDOFF.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result),flush=True)
