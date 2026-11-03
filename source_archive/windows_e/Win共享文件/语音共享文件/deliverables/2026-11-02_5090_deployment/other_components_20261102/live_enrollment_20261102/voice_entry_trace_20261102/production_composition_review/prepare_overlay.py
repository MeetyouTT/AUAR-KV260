"""Independent public/synthetic runtime overlay; no original source modifications."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
LIVE=HERE.parent.parent
BASE=LIVE/'split_commands_20261102/actual_release/runtime'
CANDIDATE=HERE.parent/'candidate'
PRIOR=LIVE/'split_commands_20261102/production_composition_review'
DEST=HERE/'runtime'
EXPECTED={
 'board/runtime/board_business.py':(
  'ea4f4565f558e5e2b6a347360f362e7810dd5792b2d2fe7af3a26389e26514d7',
  'd034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc'),
 'board/runtime/audio/board_dialogue_jobs.py':(
  '43708b7fcbf72b11d7a37b01ae090c2cdb3e621b5f334151601206735a34a1fc',
  '580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464'),
}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def paths(root):return {
 p.relative_to(root).as_posix():sha(p) for p in root.rglob('*')
 if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

assert not DEST.exists(),'Use a fresh independent overlay directory'
before=paths(BASE)
for name,(old,new) in EXPECTED.items():
 assert before[name]==old and sha(CANDIDATE/name)==new,(name,'SHA mismatch')
shutil.copytree(BASE,DEST,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in EXPECTED:shutil.copyfile(CANDIDATE/name,DEST/name)
after=paths(DEST)
changed={name for name in before if before[name]!=after.get(name)}
assert before.keys()==after.keys() and changed==EXPECTED.keys()
assert paths(BASE)==before,'Original release must remain unchanged'
test=(PRIOR/'test_real_composition.py').read_text(encoding='utf-8')
changes={
 "RELEASE=HERE.parent/'actual_release/runtime'":"RELEASE=HERE/'runtime'",
 EXPECTED['board/runtime/board_business.py'][0]:EXPECTED['board/runtime/board_business.py'][1],
 "PINS={'board/runtime/board_business.py'":"PINS={'board/runtime/audio/board_dialogue_jobs.py':'580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464',\n 'common/binding_intent.py':'8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1',\n 'board/runtime/board_business.py'",
}
for old,new in changes.items():
 assert test.count(old)==1,(old,'test harness substitution must be exact')
 test=test.replace(old,new)
(HERE/'test_real_composition.py').write_text(test,encoding='utf-8')
manifest=dict(scope='local_synthetic_only',original_release_modified=False,
 overlay_changed_files={name:dict(before_sha256=before[name],after_sha256=after[name]) for name in sorted(changed)},
 original_release_sha256=before,overlay_sha256=after,
 original_test_sha256=sha(PRIOR/'test_real_composition.py'),
 overlay_test_sha256=sha(HERE/'test_real_composition.py'),
 test_changes_only=['independent runtime location','explicit business d034 pin','explicit Jobs580b and intent8048 pins'])
(HERE/'OVERLAY_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(after),changed=sorted(changed),original_release_modified=False)))
