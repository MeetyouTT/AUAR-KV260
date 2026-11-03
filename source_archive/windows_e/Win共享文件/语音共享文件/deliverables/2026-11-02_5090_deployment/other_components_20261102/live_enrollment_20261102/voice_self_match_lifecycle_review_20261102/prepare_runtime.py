"""Copy frozen public sources and three newly pinned public modules only."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'voice_self_match_query_alias_20261102'
DEST=HERE/'integration_runtime'
assert not DEST.exists(),'Fresh independent integration runtime required'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
PINS={
 'tools/board_recording.py':'e70a9f4ca4768b3a1fabfc33145e39edbcb8cf20e0c76f269cc0b032fb54ce26',
 'tools/production_memory_presentation.py':'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2',
 'board/runtime/history_delete.py':'647b5cf85ad5595305067bcced2b118f83e89ca79ba45b7ad91090fd9515023f'}
shutil.copytree(OLD/'candidate_runtime',DEST,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name,pin in PINS.items():
 src=OLD/'integration_source_44e'/name
 assert sha(src)==pin
 (DEST/name).parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(src,DEST/name)
shutil.copyfile(OLD/'yuki_pair.formal.public.json',HERE/'yuki_pair.formal.public.json')
text=(OLD/'composition.py').read_text(encoding='utf-8')
text=text.replace("RELEASE=HERE/(MODE+'_runtime')","RELEASE=HERE/'integration_runtime'")
start=text.index('BASE_PINS=');end=text.index('class Mono:')
pins={name:sha(DEST/name) for name in (
 'common/feature_intents.py','board/runtime/board_speaker_business.py','board/runtime/board_business.py',
 'tools/yuki_jobs_candidate.py','tools/formal_yuki.py','tools/streaming_controller.py','tools/realtime_controller.py',
 'tools/voice_first_recording.py','tools/handsfree_recording.py','tools/barge_in_recording.py')}
pins.update(PINS)
text=text[:start]+'PINS='+repr(pins)+"\nassert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==sha for name,sha in PINS.items())\n\n"+text[end:]
text=text.replace('from board.runtime.board_business import BoardBusinessRuntime,LocalIdentityReplies',
 'from board.runtime.board_business import BoardBusinessRuntime,BoardBusinessConfig,LocalIdentityReplies')
first=text.index('        # The public snapshot lacks')
last=text.index('        self.business=BoardSpeakerBusiness.create',first)
text=text[:first]+'''        from common.character_profile import selected_profile
        self.runtime=BoardBusinessRuntime(BoardBusinessConfig(str(path.resolve()),utc_bounds=(900.,2000.),data_origin='synthetic'),
            'synthetic-boot',asr=self.asr,system_prompt=selected_profile().persona_full_prompt,
            conversation_selection=ConversationSelection(path/'synthetic-conversation.json'),
            identity_snapshot=lambda:None,identity_command=lambda command:pytest.fail('Synthetic voice must not command camera'),
            client=self.models,timeline=self.timeline,clock=self.mono)
        self.runtime.jobs.select_conversation(resume=False)
'''+text[last:]
# Keep the actual CandidatePair+bind_runtime_pair code and direct registration
# helper, but the new explicit owner test uses its own recording path below.
(HERE/'base_composition.py').write_text(text,encoding='utf-8')
(HERE/'INTEGRATION_SOURCE_MANIFEST.json').write_text(json.dumps(dict(
 status='PUBLIC_INTEGRATION_SOURCE_COPY_ONLY',extra_public_pins=PINS,loaded_pins=pins,
 production_modified=False,board_accessed=False,full_Runtime_init_targeted=True),indent=2)+'\n',encoding='utf-8')
print('Independent integration copy and full Runtime.__init__ harness prepared')
