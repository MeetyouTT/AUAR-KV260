"""Verify this report package and reproduce the bundled Skill without board/model IO."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    if out.exists(): parser.error('--out must name a new directory')
    out.mkdir(parents=True)
    status={'status':'FAIL','scope':'report_evidence_and_offline_generated_skill',
            'python':platform.python_version(),'board_verified':False,'full_system_reproduced':False}
    try:
        source_manifest=json.loads((ROOT/'source_index.json').read_text(encoding='utf8'))
        checked=0
        for row in source_manifest['entries']:
            rel=row.get('report_copy')
            if not rel: continue
            p=(ROOT/rel).resolve()
            try:
                p.relative_to(ROOT.resolve())
            except ValueError:
                raise ValueError('source path leaves package')
            if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']: raise ValueError('evidence mismatch: '+rel)
            checked+=1
        status['evidence_files_checked']=checked
        skill=ROOT/'skill/pynq-contract-testgen'
        manifest=json.loads((ROOT/'attachments/validation/skill_source_manifest.json').read_text(encoding='utf8'))
        for rel,wanted in manifest.items():
            if hashlib.sha256((skill/rel).read_bytes()).hexdigest()!=wanted:
                raise ValueError('skill source mismatch: '+rel)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
        steps=[('unit_tests',[sys.executable,'-B','-m','unittest','discover','-s','tests','-v']),
               ('examples',[sys.executable,'-B','scripts/reproduce.py','--out',str(out/'examples')])]
        for name,cmd in steps:
            p=subprocess.run(cmd,cwd=skill,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace')
            (out/(name+'.log')).write_text(p.stdout,encoding='utf8')
            if p.returncode: raise RuntimeError(name+' failed; see log')
        summary=json.loads((out/'examples/summary.json').read_text(encoding='utf8'))
        if summary['status']!='PASS' or summary['board_verified'] or summary['pynq_imported']:
            raise ValueError('invalid offline validation level')
        status.update(status='PASS',examples=summary['examples'],skill_source_files_checked=len(manifest))
    except Exception as exc:
        status['error']=type(exc).__name__+': '+str(exc)
    (out/'summary.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(status,ensure_ascii=False))
    return 0 if status['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())
