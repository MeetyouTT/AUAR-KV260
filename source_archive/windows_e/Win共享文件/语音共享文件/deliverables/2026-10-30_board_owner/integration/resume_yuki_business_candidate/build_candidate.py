"""Build an independent source/assets review package. Never deploy or run it.

Inputs are locally pinned snapshots. Only this script's candidate directory is
written. No model, database, GUI, board, network or service is accessed.
"""
import ast
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import textwrap
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[3]
INTEGRATION = ROOT.parent
RUNTIME = INTEGRATION/'resume_runtime'
PERSONA = PROJECT/'deliverables/2026-10-30_board_owner/character_persona_candidate'
NATIVE = PROJECT/'deliverables/2026-10-30_yuki_native_validation'
FINGERPRINT = '730de9634b8daa076569d8182faba69cb4a67f75a8a8791aa649c2bbb982c4c9'
NATIVE_SHA = 'c0107904f8cd0b3e351666ade5fc7234e4278a82d165925dbbdc1459783baebb'
PERSONA_SHA = '33d2dbb87348591da9e288bb9867a8e246fa63a955c071236eeeb24688e2d536'
PERSONA_LOADER_SHA = 'c02890cbcbe60419d9834909789f3b6bc0f3ced0e48dfd187f28190de048416b'
PROMPT_SHA = '11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e'
PROFILE_SHA = 'b7b71396c267db80a44c2b32df4ba53ded7920ac952b2fbbfebafba349f85f55'
OUTPUT = ROOT/'candidate'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(relative, raw):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid owned output path')
    target = OUTPUT/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or not target.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Output must stay in the independent candidate')
    target.write_bytes(raw if isinstance(raw, bytes) else raw.encode('utf-8'))


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Pinned source integration point changed: '+old[:90])
    return source.replace(old, new, 1)


def function(source, class_name, name):
    tree = ast.parse(source)
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    node = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return textwrap.dedent(''.join(source.splitlines(True)[node.lineno-1:node.end_lineno]))+'\n'


def build_jobs(source):
    admit = function(source, 'BoardDialogueJobs', '_admit_text')
    admit = replace_once(admit, '    from common.spoken_input import prepare_spoken_input\n',
        '    self.character_pair.require_ready()\n    prepare_spoken_input = self.character_pair.speech.prepare\n')
    admit = replace_once(admit, '    from common.voice_wake import wake_request\n',
        '    wake_request = self.character_pair.speech.wake_request\n')
    route = function(source, 'BoardDialogueJobs', '_route')
    route = replace_once(route, '    from common.spoken_input import prepare_spoken_input\n',
        '    self.character_pair.require_ready()\n'
        '    if self.character_pair.speech.legacy_vocative(text):\n        return None, None\n'
        '    text = self.character_pair.speech.strip_address(text)\n'
        '    prepare_spoken_input = self.character_pair.speech.prepare\n')
    route = replace_once(route, '    from board.runtime.character import CHARACTER_NAME\n',
        '    CHARACTER_NAME = self.character_pair.identity.display_name\n')
    return ('"""Instance-bound copies of exactly two pinned methods.\n'
            'Only pair guards/address policy differ; core queues/ACK/PCM remain original.\n"""\n'
            'import re\nfrom board.runtime.audio.board_dialogue_jobs import BoardCapabilityNotReady\n\n'+admit+'\n'+route)


