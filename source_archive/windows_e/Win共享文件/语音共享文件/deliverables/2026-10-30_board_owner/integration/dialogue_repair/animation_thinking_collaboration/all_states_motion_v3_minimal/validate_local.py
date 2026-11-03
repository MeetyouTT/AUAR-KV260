"""Current-pin Python facial tests and static native-contract checks only."""
import ast
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

HERE=Path(__file__).resolve().parent
ANIM=HERE.parent
PROJECT=ANIM.parents[4]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    mapping_path=ANIM.parent/'release_v22_camera_rebind_candidate/camera_rebind_evidence/source_mapping.json'
    mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
    base=json.loads((HERE/'BASELINE_V22.json').read_text(encoding='utf-8'))
    if mapping['startup_sha256']!=base['startup_sha256']:raise ValueError('Baseline changed')
    runtime=HERE/'local_test_runtime';runtime.mkdir(exist_ok=False)
    roots=(ANIM/'runtime_v16',HERE/'before/aura',PROJECT/'aura')
    for relative,expected in mapping['component_pins'].items():
        if not relative.endswith('.py') and relative!='config/yuki_pair.formal.json':continue
        for root in roots:
            source=root/relative
            if source.is_file() and sha(source)==expected:
                target=runtime/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
                break
    sys.path.insert(0,str(runtime));sys.dont_write_bytecode=True
    suite=unittest.defaultTestLoader.discover(str(ANIM/'tests'),pattern='test_thinking_animation.py')
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (HERE/'LOCAL_TEST_LOG.txt').write_text(stream.getvalue(),encoding='utf-8')
    loaded={};mismatches=[]
    for name,module in tuple(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file)
        try:relative=path.resolve().relative_to(runtime.resolve()).as_posix()
        except ValueError:continue
        if path.suffix!='.py':continue
        loaded[relative]=sha(path)
        if loaded[relative]!=mapping['component_pins'].get(relative):mismatches.append(relative)
    old=(ANIM/'candidate/native/yuki_host.cpp').read_text(encoding='utf-8')
    new=(HERE/'candidate/native/yuki_host.cpp').read_text(encoding='utf-8')
    # These exact blocks include all existing pose/facial and owner/TTL gates.
    blocks={
        'pose_expression_facial_policy':(' void controls(', ' static PlaybackStatus author('),
        'render_clock_physics_and_draw':(' void draw(', '\n};'),
        'C_control_validation':('int yuki_control(', 'int yuki_render(')}
    for label,(start,end) in blocks.items():
        expected=old[old.index(start):old.index(end,old.index(start))]
        actual=new[new.index(start):new.index(end,new.index(start))]
        if expected!=actual:raise ValueError('Existing native block changed: '+label)
    old_mouth=old[old.index('  const double target=live?'):old.index('\n }\n void draw(')]
    new_mouth=new[new.index('  const double target=live?'):new.index('\n }\n void draw(')]
    if old_mouth!=new_mouth:raise ValueError('Mouth smoothing/cancel logic changed')
    header=(HERE/'candidate/native/gentle_motion.hpp').read_text(encoding='utf-8')
    if 'names{"head_LR","head_slant"}' not in header or 'std::array<ParamId,2> motion' not in new:
        raise ValueError('Unexpected added motion channel set')
    if max(3.17*1.08/3.6,1.58*1.08/1.9)>1:raise ValueError('Analytic offset envelope failed')
    audit=json.loads((ANIM/'all_states_motion_v2/RESOURCE_AUDIT.json').read_text(encoding='utf-8'))
    for pose in audit['authored_pose_ranges']:
        for name,limit in (('head_LR',3.6),('head_slant',1.9)):
            values=pose['ranges'][name]
            if values['authored_min']-limit < -30 or values['authored_max']+limit > 30:
                raise ValueError('Authored range exceeded')
    for file in HERE.glob('*.py'):ast.parse(file.read_text(encoding='utf-8'))
    summary=dict(schema='aura.minimal-motion-local-validation.v1',successful=result.wasSuccessful() and not mismatches,
        python_tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        loaded_dependency_pins=loaded,loaded_dependency_mismatches=mismatches,
        native_critical_blocks_identical=list(blocks)+['author_mouth_smoothing_and_cancel'],
        added_motion_channels=['head_LR','head_slant'],analytic_max_offsets=[3.4236,1.7064],
        unchanged_body_and_physics_assets=True,local_cpp_compiler_available=False,
        native_candidate_compiled_or_executed=False,device_access=False,
        physical_audio_or_fps_acceptance=False,production_modified=False)
    (HERE/'LOCAL_TEST_RESULTS.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(stream.getvalue());print(json.dumps(summary))
    raise SystemExit(0 if summary['successful'] else 1)


if __name__=='__main__':main()
