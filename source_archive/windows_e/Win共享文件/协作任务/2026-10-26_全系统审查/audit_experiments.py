"""Read-only source audit and isolated reproductions. No models or hardware.

Run with an existing Python containing the standard library only. It parses
source and imports pure face-control math, the injected VSRV driver and a
reader class without opening any socket. Results go to a new JSON file.
"""
import argparse
import ast
import hashlib
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
WORKSPACE = Path(__file__).resolve().parents[2]
VOICE = WORKSPACE / '语音共享文件/aura'
PAN = WORKSPACE / '协作任务/2026-10-25_GitHub转轴低延迟闭环修复'
SOURCE = PAN / 'continuous_v10r10'
V12 = WORKSPACE / '协作任务/2026-10-25_来电恢复与转轴验证_r2/face_source_v12'
NATIVE = WORKSPACE / '语音共享文件/deliverables/2026-10-24_native_critical_live'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint_checks():
    groups = {}
    checks = []
    for row in (SOURCE / 'SOURCE_SHA256.txt').read_text().splitlines():
        expected, relative = row.split(maxsplit=1)
        path = SOURCE / relative
        checks.append({'file': relative, 'exists': path.is_file(),
                       'match': path.is_file() and digest(path) == expected})
    groups['r10_source'] = checks
    native = json.loads((NATIVE / 'SHA256SUMS.json').read_text(encoding='utf-8-sig'))['files_sha256']
    groups['native_frozen_source'] = [
        {'file': name, 'exists': (NATIVE / name).is_file(),
         'match': (NATIVE / name).is_file() and digest(NATIVE / name) == expected}
        for name, expected in native.items() if name.startswith('source/')]
    root = WORKSPACE / '语音共享文件/deliverables/2026-10-21_environment_frontend/pc_service'
    frontend = json.loads((root / 'manifest.json').read_text(encoding='utf-8-sig'))
    groups['pc_frontend'] = [
        {'file': name, 'exists': (root / 'aura' / name).is_file(),
         'match': (root / 'aura' / name).is_file() and digest(root / 'aura' / name) == expected}
        for name, expected in frontend.items()]
    aliases = {'native_entry_operator.py': WORKSPACE / '语音共享文件/deliverables/2026-10-24_pan_follow_shadow/source/native_operator_v1/native_entry_operator.py',
               'face_source.py': WORKSPACE / '语音共享文件/deliverables/2026-10-24_pan_follow_shadow/source/face_edge_v5/face_source.py'}
    pins = json.loads((V12 / 'deployment-manifest.json').read_text())['pins']
    groups['v12_pins_local_aliases'] = []
    for board_path, expected in pins.items():
        name = board_path.rsplit('/', 1)[1]
        local = aliases.get(name, V12 / name)
        groups['v12_pins_local_aliases'].append({'board_file': board_path,
            'local_file': str(local.relative_to(WORKSPACE)), 'exists': local.is_file(),
            'match': local.is_file() and digest(local) == expected})
    return {name: {'checked': len(rows), 'matched': sum(x['match'] for x in rows),
                   'failures': [x for x in rows if not x['match']]}
            for name, rows in groups.items()}


def static_inventory():
    counts, errors = {}, []
    roots = {'windows_and_shared': [VOICE / n for n in ('common', 'board', 'host', 'tools')],
             'native_frozen': [NATIVE / 'source'], 'r10': [SOURCE], 'v12': [V12]}
    for label, directories in roots.items():
        count = 0
        for directory in directories:
            for path in directory.rglob('*.py'):
                if '.sync-conflict-' in path.name or '__pycache__' in path.parts:
                    continue
                count += 1
                try:
                    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
                except (SyntaxError, UnicodeError) as exc:
                    errors.append({'file': str(path.relative_to(WORKSPACE)), 'error': str(exc)})
        counts[label] = count
    configs = list((VOICE / 'config').glob('*.json'))
    for path in configs:
        try:
            json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError, UnicodeError) as exc:
            errors.append({'file': str(path.relative_to(WORKSPACE)), 'error': str(exc)})
    storage = json.loads((VOICE / 'config/model_storage.local.json').read_text())
    return {'python_files_parsed': counts, 'config_json_files_parsed': len(configs),
            'parse_errors': errors, 'model_storage_configuration': storage,
            'model_weights_opened': False}


