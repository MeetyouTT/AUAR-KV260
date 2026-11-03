"""Round-trip the expanded archive and rerun its offline entry points on Ubuntu."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE=Path('/home/ghmd/auar-board-evidence-9a4f-20261103-01a1a08b')
ROOT=BASE/'auar_xuefei'
QA=BASE/'verification'
RAR=Path('/home/ghmd/auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar')
VIV=Path('/home/ghmd/Xilinx_2022.2/Vivado/2022.2')
VIT=Path('/home/ghmd/Xilinx_2022.2/Vitis/2022.2')
OLDQA=Path('/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification')
RUN=QA/'final_roundtrip'
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',XILINX_VIVADO=str(VIV),XILINX_VITIS=str(VIT))
ENV['PATH']=str(VIV/'bin')+':'+str(VIT/'bin')+':'+ENV.get('PATH','')
state={'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commands':[],'board_accessed':False,'new_physical_board_test_performed':False}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def save():
    p=QA/'final_progress.json'
    tmp=p.with_suffix('.tmp')
    tmp.write_text(json.dumps(state,indent=2)+'\n')
    tmp.replace(p)

def command(name,args,cwd):
    state['active']=name
    save()
    log=RUN/(name+'.log')
    started=time.monotonic()
    with log.open('xb') as f:
        result=subprocess.run([str(v) for v in args],cwd=str(cwd),env=ENV,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
    entry={'name':name,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-started,3),'log_sha256':sha(log),'log':str(log),'command':[str(v) for v in args]}
    state['commands'].append(entry)
    save()
    print(name,result.returncode,flush=True)
    if result.returncode:raise RuntimeError(name+': '+log.read_text(errors='replace')[-2400:])

try:
    RUN.mkdir(exist_ok=False)
    arcdir=QA/'archive'
    arcdir.mkdir(exist_ok=False)
    archive=arcdir/'auar_xuefei_board_enhanced.rar'
    command('rar_create',[RAR,'a','-ma5','-m5','-r','-idq',archive,'auar_xuefei'],BASE)
    assert archive.read_bytes()[:8]==bytes.fromhex('526172211a070100')
    assert 0<archive.stat().st_size<200000000
    state['archive']={'file':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size,'format':'RAR5','sole_root':'auar_xuefei'}
    (arcdir/'archive.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    shutil.copyfile(str(QA/'verify_skill.tcl'),str(arcdir/'verify_skill.tcl'))
    command('rar_test',[RAR,'t','-idq',archive],arcdir)
    unpack=RUN/'expanded'
    unpack.mkdir()
    command('rar_extract',[RAR,'x','-idq',archive,str(unpack)+'/'],arcdir)
    assert sorted(p.name for p in unpack.iterdir())==['auar_xuefei']
    extracted=unpack/'auar_xuefei'
    source={p.relative_to(ROOT).as_posix():sha(p) for p in ROOT.rglob('*') if p.is_file()}
    restored={p.relative_to(extracted).as_posix():sha(p) for p in extracted.rglob('*') if p.is_file()}
    assert source==restored
    state['archive'].update(exact_extracted_files_matched=len(source),expanded_bytes=sum(p.stat().st_size for p in extracted.rglob('*') if p.is_file()),all_file_bytes_match_source_snapshot=True,checksum_entries=len((extracted/'checksums.sha256').read_text().splitlines()))
    command('sha256sum',[shutil.which('sha256sum'),'--quiet','-c','checksums.sha256'],extracted)
    pins=json.loads((extracted/'report/evidence/implementation_receipt.json').read_text())['hardware_source_sha256']
    assert all(sha(extracted/name)==expected for name,expected in pins.items())
    state['unchanged_cold_implementation_inputs_matched']=len(pins)
    command('evidence_replay',[sys.executable,'-B',extracted/'board/verify_evidence.py','--out',RUN/'evidence'],extracted)
    evidence=json.loads((RUN/'evidence/comparison.json').read_text())
    assert evidence['status']=='PASS' and len(evidence['checks'])==147 and not evidence['hardware_executed_now']
    state['preserved_evidence_checks_passed']=len(evidence['checks'])
    command('evidence_negative',[sys.executable,'-B','-m','unittest','discover','-s','board/tests','-v'],extracted)
    assert 'Ran 5 tests' in (RUN/'evidence_negative.log').read_text()
    state['evidence_unit_tests_passed']=5
    rootfs=OLDQA/'final-roundtrip02/staged-board'
    command('runtime_file_comparison',[sys.executable,'-B',extracted/'board/bringup/check_runtime.py','--rootfs',rootfs,'--out',RUN/'runtime_files.json'],extracted)
    runtime=json.loads((RUN/'runtime_files.json').read_text())
    assert runtime['status']=='PASS' and len(runtime['checks'])==439 and not runtime['functional_board_test_performed']
    state['offline_rootfs_file_checks_passed']=439
    command('yunet_fixture_description',[sys.executable,'-B',extracted/'board/bringup/run_yunet_synthetic.py','--describe'],extracted)
    cand=extracted/'board/artifacts_candidate'
    command('paired_artifact_export',[sys.executable,'-B',extracted/'board/bringup/prepare_artifacts.py','--hardware-dir',cand,'--firmware-dir',cand,'--out',RUN/'paired_artifacts'],extracted)
    am=json.loads((RUN/'paired_artifacts/manifest.json').read_text())
    assert am['preparation_status']=='PASS' and am['board_verified'] is False
    state['packaged_artifacts_checked']=len(am['files'])
    command('skill_tcl',[VIV/'bin/vivado','-mode','batch','-source',arcdir/'verify_skill.tcl','-log',RUN/'skill_tcl.vivado.log','-journal',RUN/'skill_tcl.jou','-tclargs',RUN/'skill_tcl'],RUN)
    sr=json.loads((RUN/'skill_tcl/verification.json').read_text())
    assert sr['status']=='PASS' and sr['unit_tests']==15 and sr['mock_total']==73 and sr['tcl']=='8.5.14' and sr['board_verified'] is False
    state['skill_tcl']=sr
    rebuild=RUN/'rebuild'
    for stage in ['software','rtl','prepare']:
        args=[sys.executable,'-B',extracted/'build/reproduce.py','--out',rebuild,'--stage',stage]
        if stage in ['rtl','prepare']:args+=['--vivado',VIV/'bin/vivado']
        if stage=='prepare':args+=['--vitis-root',VIT,'--rtl-results',rebuild/'rtl/result.json']
        command('rebuild_'+stage,args,extracted)
        receipt=json.loads((rebuild/(stage+'.receipt.json')).read_text())
        assert receipt['status']=='PASS' and receipt['board_accessed'] is False
    state['new_rebuild_stages_passed']=['software','rtl','prepare']
    # Executed programs must leave the archive source and extracted tree unchanged.
    after={p.relative_to(extracted).as_posix():sha(p) for p in extracted.rglob('*') if p.is_file()}
    assert after==restored
    state['extracted_tree_unchanged_after_checks']=True
    original=Path('/home/ghmd/下载/AUAR_方案A源码交付_9a4f_20261103/auar_xuefei_source.rar')
    assert sha(original)=='022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4'
    state['original_source_archive_preserved']=True
    state['status']='PASS'
    state['active']=None
    state['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
    (arcdir/'archive_verification.json').write_text(json.dumps(state,indent=2)+'\n')
    print('BOARD_ENHANCED_ARCHIVE_PASS',state['archive']['bytes'],state['archive']['sha256'],flush=True)
except Exception as e:
    state.update(status='FAIL',error=type(e).__name__+': '+str(e))
    save()
    print('FAILED',state['error'],flush=True)
    raise
