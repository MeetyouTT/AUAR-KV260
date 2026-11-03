"""Root-only existing SQLite recovery under both exclusive maintenance locks."""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import fcntl,hashlib,json,os,pathlib,sqlite3,stat,subprocess,sys,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
private=pathlib.Path('/home/root/.local/share/aura-board-business')
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
raw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='12a26c81167ecee7293d0d9be77ec7834894d413f07bab6d8a27e4c8cdfe0392'
pins=json.loads(raw)['component_sha256'];assert len(pins)==379
for rel,pin in pins.items():
 path=root/'runtime/aura'/rel
 assert path.resolve()==path and hashlib.sha256(path.read_bytes()).hexdigest()==pin
unit=lambda:dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','Job'],text=True).splitlines())
def require_closed():
 state=unit();assert state['MainPID']=='0' and state['ActiveState']=='failed' and not state['Job']
 for path in pathlib.Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try: command=(path/'cmdline').read_bytes().split(b'\0')
  except (FileNotFoundError,ProcessLookupError):continue
  assert str(root/'runtime/aura/tools/board_avatar_pan.py').encode() not in command
require_closed()
info=private.stat();assert private.resolve()==private and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o700
sys.path.insert(0,str(root/'runtime/aura'))
from common.board_production_bootstrap import _private_file,verify_production_bootstrap
receipt=_private_file(private,'production-bootstrap.json')
receipt_sha='8933586747fa9283e36e596ca8084fdc0572228fe87c54e02eaa6e0cc36ebf2c'
assert hashlib.sha256(receipt.read_bytes()).hexdigest()==receipt_sha
database=_private_file(private,'timeline.sqlite3')
journal=_private_file(private,'timeline.sqlite3-journal')
assert journal.stat().st_size==66176
lock=_private_file(private,'writer.lock')
with open('/run/aura-production-publisher.lock','a') as publication,lock.open('r+b') as writer:
 fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
 fcntl.flock(writer,fcntl.LOCK_EX|fcntl.LOCK_NB)
 require_closed()
 before={'database_bytes':database.stat().st_size,'journal_bytes':journal.stat().st_size}
 connection=sqlite3.connect(database.as_uri()+'?mode=rw',uri=True,timeout=.15,isolation_level=None)
 try:
  connection.execute('PRAGMA query_only=ON')
  connection.execute('BEGIN')
  assert connection.execute('PRAGMA quick_check').fetchall()==[('ok',)]
  connection.rollback()
 finally:connection.close()
 proof=verify_production_bootstrap(private,receipt,receipt_sha)
 require_closed()
 assert proof['receipt_verified'] and proof['profiles_migration_verified']
 print(json.dumps({'status':'SQLITE_ENGINE_RECOVERY_AND_ORIGINAL_BOOTSTRAP_VERIFIED','observed_mono':time.monotonic(),
  'before':before,'after_database_bytes':database.stat().st_size,'journal_remaining':journal.exists(),
  'receipt_verified':proof['receipt_verified'],'profiles_migration_verified':proof['profiles_migration_verified'],
  'private_rows_exported':False,'application_write_statements':0,'database_created':False,'ui_started':False}))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-root-only', action='store_true')
    args = parser.parse_args()
    if not args.execute_root_only:
        print(json.dumps({'status':'DRY_NO_DEVICE_ACCESS'}))
    else:
        value = json.loads(ssh('python3 -B -', REMOTE, timeout=60))
        path = HERE / ('actual_sqlite_recovery_' + str(time.time_ns()) + '.json')
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
        print(json.dumps({'file':str(path),'result':value}))
