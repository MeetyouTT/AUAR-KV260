# -*- coding: utf-8 -*-
"""Policy 层校验器：视觉声明必须有证据（grounding）、白名单、回复长度、越权。"""
import typing

from .core import ValidationContext, ValidationResult


def _as_dict(value: typing.Any) -> typing.Dict:
    """脏数据保护：非 dict 一律当空对象（Validator 不得因非法响应抛异常）。"""
    return value if isinstance(value, dict) else {}


def _pos(ss: typing.Dict) -> typing.Optional[str]:
    return _as_dict(ss.get("current_target")).get("position")


def _has_recent_event(ss: typing.Dict, ev_type: str) -> bool:
    events = ss.get("recent_events")
    if not isinstance(events, list):
        return False
    return any(isinstance(ev, dict) and ev.get("type") == ev_type for ev in events)


def _claims(response: typing.Dict) -> typing.List[typing.Dict]:
    """visual_claims 中的对象条目；非数组/非对象条目忽略（Schema 层判其非法）。"""
    claims = response.get("visual_claims") or []
    if not isinstance(claims, list):
        return []
    return [c for c in claims if isinstance(c, dict)]


class PolicyValidator:
    """策略校验：涉及"事实/权限"层面，防止 LLM 伪造视觉事实或越权控制硬件。

    检查项（主计划 §9.3 / §22.10；第 9 轮强化新增 5、6）：
      1. emotion / avatar_action 必须在白名单；
      2. reply_text 长度受限；
      3. 摄像头非 online 时不得声明"看到人"；
      4. visual_claims 每条 fact 必须有 SceneState 证据（grounding）；
      5. 同一条响应不得同时声明多个不同位置（自相矛盾）；
      6. 主机不得通过 control_requests 越权控制 FPGA/camera/audio。
    """

    # 位置类事实：同一条响应里出现 ≥2 个不同位置 → 自相矛盾
    POSITION_FACTS = ("person_on_left", "person_on_center", "person_on_right")
    # "看到人"类事实：camera_state != online 时一律拒绝
    PERSON_FACTS = ("person_present", "person_recently_entered",
                    "person_recently_left") + POSITION_FACTS

    # 支持的视觉事实 → 证据判定函数（f: scene_state -> bool）
    FACT_RULES = {
        "person_present": lambda ss: ss.get("people_count", 0) > 0,
        "person_on_left": lambda ss: _pos(ss) == "left",
        "person_on_center": lambda ss: _pos(ss) == "center",
        "person_on_right": lambda ss: _pos(ss) == "right",
        "person_recently_entered": lambda ss: _has_recent_event(ss, "person_enter"),
        "person_recently_left": lambda ss: _has_recent_event(ss, "person_exit"),
        "no_person": lambda ss: ss.get("people_count", 0) == 0,
        "no_visual_evidence": lambda ss: not ss.get("current_target") and not ss.get("recent_events"),
    }

    def validate_response(self, response: typing.Dict, ctx: ValidationContext) -> ValidationResult:
        res = ValidationResult(layer="policy.response", ok=True)
        if not isinstance(response, dict):
            res.add("policy.not_object", "response 必须是 JSON 对象，收到 %s" % type(response).__name__)
            return res
        ss = _as_dict(ctx.scene_state)

        # 1. emotion / avatar 白名单
        emotion = response.get("emotion")
        if emotion is not None and ctx.allowed_emotions and emotion not in ctx.allowed_emotions:
            res.add("policy.emotion_not_allowed",
                    "emotion=%s 不在白名单 %s" % (emotion, list(ctx.allowed_emotions)))
        avatar = response.get("avatar_action")
        if avatar is not None and ctx.allowed_avatar_actions and avatar not in ctx.allowed_avatar_actions:
            res.add("policy.avatar_not_allowed",
                    "avatar_action=%s 不在白名单 %s" % (avatar, list(ctx.allowed_avatar_actions)))

        # 2. reply 长度（非字符串交给 Schema 层判类型）
        reply = response.get("reply_text")
        if isinstance(reply, str) and len(reply) > ctx.max_reply_len:
            res.add("policy.reply_too_long",
                    "reply_text 长度 %d 超过上限 %d" % (len(reply), ctx.max_reply_len))

        claims = _claims(response)

        # 3. 摄像头不是 online 就没有新视觉证据 → 不得声明"看到人"
        camera = ss.get("camera_state")
        if camera is not None and camera != "online":
            for claim in claims:
                if claim.get("fact") in self.PERSON_FACTS:
                    res.add("policy.camera_not_online",
                            "camera_state=%s 时不得声明看到人（fact=%s）" % (camera, claim.get("fact")))
                    break

        # 4. visual_claims grounding：无证据 → 拒绝，不允许 LLM 补造事实
        for claim in claims:
            fact = claim.get("fact")
            rule = self.FACT_RULES.get(fact) if isinstance(fact, str) else None
            if rule is None:
                res.add("policy.unknown_fact",
                        "未知视觉事实 %r，拒绝（改输出 no_visual_evidence/不确定）" % (fact,))
                continue
            if not rule(ss):
                res.add("policy.visual_claim_ungrounded",
                        "视觉事实 %r 在当前 SceneState 中无证据，拒绝" % fact)

        # 5. 位置自相矛盾：同一条响应同时声明多个不同位置
        positions = {c.get("fact") for c in claims if c.get("fact") in self.POSITION_FACTS}
        if len(positions) > 1:
            res.add("policy.conflicting_visual_claims",
                    "同一条响应同时声明多个位置 %s，自相矛盾，拒绝" % sorted(positions))

        # 6. 越权控制硬件
        ctrl = response.get("control_requests")
        if ctrl:
            size = len(ctrl) if isinstance(ctrl, (list, dict, str)) else 1
            res.add("policy.control_denied",
                    "主机不得直接控制硬件，control_requests 必须为空（当前 %d 条）" % size)

        return res
