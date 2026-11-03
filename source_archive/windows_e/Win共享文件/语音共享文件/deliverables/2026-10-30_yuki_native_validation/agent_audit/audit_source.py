#!/usr/bin/env python3
"""Read-only source preflight for NekoMote commit 4fbf55aa6009df76ac40dc5f18e3781914bc464f.

This checks selected known gates. It neither converts PSB nor certifies playback.
Only the explicitly selected report and optional probe requests are written.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

COMMIT = "4fbf55aa6009df76ac40dc5f18e3781914bc464f"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def walk(value, path=""):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from walk(child, path + "/" + escaped)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + "/" + str(index))


def layers(model):
    def recurse(items, prefix, part):
        for index, item in enumerate(items):
            path = prefix + "/" + str(index)
            yield path, item, part
            yield from recurse(item.get("children", []) or [], path + "/children", part)
    for group, obj in model.get("object", {}).items():
        for name, part in obj.get("motion", {}).items():
            prefix = "/object/" + group + "/motion/" + name + "/layer"
            yield from recurse(part.get("layer", []) or [], prefix, part)


def audit(model, model_path, resx_path, resource_root):
    failures, conditional = [], []
    hist = {name: Counter() for name in (
        "type", "stencilType", "coordinate", "meshTransform", "meshCombine",
        "meshSyncChildMask", "inheritMask", "groundCorrection", "joinTarget",
        "transformOrder", "bm", "mesh_bp_lengths")}
    def problem(code, path, value):
        failures.append({"gate": code, "path": path, "value": value})
    if model.get("spec") != "ems":
        problem("importer_spec_requires_ems", "/spec", model.get("spec"))
    version = model.get("version")
    if not isinstance(version, (int, float)) or not 3 <= version < 4:
        problem("importer_version_requires_3_x", "/version", version)
    counts = Counter()
    stencils = []
    for path, layer, part in layers(model):
        counts["layers"] += 1
        for key in hist:
            if key in layer:
                hist[key][json.dumps(layer[key], ensure_ascii=False)] += 1
        typ = layer.get("type", 0)
        if typ not in (0, 1, 2, 3, 12):
            problem("layer_type", path + "/type", typ)
        if typ == 12:
            stencils.append({
                "path": path, "label": layer.get("label"),
                "stencilType": layer.get("stencilType", 0),
                "sources": layer.get("stencilCompositeMaskLayerList", [])
            })
            if layer.get("stencilType", 0) != 5:
                problem("type12_stencil_requires_5", path, layer.get("stencilType", 0))
        for key, allowed in (("coordinate", (0,)), ("meshTransform", (0, 1)),
                             ("meshCombine", (0, 1)), ("meshSyncChildMask", (0, 1, 8))):
            val = layer.get(key, 0)
            if val not in allowed:
                problem("unsupported_common:" + key, path + "/" + key, val)
        order = layer.get("transformOrder", []) or []
        if order and order != [0, 3, 2, 1]:
            problem("unsupported_common:transformOrder", path + "/transformOrder", order)
        division = layer.get("meshDivision", 0)
        if not isinstance(division, (int, float)) or not 0 <= division <= 256:
            problem("geometry_meshDivision_0_256", path + "/meshDivision", division)
        inherit = layer.get("inheritMask", 0)
        accepted = inherit in (0x20007fc, 0x7fc) or (typ == 12 and inherit == 0x24007fc)
        if not accepted:
            # There are narrow exported-locator exceptions later in the evaluator.
            conditional.append({"gate": "inheritMask_needs_runtime_check",
                                "path": path, "value": inherit})
        binding = layer.get("parameterize")
        if binding is None:
            binding = part.get("parameterize")
        parameters = layer.get("parameter") or part.get("parameter") or []
        if binding is not None and (not isinstance(binding, int) or
                                    binding < 0 or binding >= len(parameters)):
            problem("parameter_binding_index", path + "/parameterize", binding)
        for i, frame in enumerate(layer.get("frameList", []) or []):
            counts["frames"] += 1
            content = frame.get("content")
            if not isinstance(content, dict):
                continue
            cp = path + "/frameList/" + str(i) + "/content"
            blend = content.get("bm") or 0
            hist["bm"][str(blend)] += 1
            if blend not in (0, 19):
                problem("pose_blend_0_or_19", cp + "/bm", content["bm"])
            mesh = content.get("mesh")
            if isinstance(mesh, dict):
                counts["mesh_dicts"] += 1
                if mesh.get("cc") is not None:
                    counts["mesh_cc_nonnull"] += 1
                    problem("mesh_cc_unverified", cp + "/mesh/cc", "nonnull")
                bp = mesh.get("bp")
                if bp is not None:
                    counts["mesh_bp_nonnull"] += 1
                    length = len(bp) if isinstance(bp, list) else "not_list"
                    hist["mesh_bp_lengths"][str(length)] += 1
                    if length != 32:
                        problem("importer_bp_requires_32_values", cp + "/mesh/bp", length)
            # These fields mark a pose unsupported even if import succeeds.
            if frame.get("type") == 1:
                conditional.append({"gate": "pose_frame_type1", "path": cp})
            for key in ("zx", "zy", "ox", "oy"):
                if content.get(key) is not None:
                    conditional.append({"gate": "pose_field:" + key, "path": cp})
            if (content.get("flip") or 0) != 0:
                conditional.append({"gate": "pose_flip", "path": cp})
            if content.get("color", 0x808080ff) not in (0x808080ff, None):
                conditional.append({"gate": "pose_color", "path": cp,
                                    "value": content["color"]})
    textures = []
    resources = read_json(resx_path).get("Resources", {}) if resx_path else {}
    root = Path(resource_root) if resource_root else model_path.parent
    for name, source in model.get("source", {}).items():
        tex = source.get("texture", {})
        pixel = tex.get("pixel")
        mapped = resources.get(pixel[10:]) if isinstance(pixel, str) and pixel.startswith("#resource#") else None
        textures.append({"name": name, "type": tex.get("type"),
                         "size": [tex.get("width"), tex.get("height")],
                         "pixel": pixel, "resx_path": mapped,
                         "file_exists": (root / mapped).is_file() if isinstance(mapped, str) else False,
                         "needs_explicit_texture_mapping": pixel is None})
    timelines = [{"label": t.get("label"), "diff": t.get("diff", 0),
                  "lastTime": t.get("lastTime"), "loopBegin": t.get("loopBegin"),
                  "loopEnd": t.get("loopEnd")}
                 for t in model.get("metadata", {}).get("timelineControl", [])]
    return {"nekomote_commit": COMMIT, "source": str(model_path),
            "source_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
            "scope": "selected static gates only; not import/runtime/GPU certification",
            "visual_certified": False, "playback_certified": False,
            "spec": model.get("spec"), "version": version,
            "counts": dict(counts), "histograms": {k: dict(v) for k, v in hist.items()},
            "stencils": stencils, "textures": textures, "timelines": timelines,
            "known_gate_failures": failures, "conditional_runtime_checks": conditional}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("model_json", type=Path)
    p.add_argument("--resx", type=Path)
    p.add_argument("--resource-root", type=Path)
    p.add_argument("--output", type=Path, default=Path(__file__).parent / "source-preflight.json")
    p.add_argument("--probe-requests", type=Path,
                   help="Optional output directory for initial/each-timeline playback probe inputs")
    p.add_argument("--steps", type=int, default=120)
    a = p.parse_args()
    if not 1 <= a.steps <= 36000:
        p.error("--steps must be in 1..36000")
    model = read_json(a.model_json)
    report = audit(model, a.model_json.resolve(), a.resx, a.resource_root)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if a.probe_requests:
        a.probe_requests.mkdir(parents=True, exist_ok=True)
        cases = [None] + report["timelines"]
        index = []
        for number, timeline in enumerate(cases):
            request = {"steps": a.steps, "random_seed": 1, "observe_springs": True,
                       "dump_frame": True}
            if timeline is not None:
                request["plays"] = [{"label": timeline["label"],
                                      "flags": 3 if timeline["diff"] else 0}]
            name = f"{number:02d}.json"
            (a.probe_requests / name).write_text(
                json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            index.append({"request": name,
                          "timeline": timeline["label"] if timeline else None})
        (a.probe_requests / "index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(a.output), "known_gate_failures":
                      len(report["known_gate_failures"]), "conditional_checks":
                      len(report["conditional_runtime_checks"]),
                      "timeline_count": len(report["timelines"]),
                      "visual_certified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
