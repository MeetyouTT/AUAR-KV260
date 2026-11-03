"""Read-only joint dialogue/vision/axis metadata observer, supplied via SSH stdin.

EXPECTED must be prepended by the host from a fresh, independently checked
deployment receipt. This program never changes listening, pages or motion.
"""
import argparse
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import re
import time

STARTUP = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')

def obj(value,key):
    result = value.get(key,{}) if isinstance(value,dict) else {}
    return result if isinstance(result,dict) else {}

def token(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16] if type(value) is str and value else None

def metrics(value,depth=0):
    if not isinstance(value,dict) or depth>4:return {}
    output = {}
    for key,item in value.items():
        if type(key) is not str or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,70}',key):continue
        if type(item) in (int,float,bool) or item is None:output[key] = item
        elif isinstance(item,dict):output[key] = metrics(item,depth+1)
        elif key in ('request_id','capture_id','session_id'):output[key+'_hash'] = token(item)
        elif key=='error_class' and type(item) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,80}',item):output[key] = item
    return output

def scalar(value,key):
    item = value.get(key) if isinstance(value,dict) else None
    return item if item is None or type(item) in (int,float,bool) else None

def enum(value,allowed):
    return value if type(value) is str and value in allowed else None

def get(port,path):
    connection = http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    begin = time.monotonic()
    try:
        connection.request('GET',path)
        response = connection.getresponse();raw = response.read(2097153)
        assert response.status==200 and len(raw)<=2097152
        result = json.loads(raw)
        assert isinstance(result,dict)
        return result,(time.monotonic()-begin)*1000
    finally:connection.close()

def guard(expected):
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=expected['boot_id']:
        raise RuntimeError('boot_changed')
    if hashlib.sha256(STARTUP.read_bytes()).hexdigest()!=expected['startup_sha256']:
        raise RuntimeError('startup_changed')
    for item in expected['owners'].values():
        root = Path('/proc')/str(item['pid'])
        if (root/'stat').read_text().rsplit(')',1)[1].split()[19]!=str(item['birth_ticks']):
            raise RuntimeError('owner_birth_changed')
        if hashlib.sha256((root/'cmdline').read_bytes()).hexdigest()!=item['command_sha256']:
            raise RuntimeError('owner_command_changed')

def project_gui(state):
    business = obj(state,'board_business');job = obj(business,'dialogue')
    if 'latency' not in job:job = obj(obj(state,'local_transcription'),'service')
    hf = obj(state,'handsfree_dialogue');rec = obj(state,'local_recording')
    transcription = obj(state,'local_transcription');ack = obj(job,'last_playback_ack')
    pan = obj(state,'manual_pan');display = obj(state,'avatar_display')
    return {'event':'SAMPLE','board_mono':time.monotonic(),'api_sequence':scalar(state,'sequence'),
        'phase':enum(state.get('phase'),('IDLE','VOICE_PREPARING','VOICE_STARTING','SPEAKING','ACTION','DIALOGUE_WAITING')),
        'ui_page':enum(state.get('ui_page'),('main','vision','settings','devices','history','profiles','memory')),
        'playing':scalar(state,'playing'),'hf_enabled':scalar(hf,'enabled'),
        'hf_state':enum(hf.get('state'),('PAUSED','WAITING_SERVICE','WAITING_SPEECH','WAITING_WAKE','COOLDOWN','CONVERSATION')),
        'microphone_open':scalar(hf,'microphone_open'),
        'recording_state':enum(rec.get('state'),('IDLE','READY','RECORDING','ERROR','STOPPING')),
        'recording_sample_count':scalar(rec,'sample_count'),'recording_duration_seconds':scalar(rec,'duration_seconds'),
        'recording_metadata':metrics(obj(rec,'result')),
        'transcription_state':enum(transcription.get('state'),('IDLE','DISABLED','PENDING','TRANSCRIBING','READY','ANSWERING','ANSWERED','ERROR','CANCELLED')),
        'turn_hash':token(transcription.get('request_id')),
        'job_pending':scalar(job,'pending'),'latency':metrics(obj(job,'latency')),
        'ack':{'turn_hash':token(ack.get('request_id')),'committed':scalar(ack,'committed'),'metrics':metrics(ack)},
        'audio_frontend':metrics(obj(state,'audio_frontend')),'audio_output':metrics(obj(state,'audio_output')),
        'stream_diagnostics':metrics(obj(state,'stream_diagnostics')),'job_diagnostics':metrics(obj(job,'diagnostics')),
        'stream_metrics':metrics(obj(state,'stream')),
        'native_frames':scalar(display,'frames'),'avatar_visible':scalar(display,'visible'),
        'avatar_frame_scheduling':scalar(display,'frame_scheduling_active'),'target_fps':scalar(display,'target_fps'),
        'gui_fault_count':scalar(obj(state,'runtime_faults'),'count'),
        'memory':dict(metrics(obj(business,'memory')),error_present=bool(obj(business,'memory')['error']) if 'error' in obj(business,'memory') else None),
        'pan':{'automatic_following':scalar(pan,'automatic_following'),
            'state':enum(pan.get('state'),('READY','MOVING','CONNECTING','FAULT','UNAVAILABLE','CLOSED','STOPPING')),
            'pulse_us':scalar(pan,'pulse_us'),'target_us':scalar(pan,'target_us'),
            'readback':{key:scalar(obj(pan,'readback'),key) for key in ('flags','width_us','lease_left_ms','active','armed','referenced','bound','reason')}},
        'recording_error_present':bool(rec['error']) if 'error' in rec else None,
        'hf_error_present':bool(hf['error']) if 'error' in hf else None}