def build_business(source):
    init = function(source, 'GuiBoardBusiness', '__init__')
    init = replace_once(init, '    from tools.dialogue_host_ollama import fast_system_prompt\n', '')
    init = replace_once(init, '    from common.device_policy import MODEL_HINT\n', '')
    init = replace_once(init, '    self.recording = None\n',
        '    self.character_pair = stage.character_pair\n'
        '    if self.character_pair is None:\n        raise ValueError("Explicit candidate pair required")\n'
        "    self.face_readback_spec = value.get('face_readback')\n"
        '    self.recording = None\n')
    init = replace_once(init, "                'frontend_threads', 'visual_device_id', 'speaker'}",
        "                'frontend_threads', 'visual_device_id', 'speaker', 'face_readback'}")
    init = replace_once(init, 'asr=asr, system_prompt=fast_system_prompt()+MODEL_HINT,',
        'asr=asr, system_prompt=self.character_pair.selected_prompt,')
    # prepare_feedback happens before realization in the accepted constructor;
    # validate cue text without a premature readiness gate, then require ready
    # for later uses on the running same-pair owner.
    init = replace_once(init, '        self.runtime.jobs.prepare_feedback()\n',
        '        validate_feedback_character(feedback())\n'
        '        self.runtime.jobs.prepare_feedback()\n'
        '        self.runtime.jobs.feedback_provider = selected_feedback_provider(feedback, self.character_pair)\n')
    init = replace_once(init, '        self.runtime.initialize_clock(timeout=3.)\n',
        '        bind_runtime_pair(self.runtime, self.character_pair)\n'
        '        self.runtime.initialize_clock(timeout=3.)\n')
    speaker = function(source, 'GuiBoardBusiness', '_attach_speaker')
    speaker = replace_once(speaker, '    readback = FaceGalleryReadback.configured()',
        '    readback = load_private_face_readback(self.face_readback_spec)')
    return ('"""Candidate constructor; original factory/profile/guide methods are inherited.\n'
            'No runtime globals or main source are changed.\n"""\n'
            'from pathlib import Path\n'
            'from tools.board_business_gui import (GuiBoardBusiness, BoardBusinessConfig,\n'
            '    create_board_business_runtime, ConversationSelection, local_feedback_provider)\n'
            'from tools.yuki_business_candidate import (bind_runtime_pair, load_private_face_readback,\n'
            '    selected_feedback_provider, validate_feedback_character)\n\n'
            'class CandidateGuiBoardBusiness(GuiBoardBusiness):\n'+textwrap.indent(init, '    ')+
            '\n'+textwrap.indent(speaker, '    ')+
            '\n    def activate(self):\n        self.character_pair.require_ready()\n        return super().activate()\n\n'
            'def prepare_board_business(stage, value, aura):\n'
            '    return CandidateGuiBoardBusiness(stage, value, aura)\n')


