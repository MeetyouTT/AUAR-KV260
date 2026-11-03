"""Board display/guard and metadata-only capture diagnostics; no device IO."""
import errno
import math
import time


_TASKS = frozenset(('IDLE', 'DISABLED', 'TRANSCRIBING', 'GENERATING', 'PLAYING',
                   'ANSWERED', 'ERROR', 'CANCELLED', 'READY', 'EMPTY'))
_CAPTURE_STATES = frozenset(('IDLE', 'RECORDING', 'READY', 'ERROR', 'CANCELLED', 'STOPPING', 'CLOSED'))
_MONITOR_STATES = frozenset(('PAUSED', 'COOLDOWN', 'WAITING_WAKE', 'WAITING_SPEECH',
    'WAITING_AUDIO_IDLE', 'WAITING_SERVICE', 'CHECKING_WAKE', 'CONVERSATION',
    'PREPARING_SPEECH', 'CONFIRMING_SPEECH', 'CHECKING_SPEECH', 'WAITING_PERSON'))
_REASONS = frozenset(('', 'AUDIO_WAKE_WORD', 'WAKE_ACCEPTED', 'DIRECT_SPEECH', 'SPEECH_ACCEPTED', 'AUDIO_SESSION',
    'NO_AUDIO_SESSION', 'SERVICE_ERROR', 'CAPTURE_ERROR', 'USER_PAUSED',
    'CONVERSATION_SILENCE', 'SILENCE_TIMEOUT', 'AUDIO_OWNER_CHANGED',
    'SPEECH_TARGET_NOT_CONFIRMED', 'WAITING_FRESH_FACE', 'VISUAL_UNAVAILABLE',
    'BUSINESS_OR_NATIVE_NOT_READY', 'EXPLICIT_USER_PAUSE',
    'LISTENING_PREFERENCE_UNAVAILABLE', 'SERVICE_NOT_READY',
    'VISUAL_SPEECH_NOT_BOUND', 'TARGET_CHANGED', 'NO_VALID_INITIAL_SPEECH', 'CURRENT_TURN_CANCELLED'))
_MESSAGES = {
    'none': '',
    'pcm_input_queue_overflow': '语音处理未及时消费采集数据，本轮已停止；请检查前端耗时后重试。',
    'pcm_input_truncated_frame': '麦克风帧不完整，本轮未提交；请检查采集链路后重试。',
    'pcm_input_read_failed': '麦克风读取失败，本轮未提交；请检查麦克风连接后重试。',
    'pcm_input_source_stop_failed': '采集源未能正常停止；请保持暂停并检查采集进程。',
    'pcm_input_reader_not_stopped': '采集读取线程尚未结束；请保持暂停并检查采集进程。',
    'capture_device_busy': '麦克风被其他采集占用；请结束占用后恢复聆听。',
    'arecord_failed': '麦克风采集程序启动或运行失败；请检查设备和采集程序。',
    'capture_truncated': '录音不完整或过短，本轮未提交；请检查采集状态后重试。',
    'capture_timeout': '麦克风采集超时，本轮未提交；请检查采集进程。',
    'frontend_error': '板端语音前端处理失败；请检查前端状态后重试。',
    'capture_snapshot_failed': '暂时无法读取采集状态；请保持暂停并检查采集状态。',
    'capture_not_bound': '板端采集尚未绑定，正在等待语音初始化。',
    'capture_unknown_error': '采集或聆听出现未分类故障；请保持暂停并检查安全诊断。',
}
_PCM_CODES = tuple(k for k in _MESSAGES if k.startswith('pcm_input_'))
_QUEUE_NUMBERS = ('frame_bytes', 'capacity_frames', 'capacity_ms', 'queued_frames',
    'peak_frames', 'frames_read', 'frames_delivered', 'source_read_mean_ms',
    'source_read_max_ms', 'queue_mean_ms', 'queue_max_ms')
_FRONTEND_NUMBERS = ('frames', 'processed_samples', 'last_roundtrip_ms', 'max_roundtrip_ms',
    'worker_pid', 'worker_generation', 'ipc_rpc_last_ms', 'ipc_rpc_max_ms', 'ipc_rpc_total_ms',
    'worker_frame_wall_last_ms', 'worker_frame_wall_max_ms', 'worker_frame_wall_total_ms',
    'worker_frame_cpu_last_ms', 'worker_frame_cpu_max_ms', 'worker_frame_cpu_total_ms')
_STATS = ('armed', 'speech_starts', 'submitted', 'entry_rejected', 'visual_stops')
_PRIORITY_STATUSES = frozenset(('not_started', 'unsupported_platform', 'permission_denied',
    'apply_failed', 'active', 'not_applied', 'restore_wrong_thread', 'restore_failed',
    'restored', 'not_reported', 'UNKNOWN'))
