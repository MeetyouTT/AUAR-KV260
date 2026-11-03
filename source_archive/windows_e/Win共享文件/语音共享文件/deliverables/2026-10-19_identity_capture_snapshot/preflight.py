"""Real status, cancellation and source capture; never send database commands."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and c['preflight_passed']
remote=r'''
import json,sys,threading,urllib.request
from pathlib import Path
c=CANDIDATE;sys.path.insert(0,str(Path(c['runtime'])/'aura'))
from board.interaction.ui_services import UiServiceClient
from board.interaction.ui_contract import SnapshotGate,millis,validate_snapshot
from board.runtime.audio.channel_jobs import ChannelConversationJobs
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
snapshot=json.load(urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/status',timeout=4))
client=object.__new__(UiServiceClient)
client.boot_id=boot;client.condition=threading.Condition();client.clock=millis;client.link='READY'
client.gate=SnapshotGate(boot);client.gate.ingest(snapshot);client.gate.cancel()
try:validate_snapshot(client.gate.read(),boot,millis());old_rejected=False
except ValueError:old_rejected=True
assert old_rejected
job=object.__new__(ChannelConversationJobs)
job.boot_id=boot;job.condition=threading.Condition();job.capture_owners={}
job.identity_snapshot=client.identity_snapshot;job.capture_started('preflight-capture')
owner=job.capture_owners['preflight-capture'];assert owner is not None
assert owner==snapshot and 'interaction_suppressed' not in owner
assert client.gate.read()['interaction_suppressed']
assert snapshot['source_kind']=='actual'
client.link='OFFLINE';assert client.identity_snapshot() is None
print(json.dumps({'capture_source_passed':True,'bootstrap_passed':c['preflight_passed'],
 'old_render_snapshot_rejected_reproduced':True,'actual_camera_protocol_snapshot_captured':True,
 'cancelled_subtitles_stay_masked':True,'offline_source_rejected':True,
 'database_commands_issued':False,'actual_photos_names_embeddings_exported':False}))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=25))
(HERE/'preflight.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r))
