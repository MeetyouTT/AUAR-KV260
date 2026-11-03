"""Build source-only board integration; no board, services, databases or models."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent / 'realtime_dialogue_research/first_wait_candidate'
PINS = {
    'tools/production_board_business_gui.py': 'ff624a31f60c043fd02d6648c65cad8bce473aa525ef97ce1923545dc342aa66',
    'board/runtime/board_dialogue_client.py': '38220eb34939e63b3ebcff4ccef4d8b3ddefb22ce74c98f9224244894dad44f6',
    'common/model_inference_wire.py': '0786eb20e13b88c59572cde507532d760cd7d2eb24434e904845e73be99d7255',
}
REVIEWED = {
    'candidate/compact_request_adapter.py': 'ea14001af904f80a4ca247cc5ee738f7418fd0bd0aa4ee30e5aaea13fbc31337',
    'candidate/inference_output_contract.py': 'e07936da0f3e333c4a448a2b36b70cdfecb76939449c8cdbefffe11b9244c631',
    'after/common/model_inference_wire.py': '39306c53a967f21e318f34d5642f126e8f047ee90112ac5bb83f981965aab965',
}


def checked(path, sha):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('pinned_source_changed')
    return raw


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('exact_patch_context_changed')
    return text.replace(before, after)


def main():
    baseline = json.loads((HERE / 'baseline_manifest.json').read_bytes())
    texts = {}
    for name, sha in PINS.items():
        if baseline['component_sha256'][name] != sha:
            raise ValueError('live_component_pin_changed')
        texts[name] = checked(HERE / 'before' / name, sha).decode('utf-8')
    dependency = {name: checked(RESEARCH / name, sha) for name, sha in REVIEWED.items()}
    client = texts['board/runtime/board_dialogue_client.py']
    client = once(client, '        self._date_proof_lock = threading.Lock()\n        self._date_proof = None\n',
                  '        self._date_proof_lock = threading.Lock()\n        self._date_proof = None\n'
                  '        self._output_format_capabilities = None\n')
    marker = '    def sample_health_date(self, timeline_clock, *, deadline, cancelled=lambda: False,\n'
    methods = '''    @staticmethod
    def _health_output_capabilities(body):
        backend = body.get('backend')
        if not isinstance(backend, dict):
            return None
        version, formats = backend.get('format_contract_version'), backend.get('output_formats')
        if (type(version) is not int or version != 1 or not isinstance(formats, list)
                or not 1 <= len(formats) <= 3
                or any(not isinstance(item, str) or item not in
                       ('json', 'dialogue_schema_v1', 'dialogue_abc_v1') for item in formats)
                or len(set(formats)) != len(formats) or 'json' not in formats):
            return None
        return dict(format_contract_version=1, output_formats=list(formats))

    def output_format_capabilities(self):
        """Detached white-list from the existing fully verified Date response.

        This is metadata, never an HTTP operation or authorization grant.
        """
        with self._date_proof_lock:
            value = self._output_format_capabilities
            return (dict(format_contract_version=1, output_formats=list(value['output_formats']))
                    if value is not None else None)

'''
    client = once(client, marker, methods + marker)
    client = once(client, '        control, response, proof = None, None, None\n',
        '        control, response, proof = None, None, None\n'
        '        with self._date_proof_lock:\n'
        '            self._output_format_capabilities = None\n')
    client = once(client, '            control.check()\n            return result\n',
        '            control.check()\n'
        '            with self._date_proof_lock:\n'
        '                self._output_format_capabilities = self._health_output_capabilities(body)\n'
        '            return result\n')
    gui = texts['tools/production_board_business_gui.py']
    gui = once(gui, "        optional = {'model_port', 'timeout_ms', 'timezone', 'entry_mode', 'asr_threads',\n",
        "        optional = {'model_port', 'timeout_ms', 'timezone', 'entry_mode', 'asr_threads', 'dialogue_output_format',\n")
    gui = once(gui, "        from tools.production_frontend_selection import validate_frontend_options\n",
        "        from tools.production_output_format import validate_dialogue_output_format, install_dialogue_output\n"
        "        self.dialogue_output_format = validate_dialogue_output_format(value.get('dialogue_output_format', 'json'))\n"
        "        self.dialogue_output = None\n"
        "        from tools.production_frontend_selection import validate_frontend_options\n")
    gui = once(gui, '            self.runtime.initialize_clock(timeout=3.)\n',
        '            self.runtime.initialize_clock(timeout=3.)\n'
        '            self.dialogue_output = install_dialogue_output(self.runtime,\n'
        '                mode=self.dialogue_output_format, system_prompt=self.character_pair.selected_prompt)\n')
    outputs = {
        'tools/production_board_business_gui.py': gui.encode('utf-8'),
        'board/runtime/board_dialogue_client.py': client.encode('utf-8'),
        'common/model_inference_wire.py': dependency['after/common/model_inference_wire.py'],
        'common/inference_output_contract.py': dependency['candidate/inference_output_contract.py'],
        'board/runtime/compact_request_adapter.py': dependency['candidate/compact_request_adapter.py'],
    }
    helper = HERE / 'after/tools/production_output_format.py'
    outputs['tools/production_output_format.py'] = helper.read_bytes()
    manifest = {}
    for name, raw in outputs.items():
        ast.parse(raw, filename=name, feature_version=(3, 9))
        target = HERE / 'after' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        manifest[name] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                              before_sha256=PINS.get(name))
    (HERE / 'candidate_manifest.json').write_bytes((json.dumps(dict(
        baseline_startup_sha256=baseline['startup_sha256'], sources=manifest,
        reviewed_dependencies=REVIEWED, board_memory_policy_modified=False),
        indent=2) + '\n').encode())
    (HERE / 'extra_source_map.json').write_bytes((json.dumps(
        {name: str((HERE / 'after' / name).resolve()) for name in outputs},
        ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    (HERE / 'config.fragment.json').write_bytes(b'{"dialogue_output_format":"json"}\n')
    print(json.dumps(dict(status='BOARD_SOURCE_CANDIDATE_BUILT', sources=manifest)))


if __name__ == '__main__':
    main()
