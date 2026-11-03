"""Build image/persona-only overlay over pinned production r3, locally only.

No database, service, device, network, model, GUI or system configuration access.
The publisher must merge the fragment into the fresh original config, preserve
all production data/settings paths and re-pin the composed source closure.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parent
INTEGRATION = ROOT.parent
FRESH = INTEGRATION/'resume_runtime/fresh_source'
V2 = INTEGRATION/'resume_yuki_business_candidate_v2'
OUT = ROOT/'overlay'
PAIR_VERSION = 'xuefei-yuki-board-v1-candidate'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode()


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Source integration point changed: '+old[:90])
    return source.replace(old, new, 1)


def write(relative, raw):
    path = OUT/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if isinstance(raw, bytes) else raw.encode())


def extract(source, names):
    tree = ast.parse(source)
    rows = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names:
            start = min([node.lineno]+[v.lineno for v in node.decorator_list])
            rows.append(''.join(source.splitlines(True)[start-1:node.end_lineno])+'\n')
    if len(rows) != len(names):
        raise ValueError('Pinned helper AST changed')
    return '\n'.join(rows)


def build_gtk(source):
    source = once(source, '        self.root = Path(root).resolve(strict=True)\n',
        "        self.root = Path(config['formal_stage_root']).resolve(strict=True)\n")
    source = once(source, "        self.settings_store = SettingsStore(settings_file or AURA.parent/'avatar_user_settings.json')",
        "        self.settings_store = SettingsStore(Path(config['formal_settings_paths']['user']))")
    source = once(source, "            self.transcription_store = TranscriptionStore(AURA.parent/'avatar_transcription_settings.json')",
        "            self.transcription_store = TranscriptionStore(Path(config['formal_settings_paths']['transcription']))")
    source = once(source, "            conversation_store=TranscriptionStore(AURA.parent/'avatar_conversation_settings.json')",
        "            conversation_store=TranscriptionStore(Path(config['formal_settings_paths']['conversation']))")
    source = once(source, "            self.connection_store = ConnectionStore(AURA.parent/'avatar_service_settings.json', defaults['connection'])",
        "            self.connection_store = ConnectionStore(Path(config['formal_settings_paths']['service']), defaults['connection'])")
    source = once(source, '        self.source_hashes = {}\n',
        '        self.source_hashes = {}\n'
        '        from tools.formal_yuki import prepare_pair\n'
        '        self.character_pair = prepare_pair(config, AURA, self.source_hashes)\n'
        '        self.lines, self.character = self.character_pair.demo_lines, self.character_pair.identity.display_name\n')
    source = once(source,
        "        self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py'] = hashlib.sha256(reuse.read_bytes()).hexdigest()",
        '        # New native profile never reads archival PNG preview helpers.')
    source = once(source, '        self.native_pixels = self.native_video = None\n',
        '        self.native_pixels = self.native_video = None\n'
        '        self.native_yuki = self.yuki_portrait = self.native_yuki_config = None\n')
    source = once(source, '            core = create_runtime_core(create_demo_core)\n',
        '            from tools.formal_yuki import create_native_core\n'
        '            core = create_native_core()\n')
    source = source.replace("            if config.get('native_avatar'):\n", '            if False:  # old PNG/native-pixel profile disabled only in this overlay\n')
    source = once(source, "            else:configure_board_rendering(core,self.tokens['colors']['panel_bg'])",
        '            # One EGL native sink; no old PNG rendering/configuration.')
    source = once(source, '                controller_type=StreamingController\n',
        '                from tools.formal_yuki import native_controller_type\n'
        '                controller_type=native_controller_type()\n')
    source = once(source, '                    from board.runtime.audio.channel_jobs import ChannelConversationJobs\n',
        '                    from tools.formal_yuki import local_channel_jobs_type\n'
        "                    ChannelConversationJobs=local_channel_jobs_type(config['formal_static_cues'],self.character_pair)\n")
    source = once(source,
        "            visual_controller=controller_type(core,self.jobs,self.output)\n            if config.get('portrait_offload',{}).get('enabled'):",
        "            visual_controller=controller_type(core,self.jobs,self.output)\n"
        "            from tools.formal_native_yuki import prepare_portrait\n"
        "            self.native_yuki,self.native_yuki_config=prepare_portrait(AURA,config['native_yuki'],self.output,self.source_hashes,self.character_pair)\n"
        "            visual_controller.portrait_offload=self.native_yuki\n"
        "            if False:  # old computer portrait offload disabled\n")
    source = once(source,
        '            self.controller = AvatarRenderWorker(recording_type(visual_controller,transcriber=self.transcriber,**recording_options),\n',
        '            from tools.formal_yuki import paired_recording_type\n'
        '            recording_type=paired_recording_type(recording_type,self.character_pair)\n'
        '            self.controller = AvatarRenderWorker(recording_type(visual_controller,transcriber=self.transcriber,**recording_options),\n')
    source = once(source,
        "                .25 if self.preferences['economy'] else (1/24 if config.get('native_avatar') else config['tick_ms']/1000),native_video=self.native_video,visual_fps=config.get('stable_avatar_fps',8) if config.get('native_avatar') else None,performance_path=self.evidence_root/'render_performance.jsonl')",
        "                1/24,native_video=None,visual_fps=16,performance_path=self.evidence_root/'render_performance.jsonl')\n"
        '            self.character_pair.invalidators.append(self.controller.cancel)')
    source = once(source,
        "            self.controller.set_interval(.25 if self.preferences['economy'] else (1/24 if self.config.get('native_avatar') else interval/1000))",
        '            self.controller.set_interval(1/24)')
    source = once(source, '        self.portrait = gtk.DrawingArea() if self.native_video else gtk.Image()\n',
        '        from tools.formal_native_yuki import create_gl_area\n'
        '        self.yuki_portrait=create_gl_area(self.native_yuki_config,self.native_yuki,self.character_pair)\n'
        "        self.yuki_portrait.set_size_request(self.rect['w'],self.rect['h'])\n"
        '        self.portrait=self.yuki_portrait\n'
        "        self.controls['portrait_toggle'].set_sensitive(False)\n")
    source = once(source, "        kind = data['type']\n",
        "        kind = data['type']\n"
        "        if kind in ('demo','speak','record_toggle','conversation_toggle'):\n"
        '            self.character_pair.require_ready()\n'
        "        if kind in ('portrait_fps','portrait_toggle'):\n"
        "            raise ValueError('雪妃固定本地16fps；切换必须空闲正常退出并成套回退')\n")
    source = once(source, "            if not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:",
        '            if False:  # old RGB portrait path disabled')
    source = once(source, "            if self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')",
        '            from tools.formal_native_yuki import display_status\n'
        "            state['avatar_display']=display_status(self.native_yuki)\n"
        "            state['character_pair']=self.character_pair.status()")
    source = once(source,
        "        self.controls['portrait_toggle'].set_label('画面：电脑' if mode=='remote' else\n"
        "            '画面：电脑连接中，板卡显示' if portrait.get('selected') else '画面：板卡')",
        "        self.controls['portrait_toggle'].set_label('雪妃 · 本地16fps' if self.native_yuki.ready else '雪妃 · 渲染未就绪')")
    source = once(source, '    def cleanup(self):\n        self.close_identity_face_dialog()',
        "    def cleanup(self):\n"
        "        if getattr(self,'character_pair',None) is not None:\n"
        "            self.character_pair.fail('formal_shutdown')\n"
        '        self.close_identity_face_dialog()')
    # Only current UI source strings; no history/reference/identity-key edits.
    source = source.replace('汐蓝', '雪妃')
    source = source.replace("display.get('kind')!='native_sink_handoff'", "display.get('kind') not in ('native_sink_handoff','native_yuki_egl')")
    source = once(source, "    fps,age=display.get('fps'),display.get('age_ms')\n",
        "    if display.get('presentation_state')=='hidden':return '形象已隐藏'\n"
        "    fps,age=display.get('fps'),display.get('age_ms')\n")
    return source


def main():
    fresh_meta = json.loads((FRESH/'manifest.json').read_bytes())
    v2_meta = json.loads((V2/'candidate/manifest.json').read_bytes())
    pair_meta = json.loads((V2/'candidate/aura/config/yuki_pair.candidate.json').read_bytes())
    fresh = {}
    before = {}
    names = ['tools/board_avatar_gtk.py','tools/board_avatar_worker.py','board/runtime/character.py',
             'common/spoken_input.py','common/voice_wake.py','common/voice_enrollment.py',
             'common/binding_intent.py','common/memory_commands.py','tools/voice_first_recording.py']
    for name in names:
        raw = (FRESH/'aura'/name).read_bytes()
        expected = fresh_meta['source_sha256'][name]
        if sha(raw) != expected:
            raise ValueError('Original fresh source changed: '+name)
        fresh[name] = raw.decode()
        before[name] = expected
    # Copy only already pinned native resources/persona validators. Not the
    # candidate business factory, controller, Store, profile database or config.
    runtime_pins = dict(pair_meta['runtime_pins'])
    for name, expected in runtime_pins.items():
        raw = (V2/'candidate/aura'/name).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Frozen native/persona resource changed: '+name)
        write('aura/'+name, raw)
    baseline = (V2/'candidate/aura/config/yuki_accepted_prompt.baseline.txt').read_bytes()
    write('aura/config/yuki_accepted_prompt.baseline.txt', baseline)
    meta = dict(pair_meta, schema='aura.yuki.formal_legacy_pair.v1')
    raw_meta = encode(meta)
    pair_sha = sha(raw_meta)
    write('aura/config/yuki_pair.formal.json', raw_meta)
    original_helper = (V2/'candidate/aura/tools/yuki_business_candidate.py').read_text(encoding='utf8')
    helper = ('"""Startup-fixed image/persona pair for the ORIGINAL legacy business.\n'
        'No factory/store/context/permission changes; no runtime global mutation.\n"""\n'
        'from dataclasses import dataclass\nimport hashlib\nimport json\nimport math\n'
        'from pathlib import Path\nimport re\nimport threading\nimport types\n\n'
        "PAIR_VERSION='xuefei-yuki-board-v1-candidate'\n"
        "PAIR_CONFIG_SHA256='"+pair_sha+"'\n"
        "PROFILE_ID='fuyukiss-yuki-freemote39-frame-mesh'\n"
        "PROFILE_SHA256='b7b71396c267db80a44c2b32df4ba53ded7920ac952b2fbbfebafba349f85f55'\n"
        "NATIVE_PACKAGE_SHA256='c0107904f8cd0b3e351666ade5fc7234e4278a82d165925dbbdc1459783baebb'\n\n")
    helper += extract(original_helper, ['PairRejected','_read_pinned','CharacterSpeechPolicy','PairIdentity',
        'CandidatePair','scoped_function','NumericFacials','create_native_core','native_controller_type'])
    helper = helper.replace('production_selected=False', 'production_selected=True')
    helper = once(helper, "        return (\n            dict(id='greeting', label='雪妃问候', text='你好，我是雪妃。今天想聊些什么？', emotion='friendly', action=''),\n            dict(id='happy', label='开心回应', text='太好了，又向前走了一步。我也有点开心。', emotion='happy', action=''),\n            dict(id='gentle', label='轻声回应', text='先歇一会儿吧。你愿意说的话，我会认真听。', emotion='sad', action=''),\n        )",
        '        from board.runtime.character import DEMO_LINES\n        return DEMO_LINES')
    helper += '\n'+(ROOT/'formal_pair_tail.py.in').read_text(encoding='utf8')
    write('aura/tools/formal_yuki.py', helper)
    native = (V2/'candidate/aura/tools/native_yuki_candidate.py').read_text(encoding='utf8')
    native = native.replace('from tools.yuki_business_candidate import', 'from tools.formal_yuki import')
    native = native.replace('candidate_fixed_native', 'candidate_fixed_native')
    native = native.replace('candidate_pair=True', 'candidate_pair=False, formal_pair=True')
    native += '\n'
    write('aura/tools/formal_native_yuki.py', native)
    # Use only the isolated helper function, never execute the old builder.
    spec = importlib.util.spec_from_file_location('pinned_v2_builder', V2/'build_candidate.py')
    old_builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_builder)
    write('aura/tools/board_avatar_gtk.py', build_gtk(fresh['tools/board_avatar_gtk.py']))
    write('aura/tools/board_avatar_worker.py', old_builder.build_worker(fresh['tools/board_avatar_worker.py']))
    selected_sources = INTEGRATION/'resume_windows_character_profile/after/aura'
    for name in ('common/character_profile.py','config/character_profile.local.json','board/runtime/character.py',
                 'common/spoken_input.py','common/voice_wake.py','common/voice_enrollment.py','common/binding_intent.py','common/memory_commands.py'):
        write('aura/'+name, (selected_sources/name).read_bytes())
    write('aura/tools/voice_first_recording.py', once(fresh['tools/voice_first_recording.py'],
        "wake_words=['汐蓝', '欸', '哎']", "wake_words=['御笠雪妃', '雪妃', '欸', '哎']"))
    fragment = dict(native_yuki=pair_meta['native_config'], native_avatar=True, stable_avatar_fps=16,
        portrait_offload=dict(enabled=False), character_pair=dict(enabled=True, profile_version=PAIR_VERSION,
        selection='config/yuki_pair.formal.json',selection_sha256=pair_sha))
    old_runtime = fresh_meta['runtime']
    fragment['formal_settings_paths'] = {key:old_runtime+'/avatar_'+key+'_settings.json'
        for key in ('user','transcription','conversation','service')}
    fragment['formal_stage_root'] = old_runtime+'/deliverables/2026-10-06_xilan_live'
    fragment['formal_static_cues'] = dict(path='/home/root/aura-board-owner-candidate-20261030/xuefei-static-cues-8222c2a0ff30471a/feedback.json',
        sha256='143f6b2ea0de6afcfc1fc76178faa3de22d8fdd2bbbabc7965ddc7488ea786de')
    write('config.fragment.json', encode(fragment))
    files = {}
    for path in sorted(OUT.rglob('*')):
        if path.is_file():
            relative = path.relative_to(OUT).as_posix()
            raw = path.read_bytes()
            if path.suffix == '.py':ast.parse(raw, feature_version=(3,9))
            files[relative] = sha(raw)
    manifest = dict(schema='aura.yuki.formal_legacy_overlay.v1', pair_version=PAIR_VERSION,
        based_on_runtime=fresh_meta['runtime'], based_on_startup_sha256=fresh_meta['config_sha256'],
        before_sha256=before, files=files, prompt_utf8_bytes=978,
        prompt_sha256=v2_meta['prompt_sha256'], native_package_sha256=v2_meta['native_archive_sha256'],
        business_mode='UNCHANGED_LEGACY', enable_board_business=False, synthetic_store_included=False,
        database_read=False,database_copy=False,database_migration=False,cleanup_enabled=False,
        settings_paths_changed=False,device_or_service_calls=False,performance_tests_added=False,
        original_launcher_must_remain_sha256='5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03',
        windows_service_revision='voice-xuefei-profile-20261030-r13',
        windows_source_fingerprint='83dbfae5359cbcfd27ed7bc895456177760d41310c785010e57bb02e833ca7de',
        publisher='root_only')
    (ROOT/'manifest.json').write_bytes(encode(manifest))
    with zipfile.ZipFile(ROOT/'formal_yuki.overlay.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in files:
            info = zipfile.ZipInfo(relative, (2026,10,30,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info, (OUT/relative).read_bytes())
    print(json.dumps(dict(files=len(files),source_zip_sha256=sha((ROOT/'formal_yuki.overlay.zip').read_bytes()),
        manifest_sha256=sha((ROOT/'manifest.json').read_bytes())),sort_keys=True))


if __name__ == '__main__':main()
