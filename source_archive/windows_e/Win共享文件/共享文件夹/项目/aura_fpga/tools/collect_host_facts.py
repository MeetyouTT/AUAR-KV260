# -*- coding: utf-8 -*-
"""C01 主机事实与依赖盘点（只读、可复现）。

输出：
  1) 项目\\aura_fpga\\docs\\evidence\\host_facts_<date>.json   —— 原始证据
  2) 同目录 host_facts_<date>_summary.txt                      —— 人读摘要
不写系统配置、不安装、不修改任何被测环境。
"""
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys

STAMP = "20261003"
ROOT = r"E:\share、\项目开发\FPGA-amd自主命题赛道"
AURA = os.path.join(ROOT, "项目", "aura_fpga")
EVID = os.path.join(AURA, "docs", "evidence")
JSON_OUT = os.path.join(EVID, f"host_facts_{STAMP}.json")
TXT_OUT = os.path.join(EVID, f"host_facts_{STAMP}_summary.txt")

PIP_KEY = ("torch", "numpy", "sounddevice", "soundfile", "librosa", "av", "opencv",
           "pillow", "transformers", "onnxruntime", "sherpa", "fastapi", "uvicorn",
           "flask", "websocket", "pytest")
EXES = ("ffmpeg", "ffprobe", "sox", "git", "nvidia-smi", "python", "py", "conda", "pandoc")
WEIGHT_EXT = (".onnx", ".safetensors", ".pt", ".pth", ".bin", ".gguf", ".tflite")
HASH_LIMIT = 50 * 1024 * 1024
HASH_MAX = 12
TORCH_PROBE = (
    "import json\n"
    "out={}\n"
    "try:\n"
    "    import torch\n"
    "    out['version']=torch.__version__\n"
    "    out['cuda_build']=torch.version.cuda\n"
    "    out['debug']=getattr(torch.version,'debug',None)\n"
    "    out['cuda_available']=torch.cuda.is_available()\n"
    "    out['device_count']=torch.cuda.device_count()\n"
    "    out['device_name']=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None\n"
    "    out['cudnn']=torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None\n"
    "    out['cpu_threads']=torch.get_num_threads()\n"
    "except Exception as exc:\n"
    "    out['error']='%s: %s' % (type(exc).__name__, exc)\n"
    "print(json.dumps(out, ensure_ascii=False))\n"
)


def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return {"cmd": " ".join(cmd), "rc": p.returncode,
                "out": (p.stdout or "").strip()[:4000], "err": (p.stderr or "").strip()[:600]}
    except FileNotFoundError:
        return {"cmd": " ".join(cmd), "rc": None, "out": "", "err": "NOT_FOUND"}
    except Exception as exc:  # noqa: BLE001
        return {"cmd": " ".join(cmd), "rc": None, "out": "", "err": f"{type(exc).__name__}: {exc}"}


