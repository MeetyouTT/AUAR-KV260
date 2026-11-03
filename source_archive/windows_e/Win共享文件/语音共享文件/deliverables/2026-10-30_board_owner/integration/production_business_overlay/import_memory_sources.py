"""Copy only the independently frozen public migration source, never data."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
EXPECTED='87c8df8b1a4afb0f4d1096053cbb7db8f1a2c256b013d65c0974d5b1219ecd30'


def main():
    path=HERE.parent/'production_memory_handoff/HANDOFF.json';raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==EXPECTED
    manifest=json.loads(raw);payload={};fixtures={}
    for row in manifest['files']:
        source=PROJECT/row['path'];data=source.read_bytes()
        assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
        if row['path'].startswith('aura/'):
            payload[row['path'][5:]]=data
        else:
            fixtures[row['path']]=data
    for relative,data in payload.items():
        out=HERE/'production_modules'/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    for relative,data in fixtures.items():
        # Needed solely by the original relative-path synthetic fixture tests;
        # outside candidate/aura, so never included in the runtime overlay.
        out=HERE/'candidate'/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    (HERE/'memory_dependency_pins.json').write_text(json.dumps({'handoff_sha256':EXPECTED,
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in payload.items()},
        'test_only_helpers':{name:hashlib.sha256(data).hexdigest() for name,data in fixtures.items()},
        'actual_user_data_read_or_copied':False},indent=2)+'\n',encoding='utf8')
    print(json.dumps({'frozen_source_files':len(payload),'private_data_or_models_opened':False}))


if __name__=='__main__':main()
