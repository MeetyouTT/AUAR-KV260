"""Independent source-pinned replay of the author suite and additional cases."""
import ast
import hashlib
import importlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import unittest


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
CANDIDATE = REPAIR / 'voice_visual_timeline_review_v90'
BASE = REPAIR / 'feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90'
PINS = {
    'board/runtime/board_business.py': 'b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2',
    'board/runtime/board_speaker_business.py': '6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816',
    'common/board_memory.py': '05095d249caf3598802d5951910b412affe167b508933c7e831e3ffacc4fc0d0',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


mapping_path = BASE.parent / 'source_mapping.v90.json'
assert sha(mapping_path) == 'df6b26927ad60d6d3513429c697d70bd15c84cfdca6d16c5527e9992cb7b04e2'
mapping = json.loads(mapping_path.read_bytes())
configs = {'config/character_profile.local.json', 'config/persona.xuefei.candidate.json',
           'config/yuki_pair.formal.json', 'config/yuki_accepted_prompt.baseline.txt'}
base_pins = {name: digest for name, digest in mapping['component_pins'].items()
             if name.endswith('.py') or name in configs}
assert len(base_pins) == 343
for name, digest in base_pins.items():
    assert sha(BASE / name) == digest, name
for name, digest in PINS.items():
    path = CANDIDATE / 'after' / name
    assert sha(path) == digest
    ast.parse(path.read_bytes(), feature_version=(3, 9))
author_test = CANDIDATE / 'test_public_replay.py'
author_test_sha = sha(author_test)
sys.dont_write_bytecode = True
sys.path[:0] = [str(BASE), str(HERE)]
package = importlib.import_module('common')
package.__path__ = [str(CANDIDATE / 'after/common'), str(BASE / 'common')]
spec = importlib.util.spec_from_file_location('independent_author_public_replay', author_test)
author = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = author
spec.loader.exec_module(author)
import test_independent_guard
from common import board_memory
assert sha(Path(board_memory.__file__)) == PINS['common/board_memory.py']
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(module)
                           for module in (author, test_independent_guard))
output = io.StringIO()
threads_before = {thread.ident for thread in threading.enumerate()}
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
for name, digest in PINS.items():
    assert sha(CANDIDATE / 'after' / name) == digest
assert sha(author_test) == author_test_sha
leaks = [thread.name for thread in threading.enumerate() if thread.ident not in threads_before]
assert not leaks, leaks
report = {
    'status': 'PASS_LOCAL_PUBLIC_ONLY' if result.wasSuccessful() else 'FAIL',
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped), 'author_replays': 25, 'new_independent_cases': 8,
    'results': output.getvalue(), 'source_pins': PINS, 'base_public_sources_verified': 343,
    'loaded_store': str(Path(board_memory.__file__)), 'author_test_sha256': author_test_sha,
    'candidate_or_original_tests_modified': False, 'thread_leaks': leaks,
    'models_devices_network_private_databases_accessed': False,
}
(HERE / 'TEST_RESULT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(output.getvalue())
raise SystemExit(0 if result.wasSuccessful() else 1)
