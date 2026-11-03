# -*- coding: utf-8 -*-
"""Semantic 层校验器：ID 匹配、scene_seq、TTL、track 存在性。"""
import typing

from .core import ValidationContext, ValidationResult


def _is_int(value: typing.Any) -> bool:
    """严格整数判断（bool 是 int 子类，必须排除，否则 True 会被当成 1）。"""
    return isinstance(value, int) and not isinstance(value, bool)


class SemanticValidator:
    """语义校验：跨字段一致性（相对 Schema 的结构校验）。

    检查项（人3 任务书 §五）：
      1. 响应 request_id 必须匹配当前在途请求；
      2. scene_seq_used 不得超前于请求携带的 scene_seq；
      3. SceneState 未过期（valid_until_ms > now_ms，TTL）；
      4. visual_claims 引用的 track_id 必须存在于 SceneState 证据中。
    """

    def validate_response(self, response: typing.Dict, ctx: ValidationContext) -> ValidationResult:
        res = ValidationResult(layer="semantic.response", ok=True)
        if not isinstance(response, dict):
            res.add("semantic.not_object", "response 必须是 JSON 对象，收到 %s" % type(response).__name__)
            return res

        # 1. request_id 匹配
        if ctx.request_id and response.get("request_id") != ctx.request_id:
            res.add("semantic.request_id_mismatch",
                    "响应 request_id=%s 与在途请求 %s 不匹配" % (response.get("request_id"), ctx.request_id))

        # 2. scene_seq 不超前（类型非法交给 Schema 层，这里只判可比较的整数）
        used = response.get("scene_seq_used", 0)
        if _is_int(used) and used > ctx.scene_seq:
            res.add("semantic.scene_seq_ahead",
                    "scene_seq_used=%d 超前于请求场景 %d" % (used, ctx.scene_seq))

        # 3. TTL 未过期 + 场景时间自洽（valid_until_ms==0 视为未设置有效期，跳过）
        self._check_scene_clock(ctx.scene_state, ctx.now_ms, res)

        # 4. track 存在性（visual_claims）
        known_track_ids = self._known_track_ids(ctx.scene_state)
        for claim in self._claims(response):
            tid = claim.get("source_track_id")
            if tid is None:
                continue
            if known_track_ids is not None and tid not in known_track_ids:
                res.add("semantic.track_not_found",
                        "visual_claim 引用的 track_id=%s 不在 SceneState 证据中" % (tid,))

        # 5. 音频代：请求发出后音频代已推进（TTS 被打断/取消）→ 旧响应必须拒绝
        if (ctx.request_audio_generation_id is not None
                and ctx.audio_generation_id != ctx.request_audio_generation_id):
            res.add("semantic.stale_audio_generation",
                    "响应属于旧音频代 (request_audio_generation_id=%s < 当前 %s)，不得覆盖新请求"
                    % (ctx.request_audio_generation_id, ctx.audio_generation_id))

        return res

    # ---- 内部工具 ----
    @staticmethod
    def _claims(response: typing.Dict) -> typing.List[typing.Dict]:
        """取 visual_claims 中的对象条目（脏数据不抛异常：非数组/非对象一律忽略，交给 Schema/Policy 判定）。"""
        claims = response.get("visual_claims") or []
        if not isinstance(claims, list):
            return []
        return [c for c in claims if isinstance(c, dict)]

    @staticmethod
    def _check_scene_clock(scene_state: typing.Optional[typing.Dict], now_ms: int,
                           res: ValidationResult) -> None:
        """SceneState 时间自洽：TTL 过期 + 有效期倒挂（valid_until_ms < captured_at_ms）。"""
        if not isinstance(scene_state, dict):
            return
        valid_until = scene_state.get("valid_until_ms")
        captured = scene_state.get("captured_at_ms")
        if not _is_int(valid_until):
            return
        if valid_until > 0 and now_ms > 0 and now_ms > valid_until:
            res.add("semantic.scene_expired",
                    "SceneState 已过期 (now=%d > valid_until=%d)" % (now_ms, valid_until))
        if _is_int(captured) and valid_until > 0 and valid_until < captured:
            res.add("semantic.scene_ttl_invalid",
                    "SceneState 有效期倒挂 (valid_until=%d < captured_at=%d)" % (valid_until, captured))

    @staticmethod
    def _known_track_ids(scene_state: typing.Optional[typing.Dict]) -> typing.Optional[typing.Set[int]]:
        if not scene_state or not isinstance(scene_state, dict):
            return None  # 无场景 → 不做 track 存在性检查（Policy 层会拒绝所有 visual claims）
        ids = set()
        cur = scene_state.get("current_target")
        if isinstance(cur, dict) and cur.get("track_id") is not None:
            ids.add(cur["track_id"])
        events = scene_state.get("recent_events")
        if isinstance(events, list):
            for ev in events:
                if isinstance(ev, dict) and ev.get("track_id") is not None:
                    ids.add(ev["track_id"])
        return ids

    def validate_scene_state(self, scene_state: typing.Dict, ctx: ValidationContext) -> ValidationResult:
        """SceneState 自身合法性（板端本地 scene 快照的语义检查）。"""
        res = ValidationResult(layer="semantic.scene", ok=True)
        if not isinstance(scene_state, dict):
            res.add("semantic.scene_not_object",
                    "scene_state 必须是对象，收到 %s" % type(scene_state).__name__)
            return res
        self._check_scene_clock(scene_state, ctx.now_ms, res)
        people = scene_state.get("people_count", 0)
        if _is_int(people) and people < 0:
            res.add("semantic.negative_people", "people_count 不能为负")
        cur = scene_state.get("current_target")
        pos = cur.get("position") if isinstance(cur, dict) else None
        if pos is not None and pos not in ("left", "center", "right"):
            res.add("semantic.invalid_position", "position 必须为 left/center/right")
        return res
