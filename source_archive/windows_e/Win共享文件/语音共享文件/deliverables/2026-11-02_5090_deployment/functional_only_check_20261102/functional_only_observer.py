"""Read-only bounded check of dialogue, speaker address, short recall and avatar; no axis controls."""
import argparse
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def atomic(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def numbers(value, depth=0):
    if not isinstance(value, dict) or depth > 5:
        return {}
    result = {}
    for key, item in value.items():
        if type(item) in (bool, int, float) or item is None:
            result[key] = item
        elif isinstance(item, dict):
            result[key] = numbers(item, depth + 1)
    return result


BOARD_MAIN = r'''
def owner_check():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == CONTRACT['boot_id'], 'boot_changed'
    assert hashlib.sha256(Path(CONTRACT['startup_path']).read_bytes()).hexdigest() == CONTRACT['startup_sha256'], 'source_changed'
    for expected in CONTRACT['owners']:
        proc = Path('/proc') / str(expected['pid'])
        assert proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == str(expected['birth_ticks']), 'owner_changed'
        assert hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest() == expected['command_sha256'], 'command_changed'

def request():
    con = http.client.HTTPConnection('127.0.0.1', 8783, timeout=2)
    try:
        con.request('GET', '/api/state')
        response = con.getresponse()
        raw = response.read(2097153)
        assert response.status == 200 and len(raw) <= 2097152
        return json.loads(raw)
    finally:
        con.close()

def extended(state):
    value = project(state)
    pan = obj(state, 'manual_pan')
    business = obj(state, 'board_business')
    speaker = obj(business, 'speaker')
    if not speaker:
        speaker = obj(obj(state, 'identity_voice_enrollment'), 'speaker')
    address = obj(speaker, 'conversation_address')
    memory = obj(business, 'memory')
    value.update(ui_page=enum(state.get('ui_page'), ('main','vision','settings','history','memory','profiles','devices')),
        pan={'state': enum(pan.get('state'), ('READY','MOVING','FAULT','CONNECTING','STOPPING','CLOSED','UNAVAILABLE')),
             'automatic_following': pan.get('automatic_following'),
             'pulse_us': pan.get('pulse_us'), 'target_us': pan.get('target_us')},
        conversation_address={'phase': enum(address.get('phase'), ('IDLE','WAITING','CACHED','MATCHED','UNKNOWN','DISABLED','REJECTED','MATCHING')),
            'required_captures': address.get('required_captures'), 'matched_captures': address.get('matched_captures'),
            'session_cached': address.get('session_cached')},
        memory={'running': memory.get('running'), 'completed': memory.get('completed'),
                'discarded': memory.get('discarded'), 'error_present': bool(memory.get('error'))},
        avatar=metrics(obj(state, 'avatar_display')))
    return value

owner_check()
started = time.monotonic()
baseline = extended(request())
seen = set()
if baseline['ack']['turn_hash']:
    seen.add(baseline['ack']['turn_hash'])
emit({'event':'BASELINE','board_mono':started,'boot_id':CONTRACT['boot_id'],
      'baseline':baseline,'max_seconds':CONTRACT['duration_seconds'],'all_actions_read_only':True})
new_turns = 0
last_guard = started
while time.monotonic() - started < CONTRACT['duration_seconds']:
    tick = time.monotonic()
    if tick-last_guard >= 2:
        owner_check()
        last_guard = tick
    try:
        value = extended(request())
        emit(value)
        ack = value['ack']
        if ack['turn_hash'] and ack['committed'] is True and ack['turn_hash'] not in seen:
            seen.add(ack['turn_hash'])
            new_turns += 1
            emit({'event':'TURN_COMPLETED','board_mono':time.monotonic(),'ordinal':new_turns,'turn_hash':ack['turn_hash']})
    except (OSError,ValueError,http.client.HTTPException) as error:
        emit({'event':'READ_UNAVAILABLE','board_mono':time.monotonic(),'error_type':type(error).__name__})
    if new_turns >= CONTRACT['target_completed_turns'] and not value.get('playing') and not value.get('job_pending'):
        break
    time.sleep(max(0, .5-(time.monotonic()-tick)))
owner_check()
last = extended(request())
emit({'event':'FINISHED','board_mono':time.monotonic(),'elapsed_seconds':time.monotonic()-started,
      'completed_new_turns':new_turns,'final':last,'board_controls_sent':0,
      'raw_audio_text_images_names_or_templates_exported':False})
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8-sig"))
    assert contract["permission_active"] is True
    assert 30 <= contract["duration_seconds"] <= 120
    assert contract["scope"] == "functional_only_axis_stopped"
    assert contract["target_completed_turns"] == 3
    source = BASE / "dialogue_latency_20261101/watch_board_latency.py"
    raw = source.read_text(encoding="utf-8-sig")
    wanted = {"obj", "token", "metrics", "enum", "jobs", "project", "emit"}
    definitions = [ast.get_source_segment(raw, node) for node in ast.parse(raw).body
                   if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert len(definitions) == len(wanted)
    payload = ("import hashlib,http.client,json,re,time\nfrom pathlib import Path\n" +
               "CONTRACT=json.loads(" + repr(json.dumps(contract)) + ")\n" +
               "\n\n".join(definitions) + "\n" + BOARD_MAIN)
    compile(payload, "functional_board_observer", "exec")
    assert "con.request('POST'" not in payload and "sqlite3" not in payload
    if args.check_only:
        print(json.dumps({"syntax_valid": True, "board_commands_sent": 0}))
        return
    gate_path = HERE / "FUNCTIONAL_ONLY_START_GATE.json"
    deadline = time.monotonic() + 30
    atomic(HERE / "FUNCTIONAL_OBSERVER_STATUS.json", {"phase": "ARMED_WAIT_START_GATE", "board_calls": 0})
    while not gate_path.is_file():
        if time.monotonic() >= deadline:
            raise RuntimeError("No fresh start gate")
        time.sleep(.2)
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
    assert gate["run_id"] == contract["run_id"]
    begin = dt.datetime.fromisoformat(gate["start_not_before_utc"])
    while dt.datetime.now(dt.timezone.utc) < begin:
        time.sleep(.1)
    assert dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(contract["may_start_before_utc"])
    key = Path.home() / ".ssh/aura_5090_board_ed25519"
    known = Path.home() / ".ssh/aura_migration_known_hosts"
    argv = [shutil.which("ssh.exe") or shutil.which("ssh"), "-i", str(key),
            "-o", "UserKnownHostsFile=" + str(known), "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=4",
            "root@192.168.50.2", "python3 -B -"]
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding="utf-8")
    process.stdin.write(payload)
    process.stdin.close()
    stop = threading.Event()

    def host_models():
        with (HERE / "windows_models.jsonl").open("x", encoding="utf-8") as stream:
            while not stop.is_set():
                item = {"host_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "host_mono": time.monotonic()}
                try:
                    with urllib.request.urlopen("http://192.168.50.1:8797/health", timeout=2) as response:
                        h = json.load(response)
                    backend = h.get("backend", {})
                    gpu = backend.get("gpu_coordination", {})
                    item.update(ok=h.get("ok"), active=h.get("active"), pending=h.get("pending"),
                        counts=numbers(h.get("counts", {})), tts_ready=backend.get("tts_ready"),
                        voice_alive=backend.get("voice", {}).get("alive"),
                        gpu_schedule=numbers(gpu), model_inference_requested=False)
                except Exception as error:
                    item["error_type"] = type(error).__name__
                stream.write(json.dumps(item, separators=(",", ":")) + "\n")
                stream.flush()
                stop.wait(1)
    worker = threading.Thread(target=host_models, daemon=True)
    worker.start()
    atomic(HERE / "FUNCTIONAL_OBSERVER_STATUS.json", {"phase": "RUNNING", "ssh_pid": process.pid,
        "run_id": contract["run_id"], "host_started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(), "board_controls_sent": 0})
    events = []
    try:
        with (HERE / "functional_events.jsonl").open("x", encoding="utf-8") as stream:
            for line in process.stdout:
                value = json.loads(line)
                value["host_observed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
                stream.write(json.dumps(value, separators=(",", ":")) + "\n")
                stream.flush()
                if value.get("event") != "SAMPLE":
                    events.append(value)
                    print(json.dumps({k: value[k] for k in ("event", "board_mono", "ordinal", "completed_new_turns", "elapsed_seconds") if k in value}), flush=True)
    finally:
        stop.set()
        worker.join(timeout=3)
    stderr = process.stderr.read()
    rc = process.wait(timeout=5)
    result = {"phase": "FINISHED" if rc == 0 else "FAILED", "exit_code": rc,
              "stderr_present": bool(stderr), "host_end_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "events": events, "board_controls_sent": 0}
    atomic(HERE / "FUNCTIONAL_OBSERVER_STATUS.json", result)
    if rc:
        raise RuntimeError("Read-only observation failed; see redacted exit status")


if __name__ == "__main__":
    main()
