"""Three-file local standalone entry routing; original biometric FSMs unchanged."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
LIVE=HERE.parent
BASE=LIVE/'start_sync_fix/candidate_runtime'
RUNTIME=HERE/'candidate_runtime'
assert not RUNTIME.exists()
RUNTIME.mkdir()
for path in BASE.rglob('*.py'):
    if '__pycache__' in path.parts:continue
    target=RUNTIME/path.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,target)
(RUNTIME/'config').mkdir(exist_ok=True)
for name in ('character_profile.local.json','board_dialogue_model.json'):
    shutil.copyfile(BASE/'config'/name,RUNTIME/'config'/name)
for name,sha in (
 ('board/runtime/audio/board_asr.py','c51488ac6bd3563bc3dc42934b321e98e26cb2b58d700318765a60ca4908ef60'),
 ('board/runtime/audio/board_dialogue_jobs.py','01b27ede0d8889c35fc9ac990e03538a55fecc7c6a604fb6f781bc5d54c09087')):
    path=LIVE/'lifecycle_review/no_speech_fix/candidate'/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
    shutil.copyfile(path,RUNTIME/name)
router=LIVE/'workflow_review/unified_identity_binding.current_a6d4.py'
assert hashlib.sha256(router.read_bytes()).hexdigest()=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
shutil.copyfile(router,RUNTIME/'tools/unified_identity_binding.py')

names=('common/binding_intent.py','board/runtime/board_business.py','board/runtime/audio/board_dialogue_jobs.py')
original={name:(RUNTIME/name).read_bytes() for name in names}
assert hashlib.sha256(original[names[0]]).hexdigest()=='8cfe3c841248b7ca56553255dcb14e400c5b52ea011e68ecd89a16862a7eb796'
assert hashlib.sha256(original[names[1]]).hexdigest()=='b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2'

intent=original[names[0]].decode('utf-8')
anchor="    value=strip_character_address(text.strip(' \\t\\r\\n。！!？?'))\n"
assert intent.count(anchor)==1
addition='''    # Explicit standalone commands are not combined enrollment consent.
    found=re.fullmatch(r'(?:请)?(?:帮我)?登记(?:我的)?人脸[，, ]*(?:(?:我叫|我的名字是|叫我)(.+))?',value)
    if found:
        name=found.group(1);name=name.strip() if name is not None else None
        return {'kind':'face_only','name':name} if name is None or valid_name(name) else {'kind':'invalid_name','name':None}
    from common.feature_intents import speaker_text
    voice=speaker_text(text)
    if voice=='登记我的声纹':return {'kind':'voice_only','name':None}
    prefix='登记我的声纹，我叫'
    if isinstance(voice,str) and voice.startswith(prefix):return {'kind':'voice_only','name':voice[len(prefix):]}
'''
intent=intent.replace(anchor,anchor+addition)
anchor="    if intent['kind']=='remember_self':\n"
assert intent.count(anchor)==1
intent=intent.replace(anchor,"    if intent['kind'] in ('remember_self','face_only'):\n")

business=original[names[1]].decode('utf-8')
anchor='        self.business = self.bridge = None\n'
assert business.count(anchor)==1
business=business.replace(anchor,anchor+'        self._standalone_entry = None\n')
anchor='    def reset(self):\n        self.flow.reset()\n'
assert business.count(anchor)==1
business=business.replace(anchor,'    def reset(self):\n        self._standalone_entry = None\n        self.flow.reset()\n')
anchor="        state = self.flow.public()\n        if self.business is not None:\n"
assert business.count(anchor)==1
business=business.replace(anchor,"""        state = self.flow.public()
        entry = getattr(self, '_standalone_entry', None)
        pending = bool(entry and entry['awaiting_name'] and self.clock() < entry['until'])
        # Polling never mutates routing ownership or the original biometric FSM.
        state.update(entry_mode=entry['mode'] if entry else None, entry_name_pending=pending)
        state['active'] = state['active'] or pending
        if self.business is not None:
