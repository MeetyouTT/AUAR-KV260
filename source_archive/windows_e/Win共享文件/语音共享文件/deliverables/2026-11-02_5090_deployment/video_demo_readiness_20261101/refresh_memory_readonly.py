"""Derive the historical aggregate reader for the freshly restored GUI owner."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ORIGINAL = OUT / 'memory_speed_status_20261101/collect_memory_counts_readonly.py'
HELPER = OUT.parent / '2026-10-18_board_dialogue/board_ssh.py'
raw = ORIGINAL.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'c0c0ba101dc13e6456c1e2df2a9bf82efaddeb906e5933557aaacafac9bea646'
code = raw.decode('utf-8')
old = "0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f"
new = "3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5"
assert code.count(old) == 1
code = code.replace(old, new)
old = "assert services['aura-avatar-ui.service'] == {'MainPID': '0', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': ''}"
new = """assert services['aura-avatar-ui.service'] == {'MainPID': '82126', 'ActiveState': 'active', 'SubState': 'running', 'Job': ''}
gui_stat = Path('/proc/82126/stat').read_text()
gui_birth = gui_stat[gui_stat.rfind(')')+2:].split()[19]
assert gui_birth == '2524927'
gui_cmd = Path('/proc/82126/cmdline').read_bytes()
assert hashlib.sha256(gui_cmd).hexdigest() == '48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'
assert services['aura-camera-ui.service']['MainPID'] == '79866'
assert services['aura-camera-ui.service']['ActiveState'] == 'active'
assert services['aura-camera-ui.service']['SubState'] == 'running'"""
assert code.count(old) == 1
code = code.replace(old, new)
old = 'assert (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)'
new = """metadata_unchanged = (before.st_size, before.st_mtime_ns, before.st_ino) == (after.st_size, after.st_mtime_ns, after.st_ino)
assert Path('/proc/82126/cmdline').read_bytes() == gui_cmd
assert Path('/proc/82126/stat').read_text().rsplit(')', 1)[1].split()[19] == gui_birth"""
assert code.count(old) == 1
code = code.replace(old, new)
code = code.replace("'database_file_metadata_unchanged': True", "'database_file_metadata_unchanged': metadata_unchanged, 'live_gui_writer_may_update_database': True")
code = code.replace("'aura-production-memory-aggregate-readonly-1'", "'aura-production-memory-aggregate-readonly-live-gui-2'")
compile(code, '<derived-memory-reader>', 'exec')
derived = HERE / 'collect_memory_current_readonly.py'
derived.write_text(code, encoding='utf-8')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('board_transport', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = json.loads(module.ssh('/usr/bin/python3 -B -I -S -', code, timeout=30))
receipt = {
    'host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'historical_reader_sha256': hashlib.sha256(raw).hexdigest(),
    'derived_reader_sha256': hashlib.sha256(code.encode()).hexdigest(),
    'adaptation': 'Fresh startup and active GUI owner verified. Snapshot remains mode=ro/query_only. Live writer metadata changes are reported, never mistaken for reader writes.',
    'board_result': result,
}
destination = HERE / 'MEMORY_CURRENT_READONLY.json'
with destination.open('x', encoding='utf-8') as handle:
    json.dump(receipt, handle, indent=2, ensure_ascii=False)
print(json.dumps({'path': str(destination), 'counts': result['counts'], 'quick_check_ok': result['quick_check_ok'], 'utc': result['utc']}, ensure_ascii=False))
