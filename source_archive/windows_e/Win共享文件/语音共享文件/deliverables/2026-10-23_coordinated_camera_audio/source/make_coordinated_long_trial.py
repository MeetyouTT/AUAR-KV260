"""Extend a reviewed short trial while preserving its restoration AST exactly."""
import argparse
import ast
import copy
import hashlib
import json
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
            elif node.value=='--on-active=600s':node.value='--on-active='+str(seconds+900)+'s'
            elif isinstance(node.value,str):
                node.value=node.value.replace('_120S_','_'+str(seconds)+'S_').replace('_SHORT_', '_WINDOW_'+str(seconds)+'S_')
    tail=next(n for n in measurement.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
        and isinstance(n.test.left,ast.Name) and n.test.left.id=='index')
    tail.test.comparators[0]=ast.Constant(value=samples-1)
    assert ast.literal_eval(measurement.iter.args[0])==samples
    assert ast.dump(ast.Module(body=guarded.finalbody,type_ignores=[]))==final_before
    main.name='long_trial';ast.fix_missing_locations(main)
    return main


def build(short, remote, group, seconds):
    raw=short.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    tree=ast.parse(raw);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    report=next(n.value for n in main.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='report')
    scope=next(v.value for k,v in zip(report.keys,report.values) if isinstance(k,ast.Constant) and k.value=='scope')
    own=ast.parse(Path(__file__).read_text());function=next(n for n in own.body if isinstance(n,ast.FunctionDef) and n.name=='extend')
    code=ast.get_source_segment(Path(__file__).read_text(),function)+'\n'
    prefix='PINNED='+repr(remote)+'\nEXPECTED='+repr(digest)+'\nSECONDS='+repr(seconds)+'\nGROUP='+repr(group)+'\nSHORT_SCOPE='+repr(scope)+'\n'
    code=prefix+'import ast,copy,hashlib,importlib.util,json,os,subprocess,sys\nfrom pathlib import Path\n'+code
    code+='''p=Path(PINNED);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
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
 (folder/'launch-result.json').write_text(json.dumps(result,indent=2)+'\\n')
else:
 assert not (folder/'launch-result.json').exists()
 reports=sorted((Path('/home/root/aura-dpu-vision-20261021')/GROUP).glob('*/deployment-result.json'),key=lambda q:q.stat().st_mtime)
 assert reports
 previous=json.loads(reports[-1].read_text())
 assert previous['complete'] and previous['passed'] and previous['rollback_verified']
 required_scope=SHORT_SCOPE if SECONDS==600 else SHORT_SCOPE.replace('_120S_','_600S_')
 assert previous['scope']==required_scope
 unit='aura-postpower-long-'+sha[:16]
 out=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec='+str(SECONDS+600),
  '--setenv=AURA_RUN_POSTPOWER_LONG=1','/usr/bin/python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
 assert out.returncode==0,out.stdout.decode(errors='replace')
 print(json.dumps({'started':True,'unit':unit,'seconds':SECONDS,'source_sha256':sha,'rollback_seconds':SECONDS+900}))
'''
    ast.parse(code);key=hashlib.sha256(code.encode()).hexdigest()[:8]
    target=Path('/home/ghmd/aura-identity-dpu-check-20261018')/('board_'+group.replace('-','_')+'_'+str(seconds)+'_'+key+'_20261023.py')
    if target.exists():assert target.read_text()==code
    else:target.write_text(code)
    modified=extend(raw,seconds)
    validation={'helper':str(target),'sha256':hashlib.sha256(code.encode()).hexdigest(),'pinned_short_sha256':digest,
        'remote_short':remote,'seconds':seconds,'samples':seconds//5+1,'last_sample_index':seconds//5,
        'runtime_max_seconds':seconds+600,'rollback_seconds':seconds+900,'restore_finalizer_ast_identical':True}
    Path(__file__).with_name('coordinated50-long-'+group+'-'+str(seconds)+'-manifest.json').write_text(json.dumps(validation,indent=2)+'\n')
    return validation


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('short',type=Path);p.add_argument('--remote',required=True)
    p.add_argument('--group',required=True);p.add_argument('--seconds',type=int,choices=(600,1800),required=True)
    a=p.parse_args();print(json.dumps(build(a.short,a.remote,a.group,a.seconds)))
