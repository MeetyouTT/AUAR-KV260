"""Bundle the frozen unittest replay and its three explicit BEFORE controls into one public artifact."""
import ast
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
REPAIR=D.parent.parent
MEMORY=REPAIR/'voice_visual_timeline_review_v90'

def sha(raw):return hashlib.sha256(raw).hexdigest()

expected={
    'COMBINED_SIX_SOURCE_MANIFEST.json':'06e5ced57c55b0ef551424c37b08c1a9bd5f43217af98c8a6f9170c1cc597f91',
    'HANDOFF.json':'25db1ba2e7f7b6e181ed137efd1a65c14d136274bf1107fdba92cc29a375589b',
    'SOURCE_MANIFEST.json':'2ad7b32e6e3afa42548c8cf89e9d41fb49d3274a6f37897837cd77bc269907b2',
    'test_public_replay.py':'c9b316b4c5848de2c4933ba15a3f362b0a0f642073d24101f33c1388495fea21'}
for name,digest in expected.items():
    assert sha((MEMORY/name).read_bytes())==digest,name
manifest=json.loads((MEMORY/'SOURCE_MANIFEST.json').read_bytes())
before={}
before_shas={}
for relative,row in manifest['files'].items():
    raw=(MEMORY/'before'/relative).read_bytes()
    assert sha(raw)==row['before_sha256'],relative
    before[relative]=raw.decode('utf-8')
    before_shas[relative]=sha(raw)
