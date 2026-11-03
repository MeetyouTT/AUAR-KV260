"""Build a narrow, hash-pinned overlay; never write frozen/core sources."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
DEFAULT_CANDIDATE = HERE.parent/'production_business_overlay'/'candidate'/'aura'
FILES = ('tools/board_avatar_gtk.py', 'board/runtime/audio/board_dialogue_jobs.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Frozen source seam changed')
    return text.replace(old, new, 1)


def gtk_patch(text):
    text = replace_once(text,
        '                self.board_business.bind_recording(recording)\n',
        '                self.board_business.bind_recording(recording)\n'
        '                from tools.production_memory_presentation import bind_presentation\n'
        '                bind_presentation(self,recording)\n')
    text = replace_once(text, '            self.build_window(windowed)\n',
        '            self.build_window(windowed)\n'
        '            from tools.production_memory_presentation import attach_presentation\n'
        '            attach_presentation(self)\n')
    text = replace_once(text, '            project_business_ui(self,state)\n',
        '            project_business_ui(self,state)\n'
        '            from tools.production_memory_presentation import project_presentation\n'
        '            state=project_presentation(self,state)\n')
    text = replace_once(text, '    def save_evidence(self):\n',
        '    def save_evidence(self):\n'
        '        from tools.production_memory_presentation import save_production_evidence\n'
        '        metadata=save_production_evidence(self)\n'
        '        if metadata is not None:return metadata\n')
    text = replace_once(text, '    def cleanup(self):\n',
        '    def cleanup(self):\n'
        '        from tools.production_memory_presentation import close_presentation\n'
        '        close_presentation(self)\n')
    text = replace_once(text, "            message = type(exc).__name__+': '+str(exc)\n",
        "            message = (type(exc).__name__ if getattr(self,'production_presentation',None) is not None\n"
        "                       else type(exc).__name__+': '+str(exc))\n")
    return text


def jobs_patch(text):
    return replace_once(text,
        '            finally:\n                self._actions.task_done()\n\n    def reset_enrollment(self):\n',
        '            finally:\n                self._actions.task_done()\n'
        '                action = None  # Retire consumed plan/PCM, keep ACK ordering.\n\n'
        '    def reset_enrollment(self):\n')


def build(candidate=DEFAULT_CANDIDATE, output=HERE/'after'):
    candidate, output = Path(candidate).resolve(), Path(output).resolve()
    if candidate == output or candidate in output.parents:
        raise ValueError('Overlay cannot modify frozen candidate')
    pins = json.loads((HERE/'input_pins.json').read_text(encoding='utf-8'))
    module = PROJECT/'aura'/'tools'/'production_memory_presentation.py'
    inputs = {name: (candidate/name).read_bytes() for name in FILES}
    inputs['tools/production_memory_presentation.py'] = module.read_bytes()
    for name, raw in inputs.items():
        if sha(raw) != pins['files'][name]:
            raise ValueError('Input SHA changed: '+name)
    results = {
        FILES[0]: gtk_patch(inputs[FILES[0]].decode('utf-8').replace('\r\n', '\n')).encode('utf-8'),
        FILES[1]: jobs_patch(inputs[FILES[1]].decode('utf-8').replace('\r\n', '\n')).encode('utf-8'),
        'tools/production_memory_presentation.py': inputs['tools/production_memory_presentation.py'],
    }
    # Parse before any output is published; no runtime imports/side effects.
    for name, raw in results.items():
        ast.parse(raw.decode('utf-8'), filename=name, feature_version=(3, 9))
    for name, raw in inputs.items():
        path = module if name == 'tools/production_memory_presentation.py' else candidate/name
        if path.read_bytes() != raw:
            raise ValueError('Source changed during build')
    manifest = dict(schema='aura.production-presentation-overlay-1', revision=2,
        base_manifest_sha256=pins['base_manifest_sha256'],
        no_device_actions=True, database_content_changed=False,
        source_only=True, hard_display_ttl_seconds=300,
        diagnostics='private_root/diagnostics/latest_metadata.json (whitelist metadata only)',
        bridge_user_subtitles=False, active_audio_ack_semantics_changed=False,
        files=[])
    for name, raw in results.items():
        target = output/'aura'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        manifest['files'].append(dict(target='aura/'+name, source=str(target),
            bytes=len(raw), sha256=sha(raw), input_sha256=pins['files'][name]))
    (HERE/'overlay_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--candidate', type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument('--output', type=Path, default=HERE/'after')
    args = parser.parse_args()
    if not args.build:
        print(json.dumps(dict(source_only=True, build_requested=False)))
        return
    result = build(args.candidate, args.output)
    print(json.dumps(dict(result='BUILT_SOURCE_ONLY', files=len(result['files']))))


if __name__ == '__main__':
    main()