_PRIORITY_SCOPES = frozenset(('capture_consumer_tid_and_inherited_pcm_pump_only',))
_PRIORITY_ERRORS = frozenset(('', 'capture_thread_priority_unsupported',
    'capture_thread_priority_permission_denied', 'capture_thread_priority_apply_failed',
    'capture_thread_priority_not_applied', 'capture_thread_priority_restore_wrong_thread',
    'capture_thread_priority_restore_failed', 'capture_thread_priority_unknown'))


def _enum(value, allowed):
    return value if isinstance(value, str) and value in allowed else 'UNKNOWN'


def _numbers(value, keys):
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in keys if key in value
            and type(value[key]) in (int, float)
            and 0 <= value[key] <= 9007199254740991 and math.isfinite(value[key])}


def _flags(value, keys):
    if not isinstance(value, dict):
        return {}
    return {key: value[key] for key in keys if type(value.get(key)) is bool}


def _capture_priority(value):
    """Project reports only; never adjust, look up or infer thread priorities."""
    value = value if isinstance(value, dict) else {}
    result = {key: value[key] if type(value.get(key)) is int and -20 <= value[key] <= 19 else None
              for key in ('requested_nice', 'original_nice', 'effective_nice', 'restored_nice')}
    result.update({key: value[key] if type(value.get(key)) is int
                   and 0 < value[key] <= 9007199254740991 else None
                   for key in ('native_tid', 'pump_native_tid')})
    result.update({key: value[key] if type(value.get(key)) is bool else None
                   for key in ('applied', 'restored', 'restoration_confirmed')})
    result['status'] = _enum(value.get('status', 'not_reported'), _PRIORITY_STATUSES)
    scope = value.get('scope')
    result['scope'] = scope if isinstance(scope, str) and scope in _PRIORITY_SCOPES else None
    code = value.get('error_code', '')
    result['error_code'] = (code if isinstance(code, str) and code in _PRIORITY_ERRORS
                            else 'capture_thread_priority_unknown')
    return result


def _error_code(value, source):
    """Never return, stringify, hash or store arbitrary exception/body text."""
    if isinstance(value, OSError) and value.errno == errno.EBUSY:
        return 'capture_device_busy'
    if not value:
        return 'none'
    if not isinstance(value, str):
        return 'frontend_error' if source == 'frontend' else 'capture_unknown_error'
    text = value[:512].strip().lower()
    if not text:
        return 'none'
    for code in _PCM_CODES:
        if text == code or text.startswith(code + ':'):
            return code
    if ('already owned by another process' in text or 'device or resource busy' in text
            or 'device is busy' in text or 'errno 16' in text):
        return 'capture_device_busy'
    if text.startswith('arecord failed with exit code') or ('arecord' in text and (
            'no such file' in text or 'not found' in text or 'failed' in text)):
        return 'arecord_failed'
    if text.startswith('recording is truncated or shorter than 100 ms'):
        return 'capture_truncated'
    if text.startswith('microphone capture exceeded its time limit'):
        return 'capture_timeout'
    if source == 'frontend' or text.startswith(('board frontend ', 'previous board frontend ')):
        return 'frontend_error'
    return 'capture_unknown_error'


