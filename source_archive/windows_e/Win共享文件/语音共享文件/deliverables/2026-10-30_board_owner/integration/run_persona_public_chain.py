"""Isolated public persona/voice transport check, never activates a GUI pair."""
import datetime
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SCRIPT=r'''
import hashlib,json,signal,sys,tempfile,time
from pathlib import Path
target=Path('/home/root/aura-board-owner-candidate-20261030/yuki-gui-capacity-20261030-r2')
aura=target/'runtime/aura';sys.path.insert(0,str(aura));signal.alarm(150)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
manifest=json.loads((target/'assembly_manifest.json').read_bytes())
assert manifest['inspection_sha256']=='d199cd3007dae5ccbafe598f8f3e8cbdc5e6acef5376344caf173e9051a3938b'
from tools.yuki_business_candidate import prepare_pair
from common.board_memory import BoardMemoryStore
from common.board_timeline_clock import StableTimelineClock
from board.runtime.board_dialogue import BoardDialogueController
from board.runtime.board_dialogue_client import InferenceHttpClient
from board.runtime.board_memory_policy import BoardContextBuilder
pair=prepare_pair(json.loads((aura/'config/board_avatar_gtk.json').read_bytes()),aura)
prompt=pair.selected_prompt
assert len(prompt.encode())==978 and hashlib.sha256(prompt.encode()).hexdigest()=='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
assert pair.state=='PREPARED' and pair.mailbox is None
client=InferenceHttpClient('192.168.50.1',8797);boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();rows=[]
with tempfile.TemporaryDirectory(prefix='public-persona-transport-',dir=str(target/'private/tmp')) as directory:
 timeline=StableTimelineClock(boot,client.health_date_source_id(),client.validate_sample,utc_bounds=BOUNDS,anchor_path=Path(directory)/'clock.json')
 client.sample_health_date(timeline,deadline=time.monotonic()+3)
 store=BoardMemoryStore(Path(directory)/'public.sqlite3',data_origin='synthetic',clock=timeline.event_time)
 controller=BoardDialogueController(store,client,board_boot_id=boot,system_prompt=prompt,context_builder=BoardContextBuilder(prompt))
 for index,text in enumerate(('你叫什么名字？','我今天有点累。','没有提供画面时，你知道我穿什么衣服吗？')):
  scope=dict(kind='conversation',id='public-persona-'+str(index));started=time.monotonic()
  plan=controller.prepare_text(text,scope=scope,session_id='public-persona-'+str(index),generation=1,budget_ms=60000,metadata=dict(source_id='public-persona-fixture'))
  assert plan.sample_rate==24000 and plan.samples>0 and len(plan.pcm)==plan.samples*2
  assert hashlib.sha256(plan.pcm).hexdigest()==plan.sha256
  controller.cancel(plan.session_id,generation=plan.generation)
  assert controller.idle and not any(m['role']=='assistant' for m in store.context(scope)['messages'])
  rows.append(dict(public_input=text,public_reply=plan.reply.text,reply_characters=len(plan.reply.text),within_style_target48=len(plan.reply.text)<=48,reply_emotion=plan.reply.emotion,seconds=round(time.monotonic()-started,3),pcm_sha256=plan.sha256,pcm_samples=plan.samples,pcm_received_and_verified=True,unplayed_plan_cancelled=True))
 assert '雪妃' in rows[0]['public_reply']
assert pair.state=='PREPARED' and pair.mailbox is None
print(json.dumps(dict(status='PASS_PUBLIC_PERSONA_TRANSPORT_ONLY',cases=rows,prompt_bytes=978,real_fixed27b=True,real_omnivoice16=True,physical_microphone_opened=False,audio_played=False,audio_archived=False,real_business_database_accessed=False,gui_pair_activated=False,dialogue_fixture_origin='synthetic',subjective_persona_quality_not_asserted=True)))
'''

def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    value=json.loads(ssh('python3 -B -','BOUNDS='+repr((now.timestamp()-86400,now.timestamp()+86400))+'\n'+SCRIPT,timeout=160))
    path=HERE/'resume_ui_trial/actual_public_persona_chain.json'
    write_json(path,dict(recorded_utc=now.isoformat(),**value));print(json.dumps(dict(output=str(path),**value),ensure_ascii=True))

if __name__=='__main__':main()
