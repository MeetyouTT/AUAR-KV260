"""Dependency-free interpreter for the project's checked-in V1 schema subset.

Only keywords present in the three legacy contracts are supported. Unknown
keywords fail rather than silently accepting them. This is not a general
replacement for jsonschema; the existing full validator remains available.
"""
import json
from common.config import PROJECT_ROOT
from common.contracts import finite
from board.runtime.validator.core import ValidationResult

SUPPORTED = {"$schema", "title", "description", "definitions", "$ref", "type", "required",
             "additionalProperties", "properties", "enum", "minLength", "maxLength",
             "minimum", "maximum", "items", "maxItems", "uniqueItems"}


def check(value, schema, root, path=""):
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise ValueError("Unsupported schema keyword: " + ",".join(sorted(unknown)))
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError("Only local schema references supported")
        resolved = root
        for key in ref[2:].split("/"):
            resolved = resolved[key]
        return check(value, resolved, root, path)
    types = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
             "string": lambda v: isinstance(v, str), "integer": lambda v: type(v) is int,
             "number": finite, "boolean": lambda v: type(v) is bool}
    kind = schema.get("type")
    if kind and (kind not in types or not types[kind](value)):
        return [path + ":type"]
    issues = []
    if "enum" in schema and value not in schema["enum"]:
        issues.append(path + ":enum")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        issues.extend(path + "." + key + ":required" for key in schema.get("required", []) if key not in value)
        if schema.get("additionalProperties") is False:
            issues.extend(path + "." + key + ":unexpected" for key in value if key not in properties)
        for key, item in value.items():
            if key in properties:
                issues.extend(check(item, properties[key], root, path + "." + key))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
            issues.append(path + ":length")
    if type(value) in (int, float):
        if not finite(value) or value < schema.get("minimum", -float("inf")) or value > schema.get("maximum", float("inf")):
            issues.append(path + ":range")
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", float("inf")):
            issues.append(path + ":items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            issues.append(path + ":duplicate")
        for index, item in enumerate(value):
            if "items" in schema:
                issues.extend(check(item, schema["items"], root, path + "." + str(index)))
    return issues


class LegacySchemaSubset:
    def __init__(self):
        self.schemas = {kind: json.loads((PROJECT_ROOT / "common/schemas" / (name + ".schema.json")).read_text(encoding="utf-8"))
                        for kind, name in (("request", "dialogue_request"), ("response", "dialogue_response"), ("scene", "scene_state"))}

    def _validate(self, kind, data):
        result = ValidationResult("schema." + kind, True)
        schema = self.schemas[kind]
        for issue in check(data, schema, schema):
            result.add("schema.invalid", issue)
        return result

    def validate_request(self, data):
        return self._validate("request", data)

    def validate_response(self, data):
        return self._validate("response", data)

    def validate_scene_state(self, data):
        return self._validate("scene", data)
