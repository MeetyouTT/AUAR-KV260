"""Derive rev3 from frozen rev2; no board/model/GUI operations."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'production_frontend_process_candidate/after/aura'
PINS={
 'board/runtime/audio/board_frontend_process.py':'8b5db6681e7ae1dd7040ab9aa2247ba59efb515286feebed5956034a6993dd63',
 'tools/production_board_business_gui.py':'911ee09873a84d4c4c176e3798749a1813bee4d42dd05c6fc0ed108c6c7cfe2a',
 'tools/production_frontend_selection.py':'bfef18d9ccd06e39357f5f375e6dc4c1d5d187bed51787e78206018658bb1a1b'}

def sha(data):return hashlib.sha256(data).hexdigest()
def once(text,before,after):
    if text.count(before)!=1:raise ValueError('Frozen rev2 anchor changed')
    return text.replace(before,after,1)

def build():
    source={}
    for name,expected in PINS.items():
        raw=(BASE/name).read_bytes()
        if sha(raw)!=expected:raise ValueError('Frozen rev2 source pin changed')
        source[name]=raw.decode('utf-8')
    text=source['board/runtime/audio/board_frontend_process.py']
    text=once(text,'_KINDS = (FRAME, RESET_DENOISER, RESET_VAD, STOP, HELLO)\n',
        '_KINDS = (FRAME, RESET_DENOISER, RESET_VAD, STOP, HELLO) + tuple(range(6,12))\n'
        'MODE_BUSY = 6\n\n'
        'def _payload_limit(kind):\n'
        '    if kind == (9 | 128):return 640000 + 4096 + 4\n'
        '    if kind in tuple(k | 128 for k in range(7,12)):return 4096\n'
        '    return MAX_PAYLOAD\n')
    text=once(text,'class _Cancelled(InterruptedError):\n',
        "class FrontendModeBusy(ValueError):\n    pass\n\n\nclass _Cancelled(InterruptedError):\n")
    text=once(text,'if len(payload) > MAX_PAYLOAD:', 'if len(payload) > _payload_limit(kind):')
    text=once(text,'reserved or size > MAX_PAYLOAD','reserved or size > _payload_limit(kind)')
    tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='serve')
    lines=text.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno]=[
        'def serve(stream, gate_factory, *, apply_priority=None, clock=time.monotonic,\n',
        '          thread_clock=time.thread_time, priority_reader=None, auto_capture_factory=None):\n',
        '    from board.runtime.audio.board_frontend_auto import serve_shared\n',
        '    return serve_shared(stream,gate_factory,apply_priority=apply_priority,clock=clock,\n',
        '        thread_clock=thread_clock,priority_reader=priority_reader,auto_capture_factory=auto_capture_factory)\n']
    text=''.join(lines)
    text=once(text,'        if code:\n            raise FrontendProcessError(',
        "        if code == MODE_BUSY:\n            raise FrontendModeBusy('frontend_auto_mode_busy')\n"
        '        if code:\n            raise FrontendProcessError(')
    text=once(text,'def _rpc(self, kind, *, payload=b\'\', generation=None, cancellable=False, timeout=None):',
        'def _rpc(self, kind, *, payload=b\'\', generation=None, cancellable=False, timeout=None, decoder=None):')
    text=once(text,'                    decision = self._accept(data)\n',
        '                    decision = decoder(data) if decoder is not None else self._accept(data)\n')
    text=once(text,'        self._rpc(kind)\n        if kind == RESET_VAD:',
        '        try:\n            self._rpc(kind)\n'
        '        except FrontendModeBusy:\n'
        '            if kind == RESET_DENOISER:self._generation -= 1\n'
        '            raise\n'
        '        if kind == RESET_VAD:')
    text=once(text,'    def shutdown(self, timeout=2.):','    def shutdown(self, timeout=8.):')
    text=once(text,'self._rpc(STOP, timeout=min(.5, timeout))','self._rpc(STOP, timeout=min(6., timeout))')
    text=once(text,'def _worker_main():\n',
        'def _worker_main():\n'
        "    if len(sys.argv)>1 and sys.argv[1]=='--exec-arecord-parent':\n"
        '        from board.runtime.audio.board_frontend_auto import exec_arecord_parent\n'
        "        if len(sys.argv)<6 or sys.argv[3]!='--':raise SystemExit(2)\n"
        '        exec_arecord_parent(int(sys.argv[2]),sys.argv[4:])\n'
        '        return\n')
    source['board/runtime/audio/board_frontend_process.py']=text
    text=source['tools/production_frontend_selection.py']
    text=once(text,"    process=value.get('frontend_process',False)\n",
        "    process=value.get('frontend_process',False)\n"
        "    capture_process=value.get('frontend_capture_process',False)\n"
        '    if type(capture_process) is not bool or capture_process and process is not True:\n'
        "        raise ValueError('Automatic capture process requires explicit frontend process')\n")
    text+='''\n\ndef automatic_capture_recording_options(gui, options):
    from board.runtime.audio.board_frontend_auto import RemoteAutomaticCapture
    def speech_start_ready(capture_id):
        recording=gui.recording
        return bool(recording is not None and ((recording.monitor_owned and recording.monitor_key) or recording.auto_enabled)
            and recording.listen_id==capture_id and recording.capture is not None
            and getattr(recording.capture,'capture_id',None)==capture_id)
    result=dict(options)
    result['auto_capture_factory']=lambda *args,**kwargs:RemoteAutomaticCapture(*args,
        frontend_pool=gui.frontend,speech_start_ready=speech_start_ready,**kwargs)
    return result
'''
    source['tools/production_frontend_selection.py']=text
    text=source['tools/production_board_business_gui.py']
    text=once(text,"'capture_priority_nice', 'frontend_process'}\n",
        "'capture_priority_nice', 'frontend_process', 'frontend_capture_process'}\n")
    text=once(text,"        self.frontend_process=value.get('frontend_process',False)\n",
        "        self.frontend_process=value.get('frontend_process',False)\n"
        "        self.frontend_capture_process=value.get('frontend_capture_process',False)\n")
    text=once(text,
        '        if self.capture_priority_nice==0:\n'
        '            return super().recording_options(visual_controller)\n'
        '        from tools.production_frontend_selection import priority_recording_options\n'
        '        return priority_recording_options(self,visual_controller)\n',
        '        if self.capture_priority_nice==0:\n'
        '            options=super().recording_options(visual_controller)\n'
        '        else:\n'
        '            from tools.production_frontend_selection import priority_recording_options\n'
        '            options=priority_recording_options(self,visual_controller)\n'
        '        if self.frontend_capture_process:\n'
        '            from tools.production_frontend_selection import automatic_capture_recording_options\n'
        '            options=automatic_capture_recording_options(self,options)\n'
        '        return options\n')
    source['tools/production_board_business_gui.py']=text
    for name,text in source.items():
        output=ROOT/'after/aura'/name;output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(text.encode('utf-8'))
    files={}
    for path in sorted((ROOT/'after/aura').rglob('*.py')):
        raw=path.read_bytes();ast.parse(raw.decode('utf-8'),feature_version=(3,9))
        name=path.relative_to(ROOT/'after/aura').as_posix()
        files['aura/'+name]=dict(sha256=sha(raw),bytes=len(raw),before_sha256=PINS.get(name))
    manifest=dict(schema='aura.frontend-complete-automatic-process.rev3',files=files,
        defaults=dict(frontend_process=False,frontend_capture_process=False),hardware_executed=False)
    raw=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    (ROOT/'overlay_manifest.json').write_bytes(raw)
    with zipfile.ZipFile(ROOT/'frontend_capture_process.overlay.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,(ROOT/'after'/name).read_bytes())
    (ROOT/'extra_source_map.json').write_text(json.dumps({name:str(ROOT/'after'/name)
        for name in sorted(files)},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(files=files,manifest_sha256=sha(raw),
        zip_sha256=sha((ROOT/'frontend_capture_process.overlay.zip').read_bytes()))))

if __name__=='__main__':build()