def ps(script):
    return run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def sha256(path, size):
    if size > HASH_LIMIT:
        return "SKIPPED_TOO_LARGE"
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_weights(root, max_depth=5, limit=400):
    found, truncated = [], False
    base_depth = root.rstrip("\\").count("\\")
    for cur, dirs, files in os.walk(root):
        if cur.count("\\") - base_depth >= max_depth:
            dirs[:] = []
        for name in files:
            if name.lower().endswith(WEIGHT_EXT):
                p = os.path.join(cur, name)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                found.append({"path": p, "bytes": st.st_size,
                              "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})
                if len(found) >= limit:
                    return found, True
    return found, truncated


def main():
    facts = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
             "note": "只读盘点；未知项保留 unknown，不猜测", "host": {}, "external_programs": {},
             "python_env": {}, "disks": {}, "paths": {}, "artifacts": {}, "raw": {}}

    facts["host"] = {
        "platform": platform.platform(),
        "win32_ver": platform.win32_ver(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
    }
    facts["raw"]["cpu"] = ps("Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | Format-List")
    facts["raw"]["os"] = ps("Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture | Format-List")
    facts["raw"]["ram_sys"] = ps("Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory | Format-List")
    facts["raw"]["gpu_nvidia_smi"] = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap", "--format=csv"])
    facts["raw"]["gpu_wmi"] = ps("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM | Format-List")

    facts["python_env"] = {"version": sys.version, "executable": sys.executable,
                           "implementation": platform.python_implementation(),
                           "venv": sys.prefix != sys.base_prefix,
                           "conda_prefix_present": "CONDA_PREFIX" in os.environ,
                           "virtual_env_present": "VIRTUAL_ENV" in os.environ}
    pip = run([sys.executable, "-m", "pip", "list", "--format=freeze"])
    pkgs = [ln for ln in pip["out"].splitlines()
            if any(ln.lower().startswith(k) for k in PIP_KEY)]
    facts["python_env"]["pip_relevant"] = pkgs
    facts["python_env"]["pip_total"] = len(pip["out"].splitlines())
    facts["python_env"]["pip_err"] = pip["err"]
    facts["python_env"]["torch_probe"] = run([sys.executable, "-c", TORCH_PROBE])

    for exe in EXES:
        facts["external_programs"][exe] = shutil.which(exe) or "NOT_FOUND"
    if shutil.which("ffmpeg"):
        facts["raw"]["ffmpeg_version"] = run(["ffmpeg", "-version"])

    for letter in "CDEF":
        d = f"{letter}:\\"
        if os.path.exists(d):
            try:
                u = shutil.disk_usage(d)
                facts["disks"][d] = {"total_gb": round(u.total / 2**30, 1),
                                     "free_gb": round(u.free / 2**30, 1)}
            except OSError:
                facts["disks"][d] = "ERROR"

    candidates = {
        "aura_fpga": AURA,
        "aura_repo_under_aura_fpga": os.path.join(AURA, "aura"),
        "aura_repo_root": os.path.join(ROOT, "aura"),
        "project_dir": os.path.join(ROOT, "项目"),
        "host_model_service": os.path.join(AURA, "host", "model_service"),
        "docs": os.path.join(AURA, "docs"),
        "contracts": os.path.join(AURA, "contracts"),
        "upstream_share_dir": r"E:\share、\项目开发",
        "upstream_dev_root": r"E:\share、\项目开发\FPGA语音助手开发",
    }
    for name, path in candidates.items():
        entry = {"path": path, "exists": os.path.exists(path)}
        if os.path.isdir(path) and name != "upstream_share_dir":
            try:
                entry["children"] = sorted(os.listdir(path))[:40]
            except OSError as exc:
                entry["children_error"] = str(exc)
        if os.path.isdir(path) and name == "upstream_share_dir":
            try:
                flat = os.listdir(path)
                entry["child_count"] = len(flat)
                entry["suspected_upstream"] = [n for n in flat if re.search(r"语音|wujing|FPGA", n)]
            except OSError as exc:
                entry["children_error"] = str(exc)
        facts["paths"][name] = entry

    scan_targets = [
        ("aura_fpga", AURA, 5, 400),
        ("aura_repo_root", os.path.join(ROOT, "aura"), 5, 300),
        ("upstream_dev_root", r"E:\share、\项目开发\FPGA语音助手开发", 3, 200),
    ]
    facts["artifacts"]["scans"] = {}
    for label, root, depth, limit in scan_targets:
        if not os.path.isdir(root):
            facts["artifacts"]["scans"][label] = {"root": root, "exists": False}
            continue
        found, truncated = walk_weights(root, max_depth=depth, limit=limit)
        for f in found[:HASH_MAX]:
            f["sha256"] = sha256(f["path"], f["bytes"])
        facts["artifacts"]["scans"][label] = {"root": root, "exists": True, "count": len(found),
                                             "truncated": truncated, "files": found}
    first = facts["artifacts"]["scans"].get("aura_fpga", {})
    facts["artifacts"]["aura_tree_weight_candidates"] = first.get("files", [])
    facts["artifacts"]["aura_tree_truncated"] = first.get("truncated")

    facts["repos"] = {}
    for label, path in (("workspace_root", ROOT), ("aura_repo_root", os.path.join(ROOT, "aura")),
                        ("aura_fpga", AURA),
                        ("upstream_wujing_lite", r"E:\share、\项目开发\FPGA语音助手开发\wujing-lite")):
        if not os.path.isdir(path):
            facts["repos"][label] = {"path": path, "exists": False}
            continue
        entry = {"path": path, "exists": True, "git_dir": os.path.isdir(os.path.join(path, ".git")),
                 "top_level": sorted(os.listdir(path))[:30]}
        if entry["git_dir"]:
            entry["head"] = run(["git", "-C", path, "rev-parse", "HEAD"])
            entry["describe"] = run(["git", "-C", path, "describe", "--tags", "--always", "--dirty"])
            entry["remote"] = run(["git", "-C", path, "remote", "-v"])
            entry["porcelain"] = run(["git", "-C", path, "status", "--porcelain"])
        facts["repos"][label] = entry

    os.makedirs(EVID, exist_ok=True)
    with open(JSON_OUT, "w", encoding="utf-8") as fh:
        json.dump(facts, fh, ensure_ascii=False, indent=2)

    lines = [f"generated_at: {facts['generated_at']}"]
    lines.append(f"platform: {facts['host']['platform']} | cpus={facts['host']['logical_cpu_count']}")
    for key in ("cpu", "os", "ram_sys", "gpu_nvidia_smi", "gpu_wmi"):
        lines.append(f"--- {key} ---")
        lines.append(facts["raw"][key]["out"] or f"[{facts['raw'][key]['err']}]")
    lines.append("--- python ---")
    lines.append(f"{facts['python_env']['version']} | exe={facts['python_env']['executable']} | venv={facts['python_env']['venv']}")
    lines.append(f"pip_total={facts['python_env']['pip_total']}")
    lines.append("pip_relevant: " + ("; ".join(pkgs) if pkgs else "(none)"))
    tp = facts["python_env"]["torch_probe"]
    lines.append("torch_probe: " + (tp["out"] or f"[{tp['err']}]"))
    lines.append("--- external programs ---")
    for k, v in facts["external_programs"].items():
        lines.append(f"{k}: {v}")
    lines.append("--- disks ---")
    for k, v in facts["disks"].items():
        lines.append(f"{k} {v}")
    lines.append("--- paths ---")
    for k, v in facts["paths"].items():
        extra = ""
        if "children" in v:
            extra = f"children={v['children']}"
        if "child_count" in v:
            extra = f"count={v['child_count']} suspected={v['suspected_upstream']}"
        lines.append(f"{k}: exists={v['exists']} {extra}")
    lines.append("--- repos ---")
    for label, entry in facts["repos"].items():
        if not entry.get("exists"):
            lines.append(f"[{label}] missing: {entry['path']}")
            continue
        lines.append(f"[{label}] {entry['path']} git={entry['git_dir']}")
        lines.append(f"  top_level={entry['top_level']}")
        if entry["git_dir"]:
            for key in ("head", "describe", "remote"):
                lines.append(f"  {key}: {entry[key]['out'] or '[empty]'}")
            pc = entry["porcelain"]["out"]
            lines.append(f"  porcelain_lines={len(pc.splitlines())}")
    lines.append("--- weight/artifact candidates ---")
    for label, scan in facts["artifacts"]["scans"].items():
        if not scan.get("exists"):
            lines.append(f"[{label}] root missing: {scan['root']}")
            continue
        lines.append(f"[{label}] root={scan['root']} count={scan['count']} truncated={scan['truncated']}")
        for f in scan["files"][:60]:
            lines.append("  {} | {} B | sha256={}".format(f["path"], f["bytes"], f.get("sha256")))
    with open(TXT_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("json:", JSON_OUT)
    print("summary:", TXT_OUT)


if __name__ == "__main__":
    main()
