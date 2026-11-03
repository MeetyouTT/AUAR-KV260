# -*- coding: utf-8 -*-
"""Validator 公共类型（Week A1 · 9/4 任务）

三层校验（人3 任务书 §五）：
  Schema    JSON 结构/字段类型/枚举（用 jsonschema）
  Semantic  ID 匹配、scene_seq、TTL、track 存在性
  Policy    视觉声明必须有证据（grounding）、白名单、回复长度、越权

错误码约定：<layer>.<code>，如 "schema.missing_field"、"semantic.request_id_mismatch"、
"policy.visual_claim_ungrounded"。
"""
import typing
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    code: str
    message: str
    path: str = ""

    def to_dict(self) -> typing.Dict:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclass
class ValidationResult:
    """一次校验的结果。ok=False 时 issues 非空。"""
    layer: str
    ok: bool
    issues: typing.List[ValidationIssue] = field(default_factory=list)

    def add(self, code: str, message: str, path: str = "") -> None:
        self.issues.append(ValidationIssue(code, message, path))
        self.ok = False

    def merge(self, other: "ValidationResult") -> None:
        self.issues.extend(other.issues)
        self.ok = self.ok and other.ok

    def to_dict(self) -> typing.Dict:
        return {
            "layer": self.layer,
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class ValidationContext:
    """校验上下文：来自板端当前状态。

    字段说明：
      request_id            当前在途请求 ID（响应必须匹配）
      scene_state           请求时携带的 SceneState（policy grounding 依据）
      scene_seq             请求时携带的 scene_seq
      audio_generation_id   当前音频代（取消后旧响应必须拒绝）
      request_audio_generation_id  发出请求时的音频代（可选；与当前代不一致 →
                            semantic.stale_audio_generation，A3「TTS 打断后不重播旧响应」）
      allowed_emotions      白名单
      allowed_avatar_actions 白名单
      max_reply_len         reply_text 最大长度
      now_ms                当前板端时间（TTL 判定）
      ttl_ms                scene 有效期
    """
    request_id: str = ""
    scene_state: typing.Optional[typing.Dict] = None
    scene_seq: int = 0
    audio_generation_id: int = 0
    request_audio_generation_id: typing.Optional[int] = None
    allowed_emotions: typing.Tuple[str, ...] = ()
    allowed_avatar_actions: typing.Tuple[str, ...] = ()
    max_reply_len: int = 200
    now_ms: int = 0
    ttl_ms: int = 30000


class ValidationError(Exception):
    """校验失败抛出的聚合异常（携带 ValidationResult）。"""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        super().__init__("校验失败[%s]: %s" % (result.layer, "; ".join(i.message for i in result.issues)))