replay=(MEMORY/'test_public_replay.py').read_bytes().decode('utf-8')
tree=ast.parse(replay)
classes=[n for n in tree.body if isinstance(n,ast.ClassDef)]
assert {n.name for n in classes}=={'Mono','Timeline','Cancel','Fixture','SpeakerReplay','Reader','VisualReplay'}
count=sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for c in classes for n in c.body)
assert count==25
prefix='''"""Pinned public memory unittest bodies; BEFORE controls are explicit source fixtures, never runtime fallbacks.

All original classes, methods and assertions are compiled unchanged. Module path
setup and before/after loaders are replaced with already verified runtime modules
plus three separately hash-checked embedded BEFORE controls. No file is added to
the application package paths. No test runs during module import.
"""
import ast
from collections import OrderedDict
from concurrent.futures import Future
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

PUBLIC_REGRESSION_API='aura-memory-public-regression-1'
EXPECTED_CASES=25
'''
text=prefix+'REPLAY_TEXT='+json.dumps(replay,ensure_ascii=False)+'\n'
text+='REPLAY_SHA256='+repr(expected['test_public_replay.py'])+'\n'
text+='BEFORE_TEXT='+repr(before)+'\nBEFORE_SHA256='+repr(before_shas)+'\n'
text+='''
def build_suite(*,args,public):
    from common.board_memory import BoardMemoryStore,MemoryBusy,ScopeDenied,IdempotencyConflict
    from common.board_timeline_clock import ClockUnavailable
    from common.speaker_turns import record
    from board.runtime.visual_memory import CameraHealthError,CameraHealthSample,VisualTimelineWorker
    active_business=importlib.import_module('board.runtime.board_business')
    active_speaker=importlib.import_module('board.runtime.board_speaker_business')
    active_memory=importlib.import_module('common.board_memory')
    for module,relative in ((active_business,'board/runtime/board_business.py'),
            (active_speaker,'board/runtime/board_speaker_business.py'),(active_memory,'common/board_memory.py')):
        if Path(module.__file__).resolve()!=(args.candidate_root/relative).resolve():
            raise ValueError('Memory AFTER module must be the verified six-source runtime')
    if hashlib.sha256(REPLAY_TEXT.encode('utf-8')).hexdigest()!=REPLAY_SHA256:
        raise ValueError('Original memory replay bytes changed')
    before={}
    for relative,source in BEFORE_TEXT.items():
        if hashlib.sha256(source.encode('utf-8')).hexdigest()!=BEFORE_SHA256[relative]:
            raise ValueError('Public BEFORE source control changed')
        stem=Path(relative).stem
        name=('common.' if relative.startswith('common/') else '')+'_joint_public_memory_before_'+stem
        module=ModuleType(name)
        module.__file__=str(Path(__file__).resolve().parent/'embedded_public_before'/relative)
        module.__package__='common' if relative.startswith('common/') else ''
        sys.modules[name]=module
        exec(compile(source,module.__file__,'exec'),module.__dict__)
        before[relative]=module
    namespace=dict(OrderedDict=OrderedDict,Future=Future,copy=copy,hashlib=hashlib,json=json,Path=Path,
        sqlite3=sqlite3,sys=sys,tempfile=tempfile,threading=threading,time=time,SimpleNamespace=SimpleNamespace,
        unittest=unittest,patch=patch,BoardMemoryStore=BoardMemoryStore,MemoryBusy=MemoryBusy,
        ScopeDenied=ScopeDenied,IdempotencyConflict=IdempotencyConflict,ClockUnavailable=ClockUnavailable,
        record=record,CameraHealthError=CameraHealthError,CameraHealthSample=CameraHealthSample,
        VisualTimelineWorker=VisualTimelineWorker,
        BUSINESS={'before':before['board/runtime/board_business.py'],'after':active_business},
        SPEAKER={'before':before['board/runtime/board_speaker_business.py'],'after':active_speaker},
        BASE_MEMORY=before['common/board_memory.py'],__name__='joint_memory_original_cases')
    tree=ast.parse(REPLAY_TEXT)
    nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) or isinstance(n,ast.Assign)
        and all(isinstance(t,ast.Name) and t.id in {'BOOT','CID'} for t in n.targets)]
    original_classes={n.name:ast.dump(n) for n in tree.body if isinstance(n,ast.ClassDef)}
    if {n.name:ast.dump(n) for n in nodes if isinstance(n,ast.ClassDef)}!=original_classes:
        raise ValueError('Original memory class/method/assertion AST changed')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(Path(__file__).with_name('original_test_public_replay.py')),'exec'),namespace)
    suite=unittest.TestSuite()
    for name in ('SpeakerReplay','VisualReplay'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(namespace[name]))
    if suite.countTestCases()!=EXPECTED_CASES:
        raise ValueError('Original 25 memory case count changed')
    return suite,dict(original_test_source_sha256=REPLAY_SHA256,original_class_method_assertion_AST_unchanged=True,
        original_cases=25,embedded_before_control_shas=BEFORE_SHA256,
        AFTER_modules_are_current_six_source_runtime=True,
        baseline_controls_use_separate_module_aliases=True,application_paths_or_active_modules_replaced=False,
        unavailable_legacy_modules_not_loaded=['test_board_memory_review.py','test_board_memory_completion.py'])
'''
ast.parse(text)
target=D/'memory_public_regressions.py'
assert not target.exists(),'Create a new adapter revision rather than overwriting a frozen module'
target.write_bytes(text.encode('utf-8'))
proof=dict(schema='aura.memory-public-replay-stdlib-adapter.v1',source_sha256=expected['test_public_replay.py'],
    adapter_sha256=sha(target.read_bytes()),original_cases=25,original_classes_methods_assertions_AST_unchanged=True,
    BEFORE_controls=before_shas,BEFORE_controls_are_explicit_negative_comparison_fixtures=True,
    AFTER_uses_current_six_source_runtime=True,source_or_test_body_edits=False,
    root_package_hashes=expected,extra_runtime_artifacts_required=0,
    unmapped_common_timeline_conversations_not_supplied=True)
(D/'MEMORY_ADAPTER_PROOF.json').write_bytes((json.dumps(proof,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(cases=count,module_sha256=sha(target.read_bytes()),bytes=target.stat().st_size)))
