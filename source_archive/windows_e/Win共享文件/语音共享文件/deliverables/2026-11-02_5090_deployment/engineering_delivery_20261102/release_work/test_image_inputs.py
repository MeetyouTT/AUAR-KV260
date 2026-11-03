from common import *
import tempfile,importlib.util,contextlib,io
spec=importlib.util.spec_from_file_location('auar_stage',str(ROOT/'board/scripts/stage.py'))
stage=importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
with tempfile.TemporaryDirectory(prefix='auar-image-') as tmp:
    d=Path(tmp);mount=d/'mount';mount.mkdir()
    p=mount/'file';p.write_bytes(b'public fixture\n');w=mount/'wrong';w.write_bytes(b'different')
    out={}; expected={a:sha(p) for a in ['/file','/wrong','/absent']}
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):
        n=stage.copy_image_inputs(mount,expected,lambda s,dest:out.update({dest:s.read_bytes()}))
    assert out=={'/file':p.read_bytes()} and n==1
    assert 'different SHA-256: /wrong' in capture.getvalue() and 'image input missing: /absent' in capture.getvalue()
    try: stage.copy_image_inputs(Path(d.anchor),{},None)
    except ValueError:pass
    else:raise AssertionError('accepted host root')
save(QA/'image_inputs_test.json',dict(status='PASS',cases=['exact copy','mismatched bytes excluded','missing file reported','host root rejected'],fixed_allowlist=len(load(ROOT/'board/config/image_inputs.json')['files']),device_access=False))
print('PASS image-root copy, corruption/missing and host-root rejection')
