"""Root-only isolated H01 overlay; verify v17 BEFORE importing production code.

Stage the unchanged worker.py/source_mapping.json, this file, frozen
SOURCE_MANIFEST.json and the two after/ source files. Do not install anything.
The original worker and every assertion run unmodified. Production source,
private stores, controls, model and device owners are never written or opened.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

WORKER_SHA = '7d5ff31d1f56cb567fd630c35056a1a33f9d239f520ad92975f47e10149153df'
CANDIDATE_MANIFEST_SHA = '8fec970eeb6b716da117b8966ee51004298a411011cfdfe436838790f932fa69'
FILES = {'common/board_memory.py', 'board/runtime/board_dialogue.py'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(condition, code):
    if not condition:
        raise ValueError(code)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--startup-config',type=Path)
    parser.add_argument('--mapping',type=Path,required=True)
    parser.add_argument('--worker',type=Path,required=True)
    parser.add_argument('--candidate-manifest',type=Path,required=True)
    parser.add_argument('--candidate-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--coordinated-slot')
    parser.add_argument('--local-replay',action='store_true')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    need(args.output.is_absolute() and not args.output.exists(),'fresh_absolute_output_required')
    worker_raw=args.worker.read_bytes()
    need(not args.worker.is_symlink() and sha(worker_raw)==WORKER_SHA,'frozen_worker_changed')
    manifest_raw=args.candidate_manifest.read_bytes()
    need(sha(manifest_raw)==CANDIDATE_MANIFEST_SHA,'candidate_manifest_changed')
    manifest=json.loads(manifest_raw)
    need(set(manifest['files'])==FILES,'exact_two_file_overlay_required')
    need(not any(name in sys.modules for name in ('common.board_memory','board.runtime.board_dialogue')),
         'fresh_test_process_required')
    spec=importlib.util.spec_from_file_location('unchanged_public_v17_worker',args.worker)
    worker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)  # This file imports only standard library.
    verification=worker.verify(args)  # Live v17 startup + all pinned public sources first.
    base=args.runtime_root.resolve(strict=True)
    candidate=args.candidate_root.resolve(strict=True)
    need(not candidate.is_relative_to(base) and not base.is_relative_to(candidate),'overlay_must_be_separate_from_production')
    pins=json.loads(args.mapping.read_bytes())['component_pins']
    if not args.local_replay:
        # Every one of the 379 startup-pinned public components, including
        # assets/native code/public metadata; no referenced private path opens.
        for relative,digest in pins.items():
            path=base/relative
            need(not path.is_symlink() and path.resolve().is_relative_to(base),'live_pin_path_escape')
            need(sha(path.read_bytes())==digest,'live_component_changed:'+relative)
        verification['all_live_components_hashed']=len(pins)
    else:
        verification['all_live_components_hashed']=False
    staged_files={path.relative_to(candidate).as_posix() for path in candidate.rglob('*')
                  if path.is_file() or path.is_symlink()}
    need(staged_files==FILES,'candidate_tree_must_contain_exactly_the_two_sources')
    applied={}
    for relative,row in manifest['files'].items():
        path=candidate/relative
        need(not path.is_symlink() and path.resolve().is_relative_to(candidate),'overlay_path_escape')
        raw=path.read_bytes()
        need(sha(raw)==row['sha256'] and row['before_sha256']==pins[relative],'overlay_source_or_baseline_changed')
        applied[relative]=dict(before_sha256=row['before_sha256'],sha256=row['sha256'],bytes=len(raw))
    overlay_record=dict(schema='aura.isolated-h01-overlay.v1',
        status='SOURCE_CHECKED_TEST_PROCESS_ONLY',candidate_manifest_sha256=CANDIDATE_MANIFEST_SHA,
        original_worker_sha256=WORKER_SHA,board_runner_sha256=sha(Path(__file__).read_bytes()),
        verified_base=verification,applied_files=applied,
        all_original_worker_assertions_unchanged=True,live_v17_verified_before_import=True,
        production_sources_written=False,production_private_store_opened=False,
        production_controls_changed=False,model_or_device_opened=False)
    if args.check_only:
        worker.persist(args.output,overlay_record)
        print(json.dumps(dict(status=overlay_record['status'],output=str(args.output))))
        return 0
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(base))
    # This changes package lookup in THIS interpreter only. The candidate has
    # exactly two regular files and cannot shadow any other runtime component.
    for package in ('common','board.runtime'):
        module=importlib.import_module(package)
        module.__path__=[str(candidate/package.replace('.','/'))]+list(module.__path__)
    argv=[str(args.worker),'--runtime-root',str(base),'--mapping',str(args.mapping),'--output',str(args.output)]
    if args.local_replay:argv.append('--local-replay')
    else:argv+=['--startup-config',str(args.startup_config),'--coordinated-slot',args.coordinated_slot]
    sys.argv=argv
    code=1
    try:
        code=worker.main()  # Unchanged worker verifies live baseline again.
        return code
    finally:
        if args.output.is_file():
            result=json.loads(args.output.read_bytes())
        else:
            result=dict(status='FAIL',error='worker_did_not_produce_evidence')
        loaded={}
        for name,relative in [('common.board_memory','common/board_memory.py'),
                              ('board.runtime.board_dialogue','board/runtime/board_dialogue.py')]:
            module=sys.modules.get(name)
            path=Path(module.__file__).resolve() if module else None
            okay=bool(path and path==candidate/relative and sha(path.read_bytes())==applied[relative]['sha256'])
            loaded[relative]=dict(loaded_from_candidate=okay)
        overlay_record['loaded_modules']=loaded
        overlay_record['candidate_modules_verified']=all(row['loaded_from_candidate'] for row in loaded.values())
        result['isolated_overlay']=overlay_record
        if not overlay_record['candidate_modules_verified']:
            result['status']='FAIL'
        worker.persist(args.output,result)
        if not overlay_record['candidate_modules_verified']:
            raise RuntimeError('Candidate modules were not loaded exactly')


if __name__=='__main__':
    raise SystemExit(main())
