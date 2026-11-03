"""Read-only current dialogue stages; no text, audio or private errors exported."""
import argparse
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import hashlib,http.client,json,math,pathlib,re,subprocess,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 c.request('GET','/api/state');r=c.getresponse();raw=r.read(1048577);assert r.status==200 and len(raw)<=1048576
 state=json.loads(raw)
finally:c.close()
def scalar(v):
 return {k:x for k,x in v.items() if type(x) in (bool,int,float) and (type(x) is bool or math.isfinite(x))}
def select(v,keys):return {k:v.get(k) for k in keys}
def code(v):
 allowed={'','none','ValueError','TypeError','RuntimeError','TimeoutError','InterruptedError','OSError','AssertionError',
  'ReplyRejected','ModelRequestError','PermissionError','StaleGeneration','MemoryConflict','MemoryDenied',
  'ScopeDenied','StaleTurn','MemoryBusy',
  'candidate_rejected','model_failed','deadline_exceeded','cancelled','board_asr_failed','profile_grant_expired',
  'clock_unverified','database_busy','compaction_failed',
  'audio_input_queue_overflow','pcm_input_queue_overflow','board_capability_not_ready'}
 return dict(present=bool(v) and v!='none',code=v if v in allowed else 'other',length=len(v) if isinstance(v,str) else None)
def stage(v):
 enums={'IDLE','READY','ERROR','CLOSED','STOPPING','RECORDING','WAITING_VISUAL','DISABLED','TRANSCRIBING',
 'GENERATING','PLAYING','ANSWERED','CANCELLED','EMPTY','WAITING_WAKE','WAITING_SPEECH','THINKING','SPEAKING',
 'LISTENING','WAITING_SERVICE','PAUSED','COOLDOWN','CONVERSATION','CHECKING_SPEECH','IDLE_READY','DRAINING'}
 return v if v in enums else 'other'
def component(v):
 if not isinstance(v,dict):return None
 out=scalar(v)
 for k in ('state','status','phase','task_state'):
  if k in v:out[k]=stage(v[k])
 for k in ('error','last_error','cleanup_error'):
  if k in v:out[k]=code(v[k])
 for k in ('text','reply','reply_text','recognized_text'):
  if k in v:out[k+'_characters']=len(v[k]) if isinstance(v[k],str) else None
 return out
def runtime_faults(v):
 if not isinstance(v,dict):return dict(count=0,last=None)
 last=v.get('last');result=dict(count=v.get('count') if type(v.get('count')) is int else 0,last=None)
 if not isinstance(last,dict):return result
 frames=[]
 for row in last.get('frames',[])[:6]:
  if not isinstance(row,dict):continue
  file=row.get('file','');fn=row.get('function','');line=row.get('line')
  if (isinstance(file,str) and re.fullmatch(r'[A-Za-z0-9_.<>-]{1,96}',file)
      and isinstance(fn,str) and re.fullmatch(r'[A-Za-z0-9_<>.]{1,80}',fn) and type(line) is int):
   frames.append(dict(file=file,function=fn,line=line))
 result['last']=dict(error_class=code(last.get('error_class','')),frames=frames,
                     frames_truncated=last.get('frames_truncated') is True)
 return result
b=state.get('board_business',{});h=state.get('handsfree_dialogue',{});dialogue=b.get('dialogue',{})
service=state.get('local_transcription',{}).get('service',{})
frontend=state.get('audio_frontend',{}).get('current',{})
failure=frontend.get('last_capture_failure',{})
out=dict(observed_mono=time.monotonic(),startup_sha256=hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest(),
 board_boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),phase=stage(state.get('phase')),
 playing=state.get('playing'),audio_output_state=stage(state.get('audio_output_state')),error=code(state.get('error','')),
 listening=select(h,('enabled','state','conversation_entered','entry_mode','wake_word_required','microphone_open','conversation_mode','voice_barge_in')),
 safe_capture=state.get('safe_capture_diagnostics',{}),
 capture_performance=scalar(frontend),
 last_capture_failure=dict(error=code(failure.get('error_code','')),
  metadata=scalar(failure),queue=scalar(failure.get('input_queue',{})),frontend=scalar(failure.get('audio_frontend',{}))),
 components={k:component(state.get(k)) for k in ('local_recording','local_transcription','board_processing','last_job','streaming_reply')},
 business=component(b),dialogue=component(dialogue),latency=scalar(dialogue.get('latency',{})),
 prepare_latency=scalar(dialogue.get('latency',{}).get('prepare',{})),
 stream_diagnostics=scalar(state.get('stream_diagnostics',{})),
 producer_diagnostics=scalar(service.get('diagnostics',dialogue.get('diagnostics',{}))),
 runtime_faults=runtime_faults(state.get('runtime_faults')),
 error_class=code(service.get('latency',dialogue.get('latency',{})).get('error_class','')),
 audio_output=component(state.get('audio_output',{})),
 audio_ipc=component(state.get('audio_output',{}).get('ipc',{})),
 recent_turn_audio=[dict(metrics=scalar(turn),audio=component(turn.get('audio_output',{})))
   for turn in state.get('turns',[])[-3:] if isinstance(turn,dict)],
 barge=component(state.get('voice_barge_in',{})),native=component(state.get('avatar_display',{})),
 last_ack=component(dialogue.get('last_playback_ack')),memory=component(b.get('memory',{})),
 memory_retry=component(b.get('memory',{}).get('retry_backoff')),retention=component(b.get('retention',{})),
 speaker=component(b.get('speaker',{})),clock=component(b.get('clock',{})),
 top_keys=sorted(state),dialogue_keys=sorted(dialogue),business_keys=sorted(b))
print(json.dumps(out))
'''

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--samples',type=int,default=1)
    p.add_argument('--interval',type=int,default=1)
    p.add_argument('--stop-on-fault',action='store_true');args=p.parse_args()
    assert args.label.replace('_','').isalnum()
    assert 1<=args.samples<=90
    assert 1<=args.interval<=5
    script='import time\nSOURCE='+repr(REMOTE)+'\nfor sample_index in range('+str(args.samples)+'):\n exec(SOURCE)\n'
    if args.stop_on_fault:script+=' if out["runtime_faults"]["count"]>0:break\n'
    script+=' time.sleep('+str(args.interval)+')\n'
    rows=[json.loads(x) for x in ssh('python3 -B -',script,timeout=args.samples*(args.interval+1)+20).splitlines() if x.strip()]
    value=rows[0] if len(rows)==1 else dict(samples=rows)
    (HERE/(args.label+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if len(rows)==1:print(json.dumps(value,ensure_ascii=True))
    else:
        transitions=[];previous=None
        for row in rows:
            current=dict(phase=row['phase'],playing=row['playing'],listening=row['listening'],
                task=row['components']['local_transcription'],capture_error=row['safe_capture']['error_code'],
                capture_counts=row['safe_capture']['counters'],latency=row['latency'],prepare=row['prepare_latency'],
                audio_output=row['audio_output'],recent_turn_audio=row['recent_turn_audio'],
                producer=row['producer_diagnostics'],consumer=row['stream_diagnostics'],error_class=row['error_class'])
            if current!=previous:transitions.append(dict(observed_mono=row['observed_mono'],**current));previous=current
        print(json.dumps(dict(samples=len(rows),transitions=transitions),ensure_ascii=True))
