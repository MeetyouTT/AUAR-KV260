"""Reuse the isolated candidate/test transport for the source-snapshot fix."""
import ast
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
prior=HERE.parent/'2026-10-19_enrollment_photo_archive'
raw=(prior/'prepare.py').read_text(encoding='utf-8')
match=re.search(r'^names=(\[.*\])$',raw,re.M)
names=ast.literal_eval(match.group(1))
names+=['aura/board/interaction/ui_services.py','aura/tests/framework/test_identity_capture_snapshot.py']
raw=raw[:match.start(1)]+repr(names)+raw[match.end(1):]
raw=raw.replace('/home/root/aura-enrollment-photos-20261019','/home/root/aura-identity-capture-snapshot-20261019')
raw=raw.replace("modules=['test_enrollment_photos'","modules=['test_identity_capture_snapshot','test_enrollment_photos'")
(HERE/'prepare.py').write_text(raw,encoding='utf-8')
raw=(prior/'run_pc_tests.py').read_text(encoding='utf-8')
raw=raw.replace("modules=('test_spoken_identity_query'","modules=('test_identity_capture_snapshot','test_board_ui_services','test_spoken_identity_query'")
(HERE/'run_pc_tests.py').write_text(raw,encoding='utf-8')
(HERE/'before/aura/board/identity').mkdir(parents=True,exist_ok=True)
raw=(prior/'stop_for_reload.py').read_text(encoding='utf-8')
(HERE/'stop_for_reload.py').write_text(raw,encoding='utf-8')
print(json.dumps({'source_files':len(names),'only_runtime_behavior_changes':['ui_services.py','board_avatar_gtk.py']}))
