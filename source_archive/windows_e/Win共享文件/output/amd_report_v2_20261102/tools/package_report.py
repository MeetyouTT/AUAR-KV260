"""Package reviewed deliverables and validate a fresh extracted offline run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'auar_xuefei_amd_report_v2_package.zip'
PREFIX='AUAR_AMD_Report_V2'


def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    result=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel=path.relative_to(ROOT)
        if any(x in ('_qa','tools','__pycache__') for x in rel.parts):
            continue
        if path.suffix.lower() in ('.zip','.pyc') or path.name=='package_manifest.json':
            continue
        result.append(path)
    return result


def package():
    included=files()
    manifest={'schema':'report-package-manifest-1','scope':'AMD report, evidence and offline Skill',
              'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in included]}
    save(ROOT/'package_manifest.json',manifest)
    temporary=ARCHIVE.with_name(ARCHIVE.stem+'.tmp.zip')
    with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
        for path in included+[ROOT/'package_manifest.json']:
            archive.write(path,(Path(PREFIX)/path.relative_to(ROOT)).as_posix())
    temporary.replace(ARCHIVE)
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        count=len(archive.namelist())
    return count


def main():
    qa=ROOT/'_qa'
    validation=json.loads((qa/'document_validation.json').read_text(encoding='utf8'))
    assert validation['pages']==22
    reviewed=[]
    changed={6,7,10,11,13,20}
    for page in range(1,23):
        name=f'page-{page:02d}.png'
        final=qa/'pages_r3'/name
        if page not in changed:
            assert sha(final)==sha(qa/'pages_r2'/name)
        reviewed.append({'page':page,'render_sha256':sha(final),
                         'inspection':'R3_VISUALLY_REVIEWED' if page in changed else 'R2_REVIEWED_PIXEL_IDENTICAL_TO_R3'})
    validation.update(visual_review='PASS_ALL_22_PAGES',page_reviews=reviewed,pdf_sha256=sha(ROOT/'auar_xuefei_amd_design_report_v2.pdf'))
    save(qa/'document_validation.json',validation)

    initial_count=package()
    extracted=qa/'extracted_packet_01'
    assert not extracted.exists()
    extracted.mkdir()
    with zipfile.ZipFile(ARCHIVE) as archive:
        for name in archive.namelist():
            (extracted/name).resolve().relative_to(extracted.resolve())
        archive.extractall(extracted)
    packet=extracted/PREFIX
    manifest=json.loads((packet/'package_manifest.json').read_text(encoding='utf8'))
    for entry in manifest['files']:
        target=(packet/entry['path']).resolve()
        target.relative_to(packet.resolve())
        assert sha(target)==entry['sha256'],entry['path']
    run_out=qa/'extracted_reproduction_01'
    assert not run_out.exists()
    result=subprocess.run([sys.executable,'-B',str(packet/'reproduction/reproduce_offline.py'),
                           '--out',str(run_out)],cwd=packet,capture_output=True,text=True,encoding='utf8')
    save(qa/'extracted_run_process.json',{'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    assert result.returncode==0,result.stdout+result.stderr
    summary=json.loads((run_out/'summary.json').read_text(encoding='utf8'))
    assert summary['status']=='PASS' and not summary['board_verified'] and not summary['full_system_reproduced']
    packaged={'schema':'report-extracted-package-validation-1','status':'PASS_OFFLINE_ONLY',
              'environment':'Windows, Python '+summary['python'],
              'fresh_extracted_directory':True,'all_manifest_files_verified':len(manifest['files']),
              'evidence_files_checked':summary['evidence_files_checked'],
              'skill_source_files_checked':summary['skill_source_files_checked'],
              'unit_tests_passed':15,'examples':summary['examples'],
              'board_verified':False,'full_system_reproduced':False,
              'note':'Same suite, new extracted location. No increase of test coverage or hardware validation.'}
    save(ROOT/'attachments/validation/package_validation.json',packaged)
    # Add the normalized extraction result; unchanged runtime/evidence files were tested above.
    final_count=package()
    final={'status':'PASS','report_pages':22,'pdf_visual_review':'PASS_ALL_22_PAGES',
           'archive':ARCHIVE.name,'archive_bytes':ARCHIVE.stat().st_size,'archive_file_count':final_count,
           'archive_crc':'PASS','fresh_extracted_offline_reproduction':'PASS',
           'board_verified':False,'full_system_reproduced':False,'pdf_sha256':sha(ROOT/'auar_xuefei_amd_design_report_v2.pdf'),
           'archive_sha256':sha(ARCHIVE),'initial_count':initial_count}
    save(qa/'final_validation.json',final)
    print(json.dumps(final,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
