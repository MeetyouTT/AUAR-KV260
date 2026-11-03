#!/usr/bin/env python3
"""Collect new and historical evidence, review links/names, and package without board access."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT/'payload'
DFX = Path('/home/ghmd/kv260-dfx-manager-repair-20261002')
ZOCL = Path('/home/ghmd/kv260-overlay-repair-20261002')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1048576),b''):
            h.update(block)
    return h.hexdigest()


def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def copy(source,dest):
    if dest.exists():
        if sha(source)!=sha(dest):
            raise RuntimeError('Refusing to overwrite different evidence: '+str(dest))
        return
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,dest)
    if sha(source)!=sha(dest):
        raise RuntimeError('Evidence copy mismatch')


def main():
    summary={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'passed':False,'board_access_this_turn':False,'permanent_installation':False,
             'new_zocl_full_build_executed':False,'new_kernel_full_build_executed':False,
             'sustained_board_test_executed':False,'new_fpga_build_executed':False,
             'checks':[],'limitations':[
                 'No fresh board state; UART currently absent',
                 'New DFX ELF is host/ABI checked, not board verified',
                 'New kernel/ZOCL wrapper not exercised through a complete build',
                 'No clean-machine tool installation or full AURA submission reproduction',
                 'No permanent enablement, PWM, or sustained board validation',
                 'Full visible chat export and latest contest scoring details remain pending']}
    entries=[]

    def command(name,argv,expected=0):
        process=subprocess.run(list(map(str,argv)),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        entry={'name':name,'argv':list(map(str,argv)),'exit_code':process.returncode,
               'expected_exit_code':expected,'stdout':process.stdout,'stderr':process.stderr}
        entries.append(entry)
        if process.returncode!=expected:
            raise RuntimeError('Entry validation failed: '+name)
        return process.stdout

    try:
        for suffix in ['a','b','c']:
            work=Path('/home/ghmd/kv260-runtime-reproduce-20261003'+suffix)
            for path in sorted((work/'logs').rglob('*')):
                if path.is_file():
                    copy(path,PAYLOAD/'evidence/reproduction'/suffix/path.relative_to(work/'logs'))
            state=json.loads((work/'logs/build_dfx/status.json').read_text())
            if not state['passed'] or not state.get('offline_image_abi_checked'):
                raise RuntimeError('DFX reproduction did not pass: '+suffix)
            summary.setdefault('dfx_reproductions',[]).append({
                'workspace_suffix':suffix,'passed':True,
                'source_state':json.loads((work/'logs/prepare_sources/status.json').read_text()),
                'artifacts':state['artifacts']})
        work=Path('/home/ghmd/kv260-runtime-reproduce-20261003c')
        for path in sorted((work/'artifacts/dfx').iterdir()):
            copy(path,PAYLOAD/'host_rebuild/dfx'/path.name)
        for path in sorted((ZOCL/'evidence/build').rglob('*')):
            if path.is_file() and path.suffix in ('.log','.json','.config','.diff','.py'):
                copy(path,PAYLOAD/'evidence/kernel_build'/path.relative_to(ZOCL/'evidence/build'))
        for name in ['tools_validation.json','tools_validation_host.json','rebuild_comparison.json']:
            copy(ROOT/'evidence'/name,PAYLOAD/'evidence'/name)
        tools=json.loads((ROOT/'evidence/tools_validation_host.json').read_text())
        if not tools['passed']:
            raise RuntimeError('Offline tools validation failed')
        summary['offline_fixture_tests_passed']=len(tools['tests'])
        summary['sandbox_fixture_failure_preserved']=True
        summary['source_export']=json.loads((ROOT/'evidence/runtime_source_export.json').read_text())
        summary['source_export'].pop('excluded_files',None)

        for script in sorted((PAYLOAD/'scripts').glob('*.py')):
            compile(script.read_text(),str(script),'exec')
            if script.name!='common.py':
                command('help-'+script.stem,[sys.executable,'-B',script,'--help'])
        for script in sorted((PAYLOAD/'skill/kv260-runtime-review/scripts').glob('*.py')):
            compile(script.read_text(),str(script),'exec')
        validation=command('skill-structure',[sys.executable,
            '/home/ghmd/.codex/skills/.system/skill-creator/scripts/quick_validate.py',
            PAYLOAD/'skill/kv260-runtime-review'])
        summary['skill_structure_passed']='Skill is valid!' in validation
        refusal=json.loads(command('target-preflight-host-refusal',
            [sys.executable,'-B',PAYLOAD/'scripts/board_preflight.py','--config',PAYLOAD/'config'],1))
        if refusal['checks_passed'] or refusal['board_switch_executed'] or not refusal['issues']:
            raise RuntimeError('Target preflight incorrectly accepted development host')
        summary['target_preflight_development_host_refusal_passed']=True
        write(PAYLOAD/'evidence/entry_validation.json',entries)

        original_export=json.loads((ROOT/'evidence/export_state.json').read_text())
        checks=[]
        for original in original_export['preserved_indexes']:
            index=Path(original['index'])
            if sha(index)!=original['sha256']:
                raise RuntimeError('Preserved index changed: '+str(index))
            process=subprocess.run(['sha256sum','-c','--quiet',str(index)],cwd=str(index.parent),
                                   text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            checks.append({'index':str(index),'sha256':sha(index),'entries':original['entries'],
                           'exit_code':process.returncode,'stderr':process.stderr})
            if process.returncode:
                raise RuntimeError('Preserved evidence changed: '+str(index))
        summary['preserved_index_checks']=checks
        summary['preserved_index_records']=sum(c['entries'] for c in checks)

        paths=[str(p.relative_to(PAYLOAD)) for p in PAYLOAD.rglob('*')]
        with tarfile.open(PAYLOAD/'sources/xrt_baseline.tar.gz','r:gz') as archive:
            paths+=['xrt_archive/'+member.name for member in archive.getmembers()]
        invalid=[p for p in paths if any(not re.fullmatch(r'[A-Za-z0-9_.-]+',part) for part in Path(p).parts)]
        uppercase=[p for p in paths if any(c.isupper() for c in p)]
        naming={'english_ascii_paths_passed':not invalid,'invalid_paths':invalid,
                'uppercase_path_count':len(uppercase),'uppercase_examples':uppercase[:20],
                'note':'Upstream build names and standard README.md/SKILL.md remain unchanged. Strict lowercase policy needs confirmation.'}
        write(PAYLOAD/'evidence/naming_review.json',naming)
        if invalid:
            raise RuntimeError('Non-English or unsupported path characters remain')
        summary['uart_by_id_directory_exists']=Path('/dev/serial/by-id').exists()
        summary['new_host_artifacts']={
            str(path.relative_to(PAYLOAD)):{'bytes':path.stat().st_size,'sha256':sha(path),
                                          'board_verified_this_run':False}
            for path in sorted((PAYLOAD/'host_rebuild').rglob('*')) if path.is_file()}
        summary['tested_inputs_reused']=json.loads((PAYLOAD/'config/source_lock.json').read_text())['board_tested_binaries']
        summary['passed']=True
        write(PAYLOAD/'evidence/verification_summary.json',summary)

        own_docs=[PAYLOAD/'README.md',PAYLOAD/'skill/README.md']
        own_docs+=list((PAYLOAD/'docs').glob('*.md'))
        own_docs+=list((PAYLOAD/'skill/kv260-runtime-review').rglob('*.md'))
        broken=[]
        for doc in own_docs:
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',doc.read_text()):
                if target.startswith(('https://','http://','#')):
                    continue
                if not (doc.parent/target.split('#')[0]).exists():
                    broken.append({'document':str(doc.relative_to(PAYLOAD)),'target':target})
        write(PAYLOAD/'evidence/link_review.json',{'passed':not broken,'broken':broken})
        if broken:
            raise RuntimeError('Broken documentation links')
        files=[p for p in sorted(PAYLOAD.rglob('*')) if p.is_file()]
        index=PAYLOAD/'SHA256SUMS'
        if index.exists():
            raise RuntimeError('Payload already sealed; do not rerun packaging')
        index.write_text(''.join('{}  {}\n'.format(sha(path),path.relative_to(PAYLOAD)) for path in files))
        process=subprocess.run(['sha256sum','-c','--quiet',str(index)],cwd=str(PAYLOAD),capture_output=True,text=True)
        if process.returncode:
            raise RuntimeError('Payload seal verification failed')
        release=ROOT/'release'
        release.mkdir(exist_ok=False)
        dest=release/'kv260_runtime_annex_20261003.tar.gz'
        with tarfile.open(dest,'w:gz') as archive:
            for path in sorted(PAYLOAD.rglob('*')):
                if path.is_file():
                    archive.add(path,arcname='kv260-runtime-annex/'+str(path.relative_to(PAYLOAD)),recursive=False)
        members={}
        with tarfile.open(dest,'r:gz') as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    raise RuntimeError('Unexpected release member type')
                members[member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
        expected={'kv260-runtime-annex/'+str(p.relative_to(PAYLOAD)):sha(p)
                  for p in PAYLOAD.rglob('*') if p.is_file()}
        if members!=expected:
            raise RuntimeError('Release member hashes differ from payload')
        receipt={'passed':True,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'payload_files_indexed':len(files),'archive_members_verified':len(members),
                 'archive':str(dest),'archive_bytes':dest.stat().st_size,'archive_sha256':sha(dest),
                 'payload_index_sha256':sha(index),'board_access':False}
        write(ROOT/'evidence/package_verification.json',receipt)
        print(json.dumps(receipt))
    except Exception as error:
        summary['passed']=False
        summary['error']=str(error)
        write(ROOT/'evidence/finalize_failure.json',summary)
        raise


if __name__=='__main__':
    main()