def build_gtk(source):
    text = source
    text = replace_once(text, '        self.source_hashes = {}\n',
        '        self.source_hashes = {}\n'
        '        from tools.yuki_business_candidate import prepare_pair\n'
        '        self.character_pair = prepare_pair(config, AURA, self.source_hashes)\n'
        '        if self.character_pair is not None:\n'
        '            self.lines, self.character = self.character_pair.demo_lines, self.character_pair.identity.display_name\n')
    text = replace_once(text, "        self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py'] = hashlib.sha256(reuse.read_bytes()).hexdigest()",
        "        if self.character_pair is None:\n"
        "            self.source_hashes['../deliverables/2026-10-06_avatar_reuse/preview_script.py'] = hashlib.sha256(reuse.read_bytes()).hexdigest()")
    text = replace_once(text, '        self.native_pixels = self.native_video = None\n',
        '        self.native_pixels = self.native_video = None\n'
        '        self.native_yuki = self.yuki_portrait = self.native_yuki_config = None\n')
    text = replace_once(text, '            core = create_runtime_core(create_demo_core)\n',
        '            if self.character_pair is not None:\n'
        '                from tools.yuki_business_candidate import create_native_core\n'
        '                core = create_native_core()\n'
        '            else:\n                core = create_runtime_core(create_demo_core)\n')
    # Only the explicit candidate skips the old native pixel sink/preloaded PNGs.
    text = text.replace("            if config.get('native_avatar'):\n", "            if config.get('native_avatar') and self.character_pair is None:\n")
    text = replace_once(text, "            else:configure_board_rendering(core,self.tokens['colors']['panel_bg'])",
        "            elif self.character_pair is None:configure_board_rendering(core,self.tokens['colors']['panel_bg'])")
    text = replace_once(text, '                from tools.board_business_gui import prepare_board_business\n',
        '                if self.character_pair is not None:\n'
        '                    from tools.yuki_business_gui import prepare_board_business\n'
        '                else:\n                    from tools.board_business_gui import prepare_board_business\n')
    text = replace_once(text, '                controller_type=StreamingController\n',
        '                controller_type=StreamingController\n'
        '                if self.character_pair is not None:\n'
        '                    from tools.yuki_business_candidate import native_controller_type\n'
        '                    controller_type=native_controller_type()\n')
    text = replace_once(text, '            recording=recording_type(visual_controller,transcriber=self.transcriber,**recording_options)\n',
        "            if self.character_pair is not None and config.get('handsfree_dialogue'):\n"
        "                from tools.yuki_business_candidate import CandidateMonitorChoice\n"
        "                recording_options['monitor_settings']=CandidateMonitorChoice(self.character_pair)\n"
        '            recording=recording_type(visual_controller,transcriber=self.transcriber,**recording_options)\n')
    text = replace_once(text, "            visual_controller=controller_type(core,self.jobs,self.output)\n            if config.get('portrait_offload',{}).get('enabled'):",
        "            visual_controller=controller_type(core,self.jobs,self.output)\n"
        "            if self.character_pair is not None:\n"
        "                from tools.native_yuki_candidate import prepare_portrait\n"
        "                self.native_yuki,self.native_yuki_config=prepare_portrait(AURA,config['native_yuki'],self.output,self.source_hashes,self.character_pair)\n"
        "                visual_controller.portrait_offload=self.native_yuki\n"
        "            elif config.get('portrait_offload',{}).get('enabled'):")
    text = replace_once(text,
        "                .25 if self.preferences['economy'] else (1/24 if config.get('native_avatar') else config['tick_ms']/1000),native_video=self.native_video,visual_fps=config.get('stable_avatar_fps',8) if config.get('native_avatar') else None,performance_path=self.evidence_root/'render_performance.jsonl')",
        "                (1/24 if self.character_pair is not None else .25 if self.preferences['economy'] else (1/24 if config.get('native_avatar') else config['tick_ms']/1000)),native_video=self.native_video,visual_fps=16 if self.character_pair is not None else config.get('stable_avatar_fps',8) if config.get('native_avatar') else None,performance_path=self.evidence_root/'render_performance.jsonl')")
    text = replace_once(text, '            if self.board_business is not None:\n                self.board_business.activate()\n',
        '            if self.board_business is not None:\n'
        '                if self.character_pair is not None:\n'
        '                    self.character_pair.invalidators.append(self.controller.cancel)\n'
        '                    self.character_pair.on_ready(self.board_business.activate)\n'
        '                else:\n                    self.board_business.activate()\n')
    text = replace_once(text,
        "            self.controller.set_interval(.25 if self.preferences['economy'] else (1/24 if self.config.get('native_avatar') else interval/1000))",
        "            self.controller.set_interval(1/24 if self.character_pair is not None else .25 if self.preferences['economy'] else (1/24 if self.config.get('native_avatar') else interval/1000))")
    text = replace_once(text, '        self.portrait = gtk.DrawingArea() if self.native_video else gtk.Image()\n',
        '        if self.character_pair is not None:\n'
        '            from tools.native_yuki_candidate import create_gl_area\n'
        '            self.yuki_portrait=create_gl_area(self.native_yuki_config,self.native_yuki,self.character_pair)\n'
        "            self.yuki_portrait.set_size_request(self.rect['w'],self.rect['h'])\n"
        '            self.portrait=self.yuki_portrait\n'
        "            self.controls['portrait_toggle'].set_sensitive(False)\n"
        "            self.controls['portrait_toggle'].set_label('雪妃 · 本地16fps候选')\n"
        '        else:\n            self.portrait = gtk.DrawingArea() if self.native_video else gtk.Image()\n')
    text = replace_once(text, '        if kind == \'portrait_fps\':\n',
        "        if self.character_pair is not None and kind in ('portrait_fps','portrait_toggle'):\n"
        "            raise ValueError('雪妃候选固定16fps；切换须空闲退出并恢复完整配对')\n"
        "        if kind == 'portrait_fps':\n")
    text = replace_once(text, "        kind = data['type']\n",
        "        kind = data['type']\n"
        "        if self.character_pair is not None and kind in ('demo','speak'):\n"
        "            self.character_pair.require_ready()\n")
    text = replace_once(text, "            if not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:",
        "            if self.character_pair is None and not self.native_video and packet['rgb'] and packet['sequence'] != self.last_avatar_sequence:")
    text = replace_once(text, "            if self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')",
        "            if self.character_pair is not None:\n"
        "                from tools.native_yuki_candidate import display_status\n"
        "                state['avatar_display']=display_status(self.native_yuki)\n"
        "                state['character_pair']=self.character_pair.status()\n"
        "            elif self.native_video:state['avatar_display']=dict(self.native_video.read(),kind='native_sink_handoff')")
    text = replace_once(text,
        "        self.controls['portrait_toggle'].set_label('画面：电脑' if mode=='remote' else\n"
        "            '画面：电脑连接中，板卡显示' if portrait.get('selected') else '画面：板卡')",
        "        if self.character_pair is not None:\n"
        "            self.controls['portrait_toggle'].set_label('雪妃 · 本地16fps候选' if self.native_yuki.ready else '雪妃 · 渲染未就绪')\n"
        "        else:\n"
        "            self.controls['portrait_toggle'].set_label('画面：电脑' if mode=='remote' else\n"
        "                '画面：电脑连接中，板卡显示' if portrait.get('selected') else '画面：板卡')")
    text = replace_once(text, '    def cleanup(self):\n        self.close_identity_face_dialog()',
        "    def cleanup(self):\n"
        "        if getattr(self,'character_pair',None) is not None:\n"
        "            self.character_pair.fail('candidate_shutdown')\n"
        "        self.close_identity_face_dialog()")
    return text


