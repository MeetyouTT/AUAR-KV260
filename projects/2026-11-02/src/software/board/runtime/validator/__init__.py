# -*- coding: utf-8 -*-
"""三层 Validator 组合（Week A1 · 9/4 任务）

用法：
  chain = ValidationChain()
  ctx = ValidationContext(request_id=..., scene_state=..., allowed_emotions=..., ...)
  result = chain.validate_response(response_dict, ctx)
  if not result.ok:
      # 丢弃动作，改为"不确定"回复
"""
import typing

from .core import ValidationContext, ValidationError, ValidationIssue, ValidationResult
from .schema_validator import SchemaValidator
from .semantic_validator import SemanticValidator
from .policy_validator import PolicyValidator

__all__ = [
    "ValidationChain", "ValidationContext", "ValidationError",
    "ValidationIssue", "ValidationResult",
    "SchemaValidator", "SemanticValidator", "PolicyValidator",
]


class ValidationChain:
    """Schema → Semantic → Policy 三层串行校验。

    任一层失败即返回该层结果（不继续后续层），保证：
    - 结构非法不进入语义判断；
    - 语义不符不进入策略判断。
    """

    def __init__(self,
                 schema: typing.Optional[SchemaValidator] = None,
                 semantic: typing.Optional[SemanticValidator] = None,
                 policy: typing.Optional[PolicyValidator] = None) -> None:
        self.schema = schema or SchemaValidator()
        self.semantic = semantic or SemanticValidator()
        self.policy = policy or PolicyValidator()

    def validate_response(self, response: typing.Any, ctx: ValidationContext) -> ValidationResult:
        res = self.schema.validate_response(response)
        if not res.ok:
            return res
        res = self.semantic.validate_response(response, ctx)
        if not res.ok:
            return res
        return self.policy.validate_response(response, ctx)

    def validate_request(self, request: typing.Any) -> ValidationResult:
        return self.schema.validate_request(request)

    def validate_scene_state(self, scene_state: typing.Any, ctx: ValidationContext) -> ValidationResult:
        res = self.schema.validate_scene_state(scene_state)
        if not res.ok:
            return res
        return self.semantic.validate_scene_state(scene_state, ctx)

    def validate_response_all(self, response: typing.Any,
                              ctx: ValidationContext) -> ValidationResult:
        """三层**全跑不短路**，合并所有 issues（layer="chain.response"）。

        用途：异常用例报告 / 现场诊断——需要知道"有几层同时不合格"时使用；
        正式链路仍走 `validate_response()`（层间短路，避免拿非法结构做后续判断）。
        """
        if not isinstance(response, dict):
            return self.schema.validate_response(response)
        merged = ValidationResult(layer="chain.response", ok=True)
        for result in (self.schema.validate_response(response),
                       self.semantic.validate_response(response, ctx),
                       self.policy.validate_response(response, ctx)):
            merged.merge(result)
        return merged
