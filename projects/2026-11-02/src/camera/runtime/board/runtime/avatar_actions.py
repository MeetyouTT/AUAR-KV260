# -*- coding: utf-8 -*-
"""avatar_action 取值**单一来源**（玩偶素材丰富填充方案 §4.1 P0-4 一致性收口）。

背景（方案 §3.3）：`avatar_action` 是响应协议里早已存在的字段（v2 才接到播放层），
但它的取值此前散落在三处、彼此并不一致：

  · `fsm._route_emotion`        只认 ack_nod / emo_surprised(=surprised) / emo_puzzled(=puzzled)；
  · `mock_adapter`（默认回复）   送的是 `wave` —— 名单外，被**静默忽略**（联调时看不到任何反应）；
  · 请求侧 `allowed_avatar_actions` 无权威来源（测试/示例里写的是 idle/wave/nod）。

本模块把「主机可上报的动作」收敛为唯一一处，其余模块只引用、不再各写一份字面量：

  ALLOWED_AVATAR_ACTIONS  板端下发给主机的白名单（= policy_validator 的取值集合）
  ACTION_TO_STATE         动作 → RuntimeState 名（fsm 第 3 层触发路由用）
  ACTION_ALIASES          短别名 → 规范值（只收历史已识别的写法，保证行为等价）
  DEFAULT_MOCK_ACTION     mock 适配器默认动作（必须是白名单成员）

与 `avatar_assets.BURST_STATES` 的关系：**播放语义（burst / loop）仍由
BURST_STATES 单点决定**，本模块不重复定义；P1-1 补 `deny_shake` 素材时，
需同步把 `DENY_SHAKE` 加进 `avatar_assets.BURST_STATES`。

`deny_shake`（摇头）在 P1-1 才补素材与运行时状态；本模块**先定义白名单、后启用状态**——
查表命中而 RuntimeState 里尚无该成员时由 fsm 按「未知动作」忽略（脏数据保护）。
"""
from __future__ import annotations

import typing

#: 主机可上报的 avatar_action 白名单（= 板端 DialogueRequest.allowed_avatar_actions 取值集合）。
#: 与方案 §4.1 P0-4 的目标集合一一对应：ack_nod / deny_shake / emo_surprised / emo_puzzled。
ALLOWED_AVATAR_ACTIONS: typing.Tuple[str, ...] = (
    "ack_nod", "deny_shake", "emo_surprised", "emo_puzzled",
)

#: 动作 → RuntimeState 名（状态枚举本身定义在 fsm.RuntimeState）。
#: deny_shake → DENY_SHAKE 由 P1-1 新增 RuntimeState 时自动生效（本表无需改动）。
ACTION_TO_STATE: typing.Dict[str, str] = {
    "ack_nod": "ACK_NOD",
    "deny_shake": "DENY_SHAKE",
    "emo_surprised": "AWAKE",
    "emo_puzzled": "PUZZLED",
}

#: 短别名 → 规范值。**只收历史已识别过的写法**（主机侧可能写 surprised / puzzled），
#: 不新增语义别名，保证归一化前后 fsm 路由行为与 v2 完全等价。
ACTION_ALIASES: typing.Dict[str, str] = {
    "surprised": "emo_surprised",
    "puzzled": "emo_puzzled",
}

#: mock 适配器默认回复使用的动作（见 dialogue_client/mock_adapter.py）。
#: 必须是 ALLOWED_AVATAR_ACTIONS 成员：历史上写的是 "wave"（名单外 → 静默忽略）。
DEFAULT_MOCK_ACTION: str = "ack_nod"


def normalize(action: typing.Any) -> str:
    """取值归一化：去首尾空白 + 小写 + 别名解析；非字符串返回空串。"""
    if not isinstance(action, str):
        return ""
    key = action.strip().lower()
    return ACTION_ALIASES.get(key, key)


def state_for(action: typing.Any) -> typing.Optional[str]:
    """动作 → RuntimeState **名**；未命中白名单返回 None（调用方据此走情绪分档兜底）。

    返回名字而非枚举成员：本模块是纯逻辑（可脱离 fsm 单测），枚举的构造由 fsm 负责。
    """
    return ACTION_TO_STATE.get(normalize(action))


def is_allowed(action: typing.Any) -> bool:
    """归一化后是否属白名单（请求侧下发 / 校验响应时用）。"""
    return normalize(action) in ALLOWED_AVATAR_ACTIONS
