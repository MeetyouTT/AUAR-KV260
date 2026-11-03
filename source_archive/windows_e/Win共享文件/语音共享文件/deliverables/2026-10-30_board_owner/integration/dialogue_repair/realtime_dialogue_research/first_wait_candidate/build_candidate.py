"""Freeze public source and build REVIEW-ONLY overlays under this folder."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[5]
AURA = PROJECT / 'aura'
SOURCES = {
    'tools/model_inference_host.py': '1bdb20045ac07950840dafc478679efbdce3c295765189280ac5c95c9d6f9bd1',
    'common/model_inference_wire.py': '0786eb20e13b88c59572cde507532d760cd7d2eb24434e904845e73be99d7255',
    'board/runtime/board_memory_policy.py': '9af4a5bfc4a039db55d8e46e08ce994e04091a0653919886fb04c23f39f94d54',
}


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('unexpected_source_shape')
    return text.replace(before, after, 1)


def method_dumps(text, class_name, excluded):
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            node.body = [child for child in node.body
                         if not isinstance(child, ast.FunctionDef) or child.name not in excluded]
    return ast.dump(tree)


def build():
    texts, pins = {}, {}
    for target, expected in SOURCES.items():
        reference = ROOT / 'reference' / target
        if reference.exists():
            raw = reference.read_bytes()
        else:
            raw = (AURA / target).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('source_pin_changed_before_freeze')
            reference.parent.mkdir(parents=True, exist_ok=True)
            reference.write_bytes(raw)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('frozen_source_mismatch')
        texts[target] = raw.decode('utf-8').replace('\r\n', '\n')
        pins[target] = {'sha256': expected, 'reference': str(reference.relative_to(ROOT)),
                        'live_public_source_still_matches': hashlib.sha256((AURA / target).read_bytes()).hexdigest() == expected}

    host = texts['tools/model_inference_host.py']
    body_start = "        options = payload['options']\n        body = chat_body(self.model, '', '', fast=True)\n        body.update(messages=payload['messages'], stream=True, format='json', keep_alive=-1,\n                    think=options.get('think', False))\n        body['options']['num_predict'] = options.get('num_predict', 512 if payload['task'] == 'summary' else 120)"
    body_new = "        from common.inference_output_contract import build_body, StreamObservation\n        body = build_body(chat_body(self.model, '', '', fast=True), payload)\n        observation = (StreamObservation(time.monotonic())\n                       if 'output_format' in payload['options'] else None)"
    host = replace_once(host, body_start, body_new)
    host = replace_once(host, "                    raise RuntimeError('backend_failed')\n                message = packet.get('message') or {}",
                        "                    raise RuntimeError('backend_failed')\n                if observation is not None:\n                    observation.packet(packet, time.monotonic())\n                message = packet.get('message') or {}")
    host = replace_once(host, "                    return {'text': ''.join(chunks), 'metrics': metrics}",
                        "                    if observation is not None:\n                        metrics.update(observation.finish(packet))\n                    return {'text': ''.join(chunks), 'metrics': metrics}")
    host = replace_once(host, '                from common.gpu_coordination import GpuBusy\n                code = (',
                        '                from common.gpu_coordination import GpuBusy\n                from common.inference_output_contract import OutputTruncated\n                code = (\'backend_output_truncated\' if isinstance(exc, OutputTruncated) else\n                        ')
    host = replace_once(host, "        return dict(model=self.model, tts='omnivoice', num_step=16,",
                        "        return dict(model=self.model, tts='omnivoice', num_step=16,\n                    format_contract_version=1, output_formats=['json', 'dialogue_schema_v1', 'dialogue_abc_v1'],")
    # All other methods, including foreground admission, TTS ownership and GPU
    # lifecycle, must be byte-equivalent at the AST level.
    def host_rest(text):
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                exclude = ({'_ollama', 'health'} if node.name == 'LocalModelBackend'
                           else {'_run'} if node.name == 'InferenceHost' else set())
                node.body = [child for child in node.body
                             if not isinstance(child, ast.FunctionDef) or child.name not in exclude]
        return ast.dump(tree)
    if host_rest(host) != host_rest(texts['tools/model_inference_host.py']):
        raise ValueError('unexpected_host_ast_delta')

    wire = texts['common/model_inference_wire.py']
    wire = replace_once(wire, "set(options) - {'think', 'num_predict'}", "set(options) - {'think', 'num_predict', 'output_format'}")
    marker = "    if 'num_predict' in options and (type(options['num_predict']) is not int or not 1 <= options['num_predict'] <= 1024):"
    wire = replace_once(wire, marker,
        "    if 'output_format' in options:\n        from common.inference_output_contract import FORMATS\n        mode = options['output_format']\n        if (not isinstance(mode, str) or mode not in FORMATS\n                or payload['task'] != 'dialogue' or options.get('think', False)):\n            raise WireError('invalid_options')\n" + marker)
    wire = replace_once(wire, "                       'eval_duration_ms', 'total_duration_ms'}\n            metrics = result['metrics']",
        "                       'eval_duration_ms', 'total_duration_ms'}\n            from common.inference_output_contract import EXTRA_METRICS\n            allowed |= EXTRA_METRICS\n            metrics = result['metrics']")

    prefix = replace_once(texts['board/runtime/board_memory_policy.py'],
                          '        messages = [system] + notes + recent + [current]',
                          '        messages = [system] + recent + notes + [current]')
    # Separate optional experiment: same selected inputs/notes and cost, only
    # final prompt order changes. No summary, command or memory logic changes.
    if method_dumps(prefix, 'BoardContextBuilder', {'__call__'}) != method_dumps(texts['board/runtime/board_memory_policy.py'], 'BoardContextBuilder', {'__call__'}):
        raise ValueError('unexpected_prefix_ast_delta')
    outputs = {'tools/model_inference_host.py': host, 'common/model_inference_wire.py': wire}
    for target, source in outputs.items():
        path = ROOT / 'after' / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8', newline='\n')
    prefix_path = ROOT / 'optional_prefix/board/runtime/board_memory_policy.py'
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    prefix_path.write_text(prefix, encoding='utf-8', newline='\n')
    new_targets = {'common/inference_output_contract.py': 'candidate/inference_output_contract.py',
                   'board/runtime/compact_request_adapter.py': 'candidate/compact_request_adapter.py'}
    delta = ''
    for target, source in outputs.items():
        delta += ''.join(difflib.unified_diff(texts[target].splitlines(keepends=True), source.splitlines(keepends=True), fromfile='a/'+target, tofile='b/'+target))
    for target, local in new_targets.items():
        source = (ROOT / local).read_text(encoding='utf-8')
        delta += ''.join(difflib.unified_diff([], source.splitlines(keepends=True), fromfile='/dev/null', tofile='b/'+target))
    (ROOT / 'output_contract_review.patch').write_text(delta, encoding='utf-8', newline='\n')
    (ROOT / 'prefix_order_separate.patch').write_text(''.join(difflib.unified_diff(
        texts['board/runtime/board_memory_policy.py'].splitlines(keepends=True), prefix.splitlines(keepends=True),
        fromfile='a/board/runtime/board_memory_policy.py', tofile='b/board/runtime/board_memory_policy.py')), encoding='utf-8', newline='\n')
    (ROOT / 'SOURCE_PINS.json').write_text(json.dumps(pins, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'REVIEW_OVERLAYS_BUILT_NOT_APPLIED', 'source_pins': len(pins),
                      'output_patch_bytes': len(delta.encode('utf-8')), 'optional_prefix_separate': True}))


if __name__ == '__main__':
    build()
