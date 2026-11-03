#!/usr/bin/env python3
"""Static reconstruction of the fixed upstream compiler's motion/mask graph.

This never evaluates animation/physics and never modifies source or model data.
Node-id matching is checked against the independently reported runtime failure.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "inputs/ems/yuk_0.ems.json"
CPP = ROOT / "source/src/runtime/geometry_scene.cpp"
AUDIT = ROOT / "evidence/cpu-audit.json"
OUTPUT = Path(__file__).resolve().parent / "mask_failure_analysis.json"
FAILURE_PATH = ("all_parts/タイムライン構造/全体構造/all_parts/全体構造/■全体レイアウト/"
                "move_UD/move_LR/□下半身配置_le/胴体回転中心/全身調整/□胴体調整_le/"
                "act_sp/全身変形基礎/stencil/□胴体マスク配置_le/髪揺れ_髪Ｒ_le54/"
                "act_sp/■髪揺れ_髪Ｒ")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads(MODEL.read_text(encoding="utf-8-sig"))
    parts = {}
    declared = set()
    raw_layers = []
    def collect(items, path):
        for i, item in enumerate(items):
            declared.add(item["label"])
            raw_layers.append((path + "/" + str(i), item))
            collect(item.get("children", []), path + "/" + str(i) + "/children")
    for group in sorted(data["object"]):
        for name in sorted(data["object"][group]["motion"]):
            part = data["object"][group]["motion"][name]
            key = group + "/" + name
            path = "/object/" + group + "/motion/" + name
            parts[key] = (part, path)
            collect(part.get("layer", []), path + "/layer")
    # Resource IDs of motions follow sorted group/name iteration, after sprites.
    resource_order = {key: i for i, key in enumerate(parts)}
    nodes = [{"id": 0, "parent": 0, "mask_original": 0, "path": "", "scope": 0}]
    scope_counter = 0
    def motion(key, parent, path, stack):
        nonlocal scope_counter
        if key in stack:
            raise ValueError("cycle in static motion graph: " + key)
        scope_counter += 1
        scope = scope_counter
        part, raw_path = parts[key]
        for i, item in enumerate(part.get("layer", [])):
            layer(item, parent, path, raw_path + "/layer/" + str(i), scope, stack + [key])
    def layer(item, parent, parent_path, raw_path, scope, stack):
        node = {"id": len(nodes), "parent": parent, "path": parent_path + "/" + item["label"],
                "raw_path": raw_path, "label": item["label"], "type": item.get("type", 0),
                "scope": scope, "stencil_type": item.get("stencilType", 0),
                "mask_sources": item.get("stencilCompositeMaskLayerList", []),
                "mask_original": 0, "possible_sprite_refs": [], "motion_refs": [],
                "initial_frame_content": None}
        refs = set()
        for frame in item.get("frameList", []):
            content = frame.get("content")
            if frame.get("time") == 0:
                node["initial_frame_content"] = content
            if frame.get("type") == 0 or not isinstance(content, dict):
                continue
            src, icon = content.get("src"), content.get("icon")
            if src is None or icon is None:
                continue
            key = src + "/" + icon
            if key in parts:
                refs.add(key)
            elif src != "blank":
                node["possible_sprite_refs"].append({"src": src, "icon": icon,
                                                     "time": frame.get("time"),
                                                     "opa": content.get("opa")})
        node["motion_refs"] = sorted(refs, key=resource_order.__getitem__)
        nodes.append(node)
        for key in node["motion_refs"]:
            motion(key, node["id"], node["path"] + "/" + key, stack)
        for i, child in enumerate(item.get("children", [])):
            layer(child, node["id"], node["path"], raw_path + "/children/" + str(i), scope, stack)
    base = data["metadata"]["base"]
    base_key = base["chara"] + "/" + base["motion"]
    motion(base_key, 0, base_key, [])
    masks = []
    for node in nodes[1:]:
        node["mask_original"] = nodes[node["parent"]]["mask_original"]
        if node["type"] != 12:
            continue
        node["mask_original"] = len(masks) + 1
        mask = {"original_id": len(masks) + 1, "owner": node["id"],
                "resolved": True, "roots": [], "missing": [], "outside_scope": [],
                "members": []}
        for name in node["mask_sources"]:
            roots = [n["id"] for n in nodes[1:]
                     if n["scope"] == node["scope"] and n["label"] == name]
            if len(roots) > 1:
                raise ValueError("ambiguous root " + name)
            if roots:
                mask["roots"].extend(roots)
            else:
                mask["missing"].append(name)
                if name in declared:
                    mask["outside_scope"].append(name)
                    mask["resolved"] = False
        if not mask["roots"]:
            mask["resolved"] = False
        for candidate in nodes[1:]:
            ancestor = candidate["id"]
            while ancestor and ancestor not in mask["roots"]:
                ancestor = nodes[ancestor]["parent"]
            if ancestor:
                mask["members"].append(candidate["id"])
        masks.append(mask)
    groups, group_by_pair = [], {}
    for node in nodes[1:]:
        original = node["mask_original"]
        if not original:
            node["mask_group"] = 0
            continue
        key = (original, node["scope"])
        if key not in group_by_pair:
            group_by_pair[key] = len(groups) + 1
            groups.append({"group_id": len(groups) + 1, "content_scope": node["scope"],
                           **masks[original - 1]})
        node["mask_group"] = group_by_pair[key]
    def short(node_id):
        n = nodes[node_id]
        return {k: n.get(k) for k in ("id", "path", "raw_path", "label", "type", "scope",
                                     "stencil_type", "mask_sources", "mask_original",
                                     "mask_group", "possible_sprite_refs", "motion_refs")}
    def group_info(group):
        return {k: v for k, v in group.items() if k != "members"} | {
            "owner_detail": short(group["owner"]),
            "root_details": [short(n) for n in group["roots"]],
            "member_count": len(group["members"]),
            "masked_possible_sprite_members": [
                short(n) for n in group["members"]
                if nodes[n]["possible_sprite_refs"] and nodes[n]["mask_group"]][:20]}
    by_path = [n for n in nodes[1:] if n["path"] == FAILURE_PATH]
    target = nodes[260]
    exact = target["path"] == FAILURE_PATH and len(by_path) == 1
    memberships = [g for g in groups if 260 in g["members"]]
    ancestors = []
    ancestor = target["parent"]
    while ancestor:
        if nodes[ancestor]["type"] == 12:
            ancestors.append(short(ancestor))
        ancestor = nodes[ancestor]["parent"]
    evidence = {"origin": "parent runtime report", "path": str(AUDIT),
                "file_present": AUDIT.is_file(),
                "reported": {"structural_import_ok": True, "compiled": True,
                             "initial_and_20_timelines_fail_at_tick": 0,
                             "playback_error": 3, "geometry_error": 8,
                             "node": 260, "node_path": FAILURE_PATH}}
    if AUDIT.is_file():
        evidence["sha256"] = digest(AUDIT)
        audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
        evidence["initial_pose"] = audit.get("initial_pose")
        evidence["geometry_diagnostics"] = audit.get("geometry_diagnostics")
        evidence["actual_summary"] = {
            "structural_import_ok": audit.get("structural_import_ok"),
            "compiled": audit.get("compiled"),
            "ok": audit.get("ok"),
            "timeline_count": len(audit.get("timelines", [])),
            "unsupported_field_count": len(audit.get("unsupported_fields", [])),
            "timeline_failure_signatures": [{
                "label": t.get("label"), "failed_author_tick": t.get("failed_author_tick"),
                "failure": t.get("failure")} for t in audit.get("timelines", [])]}
    combinators = []
    def collect_combinators(value, path=""):
        if isinstance(value, dict):
            if "meshCombinator" in value:
                item = value["meshCombinator"]
                comb = item.get("combinatorList", []) if isinstance(item, dict) else []
                resources = []
                def resources_in(node, pointer):
                    if isinstance(node, dict):
                        for k, v in node.items():
                            resources_in(v, pointer + "/" + k)
                    elif isinstance(node, list):
                        for i, v in enumerate(node):
                            resources_in(v, pointer + "/" + str(i))
                    elif isinstance(node, str) and node.startswith("#resource"):
                        resources.append({"path": pointer, "value": node})
                resources_in(item, path + "/meshCombinator")
                combinators.append({"path": path + "/meshCombinator",
                                    "label": value.get("label"),
                                    "nonnull": item is not None,
                                    "combinator_list_length": len(comb),
                                    "resource_references": resources})
            for key, child in value.items():
                collect_combinators(child, path + "/" + str(key))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                collect_combinators(child, path + "/" + str(i))
    collect_combinators(data)
    consumers = []
    for folder in ("src", "include"):
        for path in (ROOT / "source" / folder).rglob("*"):
            if path.suffix in (".cpp", ".hpp", ".h", ".c"):
                text = path.read_text(encoding="utf-8", errors="replace")
                for token in ("meshCombinator", "combinatorList", "rawMeshList"):
                    if token in text:
                        consumers.append({"path": str(path), "token": token})
    combinator_audit = ROOT / "mesh-combinator-audit.json"
    result = {
        "upstream_commit": "4fbf55aa6009df76ac40dc5f18e3781914bc464f",
        "model": {"path": str(MODEL), "sha256": digest(MODEL),
                  "spec": data.get("spec"), "version": data.get("version")},
        "source": {"path": str(CPP), "sha256": digest(CPP)},
        "runtime_evidence": evidence,
        "method": "read-only static reproduction of Compiler::motion/node and mask resolution/grouping; no animation/physics evaluation",
        "expanded_node_count": len(nodes) - 1,
        "reconstructed_node260_matches_reported_path": exact,
        "node260": short(260),
        "node260_initial_frame_content": target["initial_frame_content"],
        "stencil_ancestors": ancestors,
        "node260_own_mask_group": group_info(groups[target["mask_group"] - 1])
            if target["mask_group"] else None,
        "mask_groups_whose_sources_contain_node260": [group_info(g) for g in memberships],
        "all_mask_groups": [group_info(g) for g in groups],
        "independent_mesh_combinator_gap": {
            "field_count": len(combinators),
            "nonnull_count": sum(c["nonnull"] for c in combinators),
            "nonempty_combinator_list_count": sum(c["combinator_list_length"] > 0 for c in combinators),
            "fields": combinators, "source_symbol_occurrences": consumers,
            "parent_audit_path": str(combinator_audit),
            "parent_audit_sha256": digest(combinator_audit) if combinator_audit.is_file() else None,
            "judgment": "Nonempty source deformation programs are archived as unsupported fields; no consumer of the three source symbols exists under fixed src/include. Existing meshCombine/bp handling must not be mistaken for meshCombinator support.",
            "validated_after_mask": False,
            "mask_candidate_pass_does_not_certify_these_fields": True},
        "source_failure_branches": [
            {"line": 1346, "return_line": 1349,
             "condition": "!source.resolved",
             "returned_node": "source.node (type12 stencil owner)"},
            {"line": 1361, "return_line": 1364,
             "condition": "source member has nonzero index_count and command.mask.valid()",
             "returned_node": "source member node (the masked drawable source)"}],
        "judgment": {
            "branch": "geometry_scene.cpp:1361-1364" if exact and target["type"] != 12 else "requires runtime diagnostic confirmation",
            "reason": "reported node is a drawable mask-source member, not a type12 owner; its own inherited mask is nonzero",
            "classification": "current compiler builds a self-dependent mask source set; fixed runtime explicitly rejects it. Source labels are resolved in scope, so this immediate failure is not unresolved/missing/foreign-scope mask-source configuration.",
            "nested_vs_self_dependency": "self dependency in compiled graph, not merely two independent nested masks",
            "authored_model_invalid": "not established; the intended SDK source-vs-content traversal boundary remains unverified",
            "causal_collection": "root185(type3 referenced motion) contains its expanded body_parts motion plus author child stencil256 and masked hair260/263. Descendant closure at lines615-625 includes all of them.",
            "physics_runtime_coverage": "tick0 prepare_frame fails before author step; successful compile does not validate time-stepped physics",
            "no_source_or_model_changes": True,
            "no_workaround_authorized": "do not delete mask, clear inherited mask, disable physics, or weaken UnsupportedMask"},
        "recommended_diagnostic": {
            "location": "build_frame before return at 1364, in an independent diagnostic source copy only",
            "print": ["outer mask loop i+1", "source.node id/path", "source.resolved",
                      "source.members count", "member node id/path", "command.index_count",
                      "command.mask.value", "scene.nodes[node.value].scope",
                      "source roots and original pre-group mask id if available"],
            "preserve_behavior": "log then return the unchanged UnsupportedMask; exit remains failure"}}
    own = target["mask_group"]
    result["judgment"]["node260_own_mask_group"] = own
    result["judgment"]["outer_groups_containing_node260"] = [g["group_id"] for g in memberships]
    result["judgment"]["self_membership_present"] = any(g["group_id"] == own for g in memberships)
    result["candidate_review"] = {
        "proposal": "In an independent candidate TU only, clear mask in the copied mask source command iff command.mask.value == current outer mask i+1; preserve color command and reject other mask dependencies.",
        "status": "bounded diagnostic hypothesis, not proven equivalent semantics",
        "plausible_interpretation": "sample the raw unmasked alpha of a source while retaining masking on the final color content",
        "critical_alternative": "compiler source membership may be too broad: a type3 source may mean its own referenced-motion output, not every authored descendant including its masking content",
        "counterexample": {
            "source_B_alpha": 0.0, "masked_content_H_alpha": 1.0,
            "if_intended_source_is_B": {"mask_alpha": 0.0, "clipped_H_alpha": 0.0},
            "candidate_union_B_H": {"mask_alpha": 1.0, "clipped_H_alpha": 1.0},
            "implication": "Adding H's raw alpha to its own mask can retain pixels outside B and hide an overinclusive source-set bug. Copy-only changes alone do not prove correct source separation."},
        "needed_evidence": [
            "Log outer mask11, owner256, member260, member mask11, nonzero index_count in candidate/source-independent diagnostic run.",
            "Compare unmasked source B, source-plus-H mask coverage, and final H pixels against fixed-input existing WebGL engine output.",
            "Test parent source root with nested authored stencil separately from ordinary sibling source/content and independent nested-mask rejection.",
            "Check hair boundaries/shadow bm19, all other mask groups, both pose idles and parameters.",
            "Keep original upstream failure and candidate results separate; nonempty meshCombinator/other unsupported fields remain unresolved."],
        "not_requested_or_performed": ["no TU modification", "no mask removal", "no physics disabling", "no board connection"]}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(OUTPUT), "nodes": len(nodes)-1,
                      "exact_node260_match": exact, "target_type": target["type"],
                      "own_mask": own,
                      "source_member_of_groups": [g["group_id"] for g in memberships],
                      "group_count": len(groups)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