def reproduce_controls():
    sys.path[:0] = [str(SOURCE), str(PAN / 'offline_host_driver')]
    from continuous_face_control import EdgeConfig, FaceEdgeController
    from common.motion_observation import PROTOCOL
    from pulse_driver import PulseDriver
    from vsrv_driver import COMMIT, STOP, ID, ABI, BUILD_ID

    def packet(fid, stamp, center):
        return dict(protocol_version=PROTOCOL, source_kind='fixture', target_kind='face',
            board_boot_id='boot', service_epoch='service', camera_epoch='camera', state='READY',
            source_frame_id=fid, source_mono_ms=stamp, deadline_mono_ms=stamp+250,
            frame_width=640, frame_height=480, mirror_horizontal=True,
            target=dict(track_id=1, track_generation=1, box=[center*640-40,100.,80.,80.],score=.95))

    def trace(config):
        controller = FaceEdgeController('boot', 1469, config=config)
        result = []
        for i, center in enumerate([.79]*12+[.81,.82,.83,.84,.85,.86]+[.86]*8, 1):
            state = controller.observe(packet(i,1000+i*80,center),1000+i*80,allow_fixture=True)
            result.append(tuple(state[k] for k in ('filtered_center_ratio',
                'face_image_velocity_ratio_s','requested_velocity_us_s')))
        return result

    parameters = trace(EdgeConfig(left_ratio=.1,filter_tau_ms=30.,velocity_filter_tau_ms=30.)) == trace(
        EdgeConfig(left_ratio=.1,filter_tau_ms=500.,velocity_filter_tau_ms=300.))
    controller = FaceEdgeController('boot',1469,config=EdgeConfig(left_ratio=.1,
        maximum_speed_us_s=20.,velocity_gain_us=12.,maximum_correction_us=None,confirm_frames=2))
    for i in range(1,31):
        state=controller.observe(packet(i,1000+i*80,.807),1000+i*80,allow_fixture=True)

    class Registers:
        def __init__(self):
            self.now=10.; self.expiry=None
            self.values={0:ID,4:ABI,8:BUILD_ID,0x0c:14,0x28:0,0x2c:1469,0x30:0,
                         0x34:7,0x38:9,0x40:1469,0x44:1469}
        def read(self,n): return self.values.get(n,0)
        def read_many(self,ns): return [self.read(n) for n in ns]
        def write(self,n,value):
            self.values[n]=value
            if n==0x24 and value==COMMIT:
                self.now+=.300  # Inject a pause after the last host source-age check.
                self.expiry=self.now+self.values[0x20]/1000.
                self.values.update({0x0c:15,0x28:self.values[0x18],
                    0x44:self.values[0x1c],0x30:self.values[0x20]})
            if n==0x24 and value==STOP: self.values.update({0x0c:0,0x30:0})
    io=Registers(); driver=PulseDriver(io,BUILD_ID,'boot',clock=lambda:io.now)
    driver.reference=object(); driver.reference_time=9.9
    driver.session=7; driver.epoch=9; driver.ack_seq=0; driver.accepted_target_us=1469
    ack=driver.submit(1470,10.,freshness_s=.25,margin_s=.02)
    return {'filter_time_configuration_output_identical':parameters,
        'near_boundary_requested_us_s':state['requested_velocity_us_s'],
        'half_integer_step_time_ms_ignoring_acceleration':500/abs(state['requested_velocity_us_s']),
        'late_commit_injection':{'scope':'injected registers, not RTL or hardware',
            'pause_ms':300,'outcome':ack['outcome'],'source_deadline_s':10.25,
            'commit_s':io.now,'lease_ms':ack.get('lease_ms'),
            'relative_hardware_expiry_s':io.expiry}}


def reproduce_cleanup_order():
    from face_stream import FaceStream
    tree=ast.parse((SOURCE/'run_face_motion.py').read_text())
    cleanup=next(node for node in ast.walk(tree) if isinstance(node,ast.Try) and node.finalbody
        and ast.unparse(node.finalbody[0])=='stream.close()')
    stream=FaceStream.__new__(FaceStream)
    stream.closed=threading.Event(); stream.connection=None
    blocked=threading.Event()
    stream.thread=threading.Thread(target=lambda:blocked.wait(.12),daemon=True)
    stop_times=[]
    class Session:
        def status(self): return {}
        def close(self):
            stop_times.append(time.perf_counter())
            return {'readback':{'flags':0,'lease_left_ms':0}}
    namespace=dict(stream=stream,session=Session(),report={},packet_states={},raw_positions={},
        decisions={},observation_trace=[],timing={},reason='OPERATOR_STOP',
        atomic=lambda *args:None,a=SimpleNamespace(output=None))
    stream.thread.start(); began=time.perf_counter()
    exec(compile(ast.Module(body=cleanup.finalbody,type_ignores=[]),'<isolated-cleanup>','exec'),namespace)
    return {'scope':'exact runner cleanup AST, fake session, simulated blocked reader, no sockets',
        'configured_reader_block_ms':120,'stop_called_after_ms':round((stop_times[0]-began)*1000,3),
        'reader_cleanup_precedes_motor_stop':True,
        'physical_stop_delay_measured':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Output already exists; choose a new file')
    result={'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'source snapshots and isolated injections; no model inference or board access',
        'fingerprints':fingerprint_checks(),'static':static_inventory(),
        'controls':reproduce_controls(),'cleanup':reproduce_cleanup_order()}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
