"""Read-only snapshot of actual board voice sources and bounded runtime diagnostics."""
import ast,datetime,hashlib,json,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
tree=ast.parse((P/'deliverables/2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
board=json.loads(ssh('python3 -B -',script,timeout=20))
expected='/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime'
assert board['actual_runtime']==expected,'Actual runtime changed; rediscover before reading'
names=['tools/voice_first_recording.py','tools/handsfree_recording.py','tools/barge_in_recording.py','tools/board_recording.py',
 'board/runtime/audio/channel_jobs.py','board/runtime/audio/transcription.py','board/runtime/audio/voice_channel.py',
 'tests/framework/test_voice_channel.py','tests/framework/test_channel_jobs.py']
remote=r'''
import hashlib,json,urllib.request
from pathlib import Path
root=Path(ROOT)/'aura'
out={}
for name in NAMES:
 raw=(root/name).read_bytes();out[name]={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode('utf-8')}
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as r:s=json.load(r)
state={k:s.get(k) for k in ('phase','playing','error','audio_output_state','handsfree_dialogue','voice_barge_in','local_transcription','local_recording','generation')}
state['manual_pan']={k:s.get('manual_pan',{}).get(k) for k in ('state','pulse_us','automatic_following')}
print(json.dumps({'files':out,'state':state},ensure_ascii=True))
'''.replace('ROOT',repr(expected)).replace('NAMES',repr(names))
result=json.loads(ssh('python3 -B -',remote,timeout=20))
assert not (H/'board_snapshot.json').exists(),'Preserve existing snapshot'
for name,value in result['files'].items():
 path=H/'board_source'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value['text'],encoding='utf-8',newline='')
 assert hashlib.sha256(path.read_bytes()).hexdigest()==value['sha256']
result['files']={name:{'sha256':value['sha256']} for name,value in result['files'].items()}
result.update(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),board=board)
(H/'board_snapshot.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'source_files':len(names),'state':result['state']['handsfree_dialogue'],'actual_runtime':expected},ensure_ascii=True))
