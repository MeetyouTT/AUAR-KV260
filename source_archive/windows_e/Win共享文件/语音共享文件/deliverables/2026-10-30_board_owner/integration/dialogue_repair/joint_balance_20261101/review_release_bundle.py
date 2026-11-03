"""Main chat's local-only exact bundle review; never executes the publisher."""
import base64
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
PACKAGE = PROJECT / 'deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/package/single_projection'
EXPECTED_BUNDLE = '7da0fb13cd0694270ad2c34989f54a65ad9cb529ec7f7be5a6fa000d101af8d7'
CHANGED = 'tools/production_memory_presentation.py'
ROOT = '/home/root/aura-board-business-20261030/production-5259eab11e42af13'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    return json.loads((PACKAGE / name).read_text(encoding='utf-8'))


def main():
    raw = (PACKAGE / 'BUNDLE_MANIFEST.json').read_bytes()
    assert digest(raw) == EXPECTED_BUNDLE
    bundle = json.loads(raw)
    for relative, pin in bundle['files'].items():
        path = (PACKAGE / relative).resolve(strict=True)
        assert path.is_relative_to(PACKAGE.parents[1])
        assert digest(path.read_bytes()) == pin, relative
    base, candidate = read('base_spec.json'), read('candidate_spec.json')
    old_startup, new_startup = read('base_startup.json'), read('candidate_startup.json')
    old_manifest, new_manifest = read('base_manifest.json'), read('candidate_manifest.json')
    assert digest((PACKAGE / 'base_spec.json').read_bytes()) == '8ef2aa320d9ca2cf5a05e6b8b74458dfa7cf8c56be4efbebca69eed1102e2428'
    assert base['startup_sha256'] == '226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15'
    old_pins, new_pins = base['component_sha256'], candidate['component_sha256']
    assert len(old_pins) == len(new_pins) == 380 and old_pins.keys() == new_pins.keys()
    changed = [key for key in old_pins if old_pins[key] != new_pins[key]]
    assert changed == [CHANGED]
    assert old_pins[CHANGED] == '414ed67c68ad5f6ad3e0f89608e4f7ccef71d7b8765dfffc4f071eb806cc081a'
    assert new_pins[CHANGED] == '984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'
    assert old_startup['component_sha256'] == old_pins and new_startup['component_sha256'] == new_pins
    assert old_manifest['component_pins'] == old_pins and new_manifest['component_pins'] == new_pins
    assert (PACKAGE / 'payload/production_memory_presentation.py').read_bytes() == (HERE / 'presentation_candidate' / CHANGED).read_bytes()
    assert (PACKAGE / 'rollback/production_memory_presentation.py').read_bytes() == (HERE / 'baseline' / CHANGED).read_bytes()
    assert base['target'] == candidate['target'] == ROOT
    gui_pin = 'a695d620ddad3216de2d0447ec91d0e983a67343c2282179adece8014fccc063'
    assert base['configuration_sha256'] == candidate['configuration_sha256'] == gui_pin
    assert digest((PACKAGE / 'gui.json').read_bytes()) == gui_pin
    targets = {
        'production_memory_presentation.py': ('payload/production_memory_presentation.py', 'rollback/production_memory_presentation.py', ROOT + '/runtime/aura/' + CHANGED),
        'startup-config.json': ('candidate_startup.json', 'base_startup.json', ROOT + '/startup/config.json'),
        'production-source-manifest.json': ('candidate_manifest.json', 'base_manifest.json', ROOT + '/production_source_manifest.json'),
    }
    plans = [read('forward_plan.json'), read('rollback_plan.json')]
    assert plans[0]['allow_known_mixed_on_first_apply'] is False
    assert plans[1]['allow_known_mixed_on_first_apply'] is True
    for plan in plans:
        assert set(plan['targets']) == set(targets)
        for label, (new, old, target_path) in targets.items():
            if plan['direction'] == 'rollback':
                new, old = old, new
            row = plan['targets'][label]
            payload = base64.b64decode(row['new_base64'], validate=True)
            assert row['path'] == target_path
            assert digest(payload) == row['new_sha256'] == digest((PACKAGE / new).read_bytes())
            assert row['old_sha256'] == digest((PACKAGE / old).read_bytes())
            assert payload == (PACKAGE / new).read_bytes()
    for name, data in (('candidate_startup.json', candidate['startup_sha256']),
                       ('candidate_manifest.json', candidate['source_manifest_sha256'])):
        assert digest((PACKAGE / name).read_bytes()) == data
    source_review = json.loads((HERE / 'SOURCE_REVIEW_DECISION.json').read_text(encoding='utf-8'))
    assert source_review['candidate_sha256'] == new_pins[CHANGED]
    independent = HERE / 'independent_review/REVIEW.json'
    assert digest(independent.read_bytes()) == source_review['independent_review_sha256']
    assert json.loads(independent.read_text(encoding='utf-8'))['status'] == 'PASS_FIXED_380_COMPONENT_SCOPE'
    receipt = dict(schema='aura-joint-single-source-internal-review-1', status='APPROVED_FOR_SERIAL_OPERATOR',
                   bundle_manifest_sha256=EXPECTED_BUNDLE, candidate_source_sha256=new_pins[CHANGED],
                   base_spec_sha256=digest((PACKAGE / 'base_spec.json').read_bytes()),
                   candidate_spec_sha256=digest((PACKAGE / 'candidate_spec.json').read_bytes()),
                   candidate_startup_sha256=candidate['startup_sha256'],
                   candidate_manifest_sha256=candidate['source_manifest_sha256'],
                   unchanged_components=379, changed_source=CHANGED,
                   forward_and_exact_or_known_partial_rollback_reviewed=True,
                   normal_WM_DELETE_only_no_forced_kill=True,
                   preserve_pause_camera_firmware_and_motion_output_disabled=True,
                   required_operator_thread='01a195e4-58a7-72d3-b141-d5d373579f7f',
                   approved_scope='Exact bundle normal guarded one-source release and rollback; same-method passive postcheck',
                   real_speech_resume='User-authorized only when live measurement is ready',
                   production_or_device_access_by_reviewer=False)
    destination = HERE / 'SERIAL_OPERATOR_REVIEW.json'
    with destination.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(path=str(destination), sha256=digest(destination.read_bytes()), **receipt)))


if __name__ == '__main__':
    main()
