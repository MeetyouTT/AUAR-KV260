"""One-file fix for a cancelled native frame's uncommitted sample counters."""
import ast
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parents[1]/'production_frontend_process_capture_candidate/after/aura/board/runtime/audio/board_frontend_process.py'
PIN='7e61f1a963f9dbde7c20b9b76785eb2493e416525df21d2b0d4e961fa96712c3'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def once(text,before,after):
    if text.count(before)!=1:raise ValueError('Exact deployed helper anchor changed')
    return text.replace(before,after,1)
def main():
    raw=BASE.read_bytes()
    if sha(raw)!=PIN:raise ValueError('Exact deployed helper pin changed')
    text=raw.decode('utf-8')
    text=once(text,'    def _accept(self, payload):','    def _accept(self, payload, *, cancelled_frame=False):')
    text=once(text,'                or not 0 <= frames * 320 - samples <= 1024):',
        '                # Cancellation may advance the native model by one frame\n'
        '                # before its completed-frame counter is published. Only\n'
        '                # closed control receipts may carry that bounded residue.\n'
        '                or not (-320 if cancelled_frame else 0) <= frames * 320 - samples <= 1024):')
    text=once(text,'                    decision = decoder(data) if decoder is not None else self._accept(data)',
        '                    decision = decoder(data) if decoder is not None else self._accept(data,\n'
        '                        cancelled_frame=kind in (STOP, 6))  # 6 is closed GATE_RELEASE, never FRAME.')
    ast.parse(text,feature_version=(3,9))
    path=ROOT/'after/board/runtime/audio/board_frontend_process.py'
    path.parent.mkdir(parents=True,exist_ok=True);encoded=text.encode('utf-8');path.write_bytes(encoded)
    manifest=dict(schema='aura.cancelled-control-timeline-fix.v1',hardware_executed=False,
        files={'board/runtime/audio/board_frontend_process.py':dict(sha256=sha(encoded),bytes=len(encoded),before_sha256=PIN)},
        active_FRAME_timeline_unchanged=True,closed_control_lag_minimum=-320,lag_maximum=1024)
    body=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    (ROOT/'overlay_manifest.json').write_bytes(body)
    (ROOT/'extra_source_map.json').write_text(json.dumps({'aura/board/runtime/audio/board_frontend_process.py':str(path)},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(source_sha256=sha(encoded),manifest_sha256=sha(body))))
if __name__=='__main__':main()
