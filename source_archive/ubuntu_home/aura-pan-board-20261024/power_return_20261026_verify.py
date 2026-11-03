"""Bounded live-input and artifact audit; read-only, no controller or MMIO."""
import base64
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BOOT = 'da36c36a-ef4d-4122-8ad6-cfae3931303e'
R = Path('/home/root/aura-pan-current-20261024/16a07283')
G = R / 'gui-manual-bound-v1'
A = G / 'runtime/aura'
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
F = OPS / 'pan-face-edge-v5'
P = F / 'continuous-v10r15'
S = F / 'face-source-v17'
OLD = Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def get(port, path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=3) as r:
        return json.load(r)


def health():
    h = get(8790, '/health')
    s, identity = h['dpu_schedule'], h['identity']
    return dict(pid=h['pid'], detection_hz=h['detection_hz'], detected_frames=h['detected_frames'],
                capture_frames=h['capture_frames'], preview_frames=h['preview_frames'],
                camera_error=h['camera_error'], detector_error=h['detector_error'],
                preview_error=h['preview_error'], owner_fenced=s['owner_fenced'],
                primary_calls=s['primary_calls'], primary_overruns=s['primary_period_overruns'],
                protection_handoff=s.get('protection_handoff'), seed_loaded=s.get('seed_loaded'),
                optional={k: {n: v.get(n) for n in ('calls', 'overruns', 'disabled', 'recovery')}
                          for k, v in s['optional'].items()}, identity_ready=identity['ready'],
                sface_completed=identity['feature_inference']['completed'])


def ui():
    value = get(8783, '/api/state')
    m = value['manual_pan']
    return dict(manual_state=m['state'], error=m.get('error'), readback=m.get('readback'),
                automatic_following=m['automatic_following'], phase=value['phase'],
                playing=value.get('playing'), audio_output_state=value.get('audio_output_state'),
                recording_state=value.get('local_recording', {}).get('state'),
                transcription_pending=value.get('local_transcription', {}).get('service', {}).get('pending'))


def main():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
    assert sha(P / 'deployment-manifest.json') == 'c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de'
    assert sha(S / 'deployment-manifest.json') == '84d7359f18a5a98aa5dabba967c4ededf5e35d0c43153166fc6998729a30219c'
    cp = json.loads((P / 'deployment-manifest.json').read_text())['files']
    sp = json.loads((S / 'deployment-manifest.json').read_text())['pins']
    gp = json.loads((G / 'startup/config.json').read_text())['component_sha256']
    assert all(sha(x['destination']) == x['sha256'] for x in cp)
    assert all(sha(p) == h for p, h in sp.items())
    assert all(sha(A / p) == h for p, h in gp.items())
    assert sha(OLD / 'candidate-manifest.json') == 'ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
    candidate = json.loads((OLD / 'candidate-manifest.json').read_text())
    assert all(sha(p) == h for p, h in candidate['runtime_files'].items())
    assert all(sha(OLD / 'driver' / p) == h for p, h in candidate['payload_files'].items())
    meta = json.loads((OPS / 'meta.json').read_text())
    assert all(sha(OPS / p) == h for p, h in meta['source_pins'].items())
    before, ui_before = health(), ui()
    assert before['pid'] == 1333 and not before['owner_fenced']
    assert ui_before['manual_state'] == 'FAULT' and not ui_before['automatic_following']
    sys.path.insert(0, str(P))
    from face_stream import FaceStream
    from input_timing import InputTiming
    timing = InputTiming()
    stream = FaceStream()
    start = time.monotonic()
    events = {}
    boot_mismatch = 0
    try:
        while time.monotonic() - start < 15:
            for kind, packet in stream.drain():
                if kind == 'packet':
                    if packet.get('board_boot_id') != BOOT:
                        boot_mismatch += 1
                    timing.observe(packet, {'reason': 'READONLY_UNADMITTED'}, int(time.monotonic() * 1000))
                else:
                    events[kind] = events.get(kind, 0) + 1
            time.sleep(.01)
    finally:
        stream.close()
    end = time.monotonic()
    after, ui_after = health(), ui()
    assert after['pid'] == before['pid'] and not ui_after['automatic_following']
    assert ui_after['manual_state'] == 'FAULT' and ui_after['readback'] is None
    journal = subprocess.run(['journalctl', '-k', '-b', '-n', '500', '-o', 'json', '--no-pager'],
                             capture_output=True, text=True, timeout=4)
    warnings = 0
    first = last = None
    rows = []
    if journal.returncode == 0:
        for line in journal.stdout.splitlines():
            row = json.loads(line)
            mono = int(row.get('__MONOTONIC_TIMESTAMP', 0)) / 1000000.
            if start <= mono <= end and row.get('_BOOT_ID') == BOOT.replace('-', ''):
                rows.append(mono)
                if "HC couldn't access mem fast enough for slot 4 ep 3" in row.get('MESSAGE', ''):
                    warnings += 1
        if journal.stdout.splitlines():
            all_times = [int(json.loads(x).get('__MONOTONIC_TIMESTAMP', 0)) / 1000000. for x in journal.stdout.splitlines()]
            first, last = min(all_times), max(all_times)
    native_cfg = json.loads(Path(meta['candidate_config']).read_text())['native_execution']
    result = dict(status='READONLY_NEW_BOOT_ARTIFACT_AND_INPUT_AUDIT', boot_id=BOOT,
                  duration_s=round(end - start, 3), before=before, after=after, ui_before=ui_before, ui_after=ui_after,
                  verified_pins=dict(control=len(cp), source=len(sp), gui=len(gp), joint_runtime=len(candidate['runtime_files'])),
                  input_timing=timing.snapshot(), reader=stream.diagnostics(), stream_events=events,
                  packet_boot_mismatches=boot_mismatch, all_sources_unadmitted=True,
                  kernel=dict(returncode=journal.returncode, exact_usb_warnings_in_window=warnings,
                              bounded_tail_lines=len(journal.stdout.splitlines()), earliest_retained_mono=first,
                              latest_retained_mono=last, window_begin=start, window_end=end,
                              tail_covers_window=first is not None and first <= start),
                  current_fdt_base64=base64.b64encode(Path('/sys/firmware/fdt').read_bytes()).decode(),
                  candidate_config=str(meta['candidate_config']), native_execution=native_cfg,
                  current_gui_config_sha256=sha(G / 'startup/config.json'),
                  motor_commands_sent=0, mmio_opened=False, services_modified=False,
                  actuator_modules_loaded=sorted(set(sys.modules) & {'vsrv_driver', 'vsrv_transport', 'deadline_driver'}))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
