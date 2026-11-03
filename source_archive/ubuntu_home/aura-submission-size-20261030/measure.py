"""Measure a representative archive; this is not a complete submission release."""
import collections
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
selected = []
extensions = {'.py','.c','.cpp','.h','.v','.sv','.tcl','.xdc','.sh','.ps1','.bat','.md','.txt','.json','.csv','.yaml','.yml','.toml'}

def add_tree(root, prefix, group, directories, *, text_only=True):
    root = Path(root)
    for directory in directories:
        path = root/directory
        if not path.exists():
            continue
        for source in path.rglob('*'):
            if not source.is_file() or source.is_symlink() or '__pycache__' in source.parts:
                continue
            if text_only and source.suffix.lower() not in extensions:
                continue
            if source.name.endswith('.local.json') or source.name.startswith('.'):
                continue
            selected.append((source, prefix+'/'+source.relative_to(root).as_posix(), group))

software = [('board','/home/ghmd/Win共享文件/共享文件夹/aura'),
            ('pc','/home/ghmd/Win共享文件/语音共享文件/aura')]
for name, root in software:
    add_tree(root,'aura/src/'+name,'software',
             ['board','common','host','hardware','ui','scripts','tools','tests','skills'])

hardware = Path('/home/ghmd/aura-pan-wide-20261028')
add_tree(hardware,'aura/src/fpga','fpga_source', ['candidate/rtl','candidate/native','candidate/scripts','controller'])
add_tree(hardware/'platform','aura/src/platform','platform_inputs',['inputs','ip_repo'],text_only=False)
for name in ['build_joint.py','prepare.tcl','implement.tcl','platform/platform_generated.tcl']:
    selected.append((hardware/name,'aura/build/'+name,'fpga_source'))
add_tree(hardware/'bundle','aura/board','firmware',['lib/firmware'],text_only=False)
for name in ['visual_servo_source.bit','visual_servo_source_implemented.xsa']:
    selected.append((hardware/'implementation'/name,'aura/build/artifacts/'+name,'hardware_artifacts'))
for source in (hardware/'implementation').glob('*.rpt'):
    selected.append((source,'aura/build/reports/'+source.name,'hardware_reports'))
reference = Path('/home/ghmd/aura-pan-joint-20261023/implementation/source_routed.dcp')
selected.append((reference,'aura/build/reference/source_routed.dcp','incremental_reference'))

output_dir = Path(tempfile.mkdtemp(prefix='aura-size-probe-'))
archive_path = output_dir/'size_probe_not_submission.zip'
names = [name for _,name,_ in selected]
assert len(names) == len(set(names)), 'Duplicate archive entry'
by_group = collections.defaultdict(lambda:{'files':0,'raw_bytes':0,'compressed_bytes':0})
with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for source,name,group in selected:
        archive.write(source,name)
        info=archive.getinfo(name)
        by_group[group]['files']+=1
        by_group[group]['raw_bytes']+=info.file_size
        by_group[group]['compressed_bytes']+=info.compress_size
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
result={
    'scope':'REPRESENTATIVE_SIZE_PROBE_NOT_FINAL_OR_COMPLETE_SUBMISSION',
    'archive_path':str(archive_path),
    'archive_bytes':archive_path.stat().st_size,
    'strict_budget_bytes':200000000,
    'under_budget_for_selected_content':archive_path.stat().st_size<200000000,
    'groups':dict(by_group),
    'zip_crc_integrity':'PASS',
    'not_included':['large_model_weights','avatar_assets','virtual_environments','full_design_report','demonstration_video','all_final_evidence','latest_live_board_and_windows_merge','all_final_build_dependencies'],
    'notes':['Original files were not altered or deleted.',
             'The current build explicitly pins the incremental reference DCP; this probe includes it. A final package cannot silently remove required build inputs.',
             'Models/assets need an allowed, pinned and tested acquisition path or separate delivery.'],
}
(ROOT/'size_probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
