"""Pinned source-only process-gate extension; no board or model access."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'production_frontend_capacity_candidate/after/aura'
EXPECTED = {
    'tools/production_board_business_gui.py':'1d4cdb9dd9179476e34fd8b9574b497615f597dbbd082d873d3fdedb619e391d',
    'tools/production_frontend_selection.py':'c9d095bb722a8dd0096ffdb373910ae364e0e4cd12dcb4d0fdc20ac55bf627a2'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Pinned source anchor changed')
    return text.replace(before, after, 1)


def build():
    sources = {}
    for name, expected in EXPECTED.items():
        raw = (BASE / name).read_bytes()
        if sha(raw) != expected:
            raise ValueError('Frontend base source pin changed')
        sources[name] = raw.decode('utf-8')
    text = sources['tools/production_frontend_selection.py']
    text = replace_once(text,
        "    priority=value.get('capture_priority_nice',0)\n",
        "    priority=value.get('capture_priority_nice',0)\n"
        "    process=value.get('frontend_process',False)\n"
        "    if type(process) is not bool or process and (optimization!='baseline' or type(value.get('frontend_threads',1)) is not int or value.get('frontend_threads',1)!=1):\n"
        "        raise ValueError('Process frontend is explicit baseline with one model thread')\n")
    text = replace_once(text,
        'def create_frontend_pool(directory,*,optimization,num_threads=1):\n'
        '    from board.runtime.audio.board_capture import BoardFrontendPool\n',
        'def create_frontend_pool(directory,*,optimization,num_threads=1,frontend_process=False):\n'
        '    from board.runtime.audio.board_capture import BoardFrontendPool\n'
        '    if type(frontend_process) is not bool:\n'
        "        raise ValueError('Explicit process frontend boolean required')\n"
        '    if frontend_process:\n'
        "        if optimization!='baseline' or type(num_threads) is not int or num_threads!=1:\n"
        "            raise ValueError('Process frontend requires baseline/one model thread')\n"
        '        from board.runtime.audio.board_frontend_process import BoardProcessSpeechGate\n'
        '        return BoardFrontendPool(BoardProcessSpeechGate(directory,num_threads=1))\n')
    sources['tools/production_frontend_selection.py'] = text
    text = sources['tools/production_board_business_gui.py']
    text = replace_once(text,
        "'frontend_optimization', 'capture_priority_nice'}\n",
        "'frontend_optimization', 'capture_priority_nice', 'frontend_process'}\n")
    text = replace_once(text,
        '        self.frontend_optimization,self.capture_priority_nice=validate_frontend_options(value)\n',
        '        self.frontend_optimization,self.capture_priority_nice=validate_frontend_options(value)\n'
        "        self.frontend_process=value.get('frontend_process',False)\n")
    text = replace_once(text,
        "                                            num_threads=value.get('frontend_threads', 1))\n",
        "                                            num_threads=value.get('frontend_threads', 1),frontend_process=self.frontend_process)\n")
    # Cover every failure after the owned child is constructed, including the
    # config constructor that preceded the original runtime-only try block.
    begin = text.index('        self.frontend = create_frontend_pool(')
    end = text.index('        try:\n            self.runtime =', begin)
    setup = ''.join('    ' + line for line in text[begin:end].splitlines(keepends=True))
    text = text[:begin] + '        try:\n' + setup + text[end + len('        try:\n'):]
    text = replace_once(text,
        '    def activate(self):\n',
        '    def close(self):\n'
        '        # A lease close cancels one turn; only GUI shutdown retires this model child.\n'
        "        pool=getattr(self,'frontend',None)\n"
        "        shutdown=getattr(getattr(pool,'gate',None),'shutdown',None)\n"
        '        if callable(shutdown):\n'
        "            recording=getattr(self,'recording',None)\n"
        "            if recording is not None and not self.worker_owned and not recording.closed:\n"
        '                recording.close()\n'
        '            pool.close()\n'
        '            if not shutdown():\n'
        "                raise RuntimeError('frontend_worker_shutdown_incomplete')\n"
        '        return super().close()\n\n'
        '    def activate(self):\n')
    sources['tools/production_board_business_gui.py'] = text
    for name, text in sources.items():
        output = ROOT / 'after/aura' / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(text.encode('utf-8'))
    files = {}
    for path in sorted((ROOT / 'after/aura').rglob('*.py')):
        raw = path.read_bytes()
        ast.parse(raw.decode('utf-8'), feature_version=(3,9))
        name = path.relative_to(ROOT / 'after/aura').as_posix()
        files['aura/' + name] = dict(sha256=sha(raw), bytes=len(raw), before_sha256=EXPECTED.get(name))
    manifest = dict(schema='aura.frontend-process-overlay.v1', files=files,
        hardware_executed=False, selection=dict(frontend_process=True,
            frontend_optimization='baseline',frontend_threads=1,capture_priority_nice=-10),
        default_frontend_process=False)
    raw = (json.dumps(manifest,indent=2) + '\n').encode('utf-8')
    (ROOT / 'overlay_manifest.json').write_bytes(raw)
    with zipfile.ZipFile(ROOT / 'frontend_process.overlay.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            item = zipfile.ZipInfo(name,(2026,10,30,0,0,0))
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item,(ROOT / 'after' / name).read_bytes())
    (ROOT / 'extra_source_map.json').write_text(json.dumps({name:str(ROOT / 'after' / name)
        for name in sorted(files)},indent=2) + '\n',encoding='utf-8')
    print(json.dumps(dict(files=files,manifest_sha256=sha(raw),
        zip_sha256=sha((ROOT / 'frontend_process.overlay.zip').read_bytes()))))


if __name__ == '__main__':
    build()
