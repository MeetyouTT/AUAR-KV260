"""Prepare a paired preview-only projection without changing general UI reads."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
METHOD = b'''
    def read_preview(self):
        """Fresh display-only metadata; omit dialogue, identities and intents.

        The gate owns a validated detached snapshot. Read its source deadline
        under the same lock on every call; never cache or extend freshness.
        Commands and identity bindings continue through their original reads.
        """
        with self.condition:
            value = self.gate.value if self.link == 'READY' else None
            if value is None or self.clock() >= value['observed_mono_ms'] + value['ttl_ms']:
                return {'snapshot': None, 'preview': None, 'raw_preview': False}
            camera = value['modules'].get('camera', {})
            frame = value.get('preview')
            snapshot = {
                'board_boot_id': value['board_boot_id'],
                'service_epoch': value['service_epoch'],
                'source_kind': value['source_kind'],
                'modules': {'camera': {key: camera[key] for key in
                    ('state', 'preview_transport') if key in camera}},
                'preview': dict(frame) if frame is not None else None,
            }
            preview = self.preview if frame is not None and frame == self.preview_key else None
            if preview and self.clock() - frame['captured_mono_ms'] > 1500:
                preview = None
            return {'snapshot': snapshot, 'preview': preview,
                    'raw_preview': self.use_raw(snapshot, self.connection)}

'''


def main():
    index = json.loads((HERE / 'source_index.json').read_text(encoding='utf-8'))
    changes = {}
    for relative in ('board/interaction/ui_services.py', 'tools/board_camera_preview.py'):
        before = (HERE / 'baseline' / relative).read_bytes()
        assert hashlib.sha256(before).hexdigest() == index['files'][relative]['sha256']
        if relative.endswith('ui_services.py'):
            anchor = b'    def identity_snapshot(self):'
            assert before.count(anchor) == 1 and b'def read_preview(' not in before
            after = before.replace(anchor, METHOD + anchor, 1)
        else:
            anchor = b"                view=self.services.read();snapshot=view['snapshot']"
            assert before.count(anchor) == 1
            after = before.replace(anchor,
                b"                reader=getattr(self.services,'read_preview',None)\n"
                b"                view=reader() if reader is not None else self.services.read()\n"
                b"                snapshot=view['snapshot']", 1)
        ast.parse(after.decode('utf-8'))
        path = HERE / 'preview_candidate' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == after
        else:
            with path.open('xb') as handle:
                handle.write(after)
        changes[relative] = dict(before_sha256=hashlib.sha256(before).hexdigest(),
                                 after_sha256=hashlib.sha256(after).hexdigest(),
                                 before_bytes=len(before), after_bytes=len(after))
    evidence = dict(schema='aura-preview-projection-candidate-1',
                    status='LOCAL_CANDIDATE_NOT_DEPLOYED',
                    baseline_startup=index['startup_sha256'], files=changes,
                    general_read_or_identity_or_command_changed=False,
                    camera_detector_or_render_cadence_changed=False,
                    source_time_deadlines_unchanged=True,
                    production_modified=False, device_access=False)
    (HERE / 'preview_candidate_manifest.json').write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence))


if __name__ == '__main__':
    main()
