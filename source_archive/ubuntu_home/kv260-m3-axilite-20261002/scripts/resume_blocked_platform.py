#!/usr/bin/env python3
"""Stop only this tracked blocked build, then resume its project outside sandbox."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import signal
import subprocess
import time

root = Path(__file__).resolve().parent.parent
previous = root / "logs/platform_02/result.json"
record = json.loads(previous.read_text())
processes = {}
matches = []
for entry in Path("/proc").iterdir():
    if not entry.name.isdigit():
        continue
    try:
        status = dict(line.split(":", 1) for line in (entry / "status").read_text().splitlines() if ":" in line)
        if int(status["Uid"].split()[0]) != os.getuid():
            continue
        stat = (entry / "stat").read_text().rsplit(")", 1)[1].split()
        pid = int(entry.name)
        processes[pid] = {"ppid": int(status["PPid"]), "start_ticks": stat[19], "name": status["Name"].strip()}
        if (entry / "cwd").resolve() != root:
            continue
        args = (entry / "cmdline").read_bytes().split(b"\0")
        namespace_ids = [int(value) for value in status.get("NSpid", str(pid)).split()]
        if (str(root / "run_m3_build.sh").encode() in args and b"platform" in args
                and namespace_ids[-1] == record.get("pid")):
            matches.append(pid)
    except (OSError, ValueError, KeyError):
        continue
if len(matches) > 1:
    raise SystemExit("Ambiguous tracked build PID; refusing to stop any process")
stopped = []
if matches:
    target = matches[0]
    family = {target}
    while True:
        children = {pid for pid, info in processes.items() if info["ppid"] in family}
        expanded = family | children
        if expanded == family:
            break
        family = expanded
    for pid in sorted(family - {target}, reverse=True) + [target]:
        try:
            now = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
            if now[19] == processes[pid]["start_ticks"]:
                os.kill(pid, signal.SIGTERM)
                stopped.append({"pid": pid, "name": processes[pid]["name"]})
        except (OSError, ValueError):
            pass
    for _ in range(100):
        if not (Path("/proc") / str(target)).exists():
            break
        time.sleep(0.1)
    else:
        raise SystemExit("Tracked build did not stop; refusing concurrent project access")
else:
    if record.get("state") == "running":
        raise SystemExit("Tracked running build not found; refusing concurrent project access")

attempt = 1
while (root / "logs" / f"platform_resume_{attempt:02d}").exists():
    attempt += 1
directory = root / "logs" / f"platform_resume_{attempt:02d}"
directory.mkdir()
state = {"phase": "platform_resume", "started_at_utc": datetime.now(timezone.utc).isoformat(),
         "stopped_tracked_build_processes": stopped, "state": "running",
         "reason": "HLS framebuffer synthesis could not create a local port in sandbox"}
result_path = directory / "result.json"
result_path.write_text(json.dumps(state, indent=2) + "\n")
print("Resuming tracked platform, complete log:", directory / "console.log", flush=True)
with (directory / "console.log").open("x") as log:
    process = subprocess.Popen(["bash", str(root / "run_m3_build.sh"), "resume-platform"],
                               cwd=root, stdout=log, stderr=subprocess.STDOUT)
    state["pid"] = process.pid
    result_path.write_text(json.dumps(state, indent=2) + "\n")
    returncode = process.wait()
state.update({"state": "finished", "returncode": returncode,
              "ended_at_utc": datetime.now(timezone.utc).isoformat()})
result_path.write_text(json.dumps(state, indent=2) + "\n")
print("Resumed platform returncode:", returncode, flush=True)
raise SystemExit(returncode)
