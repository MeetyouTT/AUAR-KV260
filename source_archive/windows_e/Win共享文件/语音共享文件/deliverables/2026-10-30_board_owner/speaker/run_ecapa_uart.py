"""Exclusive short UART stage/launch/poll; root owns inter-task scheduling."""
import argparse
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("stage", "launch", "poll"))
    parser.add_argument("--base", required=True)
    parser.add_argument("--pin", required=True)
    args = parser.parse_args()
    assert args.base.startswith("http://192.168.50.1:")
    assert len(args.pin) == 64 and set(args.pin) <= set("0123456789abcdef")
    config = dict(base=args.base, pin=args.pin, mode=args.mode)
    source = (HERE / "board_candidate_operation.py").read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = HERE / "evidence" / (stamp + "-" + args.mode)
    evidence.mkdir(parents=True, exist_ok=False)
    (evidence / "source.py").write_bytes(source)
    transport = load("ecapa_uart_transport", "/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py")
    wire = load("ecapa_uart_wire", "/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py")
    temporary = "/tmp/aura-ecapa-reviewed-" + source_hash[:16] + "-" + stamp + ".b64"
    status = dict(mode=args.mode, complete=False, script_sha256=source_hash, evidence=str(evidence))
    uart = None
    with (evidence / "serial.raw").open("xb") as raw:
        try:
            uart = transport.UART(raw); uart.connect()
            encoded = base64.b64encode(gzip.compress(source, mtime=0)).decode()
            for index, offset in enumerate(range(0, len(encoded), 700)):
                part = encoded[offset:offset+700]
                body = ("from pathlib import Path\np=Path(%r);assert not p.is_symlink()\n" % temporary +
                        "assert (p.stat().st_size if p.exists() else 0)==%d\n" % offset +
                        "with p.open(%r) as out:out.write(%r)\n" % ("xb" if offset == 0 else "ab", part.encode()))
                code, _, _ = uart.command(wire.wire(body), "ES%03d" % index, 10)
                assert code == 0
            body = ("import base64,gzip,hashlib\nfrom pathlib import Path\np=Path(%r)\n" % temporary +
                    "assert not p.is_symlink()\ndata=gzip.decompress(base64.b64decode(p.read_bytes(),validate=True))\n" +
                    "assert hashlib.sha256(data).hexdigest()==%r\n" % source_hash +
                    "try:exec(compile(data,'board_candidate_operation.py','exec'),{'__name__':'__main__','CONFIG':%r})\n" % config +
                    "finally:p.unlink()\n")
            code, result, checksum = uart.command(wire.wire(body), "ECAPA01", 50 if args.mode == "stage" else 15)
            (evidence / "result.output").write_bytes(result)
            status.update(exit_code=code, result_sha256=checksum)
            assert code == 0
            parsed = json.loads(result)
            (evidence / "result.json").write_text(json.dumps(parsed, indent=2))
            status["complete"] = True
        except Exception as exc:
            status["error"] = type(exc).__name__ + ": " + str(exc)
        finally:
            if uart is not None:
                status["console_echo_restored"] = uart.close()
    (evidence / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    if not status["complete"] or not status.get("console_echo_restored"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