def build_worker(source):
    text = replace_once(source,
        "                        fps=offload.target_fps if offload.status()['mode']=='remote' else 8",
        "                        fps=16 if getattr(offload,'candidate_fixed_native',False) else offload.target_fps if offload.status()['mode']=='remote' else 8")
    text = replace_once(text, '                    elif meta:\n',
        "                    elif meta and meta.get('_native_yuki'):\n"
        "                        # The single GTK/EGL sink owns all pixels.\n                        pass\n"
        "                    elif meta:\n")
    text = replace_once(text, '        performance=PerformanceRecorder(performance_path) if performance_path else None',
        "        performance=PerformanceRecorder(performance_path) if performance_path and not getattr(getattr(self.visual_owner,'portrait_offload',None),'candidate_fixed_native',False) else None")
    text = replace_once(text, '                    if not self.native_video or time.monotonic()-self.last_state_time>=.1:',
        "                    if (not self.native_video and not getattr(offload,'candidate_fixed_native',False)) or time.monotonic()-self.last_state_time>=.1:")
    return text


def main():
    bundle = INTEGRATION/'resume_bundle'/(FINGERPRINT+'.zip')
    native = NATIVE/'isolated-yuki-candidate16-resource-20261030.zip'
    if digest(native.read_bytes()) != NATIVE_SHA:
        raise ValueError('Reviewed native527-file package changed')
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        if manifest['source_fingerprint'] != FINGERPRINT:
            raise ValueError('Board business source bundle changed')
        baseline = {}
        for relative, expected in manifest['source_sha256'].items():
            raw = archive.read('code/'+relative)
            if digest(raw) != expected or not relative.endswith('.py'):
                raise ValueError('Board source manifest mismatch')
            baseline[relative] = raw
            write('aura/'+relative, raw)
        if len(baseline) != 310:
            raise ValueError('Expected exact310-Python business bundle')
    fresh = read_json(RUNTIME/'fresh_source/manifest.json')
    gui_manifest = read_json(RUNTIME/'gui_candidate_manifest.json')
    gui_entry = {row['path']: row for row in gui_manifest['entrypoints']}
    gtk_raw = (RUNTIME/'gui_candidate/aura/tools/board_avatar_gtk.py').read_bytes()
    profile_raw = (RUNTIME/'gui_candidate/aura/tools/profile_selection_ui.py').read_bytes()
    for name, raw in (('tools/board_avatar_gtk.py', gtk_raw), ('tools/profile_selection_ui.py', profile_raw)):
        if digest(raw) != gui_entry[name]['candidate_sha256']:
            raise ValueError('Latest reviewed GUI candidate changed')
        if gui_entry[name]['source_sha256'] != fresh['source_sha256'][name]:
            raise ValueError('GUI no longer derives from the independently acquired r3 source')
    worker_raw = (RUNTIME/'fresh_source/aura/tools/board_avatar_worker.py').read_bytes()
    if digest(worker_raw) != fresh['source_sha256']['tools/board_avatar_worker.py']:
        raise ValueError('Fresh worker snapshot changed')
    if worker_raw != baseline['tools/board_avatar_worker.py']:
        raise ValueError('Worker has conflicting newer bundle changes; manual rebase required')
    native_pins = {}
    with zipfile.ZipFile(native) as archive:
        native_manifest = json.loads(archive.read('manifest.json'))
        if len(archive.namelist()) != 527 or native_manifest['measured_fps'] != 16:
            raise ValueError('Incorrect native candidate version')
        for name, expected in native_manifest['files'].items():
            raw = archive.read(name)
            if digest(raw) != expected:
                raise ValueError('Native source/assets manifest mismatch')
            prefix = 'runtime-overlay/aura/'
            if name.startswith(prefix):
                relative = name[len(prefix):]
                if relative.startswith('assets/yuki/') or relative in ('tools/native_yuki.py','tools/egl_window.py','tools/libaura_yuki.so'):
                    write('aura/'+relative, raw)
                    native_pins[relative] = expected
        native_config = json.loads(archive.read('native_yuki.config.fragment.json'))['native_yuki']
    for source, target, expected in (
        ('board_persona_candidate.py', 'tools/board_persona_candidate.py', PERSONA_LOADER_SHA),
        ('persona.xuefei.candidate.json', 'config/persona.xuefei.candidate.json', PERSONA_SHA)):
        raw = (PERSONA/source).read_bytes()
        if digest(raw) != expected:
            raise ValueError('Frozen persona candidate changed')
        write('aura/'+target, raw)
        native_pins[target] = expected
    # Extract only the public accepted prompt function. Do not import the old
    # Windows host; it has unrelated parallel edits and is never executed here.
    host_tree = ast.parse(baseline['tools/dialogue_host_ollama.py'])
    prompt_node = next(node for node in host_tree.body if isinstance(node, ast.FunctionDef) and node.name == 'fast_system_prompt')
    prompt_source = ast.unparse(prompt_node)
    write('accepted_prompt_function.review.txt', prompt_source+'\n')
    # This expression is byte-exact with the frozen1032B board persona contract.
    speech_tree = ast.parse(baseline['common/spoken_input.py'])
    speech_hint = next(ast.literal_eval(n.value) for n in speech_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SPEECH_INPUT_HINT' for t in n.targets))
    device_tree = ast.parse(baseline['common/device_policy.py'])
    device_hint = next(ast.literal_eval(n.value) for n in device_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MODEL_HINT' for t in n.targets))
    old_prompt = ('你是桌面玩偶汐蓝，名字叫汐蓝的桌面玩偶助手。和面前的人连续闲聊。'
        '自然、亲近、像朋友接话，不复述用户，不用客服语气。通常一两句，最多48个中文字。'
        '用中文全角标点，自然停顿和语气词。记住上文，不虚构视觉。'+speech_hint+
        '输出JSON：reply_text为说出口的话，emotion为neutral/friendly/happy/sad之一，avatar_action为空字符串。'+device_hint)
    if len(old_prompt.encode()) != 1032 or digest(old_prompt.encode()) != 'ee62d5bacde4e3060dc53142191395c5b2abf766e08e147be991cbd857838a6b':
        raise ValueError('Accepted prompt baseline changed')
    write('aura/config/yuki_accepted_prompt.baseline.txt', old_prompt)
    pair = dict(schema='aura.yuki.business_pair.v1', native_package_sha256=NATIVE_SHA,
        accepted_prompt_sha256=digest(old_prompt.encode()), native_config=native_config, runtime_pins=native_pins,
        identity=dict(profile_version='xuefei-yuki-board-v1-candidate', display_name='雪妃', formal_name='御笠雪妃',
            romanized_name='YUKI MIKASA', render_profile_id='fuyukiss-yuki-freemote39-frame-mesh',
            render_source_profile_sha256=PROFILE_SHA, persona_config_sha256=PERSONA_SHA, prompt_sha256=PROMPT_SHA))
    pair_raw = json.dumps(pair, ensure_ascii=False, indent=2).encode()
    write('aura/config/yuki_pair.candidate.json', pair_raw)
    overrides = {
        'tools/board_avatar_gtk.py': build_gtk(gtk_raw.decode()),
        'tools/board_avatar_worker.py': build_worker(worker_raw.decode()),
        'tools/profile_selection_ui.py': profile_raw.decode(),
        'tools/yuki_jobs_candidate.py': build_jobs(baseline['board/runtime/audio/board_dialogue_jobs.py'].decode()),
        'tools/yuki_business_gui.py': build_business(baseline['tools/board_business_gui.py'].decode()),
    }
    for name in ('yuki_business_candidate.py', 'native_yuki_candidate.py'):
        source = (ROOT/'templates'/name).read_text(encoding='utf-8')
        overrides['tools/'+name] = source.replace('__PAIR_CONFIG_SHA256__', digest(pair_raw))
    for name, source in overrides.items():
        ast.parse(source)
        write('aura/'+name, source)
    fragment = dict(character_pair=dict(enabled=True, profile_version=pair['identity']['profile_version'],
            selection='config/yuki_pair.candidate.json', selection_sha256=digest(pair_raw)),
        native_yuki=native_config, native_avatar=True, stable_avatar_fps=16,
        portrait_offload=dict(enabled=False))
    write('yuki_business.config.fragment.json', json.dumps(fragment, ensure_ascii=False, indent=2))
    # Complete source package, with changed GTK/worker review diffs. Never apply
    # old native-overlay GTK wholesale to the newer business GUI.
    patches = []
    for name, old in (('tools/board_avatar_gtk.py', gtk_raw), ('tools/board_avatar_worker.py', worker_raw)):
        patches.append(''.join(difflib.unified_diff(old.decode().splitlines(True), overrides[name].splitlines(True),
            fromfile='reviewed-business/'+name, tofile='yuki-candidate/'+name)))
    write('business_native.patch', '\n'.join(patches))
    files = {p.relative_to(OUTPUT).as_posix(): dict(sha256=digest(p.read_bytes()), bytes=p.stat().st_size)
             for p in sorted(OUTPUT.rglob('*')) if p.is_file() and p.name != 'manifest.json'}
    unchanged = {name: digest(raw) for name, raw in baseline.items() if name not in overrides}
    result = dict(schema='aura.yuki.board_business.source_candidate.v1', status='SOURCE_ONLY_NOT_SELECTED',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_business_fingerprint=FINGERPRINT, source_archive_sha256=digest(bundle.read_bytes()),
        source_python_count=len(baseline), fresh_runtime=fresh['runtime'], fresh_boot=fresh['boot'],
        native_archive_sha256=NATIVE_SHA, native_archive_files=527, persona_config_sha256=PERSONA_SHA,
        prompt_utf8_bytes=978, prompt_sha256=PROMPT_SHA, pair_config_sha256=digest(pair_raw),
        production_entry_changed=False, services_called=False, devices_opened=False,
        business_data_included=False, model_weights_included=False, hardware_publisher='root_only',
        core_baseline_unchanged_sha256=unchanged, files=files)
    write('manifest.json', json.dumps(result, ensure_ascii=False, indent=2))
    target = ROOT/'yuki_business.source_candidate.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUTPUT.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(OUTPUT).as_posix())
    receipt = dict(status=result['status'], files=len(files)+1, python_files=sum(n.endswith('.py') for n in files),
        zip_sha256=digest(target.read_bytes()), zip_bytes=target.stat().st_size,
        manifest_sha256=digest((OUTPUT/'manifest.json').read_bytes()), pair_config_sha256=digest(pair_raw))
    (ROOT/'build_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
