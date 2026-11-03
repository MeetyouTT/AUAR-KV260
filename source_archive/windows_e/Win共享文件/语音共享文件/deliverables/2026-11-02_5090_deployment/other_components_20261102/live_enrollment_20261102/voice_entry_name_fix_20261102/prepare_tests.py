"""Create real-Yuki composition harness from the sealed original synthetic harness."""
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
old=(HERE.parent/'split_commands_20261102/production_composition_review/test_real_composition.py').read_text(encoding='utf-8')
old=old[:old.index('@pytest.mark.parametrize')]
old=old.replace('import hashlib','import hashlib\nimport os\nimport json\nimport threading',1)
old=old.replace('from common.board_memory import BoardMemoryStore',
 'from common.board_memory import BoardMemoryStore\nfrom common.conversation_selection import ConversationSelection',1)
old=old.replace('            scope_provider=lambda meta:',
 "            conversation_selection=ConversationSelection(path/'synthetic-conversation.json'),\n            scope_provider=lambda meta:",1)
old=old.replace("RELEASE=HERE.parent/'actual_release/runtime'","MODE=os.environ.get('AURA_ENTRY_VARIANT','candidate')\nassert MODE in ('baseline','candidate')\nRELEASE=HERE/(MODE+'_runtime')",1)
start=old.index('PINS=')
end=old.index('class Mono:')
old=old[:start]+'''BASE_PINS=json.loads((HERE/'BASE_PINS.json').read_text(encoding='utf-8'))
CANDIDATE_PINS={
 'common/feature_intents.py':'2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2',
 'board/runtime/board_business.py':'bf185a86dfd1f94924759c194b0246b51e64cb0a09654c935e8e1310f7bbea51',
 'tools/yuki_jobs_candidate.py':'d7bade70cf15cd5c7dd9bb17be702f86c5f2d1a32ad5c5809dddffde7a71d200',
}
PINS=dict(BASE_PINS,**(CANDIDATE_PINS if MODE=='candidate' else {}))
PINS['tools/formal_yuki.py']='c74b5f00d52208d992e8ee82c998250001c781c900d31b1f72a18bdda6f492e9'
assert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==sha for name,sha in PINS.items())

'''+old[end:]
needle='        self.runtime.attach_speaker_business(self.business)'
assert old.count(needle)==1
old=old.replace(needle,needle+'''
        # Use actual current formal pair policy plus actual bind_runtime_pair.
        # Only native frame readiness is synthetic; no renderer/GL/device exists.
        from common.character_profile import selected_profile
        from tools.formal_yuki import CandidatePair
        from tools.board_persona_candidate import BoardPersonaCandidate
        from tools.yuki_business_candidate import bind_runtime_pair
        from board.runtime.board_memory_policy import BoardContextBuilder,BoardMemoryCommands
        profile=selected_profile()
        pair_meta=json.loads((HERE/'yuki_pair.formal.public.json').read_text(encoding='utf-8'))
        identity=pair_meta['identity']
        persona=BoardPersonaCandidate(identity['profile_version'],identity['display_name'],identity['persona_config_sha256'],
            identity['render_profile_id'],identity['render_source_profile_sha256'],profile.persona_full_prompt)
        pair=CandidatePair(RELEASE,pair_meta,persona)
        pair.attach_mailbox(SimpleNamespace(ready=True,lock=threading.RLock()))
        pair.observe_native_frame({'frames':1})
        self.runtime.controller.context_builder=BoardContextBuilder(profile.persona_full_prompt)
        self.runtime.controller.command_handler=BoardMemoryCommands(self.runtime.store)
        bind_runtime_pair(self.runtime,pair)
        from tools import yuki_jobs_candidate
        assert self.runtime.jobs._route.__func__ is yuki_jobs_candidate._route
        assert self.runtime.jobs._admit_text.__func__ is yuki_jobs_candidate._admit_text
''',1)
needle='        if media is not None:\n            self.runtime.jobs.acknowledge'
assert old.count(needle)==1
old=old.replace(needle,'        self.last_reply=media.plan.reply.text if media is not None else None\n'+needle,1)
(HERE/'composition.py').write_text(old,encoding='utf-8')
print('Real formal pair/yuki bind harness created with explicit SHA pins')
