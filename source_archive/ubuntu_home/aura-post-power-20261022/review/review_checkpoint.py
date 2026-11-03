"""Review extracted controller save only, using temporary files and IO faults."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path('/home/ghmd/aura-post-power-20261022')
SHORT = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_combined_live_v3_20261022.py')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

class History:
    def __init__(self, owner, path): self.owner,self.path,self.file=owner,path,None
    def open(self, mode):
        if self.owner.failure=='open': raise OSError('injected history open failure')
        self.file=self.path.open(mode);return self
    def __enter__(self): return self
    def write(self, value):
        self.owner.calls+=1
        if self.owner.failure=='second_write' and self.owner.calls==2:
            raise OSError('injected second history write failure')
        return self.file.write(value)
    def __exit__(self,*args):
        self.file.close()
        if self.owner.failure=='close':raise OSError('injected history close failure')

class Folder:
    def __init__(self, path): self.path,self.failure,self.calls=path,None,0
    def __truediv__(self,name):
        return History(self,self.path/name) if name=='observations.jsonl' else self.path/name

def main():
    source=ROOT/'make_long_trial.py'; source_hash=sha(source)
    spec=importlib.util.spec_from_file_location('_review_checkpoint_builder',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=ast.parse(SHORT.read_bytes())
    oldmain=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    oldfinal=next(n.finalbody for n in oldmain.body if isinstance(n,ast.Try) and n.finalbody)
    transformed=module.extend(SHORT.read_bytes(),1800)
    newfinal=next(n.finalbody for n in transformed.body if isinstance(n,ast.Try) and n.finalbody)
    assert ast.dump(ast.Module(body=oldfinal,type_ignores=[]))==ast.dump(ast.Module(body=newfinal,type_ignores=[]))
    selected=[]
    for node in transformed.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='written_samples' for t in node.targets):selected.append(node)
        elif isinstance(node,ast.FunctionDef) and node.name=='save':selected.append(node)
    code=compile(ast.Module(body=selected,type_ignores=[]),'<extracted-save-only>','exec')
    cases={}
    def prepare(path,report):
        folder=Folder(path);namespace={'folder':folder,'report':report,'json':json}
        def atomic(target,data):target.write_bytes(data)
        namespace['atomic']=atomic;exec(code,namespace);return folder,namespace
    with tempfile.TemporaryDirectory() as name:
        root=Path(name)
        def location(label):
            path=root/label;path.mkdir();return path
        path=location('empty');folder,ns=prepare(path,{'phase':'RESTORING','samples':[]})
        ns['save']();empty=json.loads((path/'deployment-result.json').read_text())
        cases['empty_restoring']={'samples':empty['samples'],'sample_count':empty['sample_count'],
            'history_rows':empty['sample_history_rows_written'],'history_exists':(path/'observations.jsonl').exists()}
        path=location('normal');report={'phase':'OBSERVING','samples':[{'sequence':i} for i in range(12)]}
        folder,ns=prepare(path,report);ns['save']();ns['save']()
        first=json.loads((path/'deployment-result.json').read_text())
        report['phase']='RESTORING';report['error']='synthetic supervision failure';ns['save']()
        restoring=json.loads((path/'deployment-result.json').read_text())
        report['phase']='FINISHED';ns['save']();final=json.loads((path/'deployment-result.json').read_text())
        lines=[json.loads(line) for line in (path/'observations.jsonl').read_text().splitlines()]
        cases['normal_repeat_and_phase_boundaries']={'history_sequence':[row['sequence'] for row in lines],
            'observing_samples':len(first['samples']),'restoring_samples':len(restoring['samples']),
            'restoring_preserves_error':restoring['error'],'final_samples':len(final['samples']),
            'report_in_memory_samples':len(report['samples'])}
        assert [row['sequence'] for row in lines]==list(range(12))
        assert len(first['samples'])==len(restoring['samples'])==2 and len(final['samples'])==12
        for failure in ('open','second_write','close'):
            path=location(failure);folder,ns=prepare(path,{'phase':'RESTORING','samples':[{'sequence':i} for i in range(3)]})
            folder.failure=failure;raised=None
            try:ns['save']()
            except Exception as error:raised=type(error).__name__+': '+str(error)
            before=(path/'observations.jsonl').read_text().splitlines() if (path/'observations.jsonl').exists() else []
            folder.failure=None;ns['save']()
            after=[json.loads(line)['sequence'] for line in (path/'observations.jsonl').read_text().splitlines()]
            cases['history_'+failure]={'exception_propagated':raised,'rows_before_retry':len(before),
                'sequence_after_retry':after,'duplicates_after_retry':len(after)!=len(set(after)),
                'written_samples_after_retry':ns['written_samples'][0]}
        path=location('atomic');folder,ns=prepare(path,{'phase':'RESTORING','samples':[{'sequence':i} for i in range(3)]})
        def broken_atomic(*args):raise OSError('injected checkpoint atomic failure')
        ns['atomic']=broken_atomic;raised=None
        try:ns['save']()
        except Exception as error:raised=type(error).__name__+': '+str(error)
        ns['atomic']=lambda target,data:target.write_bytes(data);ns['save']()
        sequence=[json.loads(line)['sequence'] for line in (path/'observations.jsonl').read_text().splitlines()]
        cases['atomic_checkpoint_failure']={'exception_propagated':raised,'history_sequence_after_retry':sequence,
            'duplicates_after_retry':len(sequence)!=len(set(sequence))}
    assert sha(source)==source_hash,'Builder changed during review; rerun on final version'
    failures=[]
    if any(cases['history_'+name]['exception_propagated'] for name in ('open','second_write','close')):
        failures.append('New history IO failure propagates through RESTORING save before the existing rollback try; independent timer is still the fallback.')
    if any(cases['history_'+name]['duplicates_after_retry'] for name in ('second_write','close')):
        failures.append('Partially successful append/close followed by save retry duplicates history rows; written_samples advances only after full close.')
    result={'schema':'aura-long-checkpoint-review-1','reviewed_utc':datetime.now(timezone.utc).isoformat(),
        'review_passed':not failures,'blocking_findings':failures,'builder_sha256':source_hash,
        'short_helper_sha256':sha(SHORT),'restore_finalizer_ast_identical':True,
        'scope':'Extracted save function and pure AST only; temporary files/fault injection, no helper/board/systemd execution.',
        'cases':cases,'remaining_inherited_limit':'Atomic checkpoint failure also propagates as in original save; no new behavior is claimed fixed.',
        'evidence_script_sha256':sha(Path(__file__))}
    target=ROOT/'review/long-checkpoint-review.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'review_passed':not failures,'blocking_findings':len(failures),'report':str(target),'sha256':sha(target)}))

if __name__=='__main__':main()