def project_camera(state):
    schedule = obj(state,'dpu_schedule');identity = obj(state,'identity')
    return {'event':'CAMERA','board_mono':time.monotonic(),
        'source':{key:scalar(state,key) for key in ('pid','capture_frames','detected_frames','capture_age_ms','observation_age_ms')},
        'identity_ready':scalar(identity,'ready'),
        'error_present':any(bool(state.get(key)) for key in ('camera_error','detector_error','preview_error')) or bool(identity.get('error')),
        'native':{key:scalar(schedule,key) for key in ('primary_calls','primary_period_overruns','owner_fenced','quiesced','native_critical')},
        'optional':{task:{key:scalar(obj(obj(schedule,'optional'),task),key) for key in ('calls','native_completed','native_failures','overruns','disabled','not_submitted')} for task in ('yunet','sface')},
        'feature_inference':metrics(obj(identity,'feature_inference'))}

def project_axis(path,root):
    candidate = Path(path);allowed = Path(root)
    assert candidate.is_file() and not candidate.is_symlink()
    assert allowed.resolve() in candidate.resolve().parents and '/runs/' in str(candidate)
    assert candidate.stat().st_size<=4194304
    value = json.loads(candidate.read_text());result = obj(value,'result')
    if not result:result = value
    names = ('elapsed_s','pulse_us','commands_accepted','segments','visual_center_completions',
        'max_control_turn_ms','active','fatal','target_center_ratio','left_target_center_ratio',
        'recenter_trigger_side','recenter_target_center_ratio','rearm_stability_ms',
        'rearm_stability_waits','rearm_stability_passes')
    data = {key:scalar(result,key) for key in names}
    for key in ('state','reason'):
        item = result.get(key)
        data[key] = item if type(item) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}',item) else None
    status = value.get('status')
    data['report_status'] = status if type(status) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}',status) else None
    for key in ('input_timing','reader_queue','decisions'):
        data[key] = metrics(obj(result,key))
    return {'event':'AXIS','board_mono':time.monotonic(),'metadata':data}

def emit(value):print(json.dumps(value,separators=(',',':')),flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration',type=float,default=180)
    parser.add_argument('--interval',type=float,default=.5)
    parser.add_argument('--camera-interval',type=float,default=2)
    args = parser.parse_args()
    assert 1<=args.duration<=300 and .25<=args.interval<=2 and 1<=args.camera_interval<=10
    expected = EXPECTED
    assert isinstance(expected,dict) and set(expected['owners'])>={'gui','camera'}
    guard(expected)
    value,wall = get(8783,'/api/state');baseline = project_gui(value)
    seen = {baseline['ack']['turn_hash']} if baseline['ack']['turn_hash'] else set()
    completed = set();begin = time.monotonic();last_guard = begin;next_camera = begin
    emit({'event':'BASELINE','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'boot_id':expected['boot_id'],'startup_sha256':expected['startup_sha256'],
        'baseline':baseline,'interval_seconds':args.interval,'duration_seconds':args.duration,
        'observer_pid':__import__('os').getpid(),'get_latency_ms':wall,'controls_available':False})
    try:
        while time.monotonic()-begin<args.duration:
            tick = time.monotonic()
            if tick-last_guard>=5:guard(expected);last_guard=tick
            try:
                value,wall = get(8783,'/api/state');sample = project_gui(value);sample['get_latency_ms']=wall;emit(sample)
                ack = sample['ack'];hashed = ack['turn_hash']
                if hashed and ack['committed'] is True and hashed==sample['turn_hash'] and hashed not in seen:
                    completed.add(hashed);seen.add(hashed)
                    emit({'event':'TURN_COMPLETED','board_mono':time.monotonic(),'ordinal':len(completed),'turn_hash':hashed})
            except (OSError,ValueError,AssertionError,http.client.HTTPException) as error:
                emit({'event':'GUI_UNAVAILABLE','board_mono':time.monotonic(),'error_type':type(error).__name__})
            if tick>=next_camera:
                next_camera = tick+args.camera_interval
                try:
                    value,wall = get(8790,'/health');sample=project_camera(value);sample['get_latency_ms']=wall;emit(sample)
                except (OSError,ValueError,AssertionError,http.client.HTTPException) as error:
                    emit({'event':'CAMERA_UNAVAILABLE','board_mono':time.monotonic(),'error_type':type(error).__name__})
                if expected.get('axis_report_path'):
                    try:emit(project_axis(expected['axis_report_path'],expected['axis_release_root']))
                    except (OSError,ValueError,AssertionError) as error:
                        emit({'event':'AXIS_REPORT_UNAVAILABLE','board_mono':time.monotonic(),'error_type':type(error).__name__})
            time.sleep(max(0,args.interval-(time.monotonic()-tick)))
        guard(expected)
    finally:
        emit({'event':'FINISHED','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'completed_new_turns':len(completed),'actual_duration_seconds':time.monotonic()-begin,
            'controls_sent':False,'database_opened':False,'raw_text_audio_images_or_identity_exported':False})

if __name__=='__main__':main()
