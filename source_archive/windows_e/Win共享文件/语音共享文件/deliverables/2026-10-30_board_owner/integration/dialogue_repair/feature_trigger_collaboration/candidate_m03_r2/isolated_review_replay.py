"""Standalone stdlib replay of the FOUR UNCHANGED independent counterexamples.

No production factory, private database, model, microphone, camera or playback.
An explicitly selected public source snapshot supplies original Store/controller
classes. Candidate and review bytes are verified before any application import.
This is snapshot validation; a recovered live release needs a separate rebase.
"""
import argparse
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import sys

MANIFEST='b708c78fb75a2f621fdc99363d41342689951665bc8e0053486f44aba79b1bac'
REVIEW='7528a035ae301b3bf0d3bb0747cb52c322f82b5a1c236102ba5d47915e0c008b'
FILES={'board/runtime/board_business.py','board/runtime/history_delete.py','tools/production_memory_presentation.py'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def need(ok,code):
    if not ok:raise ValueError(code)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-runtime-snapshot',type=Path,required=True)
    parser.add_argument('--mapping',type=Path,required=True)
    parser.add_argument('--candidate-manifest',type=Path,required=True)
    parser.add_argument('--candidate-root',type=Path,required=True)
    parser.add_argument('--original-review',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--root-coordinated-slot')
    args=parser.parse_args()
    need(args.output.is_absolute() and not args.output.exists(),'fresh_absolute_output_required')
    need(sys.platform!='linux' or bool(args.root_coordinated_slot),'root_coordinates_board_execution')
    raw=args.candidate_manifest.read_bytes();need(sha(raw)==MANIFEST,'frozen_candidate_manifest_changed')
    manifest=json.loads(raw);mapping_raw=args.mapping.read_bytes()
    need(sha(mapping_raw)==manifest['baseline_mapping_sha256'],'saved_v18_mapping_changed')
    mapping=json.loads(mapping_raw);need(len(mapping['component_pins'])==379,'saved_component_count_changed')
    need(set(manifest['files'])==FILES,'exact_three_candidate_files_required')
    need(sha(args.original_review.read_bytes())==REVIEW,'original_review_assertions_changed')
    base=args.public_runtime_snapshot.resolve(strict=True);candidate=args.candidate_root.resolve(strict=True)
    need(not base.is_relative_to(candidate) and not candidate.is_relative_to(base),'separate_source_roots_required')
    expected={p:s for p,s in mapping['component_pins'].items() if p.endswith('.py') or p in {
        'config/character_profile.local.json','config/persona.xuefei.candidate.json',
        'config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'}}
    for relative,digest in expected.items():
        path=base/relative
        need(not path.is_symlink() and path.resolve().is_relative_to(base),'snapshot_path_escape')
        need(sha(path.read_bytes())==digest,'snapshot_source_changed:'+relative)
    need({p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file() or p.is_symlink()}==FILES,
         'unexpected_candidate_files')
    for relative,row in manifest['files'].items():
        path=candidate/relative
        need(not path.is_symlink() and path.resolve().is_relative_to(candidate),'candidate_path_escape')
        need(sha(path.read_bytes())==row['sha256'],'candidate_source_changed:'+relative)
        need(row['before_sha256']==mapping['component_pins'].get(relative),'different_before_pin')
    sys.dont_write_bytecode=True;sys.path.insert(0,str(base))
    for package in ('board.runtime','tools'):
        module=importlib.import_module(package)
        module.__path__=[str(candidate/package.replace('.','/'))]+list(module.__path__)
    loaded={}
    for name in ('common.board_memory','board.runtime.board_dialogue','board.runtime.history_delete',
                 'board.runtime.board_business','tools.production_memory_presentation'):
        module=importlib.import_module(name);path=Path(module.__file__).resolve()
        loaded[name]=dict(path=str(path),sha256=sha(path.read_bytes()))
    need(loaded['common.board_memory']['sha256']==mapping['component_pins']['common/board_memory.py'],'wrong_original_store')
    need(loaded['board.runtime.board_dialogue']['sha256']==mapping['component_pins']['board/runtime/board_dialogue.py'],'wrong_original_controller')
    need(loaded['board.runtime.history_delete']['sha256']==manifest['files']['board/runtime/history_delete.py']['sha256'],'wrong_delete_handler')
    # Source tests retain their original file, globals, code and assertions.
    spec=importlib.util.spec_from_file_location('unchanged_independent_m03_review',args.original_review)
    review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
    parents=None if sys.platform!='linux' else '/dev/shm'
    before=set(threading.enumerate());old_temp=tempfile.tempdir
    log=io.StringIO()
    with tempfile.TemporaryDirectory(prefix='aura-public-m03-r2-',dir=parents) as owned:
        os.chmod(owned,0o700);tempfile.tempdir=owned
        try:
            suite=unittest.defaultTestLoader.loadTestsFromTestCase(review.DeleteBoundaryReview)
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        finally:tempfile.tempdir=old_temp
    value=dict(schema='aura.m03-r2.public-snapshot-replay.v1',
        status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),
        host='board' if sys.platform=='linux' else 'local_windows',coordinated_slot=args.root_coordinated_slot,
        saved_source_baseline=mapping['startup_sha256'],live_recovered_release_verified=False,
        warning='Snapshot replay only. New boot/cold-start source merge requires fresh root review and binding.',
        source_manifest_sha256=MANIFEST,unchanged_review_sha256=REVIEW,original_assertions_changed=False,
        verified_public_source_files=len(expected),loaded_modules=loaded,
        public_test_log=log.getvalue(),owned_temporary_store_removed=not Path(owned).exists(),
        new_threads_remaining=len(set(threading.enumerate())-before),
        production_changed=False,production_private_store_opened=False,model_or_device_or_network_used=False)
    args.output.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(status=value['status'],tests=value['tests'],failures=value['failures'],errors=value['errors']),ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
