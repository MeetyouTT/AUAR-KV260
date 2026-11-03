"""Board-mode display/connection guard; never writes legacy preferences."""
import time


def guard_legacy_configuration(stage, data):
    if getattr(stage, 'board_business', None) is not None and data.get('type') in (
            'asr_config', 'ui_edit', 'connection_apply', 'ui_service_config'):
        raise ValueError('正式板端语音与服务地址由启动配置管理，请保持原连接设置。')


def project_business_ui(stage, state):
    owner = getattr(stage, 'board_business', None)
    if owner is None:
        return
    runtime = owner.runtime
    endpoint = runtime.config.model_host + ':' + str(runtime.config.model_port)
    transcription = state.get('local_transcription', {})
    task = transcription.get('state', 'IDLE')
    label = {'TRANSCRIBING':'板端识别中', 'GENERATING':'正在生成', 'PLAYING':'正在播放',
             'ANSWERED':'本轮完成', 'ERROR':'本轮请求失败', 'CANCELLED':'本轮已取消'}.get(task, '已配置')
    stage.mode_label.set_text('板端语音与记忆 · Windows 仅运行模型')
    stage.host_status_label.set_text('模型服务 '+endpoint+' · '+label)
    stage.host_entry.set_editable(False)
    stage.port_entry.set_editable(False)
    for name in ('edit_host','edit_port','connect','disconnect'):
        control = stage.controls.get(name)
        if control is not None:
            control.set_sensitive(False)
    state['board_processing'] = dict(asr_location='board', memory_location='board',
        models_endpoint=endpoint, task_state=task, remote_asr=False, legacy_business_ports_used=False,
        model_readiness_claimed=False)
    if time.monotonic() >= getattr(stage, 'toast_until', 0):
        stage.footer.set_text('板端处理与保存 · 模型 '+endpoint+' · '+label)
