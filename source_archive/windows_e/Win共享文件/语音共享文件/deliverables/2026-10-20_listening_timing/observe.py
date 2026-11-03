"""Observe a bounded human trial through metadata; never export speech/text."""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
assert 5 <= seconds <= 55
remote = r'''
import json,time,urllib.request
rows=[];until=time.monotonic()+SECONDS
while time.monotonic()<until:
 u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
 tx=u['local_transcription'];svc=tx['service'];hf=u['handsfree_dialogue']
 rows.append({'at_mono':round(time.monotonic(),2),
  'handsfree':{k:hf.get(k) for k in ('enabled','state','reason','microphone_open','visual_bound','listening_timing','diagnostics','conversation_entered')},
  'barge_in':u.get('voice_barge_in'),
  'recording':u['local_recording']['state'],'transcription_state':tx['state'],
  'transcript_characters':len(tx.get('text','')),'reply_characters':len(u.get('reply','')),
  'phase':u['phase'],'playing':u['playing'],'audio_output_state':u['audio_output_state'],
  'last_playback_ack':svc.get('last_playback_ack'),
  'completed_turns':u['automatic_conversation']['completed_turns']})
 time.sleep(.25)
print(json.dumps({'rows':rows,'human_interruption_verified':False,
 'operator_started_recording':False,'audio_or_transcript_exported':False}))
'''.replace('SECONDS', str(seconds), 1)
r = json.loads(ssh('python3 -B -', remote, timeout=seconds + 15))
target = HERE / ('passive_trial_' + time.strftime('%Y%m%d_%H%M%S') + '.json')
target.write_text(json.dumps(r, indent=2), encoding='utf-8')
print(json.dumps({'evidence':str(target), 'samples':len(r['rows']),
 'states':sorted({row['handsfree']['state'] for row in r['rows']}),
 'maximum_interrupted_turns':max(row['barge_in'].get('interrupted_turns',0) for row in r['rows']),
 'latest':r['rows'][-1], 'human_interruption_verified':False}))