def safe_capture_diagnostics(stage):
    """Read one current capture snapshot, selecting only fixed enums/numbers.

    No capture start/stop/read/take, model, ASR, Store, file or device operation.
    Raw errors are classified in this call and are never retained in output.
    """
    owner = getattr(stage, 'board_business', None)
    recording = getattr(owner, 'recording', None) if owner is not None else None
    if recording is None:
        return dict(schema='aura.safe-capture-diagnostics-1', error_code='capture_not_bound',
                    error_source='recording', status_text=_MESSAGES['capture_not_bound'],
                    snapshot_available=False, microphone_open=None,
                    capture_priority=_capture_priority(None))
    capture = getattr(recording, 'capture', None)
    snapshot, snapshot_failed = {}, False
    if capture is not None:
        try:
            candidate = capture.snapshot()
            if isinstance(candidate, dict):
                snapshot = candidate
            else:
                snapshot_failed = True
        except Exception:
            snapshot_failed = True
    queue = snapshot.get('input_queue', {})
    frontend = snapshot.get('audio_frontend', {})
    queue = queue if isinstance(queue, dict) else {}
    frontend = frontend if isinstance(frontend, dict) else {}
    candidates = []
    if snapshot_failed:
        candidates.append(('capture_snapshot_failed', 'snapshot'))
    for source, raw in (('input_queue', queue.get('error')), ('capture', snapshot.get('error')),
            ('recording', getattr(recording, 'recording_error', '')),
            ('monitor', getattr(recording, 'monitor_error', '')),
            ('automatic', getattr(recording, 'auto_error', '')),
            ('frontend', frontend.get('error'))):
        code = _error_code(raw, source)
        if code != 'none':
            candidates.append((code, source))
    # Prefer a typed queue/capture cause to a generic error copied by monitor.
    primary = next((item for item in candidates if item[0] != 'capture_unknown_error'),
                   candidates[0] if candidates else ('none', 'none'))
    monitor_state = _enum(getattr(recording, 'monitor_state', None), _MONITOR_STATES)
    reason = _enum(getattr(recording, 'monitor_reason', None), _REASONS)
    if primary[0] == 'none' and monitor_state == 'COOLDOWN' and reason in ('SERVICE_ERROR', 'CAPTURE_ERROR'):
        primary = ('capture_unknown_error', 'monitor_reason')
    capture_state = _enum(snapshot.get('state'), _CAPTURE_STATES)
    enabled = getattr(recording, 'monitor_enabled', None)
    enabled = enabled if type(enabled) is bool else None
    status = _MESSAGES[primary[0]]
    if primary[0] == 'none':
        status = ('聆听已暂停' if enabled is False else
                  ('正在聆听唤醒词' if getattr(recording, 'wake_word_required', True) else '正在聆听，可直接说话')
                  if capture_state == 'RECORDING' and snapshot.get('input_ready') is True else
                  '麦克风已打开，正在准备采集' if capture_state == 'RECORDING' else
                  '等待当前播放结束后继续聆听' if monitor_state == 'WAITING_AUDIO_IDLE' else
                  '语音尚未就绪，正在等待服务' if monitor_state == 'WAITING_SERVICE' else
                  '等待自动聆听就绪')
    return dict(schema='aura.safe-capture-diagnostics-1', error_code=primary[0],
        error_source=primary[1], status_text=status, snapshot_available=bool(snapshot),
        monitor_state=monitor_state, monitor_reason=reason, monitor_enabled=enabled,
        recording_state=_enum(getattr(recording, 'recording_state', None), _CAPTURE_STATES),
        capture_state=capture_state,
        microphone_open=capture_state == 'RECORDING' if capture_state != 'UNKNOWN' else None,
        counters=_numbers(getattr(recording, 'monitor_stats', {}), _STATS),
        input_queue=dict(_numbers(queue, _QUEUE_NUMBERS), **_flags(queue,
            ('enabled', 'eof', 'closed', 'cancelled', 'reader_alive'))),
        audio_frontend=dict(_numbers(frontend, _FRONTEND_NUMBERS), **_flags(frontend,
            ('enabled', 'closed', 'capture_lease_closed', 'worker_process_alive'))),
        capture_priority=_capture_priority(snapshot.get('capture_priority')),
        capture=dict(_numbers(snapshot, ('sample_count', 'listening_seconds')),
                     **_flags(snapshot, ('input_ready', 'speech_active', 'has_result'))))


def guard_legacy_configuration(stage, data):
    if getattr(stage, 'board_business', None) is not None and data.get('type') in (
            'asr_config', 'ui_edit', 'connection_apply', 'ui_service_config'):
        raise ValueError('正式板端语音与服务地址由启动配置管理，请保持原连接设置。')


def _write_widget(stage, widget, method, value):
    """Use the stage's value guard; retain compatibility with other shells."""
    guarded = getattr(stage, '_ui_set', None)
    if guarded is None:
        getattr(widget, method)(value)
    else:
        guarded(widget, method, value)


def project_business_ui(stage, state):
    owner = getattr(stage, 'board_business', None)
    if owner is None:
        return
    runtime = owner.runtime
    endpoint = runtime.config.model_host + ':' + str(runtime.config.model_port)
    transcription = state.get('local_transcription', {})
    task = _enum(transcription.get('state', 'IDLE'), _TASKS)
    label = {'TRANSCRIBING':'板端识别中', 'GENERATING':'正在生成', 'PLAYING':'正在播放',
             'ANSWERED':'本轮完成', 'ERROR':'本轮请求失败', 'CANCELLED':'本轮已取消'}.get(task, '已配置')
    diagnostics = safe_capture_diagnostics(stage)
    hint = diagnostics['status_text']
    _write_widget(stage, stage.mode_label, 'set_text', '板端语音与记忆 · Windows 仅运行模型')
    _write_widget(stage, stage.host_status_label, 'set_text', '模型服务 '+endpoint+' · '+label+' · '+hint)
    _write_widget(stage, stage.host_entry, 'set_editable', False)
    _write_widget(stage, stage.port_entry, 'set_editable', False)
    for name in ('edit_host','edit_port','connect','disconnect'):
        control = stage.controls.get(name)
        if control is not None:
            _write_widget(stage, control, 'set_sensitive', False)
    state['board_processing'] = dict(asr_location='board', memory_location='board',
        models_endpoint=endpoint, task_state=task, remote_asr=False, legacy_business_ports_used=False,
        model_readiness_claimed=False)
    state['safe_capture_diagnostics'] = diagnostics
    if time.monotonic() >= getattr(stage, 'toast_until', 0):
        _write_widget(stage, stage.footer, 'set_text', '板端处理与保存 · 模型 '+endpoint+' · '+hint)
