"""Prove the code-only handover imports and decodes with the real external model."""
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

WORK=Path(__file__).resolve().parent
inventory=json.loads((WORK/'inventory.json').read_text())
archive=Path(inventory['complete_code_archive'])
model=Path('/home/ghmd/Win共享文件/共享文件夹/aura/models/asr')
python='/home/ghmd/aura-asr-integration-20261016/host-env/bin/python'
with tempfile.TemporaryDirectory(prefix='aura-asr-code-only-') as folder:
    root=Path(folder)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
        z.extractall(root)
    code=('import json,runpy,sys; '
          'namespace=runpy.run_path(%r); engine=namespace["Paraformer"](%r); '
          'print(json.dumps({"model_id":engine.model_id,"probe_text":engine.probe_text,'
          '"asr_source":sys.modules["board.runtime.audio.asr"].__file__,'
          '"wire_source":sys.modules["common.asr_wire"].__file__},ensure_ascii=False))')%(
              str(root/'tools/asr_server.py'),str(model))
    process=subprocess.run([python,'-I','-B','-c',code],cwd=folder,stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,text=True,timeout=30)
    assert process.returncode==0,process.stderr[-3000:]
    decoded=json.loads(process.stdout)
    for key in ('asr_source','wire_source'):Path(decoded[key]).relative_to(root)
    assert decoded['model_id']=='paraformer-f36a0433bcf096bd6d6f11b8' and decoded['probe_text']
report={'status':'PASS_ISOLATED_CODE_ARCHIVE_ACTUAL_MODEL','archive':str(archive),
        'source_files':8,'model_weights_packaged':False,'model_source':str(model),
        'actual_probe':decoded,'windows_runtime_verified':False,'lan_verified':False}
(WORK/'isolated_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
