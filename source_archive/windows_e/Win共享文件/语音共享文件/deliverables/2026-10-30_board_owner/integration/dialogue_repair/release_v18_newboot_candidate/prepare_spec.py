"""Create local source-bound specs for root review. Never imports SSH."""
import argparse
import copy
import json
from pathlib import Path

import publish_newboot as publisher


def prepare():
    spec = json.loads((publisher.REPAIR / 'release_v18_candidate/v18_spec.json').read_bytes())
    receipt = json.loads((publisher.REPAIR / 'progress_followup_20261031/new_boot_readback_written_1793494938568495700.json').read_bytes())
    assert receipt['ready'] is True and receipt['written'] is True
    spec.update(boot_id=publisher.NEW_BOOT, previous_boot_id=publisher.OLD_BOOT,
        new_boot_state='PREPARE', source_overrides={}, camera_owner=receipt['owner'],
        face_readback={'path': '/home/root/aura-board-owner-candidate-20261030/private-pin-bebd3e7d-1335-20261031/face_gallery_readback.local.json',
            'sha256': receipt['candidate_sha256']}, component_sha256=publisher.inputs()[0])
    return publisher.validate_spec(spec, 'guard-failed')


def proposed(overrides):
    spec = prepare()
    pins, startup, gui = publisher.inputs()
    spec['source_overrides'] = {}
    for rel, path in overrides.items():
        if rel not in publisher.ALLOWED_OVERRIDES:
            raise ValueError('unreviewed_source_override')
        path = Path(path).resolve(strict=True)
        raw = path.read_bytes()
        spec['source_overrides'][rel] = {'local_source': str(path), 'before_sha256': pins[rel], 'sha256': publisher.sha(raw)}
        spec['release_sources'][rel] = publisher.sha(raw)
        pins[rel] = publisher.sha(raw)
    gui['board_business']['face_readback'] = spec['face_readback']
    spec['configuration_sha256'] = publisher.sha(publisher.encoded(gui))
    pins['config/board_avatar_gtk.json'] = spec['configuration_sha256']
    spec['component_sha256'] = pins
    startup['component_sha256'] = pins
    spec.update(startup_sha256=publisher.sha(publisher.encoded(startup)), source_manifest_sha256='0' * 64,
        new_boot_state='APPLIED', previous_startup_sha256=publisher.BASE_STARTUP,
        previous_source_manifest_sha256=publisher.BASE_MANIFEST)
    return publisher.validate_spec(spec, 'start')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--override', action='append', default=[])
    parser.add_argument('--proposed-applied', action='store_true')
    args = parser.parse_args()
    overrides = {}
    for item in args.override:
        rel, path = item.split('=', 1)
        if rel in overrides:
            raise ValueError('duplicate_override')
        overrides[rel] = path
    if overrides and not args.proposed_applied:
        parser.error('--override requires --proposed-applied')
    value = proposed(overrides) if args.proposed_applied else prepare()
    raw = publisher.encoded(value)
    with args.output.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status':'LOCAL_SPEC_PREPARED_NO_SSH','path':str(args.output), 'sha256':publisher.sha(raw),
        'manifest_sha_requires_apply_receipt':args.proposed_applied},ensure_ascii=True))


if __name__ == '__main__':
    main()
