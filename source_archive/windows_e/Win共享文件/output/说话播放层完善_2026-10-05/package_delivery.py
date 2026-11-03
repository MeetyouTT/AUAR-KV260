import difflib
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(r'E:\项目\共享文件夹\aura'); OUT=Path(__file__).parent
DEL=ROOT.parent/'deliverables/2026-10-05_avatar_naturalness'
QA=DEL/'验证'; QA.mkdir(parents=True,exist_ok=True)
for name in ['pytest.log','playback_verification.json','window_verification.json','window_frames.json',
             'c_cursor_verification.json','export_verification.json','export_verification.log',
             'board_export.log','before_after_boundaries.png','说话连续播放预览.gif',
             'verify_segment_exit.log','verify_pool_rotation.log',
             'verify_playback.py','window_check.py','check_c_cursor.py','verify_export.py']:
    shutil.copy2(OUT/name,QA/name)
back=QA/'before'; back.mkdir(exist_ok=True)
parts=[]
for name,rel in [('avatar_player.py','board/interaction/avatar_player.py'),
                 ('demo_script.py','tools/demo_script.py'),('demo_stage.py','tools/demo_stage.py')]:
    shutil.copy2(OUT/'before'/name,back/name)
    parts.extend(difflib.unified_diff((OUT/'before'/name).read_text(encoding='utf-8').splitlines(True),
                    (ROOT/rel).read_text(encoding='utf-8').splitlines(True),fromfile='before/'+rel,tofile='after/'+rel))
(QA/'playback_changes.diff').write_text(''.join(parts),encoding='utf-8')
table=json.loads((ROOT/'ui/avatar_board_manifest.json').read_text(encoding='utf-8'))
rels=['ui/avatar_board_manifest.json','ui/ui_state.schema.json','ui/ui_layout_spec.json','ui/ui_tokens.json',
      'board/interaction/lvgl/avatar_assets_table.h','board/interaction/lvgl/avatar_playback.h',
      'docs/说话播放层完善与素材交接_2026-10-05.md','docs/说话素材生成与验收工作流_v3.md',
      'docs/说话素材自然度提示词包_v3.md','docs/说话素材自然度提示词_v3.json']
for r in table['resources']:
    folder=ROOT/'assets/avatar'/r['asset']
    rels.extend(p.relative_to(ROOT).as_posix() for p in [folder/n for n in ['frames.rgb565','meta.json','segments.json','motion.json']] if p.is_file())
entries=[{'file':rel,'bytes':(ROOT/rel).stat().st_size,'sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()} for rel in rels]
readme='''AURA avatar board inputs v1.2 — 2026-10-05
PC / SIMULATED export; hardware integration and display cadence remain unverified.
15 runtime states, 16 resources, 573 source frames, 24fps, 464x480.
RGB565: big-endian R5G6B5 with #FCFCF3 background. Stream with double buffering.
Algorithm: continuous_cursor_v1; primary window only; no random loop phase;
cosine round trip; interpolate adjacent source frames only.
The historical blend stage is a 150ms VELOCITY ramp, not a pose crossfade.
Stop/cancel recovers to the nearer clip endpoint; pool rotation to the last endpoint.
Request rotation after 6s and wait for recovery before switching resources.
Use avatar_playback.h for the continuous cursor; renderer/event policy still required.
C cursor numerical parity is PC tested, not an installed LVGL implementation.
The seven v3 prompt types are planned; no new generated materials are included.
release_manifest.json provides size/SHA256 for every payload.
'''
archive=DEL/'aura_avatar_board_inputs_2026-10-05_v1_2.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for rel in rels: z.write(ROOT/rel,rel)
    z.writestr('README_BOARD_INPUTS.txt',readme)
    z.writestr('release_manifest.json',json.dumps({'schema_version':'1.2','environment':'PC / SIMULATED','files':entries},ensure_ascii=False,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for entry in entries: assert hashlib.sha256(z.read(entry['file'])).hexdigest()==entry['sha256']
(QA/'board_package.json').write_text(json.dumps({'archive':archive.name,'payload_files':len(entries),
    'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,
    'all_payload_sha256_verified':True,'archive_crc_ok':True},indent=2),encoding='utf-8')
source_rels=['board/interaction/avatar_player.py','board/interaction/avatar_timing.py','board/interaction/avatar_board.py',
    'scripts/board_export.py','tools/demo_script.py','tools/demo_stage.py','tools/build_naturalness_workflows.py',
    'tools/verify_segment_exit.py','tools/verify_pool_rotation.py',
    'tools/check_naturalness_candidate.py','tools/run_demo_script.bat','tools/launch_script_window.ps1','tools/show_demo_script.py',
    'tests/test_avatar_continuity.py','tests/test_avatar_playback_integration.py','tests/test_naturalness_workflows.py',
    'tests/test_naturalness_candidate.py','README.md','.cline-handover.md','docs/项目接手说明_AI_当前进度与待办.md']
tracked=[ROOT/p for p in source_rels+rels[:10]]+[ROOT.parent/'.cline-handover.md']
tracked+=sorted(p for p in DEL.rglob('*') if p.is_file() and p.name!='同步校验.json')
records=[]
for p in tracked:
    records.append({'file':p.relative_to(ROOT.parent).as_posix(),'bytes':p.stat().st_size,
                    'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'status':'VERIFIED','files':records,'new_assets_generated':False,'hardware_verified':False}
(DEL/'同步校验.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for r in records:
    p=ROOT.parent/r['file']; assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
print(json.dumps({'tracked_files':len(records),'workflow_graphs':len(list((DEL/'素材生成工作流').glob('*_api.json'))),
                  'package_mib':archive.stat().st_size/1024**2,'all_hashes_verified':True},ensure_ascii=False))