""")
anchor='    def _visual(self, job):\n'
assert business.count(anchor)==1
helpers='''    def _entry_for(self, meta):
        entry = getattr(self, '_standalone_entry', None)
        if entry is not None and (entry['actor'] != (meta['board_boot_id'], meta['session_id'])
                or entry['awaiting_name'] and self.clock() >= entry['until']):
            self._standalone_entry = None
            return None
        return entry

    def _new_entry(self, meta, mode, *, awaiting_name=False):
        # Only route the already requested original FSM. No name/sample/grant.
        entry = dict(mode=mode, actor=(meta['board_boot_id'], meta['session_id']),
                     awaiting_name=awaiting_name, until=self.clock()+120 if awaiting_name else None)
        self._standalone_entry = entry
        return entry

'''
business=business.replace(anchor,helpers+anchor)
anchor='''            exchange = None
            board_text = None
            try:
                if self.business is not None:
'''
assert business.count(anchor)==1
branch='''            exchange = None
            board_text = None
            entry = self._entry_for(job.meta)
            try:
                from common.feature_intents import speaker_requested, speaker_query_requested
                from tools.provisional_voice import query_reply
                intent = binding_intent(text)
                requested = {'face_only':'face', 'voice_only':'voice'}.get(intent['kind'])
                if entry is not None and (requested is not None and requested != entry['mode']
                        or intent['kind'] == 'remember_self'):
                    emit(BoardReply('当前已有登记正在进行。请先完成或取消本次登记，再选择另一种入口。', 'friendly'), final_cue=True)
                    return
                if requested is not None and entry is None:
                    if self.flow.public()['active'] or self.business is not None and self.business.public()['active']:
                        emit(BoardReply('当前已有登记正在进行。请先完成或取消本次登记，再选择另一种入口。', 'friendly'), final_cue=True)
                        return
                    entry = self._new_entry(job.meta, requested,
                        awaiting_name=requested == 'voice' and intent['name'] is None)
                if intent['kind'] == 'invalid_name':
                    emit(BoardReply(render(result('bad_name')), 'friendly'), final_cue=True)
                    return
                if entry is not None and entry['mode'] == 'voice':
                    if self.business is None:
                        raise BoardCapabilityNotReady('speaker_identity')
                    compact = text.strip(' 。！!？?')
                    cancel = compact in ('取消', '取消登记', '不保存', '取消声纹登记',
                        '停止声纹登记', '不登记声纹了', '不要保存声纹')
                    if compact == '确认保存身份关联':
                        emit(BoardReply('当前是单独声纹登记。请按提示完成三段录音，最后说“确认保存声纹”。', 'friendly'), final_cue=True)
                        return
                    from common.voice_enrollment import confirmed, update_confirmed
                    if confirmed(text) or update_confirmed(text):
                        emit(BoardReply('当前是单独声纹登记。最后的保存口令是“确认保存声纹”。', 'friendly'), final_cue=True)
                        return
                    interpreted = text
                    if requested == 'voice':
                        if not entry['awaiting_name'] and self.business.public()['active']:
                            emit(BoardReply('本轮声纹登记仍在进行，请继续按提示采样或取消后重新开始。', 'friendly'), final_cue=True)
                            return
                        interpreted = ('登记我的声纹' if intent['name'] is None else
                                       '登记我的声纹，我叫' + intent['name'])
                        if intent['name'] is not None:entry['awaiting_name'] = False
                    elif entry['awaiting_name'] and not cancel:
                        if intent['kind'] == 'name_hint' and not self.business.public()['active']:
                            interpreted = '登记我的声纹，我叫' + intent['name']
                            entry['awaiting_name'] = False
                        elif speaker_query_requested(text) or query_reply(text, {'state':'UNKNOWN'}) is not None:
                            interpreted = '查询我的声纹'
                        else:
                            interpreted = '登记我的声纹'
                    elif query_reply(text, {'state':'UNKNOWN'}) is not None:
                        interpreted = '查询我的声纹'
                    spoken = self.business.turn(job.meta, interpreted, job.pcm,
                        is_current=current, cancel_event=cancel_event, deadline=job.deadline)
                    if cancel:self._standalone_entry = None
                    if spoken is None:return DIALOGUE_ROUTE
                    emit(BoardReply(spoken, 'friendly'), final_cue=True)
                    return
                if entry is not None and entry['mode'] == 'face':
                    if speaker_requested(text):
                        emit(BoardReply('当前是人脸登记。请先完成或取消本次登记，再开始声纹登记。', 'friendly'), final_cue=True)
                        return
                    board_text = ('取消登记' if text.strip(' 。！!？?') in ('取消','不保存') else
                                  face_enrollment_text(text, active=self.flow.public()['active']))
                if self.business is not None and entry is None:
'''
business=business.replace(anchor,branch)
anchor='''            finally:
                if exchange is not None:
                    exchange.cancel()
        return controller.prepare_local_sequence(text, produce, reply_sink, **kwargs)
'''
assert business.count(anchor)==1
business=business.replace(anchor,'''            finally:
                if exchange is not None:
                    exchange.cancel()
                if entry is not None and self._standalone_entry is entry:
                    if entry['mode'] == 'face' and not self.flow.public()['active']:
                        self._standalone_entry = None
                    elif (entry['mode'] == 'voice' and not entry['awaiting_name']
                            and (self.business is None or not self.business.public()['active'])):
                        self._standalone_entry = None
        return controller.prepare_local_sequence(text, produce, reply_sink, **kwargs)
''')

jobs=original[names[2]].decode('utf-8')
old="('remember_self', 'name_hint', 'invalid_name')"
assert jobs.count(old)==2
jobs=jobs.replace(old,"('remember_self', 'name_hint', 'invalid_name', 'face_only', 'voice_only')",1)
jobs=jobs.replace(old,"('remember_self', 'name_hint', 'invalid_name', 'face_only')",1)
changed=dict(zip(names,(intent,business,jobs)))
manifest=[];diff=[]
for name,source in changed.items():
    ast.parse(source)
    target=RUNTIME/name;target.write_text(source,encoding='utf-8',newline='\n')
    manifest.append(dict(file=name,before_sha256=hashlib.sha256(original[name]).hexdigest(),
        after_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    diff.extend(difflib.unified_diff(original[name].decode().splitlines(True),source.splitlines(True),
                                   fromfile='a/'+name,tofile='b/'+name))
(HERE/'CANDIDATE.diff').write_text(''.join(diff),encoding='utf-8')
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(status='LOCAL_CANDIDATE_NOT_DEPLOYED',
    baseline_startup='f507bfa6cb5ea5de807dd36601ac4ff2e4af9bba5aa75f6fd5a2b3a5fd54e3eb',
    changed_files=manifest,board_accessed=False,production_changed=False,
    router_sha256=hashlib.sha256((RUNTIME/'tools/unified_identity_binding.py').read_bytes()).hexdigest(),
    preserved_asr_sha256=hashlib.sha256((RUNTIME/'board/runtime/audio/board_asr.py').read_bytes()).hexdigest(),
    new_joint_alias=False,standalone_link_creation=False),indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest))
