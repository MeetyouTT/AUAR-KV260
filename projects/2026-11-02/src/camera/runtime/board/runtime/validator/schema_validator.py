# -*- coding: utf-8 -*-
"""Schema 层校验器：用 jsonschema 验证 DialogueRequest / DialogueResponse / SceneState 结构。

错误码（第 9 轮强化）：把 jsonschema 的判定关键字映射为**细粒度错误码**，
便于上层按「缺字段 / 类型错 / 枚举越界 / 数值越界 / 数组越界」分类统计与提示；
未映射的关键字统一回落 `schema.invalid`（保持向后可读）。
"""
import json
import os
import re
import typing

from .core import ValidationResult

# jsonschema 关键字 → 细粒度错误码（约定：<layer>.<code>）
_CODE_BY_KEYWORD = {
    "required": "schema.missing_field",
    "additionalProperties": "schema.unexpected_field",
    "type": "schema.type_mismatch",
    "enum": "schema.enum_violation",
    "const": "schema.const_violation",
    "minLength": "schema.string_too_short",
    "maxLength": "schema.string_too_long",
    "pattern": "schema.pattern_mismatch",
    "minimum": "schema.number_too_small",
    "exclusiveMinimum": "schema.number_too_small",
    "maximum": "schema.number_too_large",
    "exclusiveMaximum": "schema.number_too_large",
    "minItems": "schema.array_too_short",
    "maxItems": "schema.array_too_long",
    "uniqueItems": "schema.duplicate_items",
    "minProperties": "schema.object_too_small",
    "maxProperties": "schema.object_too_large",
    "format": "schema.format_mismatch",
}

# jsonschema 的 required 报错文本形如 "'reply_text' is a required property"
_REQUIRED_FIELD_RE = re.compile(r"'([^']+)'")


class SchemaValidator:
    """JSON Schema 结构校验（对话数据合同，见 schemas/）。"""

    def __init__(self, schemas_dir: typing.Optional[str] = None) -> None:
        if schemas_dir is None:
            schemas_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "common", "schemas")
        self._schemas_dir = os.path.normpath(schemas_dir)
        try:
            import jsonschema  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("缺少依赖 jsonschema，请先 pip install jsonschema") from exc
        self._jsonschema = __import__("jsonschema")
        self._request_schema = self._load("dialogue_request.schema.json")
        self._response_schema = self._load("dialogue_response.schema.json")
        self._scene_schema = self._load("scene_state.schema.json")

    def _load(self, name: str) -> typing.Dict:
        path = os.path.join(self._schemas_dir, name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _check(self, layer_name: str, data: typing.Any, schema: typing.Dict) -> ValidationResult:
        res = ValidationResult(layer=layer_name, ok=True)
        if not isinstance(data, dict):
            res.add("schema.not_object", "输入必须是 JSON 对象，收到 %s" % type(data).__name__)
            return res
        validator = self._jsonschema.Draft7Validator(schema)
        for err in sorted(validator.iter_errors(data), key=self._sort_key):
            code, message, path = self._describe(err)
            res.add(code, message, path=path)
        return res

    @staticmethod
    def _sort_key(err: typing.Any) -> typing.Tuple[str, ...]:
        """稳定排序键：path 段转字符串，避免 int/str 混排抛 TypeError。"""
        return tuple(str(p) for p in err.path)

    @staticmethod
    def _describe(err: typing.Any) -> typing.Tuple[str, str, str]:
        """jsonschema 错误 → (细粒度错误码, 原始消息, 字段路径)。"""
        keyword = getattr(err, "validator", "")
        code = _CODE_BY_KEYWORD.get(keyword, "schema.invalid")
        path = ".".join(str(p) for p in err.path)
        if keyword == "required":
            match = _REQUIRED_FIELD_RE.search(err.message or "")
            if match:      # required 的 path 指向父级，补上缺失字段名更好定位
                field = match.group(1)
                path = "%s.%s" % (path, field) if path else field
        return code, err.message, path

    def validate_request(self, data: typing.Any) -> ValidationResult:
        return self._check("schema.request", data, self._request_schema)

    def validate_response(self, data: typing.Any) -> ValidationResult:
        return self._check("schema.response", data, self._response_schema)

    def validate_scene_state(self, data: typing.Any) -> ValidationResult:
        return self._check("schema.scene", data, self._scene_schema)
