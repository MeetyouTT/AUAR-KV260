"""One reviewed board check/candidate script via the existing exclusive UART.

No production deployment, process control, retry, interrupt or login. Small
script payloads use hash-checked /tmp files and are removed after execution;
explicit staging probes may write only their reviewed independent candidate.
"""
import argparse
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parents[1] / '2026-10-30_visual_simplification/ubuntu'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('script', type=Path)
    parser.add_argument('--timeout', type=int, default=45)
    args = parser.parse_args()
    source = args.script.resolve()
    allowed_local = source.parent == HERE and source.name in (
        'board_dependency_probe.py', 'board_candidate_smoke.py', 'board_stage_asr.py', 'board_asr_probe.py',
        'board_frontend_probe.py', 'board_frontend_profile.py', 'board_gtcrn_fft_probe.py')
    allowed_semantic = (source.parent == HERE.parent / 'integration'
                        and source.name in ('board_semantic_memory_probe.py', 'board_clock_probe.py'))
    assert allowed_local or allowed_semantic
    # The frontend probe stages only its explicitly hashed candidate resources.
    assert 1 <= args.timeout <= 55
    content = source.read_bytes()
    compile(content, str(source), 'exec')
    old = load('previous_uart_runner', PREVIOUS / 'run_uart.py')
    transport = old.load_module('board_check_transport', old.TRANSPORT)
    wire = old.load_module('board_check_wire', old.WIRE)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = HERE / 'evidence' / (stamp + '-' + source.stem)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'source.py').write_bytes(content)
    status = {'script': source.name, 'script_sha256': hashlib.sha256(content).hexdigest(),
              'complete': False, 'production_readonly': True,
              'candidate_only': source.name != 'board_dependency_probe.py', 'evidence': str(out)}
    uart = None
    with (out / 'serial.raw').open('xb') as raw:
        try:
            uart = transport.UART(raw)
            uart.connect()
            encoded = base64.b64encode(gzip.compress(content, mtime=0)).decode()
            target = '/tmp/aura-board-check-' + status['script_sha256'][:16] + '-' + stamp + '.b64'
            status['temporary_script_payload'] = target
            for index, offset in enumerate(range(0, len(encoded), 700)):
                chunk = encoded[offset:offset+700]
                body = ("from pathlib import Path\n"
                        "p=Path(%r);assert not p.is_symlink()\n" % target +
                        "assert (p.stat().st_size if p.exists() else 0)==%d\n" % offset +
                        "with p.open(%r) as f:f.write(%r)\n" %
                        ('xb' if offset == 0 else 'ab', chunk.encode()))
                rc, _, _ = uart.command(wire.wire(body), 'BC%03d' % index, 10)
                assert rc == 0, 'Temporary reviewed script transfer failed'
            body = ("import base64,gzip,hashlib\nfrom pathlib import Path\n"
                    "p=Path(%r);assert not p.is_symlink()\n" % target +
                    "d=gzip.decompress(base64.b64decode(p.read_bytes(),validate=True))\n"
                    "assert hashlib.sha256(d).hexdigest()==%r\n" % status['script_sha256'] +
                    "try:exec(compile(d,%r,'exec'),{'__name__':'__main__'})\n" % source.name +
                    "finally:p.unlink()\n")
            rc, result, sha = uart.command(wire.wire(body), 'BO001', args.timeout)
            (out / 'result.output').write_bytes(result)
            status.update(exit_code=rc, result_sha256=sha)
            assert rc == 0, 'Board command failed; inspect result.output'
            parsed = json.loads(result)
            (out / 'result.json').write_text(json.dumps(parsed, indent=2) + '\n')
            status['complete'] = True
        except Exception as exc:
            status['error'] = type(exc).__name__ + ': ' + str(exc)
        finally:
            if uart is not None:
                status['console_echo_restored'] = uart.close()
    (out / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status))
    raise SystemExit(0 if status['complete'] and status.get('console_echo_restored') else 1)


if __name__ == '__main__':
    main()
