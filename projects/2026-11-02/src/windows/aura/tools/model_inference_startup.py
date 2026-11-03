"""Explicit TTS-first startup of the model-only host, before it accepts work.

The lifetime lock is shared with the installed legacy voice service. The
coordinator never stops an external owner, unloads a model, or opens business
data. Headroom snapshots are rechecked; actual operations still acquire the
original enforcing GPU leases. A failed stage leaves service publication to
the caller, which must close only its own backend.
"""
from __future__ import annotations

import math
import threading
import time
import uuid


class ModelStartupBlocked(RuntimeError):
    def __init__(self, code, stage):
        self.code, self.stage = code, stage
        super().__init__(code)


def _check(deadline, cancelled, clock):
    if cancelled.is_set():
        raise InterruptedError()
    if clock() >= deadline:
        raise TimeoutError()


def _unique_ready(value, *, stage):
    ownership = value.get('tts_ownership', {})
    if (value.get('ok') is not True or value.get('tts_ready') is not True
            or ownership.get('available') is not True
            or ownership.get('external_workers') != 0
            or ownership.get('owned_workers') != 1):
        raise ModelStartupBlocked('same_unique_tts_not_ready', stage)


def startup_models(backend, *, lock, deadline, cancelled=None, clock=time.monotonic):
    """Warm the unique RAM TTS, then preload the fixed 27B without a prompt.

    Caller holds the SAME lifetime lock as legacy 8792 until all serving and
    backend cleanup have finished. This is an explicit start operation, never
    called from construction, health or a timer. No request is accepted during
    startup. The entire sequence retains one finite <=300-second deadline.
    """
    from tools.service_instance_lock import ServiceInstanceLock
    if not isinstance(lock, ServiceInstanceLock) or not lock.held:
        raise ValueError('Require the held voice process lifetime lock')
    began = clock()
    if (type(deadline) not in (int, float) or not math.isfinite(deadline)
            or not 0 < deadline-began <= 300.001):
        raise ValueError('Require the original bounded startup deadline')
    cancelled = threading.Event() if cancelled is None else cancelled
    phases = []

    def snapshot(stage):
        _check(deadline, cancelled, clock)
        value = backend.preflight(deadline=deadline)
        _check(deadline, cancelled, clock)
        if not isinstance(value, dict) or value.get('ok') is not True:
            raise ModelStartupBlocked('preflight_unavailable', stage)
        return value

    initial = snapshot('before_tts')
    if initial.get('startup', {}).get('can_warm_unique_tts_now') is not True:
        raise ModelStartupBlocked('tts_first_startup_not_available', 'before_tts')
    # Cold file/CUDA initialization may exceed120s even with enough headroom.
    # Keep the SAME original <=300s startup deadline across both models rather
    # than inventing a shorter TTS deadline or resetting the overall budget.
    backend.warmup_tts(deadline=deadline, cancelled=cancelled,
                       request_id='startup-' + uuid.uuid4().hex)
    _check(deadline, cancelled, clock)
    after_tts = snapshot('after_tts')
    _unique_ready(after_tts, stage='after_tts')
    process = backend.voice.process
    if process is None or not callable(getattr(process, 'poll', None)) or process.poll() is not None:
        raise ModelStartupBlocked('same_unique_tts_not_ready', 'after_tts')
    if after_tts.get('admission', {}).get('llm', {}).get('can_admit_now') is not True:
        raise ModelStartupBlocked('post_tts_llm_headroom_unavailable', 'after_tts')
    phases.append({'stage': 'tts_ready', 'elapsed_ms': round((clock()-began)*1000, 2)})

    # This operation itself obtains the unchanged cold LLM admission lease.
    # No conversation text, persona or board memory is manufactured here.
    backend.preload_llm(deadline=deadline, cancelled=cancelled)
    final = snapshot('after_llm')
    _unique_ready(final, stage='after_llm')
    if backend.voice.process is not process or process.poll() is not None:
        raise ModelStartupBlocked('tts_process_changed_during_startup', 'after_llm')
    residency = final.get('llm_residency', {})
    if (residency.get('available') is not True
            or residency.get('llm_resident') is not True
            or residency.get('fresh') is not True):
        raise ModelStartupBlocked('llm_residency_unverified', 'after_llm')
    for kind in ('llm', 'tts'):
        if final.get('admission', {}).get(kind, {}).get('can_admit_now') is not True:
            raise ModelStartupBlocked('steady_' + kind + '_headroom_unavailable', 'after_llm')
    _check(deadline, cancelled, clock)
    phases.append({'stage': 'llm_and_same_tts_ready', 'elapsed_ms': round((clock()-began)*1000, 2)})
    return {'ready': True, 'order': 'tts_then_fixed_27b', 'phases': phases,
            'same_tts_process': True, 'memory_only': True,
            'steady_admission': final['admission'], 'automatic_unload': False,
            'business_store_opened': False, 'original_deadline_preserved': True}
