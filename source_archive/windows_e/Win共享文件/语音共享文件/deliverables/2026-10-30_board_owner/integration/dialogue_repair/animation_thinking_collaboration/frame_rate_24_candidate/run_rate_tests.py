"""Device-free behavior/clock tests for each pinned16/24 startup variant."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fps',type=int,choices=(16,24),required=True)
    args=parser.parse_args();variant=HERE/('paired_'+str(args.fps))
    receipt=json.loads((variant/'PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
    animation=HERE.parent
    mapping=json.loads((animation.parent/'release_v17_candidate/v17_evidence/source_mapping.json').read_text(encoding='utf-8'))
    runtime=HERE/('test_runtime_'+str(args.fps));runtime.mkdir(exist_ok=True)
    # Only unchanged display dependencies are needed by these tests. Feature v3
    # modules are not exercised, imported as services, or overwritten here.
    for source in (animation/'runtime_v16').rglob('*'):
        if not source.is_file() or source.suffix not in ('.py','.json'):continue
        relative=source.relative_to(animation/'runtime_v16').as_posix()
        destination=runtime/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    for relative,expected in receipt['files'].items():
        source=variant/'aura'/relative
        if sha(source)!=expected:raise ValueError('Variant changed before testing')
        destination=runtime/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    os.environ['AURA_NATIVE_RATE_TEST_FPS']=str(args.fps)
    sys.path.insert(0,str(runtime));sys.dont_write_bytecode=True
    suite=unittest.TestLoader().discover(str(animation/'tests'),pattern='test_*.py')
    spec=importlib.util.spec_from_file_location('rate_specific_tests',HERE/'tests/test_native_frame_rate.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    suite.addTests(unittest.TestLoader().loadTestsFromModule(module))
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    loaded={};mismatches=[]
    for module in tuple(sys.modules.values()):
        value=getattr(module,'__file__',None)
        if not value:continue
        path=Path(value)
        if path.suffix!='.py' or not path.is_relative_to(runtime):continue
        relative=path.relative_to(runtime).as_posix()
        digest=sha(path);expected=receipt['files'].get(relative,mapping['component_pins'].get(relative))
        loaded[relative]=digest
        if digest!=expected:mismatches.append(relative)
    (variant/'TEST_LOG.txt').write_text(log.getvalue(),encoding='utf-8')
    summary=dict(schema='aura.native-rate-local-tests.v1',startup_fps=args.fps,
        tests_run=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
        skipped=len(result.skipped),files=receipt['files'],selection_sha256=receipt['selection_sha256'],
        device_access=False,native_library_loaded=False,actual_fps_measured=False,production_modified=False,
        includes_original_25_eye_gate_tests=True,loaded_display_dependency_pins=loaded,
        loaded_dependency_pin_mismatches=mismatches)
    (variant/'TEST_RESULTS.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue());print(json.dumps(summary))
    raise SystemExit(0 if result.wasSuccessful() and not mismatches else 1)


if __name__=='__main__':main()
