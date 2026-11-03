"""Derive only production receipt/retention glue from the frozen business core."""
from pathlib import Path
from build_candidate import replace_once

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'resume_yuki_business_candidate_v2/candidate/aura'


def main():
    text=(BASE/'board/runtime/board_business.py').read_text(encoding='utf8')
    text=replace_once(text,'    visual_device_id: object = None',
        '    visual_device_id: object = None\n'
        '    bootstrap_receipt: object = None\n'
        '    bootstrap_receipt_sha256: object = None\n'
        '    retention_enabled: bool = False')
    text=replace_once(text,"        if self.data_origin not in ('synthetic', 'board'):",
        "        if type(self.retention_enabled) is not bool:\n"
        "            raise ValueError('Retention requires an explicit configuration boolean')\n"
        "        if self.data_origin == 'board' and (not isinstance(self.bootstrap_receipt, str)\n"
        "                or not Path(self.bootstrap_receipt).is_absolute()\n"
        "                or not isinstance(self.bootstrap_receipt_sha256, str)\n"
        "                or re.fullmatch(r'[0-9a-f]{64}', self.bootstrap_receipt_sha256) is None):\n"
        "            raise ValueError('Production requires its committed private migration receipt')\n"
        "        if self.data_origin not in ('synthetic', 'board'):")
    text=replace_once(text,'        root.mkdir(parents=True, exist_ok=True, mode=0o700)',
        "        if not root.is_dir():\n            raise ValueError('Migrate the private production directory before opening its writer')")
    text=replace_once(text,"    lease = _BoardWriterLock(config.private_root, boot_id) if config.data_origin == 'board' else None\n    try:\n        return BoardBusinessRuntime(config, boot_id, writer_lock=lease, **kwargs)",
        "    proof = None\n"
        "    if config.data_origin == 'board':\n"
        "        from common.board_production_bootstrap import verify_production_bootstrap\n"
        "        verify_production_bootstrap(config.private_root, config.bootstrap_receipt, config.bootstrap_receipt_sha256)\n"
        "    lease = _BoardWriterLock(config.private_root, boot_id) if config.data_origin == 'board' else None\n"
        "    try:\n"
        "        if config.data_origin == 'board':\n"
        "            proof = verify_production_bootstrap(config.private_root, config.bootstrap_receipt, config.bootstrap_receipt_sha256)\n"
        "        return BoardBusinessRuntime(config, boot_id, writer_lock=lease, bootstrap_proof=proof, **kwargs)")
    text=replace_once(text,'worker_factory=BoardMemoryWorker, writer_lock=None):',
        'worker_factory=BoardMemoryWorker, writer_lock=None, bootstrap_proof=None):')
    text=replace_once(text,'        self.writer_lock = writer_lock',
        "        if config.data_origin == 'board' and (not isinstance(bootstrap_proof, dict)\n"
        "                or bootstrap_proof.get('receipt_verified') is not True\n"
        "                or bootstrap_proof.get('data_origin') != 'board'\n"
        "                or bootstrap_proof.get('profiles_migration_verified') is not True):\n"
        "            raise RuntimeError('The production factory requires verified committed migration provenance')\n"
        "        self.bootstrap_proof = dict(bootstrap_proof or {})\n"
        "        self.initial_selection = dict(mode='explicit_selection_required', session_is_fresh=True)\n"
        '        self.writer_lock = writer_lock')
    text=replace_once(text,'            self.memory_worker.start()',
        '            if self.config.retention_enabled:\n                self.memory_worker.start()')
    text=replace_once(text,"        return dict(mode='board-business-' + self.config.data_origin, production_cutover=False,",
        "        production = self.config.data_origin == 'board'\n"
        "        held = self.writer_lock is not None and self.writer_lock.fd is not None\n"
        "        proof = self.bootstrap_proof\n"
        "        memory_thread = getattr(self.memory_worker, 'thread', None)\n"
        "        return dict(mode='board-business-' + self.config.data_origin, data_origin=self.config.data_origin,\n"
        "                    production_cutover=bool(production and self.started and held),\n"
        "                    writer=dict(kind='board-local-single-writer', held=held, boot_id=self.boot_id),\n"
        "                    receipt=dict(verified=bool(production and proof.get('receipt_verified') is True), data_origin=proof.get('data_origin'),\n"
        "                        bundle_id=proof.get('bundle_id'), profiles_migration_verified=proof.get('profiles_migration_verified',False),\n"
        "                        profiles_imported=proof.get('profiles_imported',0)),\n"
        "                    retention=dict(enabled=self.config.retention_enabled,\n"
        "                        running=bool(memory_thread and memory_thread.is_alive()),\n"
        "                        initial_retention_enabled=proof.get('initial_retention_enabled',False)),\n"
        "                    conversation_selection=dict(self.initial_selection),")
    write('board/runtime/board_business.py',text)

    selection=(BASE/'common/conversation_selection.py').read_text(encoding='utf8')
    selection=replace_once(selection,'    def __init__(self, path):',
        '    def __init__(self, path, *, before_publish=None):')
    selection=replace_once(selection,'        self.path = Path(path)',
        "        if before_publish is not None and not callable(before_publish):\n"
        "            raise TypeError('Conversation publication hook must be callable')\n"
        "        self.before_publish = before_publish\n"
        '        self.path = Path(path)')
    selection=replace_once(selection,'        self.path.parent.mkdir(parents=True, exist_ok=True)',
        "        if self.before_publish is not None:\n"
        "            self.before_publish(cid)  # Register scope before exposing its persisted reference.\n"
        '        self.path.parent.mkdir(parents=True, exist_ok=True)')
    write('common/conversation_selection.py',selection)

    text=(BASE/'tools/yuki_business_gui.py').read_text(encoding='utf8')
    text=text.replace('CandidateGuiBoardBusiness','ProductionGuiBoardBusiness')
    text=replace_once(text,"                    'frontend_directory', 'feedback_manifest'}",
        "                    'frontend_directory', 'feedback_manifest', 'feedback_manifest_sha256', 'bootstrap_receipt', 'bootstrap_receipt_sha256'}")
    text=replace_once(text,"                    'frontend_threads', 'visual_device_id', 'speaker', 'face_readback'}",
        "                    'frontend_threads', 'visual_device_id', 'speaker', 'face_readback',\n"
        "                    'retention_enabled', 'resume_saved_conversation'}")
    text=replace_once(text,'        from board.runtime.audio.board_asr import BoardParaformer',
        "        if value['data_origin'] != 'board' or type(value.get('retention_enabled',False)) is not bool:\n"
        "            raise ValueError('Formal production requires explicit board origin and retention boolean')\n"
        "        if type(value.get('resume_saved_conversation',True)) is not bool:\n"
        "            raise ValueError('Choose saved anonymous continuation explicitly')\n"
        "        from common.board_production_bootstrap import verify_production_bootstrap\n"
        "        verify_production_bootstrap(value['private_root'], value['bootstrap_receipt'], value['bootstrap_receipt_sha256'])\n"
        "        import hashlib\n"
        "        if hashlib.sha256(Path(value['feedback_manifest']).read_bytes()).hexdigest() != value['feedback_manifest_sha256']:\n"
        "            raise ValueError('The selected public cue manifest changed')\n"
        "        readback = load_private_face_readback(value.get('face_readback'))\n"
        "        readback.verify(readback.config)\n"
        '        from board.runtime.audio.board_asr import BoardParaformer')
    text=replace_once(text,"            data_origin=value['data_origin'], visual_device_id=value.get('visual_device_id', 'board-camera'))",
        "            data_origin=value['data_origin'], visual_device_id=value.get('visual_device_id', 'board-camera'),\n"
        "            bootstrap_receipt=value['bootstrap_receipt'], bootstrap_receipt_sha256=value['bootstrap_receipt_sha256'],\n"
        "            retention_enabled=value.get('retention_enabled',False))")
    text=replace_once(text,'            bind_runtime_pair(self.runtime, self.character_pair)',
        "            from common.board_production_bootstrap import register_anonymous_conversation\n"
        "            self.runtime.jobs.conversation_selection.before_publish = (\n"
        "                lambda cid: register_anonymous_conversation(self.runtime.store, cid))\n"
        '            bind_runtime_pair(self.runtime, self.character_pair)')
    text=replace_once(text,'            validate_feedback_character(feedback())',
        "            initialize_anonymous_selection(self.runtime, value.get('resume_saved_conversation',True))\n"
        '            validate_feedback_character(feedback())')
    text += '''

def initialize_anonymous_selection(runtime, resume_saved):
    """Explicit root continuation policy; no profile/grant/token is imported."""
    import hashlib
    selection = runtime.jobs.conversation_selection
    proof = runtime.bootstrap_proof
    if resume_saved and proof.get('conversation_selection_verified') is True:
        raw = Path(selection.path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != proof.get('conversation_selection_sha256'):
            raise ValueError('Verified anonymous conversation reference changed before admission')
        runtime.jobs.select_conversation(resume=True)
        runtime.initial_selection = dict(mode='saved_anonymous', session_is_fresh=True,
                                        profile_grant_imported=False)
    elif resume_saved and not proof.get('conversation_selection_verified'):
        runtime.jobs.select_conversation(resume=False)
        runtime.initial_selection = dict(mode='new_anonymous_no_saved_reference', session_is_fresh=True,
                                        profile_grant_imported=False)
    else:
        runtime.initial_selection = dict(mode='explicit_selection_required', session_is_fresh=True,
                                        profile_grant_imported=False)
'''
    write('tools/production_board_business_gui.py',text)


def write(relative,text):
    path=HERE/'production_modules'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf8',newline='\n')


if __name__=='__main__':main()
