"""Bounded passive metadata observation while user tests; no audio/text export."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request
rows=[];until=time.monotonic()+30
while time.monotonic()<until:
 u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
 tx=u['local_transcription'];svc=tx['service']
 rows.append({'at_mono':round(time.monotonic(),2),'handsfree':u['handsfree_dialogue'],
  'recording':u['local_recording']['state'],'transcription_state':tx['state'],
  'transcript_characters':len(tx.get('text','')),'reply_characters':len(u.get('reply','')),
  'phase':u['phase'],'playing':u['playing'],'audio_output_state':u['audio_output_state'],
  'last_playback_ack':svc.get('last_playback_ack'),'completed_turns':u['automatic_conversation']['completed_turns']})
 time.sleep(.5)
print(json.dumps({'rows':rows,'human_hearing_verified':False,'operator_started_recording':False,'audio_or_transcript_exported':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=40))
(HERE/'passive_live_observation.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
acks={row['last_playback_ack']['request_id'] for row in r['rows'] if row.get('last_playback_ack') and row['last_playback_ack'].get('committed')}
print(json.dumps({'states':sorted({row['handsfree']['state'] for row in r['rows']}),'observed_committed_ack_ids':sorted(acks),
 'latest':r['rows'][-1],'human_hearing_verified':False}))
