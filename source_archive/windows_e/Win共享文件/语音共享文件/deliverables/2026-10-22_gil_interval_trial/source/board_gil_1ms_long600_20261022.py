"""Extend the pinned 1ms dual-model trial; retain the exact restore finalizer."""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

PINNED=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/cd64535922ae87f2/source.py')
EXPECTED='cd64535922ae87f278913c3c43dec344dcb8d14bccfa29bde537145911402316'
raw=PINNED.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
source=Path(sys._getframe().f_code.co_filename).resolve();sha=hashlib.sha256(source.read_bytes()).hexdigest()
record=Path('/home/root/aura-dpu-vision-20261021/gil-long-launches')/sha[:16]
record.mkdir(parents=True,exist_ok=True)

if os.environ.get('AURA_GIL_LONG_RUN')=='1':
    spec=importlib.util.spec_from_file_location('_pinned_gil_trial',PINNED)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=ast.parse(raw)
    main=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'))
    main_try=next(n for n in main.body if isinstance(n,ast.Try) and n.finalbody)
    restore_before=ast.dump(ast.Module(body=copy.deepcopy(main_try.finalbody),type_ignores=[]))
    measurement=next(n for n in main_try.body if isinstance(n,ast.For))
    class Window(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is int:
                if node.value==25:node.value=121
                elif node.value==24:node.value=120
            return node
    Window().visit(measurement)
    for node in ast.walk(main):
        if isinstance(node,ast.Constant):
            if type(node.value) is int and node.value==120:node.value=600
            elif node.value=='--on-active=360s':node.value='--on-active=1200s'
            elif node.value=='GIL_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED':node.value='GIL_1MS_DUAL_MODEL_600S_ALWAYS_RESTORED'
            elif node.value=='GIL_1MS_SHORT_WINDOW_ONLY_NOT_ROOT_CAUSE_OR_LONG_STABILITY_PROOF':
                node.value='GIL_1MS_600S_WINDOW_NOT_30MIN_THREE_MODEL_OR_ROOT_CAUSE_PROOF'
    # Window() sets the final sample index to 120, which must stay 120 rather
    # than the elapsed-time threshold 600. Set that one comparison explicitly.
    tail=next(n for n in measurement.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
        and isinstance(n.test.left,ast.Name) and n.test.left.id=='index')
    tail.test.comparators[0]=ast.Constant(value=120)
    assert ast.dump(ast.Module(body=main_try.finalbody,type_ignores=[]))==restore_before
    main.name='long_trial';ast.fix_missing_locations(main)
    exec(compile(ast.Module(body=[main],type_ignores=[]),str(source),'exec'),module.__dict__)
    try:
        module.long_trial();result={'finished':True,'scope':'Read latest gil-switch-live report for actual outcome'}
    except Exception as exc:result={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
    (record/'launch-result.json').write_text(json.dumps(result,indent=2)+'\n')
else:
    assert not (record/'launch-result.json').exists()
    reports=sorted(Path('/home/root/aura-dpu-vision-20261021/gil-switch-live').glob('*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
    assert reports
    result=json.loads(reports[-1].read_text())
    assert result['passed'] and result['complete'] and result['rollback_verified']
    assert result['scope']=='GIL_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED'
    assert result['experimental_process_setting']['actual_start_seconds']==.001
    unit='aura-gil-1ms-600-'+sha[:16]
    out=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=900',
        '--setenv=AURA_GIL_LONG_RUN=1','/usr/bin/python3','-B',str(source)],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    assert out.returncode==0,out.stdout.decode(errors='replace')
    print(json.dumps({'started':True,'unit':unit,'source_sha256':sha,'seconds':600,
        'independent_rollback_seconds':1200,'native_sources_unchanged':True}),flush=True)
