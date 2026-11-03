#!/usr/bin/env python
"""Probe the local ComfyUI server and this batch's API graphs (READ-ONLY).

Purpose (see review_20261005/rework task): before re-running any sample, record
which nodes/constraints the generator machine actually offers, instead of
assuming that local-motion / mask / reference-hold controls exist.

Outputs (into --out-dir, default <batch-root>/review_20261005):
  generator_probe_summary.txt        human readable summary
  generator_probe_node_hits.json     keyword-hit node definitions (trimmed)
  generator_probe_batch_graphs.json  per-graph class_type + input key names
"""
import argparse
import collections
import json
import os
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:8188"

KEYWORDS = [
    "motion", "mask", "track", "drag", "camera", "pose", "region", "traj",
    "flow", "optical", "smpl", "dense", "controlnet", "ipadapter", "reference",
    "inpaint", "warp", "skeleton", "animate", "wan", "cog", "hunyuan", "ltx",
    "svd", "dynami", "area", "crop", "stitch", "blend", "velocity", "anchor",
    "static", "lock", "noise", "latent", "sampler", "vae", "image",
]


def http_json(host, path, timeout=180):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(host + path, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8", "replace"))


def input_keys(info):
    keys = []
    for sec in ("required", "optional"):
        d = (info.get("input") or {}).get(sec) or {}
        if isinstance(d, dict):
            keys.extend(sorted(d.keys()))
    return sorted(set(keys))


def category_of(info):
    return str(info.get("category", ""))


def scan_batch(batch_root):
    wf_dir = os.path.join(batch_root, "workflows")
    graphs = {}
    if not os.path.isdir(wf_dir):
        return graphs, []
    for name in sorted(os.listdir(wf_dir)):
        if not name.endswith("_api.json"):
            continue
        path = os.path.join(wf_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                g = json.load(fh)
        except Exception as exc:
            graphs[name] = {"error": str(exc)}
            continue
        nodes = {}
        for nid, node in (g or {}).items():
            if not isinstance(node, dict):
                continue
            ct = node.get("class_type")
            if not ct:
                continue
            ins = sorted((node.get("inputs") or {}).keys())
            cur = nodes.setdefault(ct, {"count": 0, "inputs": set()})
            cur["count"] += 1
            cur["inputs"].update(ins)
        graphs[name] = {
            "node_count": len(g or {}),
            "class_types": {k: {"count": v["count"], "inputs": sorted(v["inputs"])}
                            for k, v in sorted(nodes.items())},
        }
    return graphs, sorted(os.listdir(wf_dir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--grep", default=None,
                    help="regex; matched node names+inputs written to generator_probe_grep.txt")
    ap.add_argument("--dump", default=None,
                    help="comma separated node names; full object_info dumped to generator_probe_dump.json")
    args = ap.parse_args()

    out_dir = args.out_dir or os.path.join(args.batch_root, "review_20261005")
    os.makedirs(out_dir, exist_ok=True)
    summary = []

    # --- 1) service + object_info -------------------------------------------
    object_info = {}
    try:
        stats = http_json(args.host, "/system_stats")
        sysinfo = (stats.get("system") or {})
        devices = stats.get("devices") or []
        summary.append("SERVICE_UP host=%s" % args.host)
        summary.append("COMFYUI_VERSION=%s python=%s os=%s" % (
            sysinfo.get("comfyui_version"), sysinfo.get("python_version"),
            str(sysinfo.get("os"))))
        for d in devices:
            summary.append("DEVICE name=%s type=%s vram_total=%.1fGB vram_free=%.1fGB" % (
                d.get("name"), d.get("type"),
                (d.get("vram_total") or 0) / 1073741824.0,
                (d.get("vram_free") or 0) / 1073741824.0))
    except Exception as exc:
        summary.append("SERVICE_DOWN host=%s err=%s" % (args.host, exc))

    try:
        object_info = http_json(args.host, "/object_info")
        summary.append("OBJECT_INFO_OK node_total=%d" % len(object_info))
    except Exception as exc:
        summary.append("OBJECT_INFO_FAIL err=%s" % exc)

    # --- 2) keyword hits ----------------------------------------------------
    hits = {}
    kw_counts = {}
    if object_info:
        for name, info in object_info.items():
            low = name.lower()
            cat = category_of(info).lower()
            matched = sorted({k for k in KEYWORDS if k in low or k in cat})
            if matched:
                hits[name] = {
                    "category": category_of(info),
                    "matched_keywords": matched,
                    "inputs": input_keys(info),
                    "outputs": sorted(str(o) for o in (info.get("output") or [])),
                }
            for k in matched:
                kw_counts[k] = kw_counts.get(k, 0) + 1
        for k in sorted(kw_counts):
            names = sorted(n for n in hits if k in hits[n]["matched_keywords"])
            summary.append("KW[%s] x%d :: %s" % (k, len(names), ", ".join(names[:25])))

    # --- 3) batch graphs ----------------------------------------------------
    graphs, wf_list = scan_batch(args.batch_root)
    summary.append("")
    summary.append("WORKFLOW_DIR_LIST=%s" % ", ".join(wf_list))
    union = collections.OrderedDict()
    for name, g in sorted(graphs.items()):
        cts = g.get("class_types") or {}
        summary.append("GRAPH %s nodes=%s classes=%s" % (
            name, g.get("node_count"), ", ".join(sorted(cts.keys()))))
        for ct, meta in cts.items():
            u = union.setdefault(ct, {"used_by": 0, "inputs": set()})
            u["used_by"] += 1
            u["inputs"].update(meta["inputs"])
    summary.append("")
    summary.append("BATCH_UNION_CLASSES x%d :: %s" % (len(union), ", ".join(union.keys())))
    for ct, meta in union.items():
        summary.append("BATCH_CLASS %s used_by=%d inputs=%s" % (
            ct, meta["used_by"], ",".join(sorted(meta["inputs"]))))
        if object_info and ct in object_info:
            avail = input_keys(object_info[ct])
            masky = [k for k in avail if "mask" in k.lower() or "region" in k.lower()
                     or "pose" in k.lower() or "track" in k.lower() or "ref" in k.lower()]
            summary.append("   AVAILABLE_INPUTS=%s" % ",".join(avail))
            if masky:
                summary.append("   CONSTRAINT_CANDIDATES=%s" % ",".join(masky))
        elif object_info:
            summary.append("   NOT_INSTALLED_OR_UNKNOWN_CLASS")

    # --- 4) nodes whose inputs accept a mask --------------------------------
    mask_nodes = []
    for name, info in (object_info or {}).items():
        keys = input_keys(info)
        if any(k.lower() == "mask" or k.lower().endswith("_mask") or "motion" in k.lower()
               for k in keys):
            mask_nodes.append((name, category_of(info), keys))
    summary.append("")
    summary.append("NODES_ACCEPTING_MASK_X%d" % len(mask_nodes))
    for name, cat, keys in sorted(mask_nodes)[:200]:
        summary.append("MASKNODE %s [%s] %s" % (name, cat, ",".join(keys)))

    # --- write --------------------------------------------------------------
    with open(os.path.join(out_dir, "generator_probe_summary.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(summary) + "\n")
    with open(os.path.join(out_dir, "generator_probe_node_hits.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"host": args.host, "keyword_count": dict(kw_counts),
                   "node_total": len(object_info), "hits": hits}, fh,
                  ensure_ascii=False, indent=2, sort_keys=True)
    with open(os.path.join(out_dir, "generator_probe_batch_graphs.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"workflows": wf_list, "graphs": graphs,
                   "batch_union_classes": {k: {"used_by": v["used_by"],
                                               "inputs": sorted(v["inputs"])}
                                           for k, v in union.items()}}, fh,
                  ensure_ascii=False, indent=2, sort_keys=True)
    print("PROBE_DONE out_dir=%s lines=%d" % (out_dir, len(summary)))

    if args.grep and object_info:
        import re
        pat = re.compile(args.grep, re.I)
        rows = []
        for name in sorted(object_info):
            if pat.search(name):
                info = object_info[name]
                rows.append("%s [%s] inputs=%s outputs=%s" % (
                    name, category_of(info), ",".join(input_keys(info)),
                    ",".join(str(o) for o in (info.get("output") or []))))
        with open(os.path.join(out_dir, "generator_probe_grep.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write("PATTERN=%s hits=%d\n" % (args.grep, len(rows)))
            fh.write("\n".join(rows) + "\n")
        print("GREP_DONE pattern=%s hits=%d" % (args.grep, len(rows)))

    if args.dump and object_info:
        names = [n.strip() for n in args.dump.split(",") if n.strip()]
        out = {}
        for n in names:
            out[n] = object_info.get(n, "NOT_INSTALLED")
        with open(os.path.join(out_dir, "generator_probe_dump.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        print("DUMP_DONE names=%d" % len(names))




if __name__ == "__main__":
    main()

