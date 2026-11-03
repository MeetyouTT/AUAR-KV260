import ast,copy,difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
relative='tools/unified_identity_binding.py'
before=(HERE/'baseline'/relative).read_bytes();after=(HERE/'candidate'/relative).read_bytes()
assert hashlib.sha256(before).hexdigest()=='f083fe8b618f4b09dce1587b3c32bf47f92510948e728615ce989ef31a1757cf'
ast.parse(after.decode('utf-8'))
(HERE/'CANDIDATE.diff').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),
    fromfile='production/'+relative,tofile='candidate/'+relative)),encoding='utf-8')
path=HERE/'SOURCE_MANIFEST.json';manifest=json.loads(path.read_text(encoding='utf-8'))
manifest.update(revision='v2',status='LOCAL_V2_CANDIDATE_TESTS_PENDING',
    v1_archive='v1/ARCHIVE_MANIFEST.json',
    v1_review_hold='Original hub also supports two whole voice-identity queries absent from the shared face-query predicate',
    shared_predicate='tools.provisional_voice.query_reply(text, {state: UNKNOWN}) is not None')
manifest['files'][relative]={'before_sha256':hashlib.sha256(before).hexdigest(),'sha256':hashlib.sha256(after).hexdigest(),'bytes':len(after)}
path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
observed=json.loads((HERE.parent/'parallel_platform/gui_startup_review/gui_bootstrap_01.json').read_text(encoding='utf-8'))['board_result']
startup=json.loads(observed['files']['/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json']['text'])
startup['component_sha256']['config/board_avatar_gtk.json']='fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
serialize=lambda value:(json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8')
assert hashlib.sha256(serialize(startup)).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
new=copy.deepcopy(startup);new['component_sha256'][relative]=hashlib.sha256(after).hexdigest()
predicted={'source_before_sha256':hashlib.sha256(before).hexdigest(),'source_after_sha256':hashlib.sha256(after).hexdigest(),
    'startup_before_sha256':hashlib.sha256(serialize(startup)).hexdigest(),'startup_after_sha256':hashlib.sha256(serialize(new)).hexdigest(),
    'changed_component_keys':[relative],'component_count':len(new['component_sha256'])}
(HERE/'PREDICTED_STARTUP_V2.json').write_text(json.dumps(predicted,indent=2)+'\n',encoding='utf-8')
print(json.dumps(predicted))
