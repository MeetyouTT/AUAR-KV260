PINNED='/home/root/aura-post-power-20261022/helpers/10261c1b5b2b7458/source.py'
EXPECTED='10261c1b5b2b745877121c90d940be80e67f91ae57a524ed2040a1f52af4f65c'
SECONDS=600
GROUP='postpower-retry-live'
SHORT_SCOPE='YUNET_RECOVERY50_GAP3_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED'
import ast,copy,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
def extend(raw, seconds):
    if seconds not in (600, 1800):
        raise ValueError('Reviewed windows are 600 and 1800 seconds')
    tree=ast.parse(raw)
    main=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'))
    guarded=next(n for n in main.body if isinstance(n,ast.Try) and n.finalbody)
    final_before=ast.dump(ast.Module(body=copy.deepcopy(guarded.finalbody),type_ignores=[]))
    measurement=next(n for n in guarded.body if isinstance(n,ast.For))
    samples=seconds//5+1
    class Window(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is int:
                if node.value==25:node.value=samples
                elif node.value==24:node.value=samples-1
            return node
    Window().visit(measurement)
    # Long supervision must not reserialize an ever-growing full history on
    # every checkpoint. Persist each numeric sample once; keep bounded live
    # progress and write the complete report at completion.
    original_save=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='save')
    bounded=ast.parse('''written_samples=[0]
def save():
    samples=report.get('samples',[])
    if len(samples)>written_samples[0]:
        with (folder/'observations.jsonl').open('a') as history:
            for sample in samples[written_samples[0]:]:
                history.write(json.dumps(sample,separators=(',',':'))+'\\n')
        written_samples[0]=len(samples)
    value=report
    if report.get('phase') in ('OBSERVING','RESTORING'):
        value=dict(report)
        value['samples']=samples if len(samples)<=2 else [samples[0],samples[-1]]
    value['sample_count']=len(samples)
    value['sample_history_file']='observations.jsonl'
    value['sample_history_rows_written']=written_samples[0]
    value['progress_checkpoint_bounded']=True
    atomic(folder/'deployment-result.json',(json.dumps(value,indent=2)+'\\n').encode())
''').body
    offset=main.body.index(original_save)
    main.body[offset:offset+1]=bounded
    for node in ast.walk(main):
        if isinstance(node,ast.Constant):
            if type(node.value) is int and node.value==120:node.value=seconds
            elif node.value=='--on-active=360s':node.value='--on-active='+str(seconds+600)+'s'
            elif isinstance(node.value,str):
                node.value=node.value.replace('_120S_','_'+str(seconds)+'S_').replace('_SHORT_', '_WINDOW_'+str(seconds)+'S_')
    tail=next(n for n in measurement.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
        and isinstance(n.test.left,ast.Name) and n.test.left.id=='index')
    tail.test.comparators[0]=ast.Constant(value=samples-1)
    assert ast.literal_eval(measurement.iter.args[0])==samples
    assert ast.dump(ast.Module(body=guarded.finalbody,type_ignores=[]))==final_before
    main.name='long_trial';ast.fix_missing_locations(main)
    return main
p=Path(PINNED);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
source=Path(sys._getframe().f_code.co_filename).resolve();sha=hashlib.sha256(source.read_bytes()).hexdigest()
folder=Path('/home/root/aura-dpu-vision-20261021/postpower-long-launches')/sha[:16]
folder.mkdir(parents=True,exist_ok=True)
if os.environ.get('AURA_RUN_POSTPOWER_LONG')=='1':
 spec=importlib.util.spec_from_file_location('_reviewed_short_trial',p)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 node=extend(raw,SECONDS)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),module.__dict__)
 try:module.long_trial();result={'finished':True,'scope':'Read the latest '+GROUP+' deployment-result for actual outcome'}
 except Exception as exc:result={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
 (folder/'launch-result.json').write_text(json.dumps(result,indent=2)+'\n')
else:
 assert not (folder/'launch-result.json').exists()
 reports=sorted((Path('/home/root/aura-dpu-vision-20261021')/GROUP).glob('*/deployment-result.json'),key=lambda q:q.stat().st_mtime)
 assert reports
 previous=json.loads(reports[-1].read_text())
 assert previous['complete'] and previous['passed'] and previous['rollback_verified']
 required_scope=SHORT_SCOPE if SECONDS==600 else SHORT_SCOPE.replace('_120S_','_600S_')
 assert previous['scope']==required_scope
 unit='aura-postpower-long-'+sha[:16]
 out=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec='+str(SECONDS+300),
  '--setenv=AURA_RUN_POSTPOWER_LONG=1','/usr/bin/python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
 assert out.returncode==0,out.stdout.decode(errors='replace')
 print(json.dumps({'started':True,'unit':unit,'seconds':SECONDS,'source_sha256':sha,'rollback_seconds':SECONDS+600}))
