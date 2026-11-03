# -*- coding: utf-8 -*-
"""事件类型与策略映射（Week A1，人3）

命名规范：<domain>.<subdomain>.<action>，全小写点分。

跨角色边界：
  人2 → 人3：scene.* / camera.* / detector.*（9/4 冻结 schema）
  人1 → 人3：fpga.* / board.*（9/6 MockBoard、9/10 寄存器合同）
  人3 内部：audio.* / dialogue.* / system.* / fsm.*

队列策略（人3 任务书 §五）：
  LATEST   视觉帧，丢旧保新
  CRITICAL 错误/取消/最终状态，不能静默丢失
  BOUNDED  普通事件，满则丢弃并计数（可见）
"""
import enum
import typing


class EventPriority(enum.IntEnum):
    """事件优先级：仅供 UI/处理线程排序参考，不替代队列策略。"""
    NORMAL = 0
    HIGH = 1
    CRITICAL = 2


class EventType:
    # ---- 视觉/场景（人2 交接） ----
    SCENE_STATE = "scene.state"                    # SceneState 更新（最终状态）
    SCENE_PERSON_ENTER = "scene.person_enter"      # 来访者进入（迟滞后）
    SCENE_PERSON_EXIT = "scene.person_exit"        # 来访者离开（grace 后）
    SCENE_TARGET_UPDATE = "scene.target_update"    # 当前目标更新
    CAMERA_LOST = "camera.lost"                    # 摄像头丢失
    CAMERA_RECOVERED = "camera.recovered"          # 摄像头恢复
    CAMERA_PREVIEW_FRAME = "camera.preview_frame"  # 预览帧（latest）
    DETECTOR_FRAME = "detector.frame"              # 检测帧元数据（latest）

    # ---- 音频（人3） ----
    AUDIO_KWS_DETECTED = "audio.kws_detected"        # 本地关键词命中
    AUDIO_VAD_START = "audio.vad_start"              # 语音开始
    AUDIO_VAD_END = "audio.vad_end"                  # 语音结束（turn 切分）
    AUDIO_CANCEL_REQUESTED = "audio.cancel_requested"  # 实体键取消（critical）
    AUDIO_PLAYBACK_START = "audio.playback_started"  # PCM 播放开始
    AUDIO_PLAYBACK_STOP = "audio.playback_stopped"   # PCM 播放结束（最终状态）
    AUDIO_DEVICE_LOST = "audio.device_lost"
    AUDIO_DEVICE_RECOVERED = "audio.device_recovered"

    # ---- 对话（人3，LAN 主机） ----
    DIALOGUE_REQUEST_SENT = "dialogue.request_sent"
    DIALOGUE_RESPONSE_RECEIVED = "dialogue.response_received"  # 最终回复（critical）
    DIALOGUE_TIMEOUT = "dialogue.timeout"
    DIALOGUE_ERROR = "dialogue.error"
    DIALOGUE_NETWORK_LOST = "dialogue.network_lost"      # 断链
    DIALOGUE_NETWORK_RESTORED = "dialogue.network_restored"

    # ---- 系统（人3） ----
    SYSTEM_HEARTBEAT = "system.heartbeat"
    SYSTEM_WORKER_CRASH = "system.worker_crash"     # worker 崩溃（critical）
    SYSTEM_PRIVACY_CHANGED = "system.privacy_changed"  # 隐私开关（critical）
    SYSTEM_SHUTDOWN = "system.shutdown"             # 关停（critical）
    SYSTEM_HEALTH_OK = "system.health_ok"           # 健康恢复

    # ---- FSM ----
    FSM_STATE_CHANGED = "fsm.state_changed"

    # ---- FPGA/板端（人1 交接） ----
    FPGA_OVERLAY_COMMITTED = "fpga.overlay_committed"
    FPGA_UNDERFLOW = "fpga.underflow"               # FIFO underflow（critical）
    FPGA_OVERFLOW = "fpga.overflow"                 # FIFO overflow（critical）
    BOARD_KEY_PRESSED = "board.key_pressed"         # PL_KEY（wake/privacy/cancel）

    # ---- 队列策略分类 ----
    LATEST_TYPES = frozenset({CAMERA_PREVIEW_FRAME, DETECTOR_FRAME})
    CRITICAL_TYPES = frozenset({
        AUDIO_CANCEL_REQUESTED,
        AUDIO_PLAYBACK_STOP,
        DIALOGUE_RESPONSE_RECEIVED,
        SYSTEM_WORKER_CRASH,
        SYSTEM_PRIVACY_CHANGED,
        SYSTEM_SHUTDOWN,
        FPGA_UNDERFLOW,
        FPGA_OVERFLOW,
    })
    # 注意：SCENE_STATE 为"最终状态"，走 CRITICAL 语义（不允许静默丢失最新状态），
    # 但其"最终状态"特性需要 latest 语义（旧状态可被新状态覆盖）。
    LATEST_FINAL_TYPES = frozenset({SCENE_STATE})


# 事件类型全集（用于校验/文档）
ALL_EVENT_TYPES = sorted(
    set(v for k, v in vars(EventType).items() if isinstance(v, str) and not k.startswith("_") and not k.isupper())
)


def event_priority_for(event_type: str) -> EventPriority:
    """辅助：事件 → 优先级（供处理线程参考，实际入队策略见 EventBus）。"""
    if event_type in EventType.CRITICAL_TYPES:
        return EventPriority.CRITICAL
    if event_type in EventType.LATEST_TYPES or event_type in EventType.LATEST_FINAL_TYPES:
        return EventPriority.HIGH
    return EventPriority.NORMAL
