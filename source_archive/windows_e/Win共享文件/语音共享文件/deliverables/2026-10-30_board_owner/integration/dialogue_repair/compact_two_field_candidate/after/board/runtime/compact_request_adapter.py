"""Optional BOARD-only model-client wrapper; no early audio or new authority.

The root injects the exact already-selected static system prompt. Only its
output field names can change; user/history/reference data are never edited.
"""
import copy
import re

from common.model_inference_wire import Owner, validate_request, validate_response
from common.inference_output_contract import canonicalize_compact, OutputContractError


class CompactRequestAdapter:
    def __init__(self, transport, *, system_prompt, capabilities, mode='dialogue_abc_v1'):
        if mode not in {'json', 'dialogue_schema_v1', 'dialogue_abc_v1', 'dialogue_ab_v1'}:
            raise ValueError('invalid_adapter_mode')
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError('require_exact_static_prompt')
        if (not isinstance(capabilities, dict) or type(capabilities.get('format_contract_version')) is not int
                or capabilities['format_contract_version'] != 1
                or not isinstance(capabilities.get('output_formats'), (list, tuple))
                or mode not in capabilities['output_formats']):
            raise ValueError('output_format_not_negotiated')
        self.transport, self.system_prompt, self.mode = transport, system_prompt, mode
        translated = system_prompt
        for canonical, alias in (('reply_text', 'a'), ('emotion', 'b'), ('avatar_action', 'c')):
            pattern = r'(?<![A-Za-z0-9_])' + canonical + r'(?![A-Za-z0-9_])'
            translated, count = re.subn(pattern, alias, translated)
            if not count:
                raise ValueError('static_prompt_contract_missing')
        if mode == 'dialogue_ab_v1':
            # The selected board persona has exactly this fixed empty-action
            # clause. Remove that redundant output obligation, never a policy.
            if translated.count('c为空字符串') != 1:
                raise ValueError('static_empty_action_contract_missing')
            translated = translated.replace('c为空字符串', '不输出动作字段', 1)
        self.translated_prompt = translated

    def request(self, kind, payload, *, deadline, cancelled):
        original = validate_request(kind, payload)
        route = (kind == 'llm' and original['task'] == 'dialogue'
                 and not original['options'].get('think', False)
                 and original['messages'][0] == {'role': 'system', 'content': self.system_prompt}
                 and 'output_format' not in original['options'])
        sent = original
        if route:
            sent = copy.deepcopy(original)
            sent['options']['output_format'] = self.mode
            if self.mode in ('dialogue_abc_v1', 'dialogue_ab_v1'):
                sent['messages'][0]['content'] = self.translated_prompt
            sent = validate_request(kind, sent)
        response = self.transport.request(kind, sent, deadline=deadline, cancelled=cancelled)
        checked = validate_response(response, Owner.from_dict(original), kind)
        if route and self.mode in ('dialogue_abc_v1', 'dialogue_ab_v1') and checked['ok']:
            if cancelled():
                raise InterruptedError('cancelled_before_compact_decode')
            # No fallback/retry model request on malformed compact output.
            checked = copy.deepcopy(checked)
            checked['result']['text'] = canonicalize_compact(checked['result']['text'], mode=self.mode)
            checked = validate_response(checked, Owner.from_dict(original), kind)
        return checked

    def cancel(self, owner):
        return self.transport.cancel(owner)

    def __getattr__(self, name):
        # Preserve public transport health/date/reconfiguration hooks. No
        # authorization, cache result or model-generated provenance is stored.
        return getattr(self.transport, name)
