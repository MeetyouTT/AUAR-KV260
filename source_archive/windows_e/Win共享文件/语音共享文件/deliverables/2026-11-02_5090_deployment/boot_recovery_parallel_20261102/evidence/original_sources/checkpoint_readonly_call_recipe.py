"""Review recipe: invoke only the original Python checkpoint reader in a sealed namespace.

Not executed during this review. This is a read-only verification recipe, not a
platform transaction, release approval, checkpoint producer or recovery entry.
It has no checkpoint consumption, C context, runner, service or device operation.
Use only in a fresh /usr/bin/python3 -B -I -S process after normal source-owner
shutdown, with the exact newly generated original checkpoint pin.
"""
import argparse
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import sys
import types


ROOT = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
CHECKPOINT = ROOT.parent/'state/native-protection-checkpoint.json'
PINS = {
    'board/vision/__init__.py': '091e8b3b95a7f46655ba0c5275630eb3aee2079b57a95a0f5ef35d4e44c47284',
    'board/vision/native_binding.py': '5f385c03cf84b1f9ba3afe4d4a6cfd3022ba639aba06b8d923f83783bfd48da6',
    'board/vision/native_protection.py': 'b8637c2aa387915a49ef0fd7a1c7cb9d015fb71802c4eaa11539a64466db1faa',
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verified_source(relative):
    path = ROOT/relative
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            'Installed public source redirected: ' + relative)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PINS[relative], 'Installed source changed: ' + relative)
    return raw


def namespace(name):
    module = types.ModuleType(name)
    module.__package__ = name
    module.__path__ = []  # No filesystem discovery of another board package.
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    module.__spec__.submodule_search_locations = []
    sys.modules[name] = module
    return module


def original_module(name, relative, raw):
    module = types.ModuleType(name)
    module.__package__ = 'board.vision'
    module.__file__ = str(ROOT/relative)
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, origin=module.__file__)
    sys.modules[name] = module  # Required by the original stdlib dataclass decorator.
    # Execute precisely the bytes already hashed, not a second loader read.
    exec(compile(raw, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint-sha256', required=True)
    parser.add_argument('--boot-id', required=True)
    args = parser.parse_args()
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            'A fresh -B -I -S interpreter is mandatory')
    require(not any(name == 'board' or name.startswith('board.') for name in sys.modules),
            'Pre-existing board module namespace refused')
    require(os.uname().machine == 'aarch64', 'Use the installed board interpreter for original ABI structures')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(args.boot_id == boot, 'Actual kernel boot differs')
    for path in (ROOT, ROOT/'board', ROOT/'board/vision'):
        require(path.is_dir() and not path.is_symlink() and path.resolve() == path,
                'Original source directory redirects')
    require(not os.path.lexists(str(ROOT/'board/__init__.py')),
            'The previously reviewed namespace root changed')
    raw_sources = {relative: verified_source(relative) for relative in PINS}
    board = namespace('board')
    vision = namespace('board.vision')
    board.vision = vision
    binding = original_module('board.vision.native_binding', 'board/vision/native_binding.py',
                              raw_sources['board/vision/native_binding.py'])
    vision.native_binding = binding
    protection = original_module('board.vision.native_protection', 'board/vision/native_protection.py',
                                 raw_sources['board/vision/native_protection.py'])
    vision.native_protection = protection
    pin = {'path': str(CHECKPOINT), 'sha256': args.checkpoint_sha256}
    require(CHECKPOINT.is_file() and not CHECKPOINT.is_symlink() and CHECKPOINT.resolve() == CHECKPOINT,
            'Original checkpoint path redirects')
    before = CHECKPOINT.read_bytes()
    require(hashlib.sha256(before).hexdigest() == pin['sha256'], 'Original final checkpoint pin differs')
    marker = CHECKPOINT.with_name(CHECKPOINT.name + '.native-consumed-' + pin['sha256'])
    require(not os.path.lexists(str(marker)), 'A consumed marker or marker-path object already exists')
    # Complete ORIGINAL Python validator, with the actual current monotonic clock.
    # No now_ns override, consume_checkpoint, NativeContext or runner call.
    loaded = protection.load_business_checkpoint(pin, boot_id=boot)
    require(loaded['sha256'] == pin['sha256'] and loaded['document'] == json.loads(before),
            'Original reader returned different checkpoint state')
    require(CHECKPOINT.read_bytes() == before and not os.path.lexists(str(marker)),
            'Checkpoint or marker changed during read-only validation')
    require(set(name for name in sys.modules if name == 'board' or name.startswith('board.')) ==
            {'board', 'board.vision', 'board.vision.native_binding', 'board.vision.native_protection'},
            'Unexpected project module was imported')
    print(json.dumps({'scope': 'ORIGINAL_PYTHON_VALIDATOR_ONLY_NO_RESTORE', 'boot_id': boot,
                      'checkpoint_pin': pin, 'source_sha256': PINS, 'loaded': loaded,
                      'board_mutations': False, 'checkpoint_consumed': False,
                      'native_context_created': False, 'device_opened': False,
                      'database_opened': False}, sort_keys=True))


if __name__ == '__main__':
    main()
