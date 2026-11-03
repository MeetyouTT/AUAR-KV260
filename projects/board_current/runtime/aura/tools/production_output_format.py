"""Opt-in dialogue format assembly using the existing verified health sample.

This module performs no IO, model operation, retry, early audio or policy work.
Summary/reasoning/TTS remain on their original transport and wire contracts.
"""
import threading

from board.runtime.compact_request_adapter import CompactRequestAdapter


def validate_dialogue_output_format(value):
    if not isinstance(value, str) or value not in ('json', 'dialogue_abc_v1'):
        raise ValueError('invalid_dialogue_output_format')
    return value


class NegotiatedDialogueClient:
    def __init__(self, transport, *, system_prompt, mode):
        self.mode = validate_dialogue_output_format(mode)
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError('require_exact_static_prompt')
        self.transport, self.system_prompt = transport, system_prompt
        self._adapter = None
        self._lock = threading.Lock()

    def _capabilities(self):
        getter = getattr(self.transport, 'output_format_capabilities', None)
        value = getter() if callable(getter) else None
        if (not isinstance(value, dict)
                or type(value.get('format_contract_version')) is not int
                or value['format_contract_version'] != 1
                or not isinstance(value.get('output_formats'), (list, tuple))
                or not 1 <= len(value['output_formats']) <= 3
                or any(not isinstance(item, str) or item not in
                       ('json', 'dialogue_schema_v1', 'dialogue_abc_v1')
                       for item in value['output_formats'])
                or len(set(value['output_formats'])) != len(value['output_formats'])
                or 'json' not in value['output_formats']):
            return None
        return dict(format_contract_version=1, output_formats=list(value['output_formats']))

    def public(self):
        capabilities = self._capabilities()
        enabled = bool(self.mode == 'dialogue_abc_v1' and capabilities
                       and self.mode in capabilities['output_formats'])
        return dict(metadata_only=True, configured_format=self.mode,
                    negotiated_dialogue_format=self.mode if enabled else 'json',
                    capability_verified=capabilities is not None,
                    capability_source='verified_model_health_date' if capabilities else 'unavailable',
                    per_turn_health_requests=0, complete_response_required=True)

    def request(self, kind, payload, *, deadline, cancelled):
        capabilities = self._capabilities() if self.mode != 'json' else None
        if capabilities is None or self.mode not in capabilities['output_formats']:
            # Old hosts receive exactly the original request. Never retry a
            # compact failure as JSON, which would duplicate a model operation.
            return self.transport.request(kind, payload, deadline=deadline, cancelled=cancelled)
        with self._lock:
            if self._adapter is None:
                self._adapter = CompactRequestAdapter(self.transport, system_prompt=self.system_prompt,
                                                       capabilities=capabilities, mode=self.mode)
            adapter = self._adapter
        return adapter.request(kind, payload, deadline=deadline, cancelled=cancelled)

    def cancel(self, owner):
        return self.transport.cancel(owner)

    def __getattr__(self, name):
        return getattr(self.transport, name)


def install_dialogue_output(runtime, *, mode, system_prompt):
    """Bind only the idle controller before workers; leave summary/raw client.

    The constructor's existing initialize_clock must already have returned.
    Missing/legacy capabilities are a normal JSON fallback, never a fabricated
    capability grant. Future existing idle Date refreshes update the RAM view.
    """
    mode = validate_dialogue_output_format(mode)
    if (runtime.started or runtime.closed or runtime.jobs.thread is not None
            or not runtime.controller.idle
            or runtime.controller.model_client is not runtime.client
            or runtime.controller.context_builder.system_prompt != system_prompt):
        raise ValueError('output_format_requires_original_idle_runtime')
    selection = NegotiatedDialogueClient(runtime.client, system_prompt=system_prompt, mode=mode)
    if mode != 'json':
        runtime.controller.model_client = selection
    return selection
