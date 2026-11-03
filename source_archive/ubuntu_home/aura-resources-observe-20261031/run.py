"""Run fixed resource probes through the existing exclusive UART transport."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("probe", choices=("discover", "observe", "details", "verify", "gpu"))
args = parser.parse_args()
spec = importlib.util.spec_from_file_location(
    "reviewed_wire", "/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py"
)
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
source = (ROOT / (args.probe + ".py")).read_text()
command = wire.wire(source)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
directory = ROOT / "evidence" / (stamp + "-" + args.probe)
directory.mkdir(parents=True, mode=0o700)
status = {
    "probe": args.probe,
    "started_host_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "complete": False,
}
uart = None
try:
    with (directory / "serial.raw").open("xb") as raw:
        try:
            uart = wire.transport_module().UART(raw)
            uart.connect()
            rc, body, digest = uart.command(command, "RESOURCE" + args.probe.upper(), 55)
            (directory / "response.output").write_bytes(body)
            status.update(exit_code=rc, output_sha256=digest, complete=(rc == 0))
            if rc == 0:
                value = json.loads(body)
                value["host_observation_started_utc"] = status["started_host_utc"]
                value["host_observation_finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                (directory / "result.json").write_text(json.dumps(value, indent=2) + "\n")
                (ROOT / (args.probe + "-latest.json")).write_text(json.dumps(value, indent=2) + "\n")
                if args.probe == "observe":
                    samples = value["samples"]
                    summary = {k: value[k] for k in ("boot_id", "scope", "before", "after", "duration_s", "cpu_percent", "dpu_completed", "gpu_memory", "collector_stopped_after", "boot_unchanged")}
                    summary["cpu_one_second_peak"] = {k: max(s["cpu"][k] for s in samples) for k in samples[0]["cpu"]}
                    summary["dpu_busy_mean_percent"] = sum(100-s["dpu"][7] for s in samples) / len(samples)
                    summary["dpu_busy_peak_percent"] = max(100-s["dpu"][7] for s in samples)
                    summary["gpu_peak"] = {k: max(s["gpu"][k] for s in samples) for k in samples[0]["gpu"]}
                    summary["memory_first_kib"] = samples[0]["memory_kib"]
                    summary["memory_last_kib"] = samples[-1]["memory_kib"]
                    summary["mem_available_min_kib"] = min(s["memory_kib"]["MemAvailable"] for s in samples)
                    print(json.dumps(summary, ensure_ascii=False), flush=True)
                else:
                    print(json.dumps(value, ensure_ascii=False), flush=True)
            else:
                print(body.decode(errors="replace")[-1500:], flush=True)
        finally:
            if uart:
                status["console_echo_restored"] = uart.close()
except Exception as error:
    status.update(error_type=type(error).__name__, error=str(error)[:300])
status["finished_host_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(directory / "status.json").write_text(json.dumps(status, indent=2) + "\n")
print(json.dumps(status), flush=True)
raise SystemExit(0 if status["complete"] else 1)
