"""Read saved numeric metadata only; rates are sparse-window completions."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'human_v17_intro_1.json'
ENUMS=frozenset(('IDLE','THINKING','SPEAKING','THINKING_FEEDBACK','TRANSCRIBING',
    'GENERATING','PLAYING','ANSWERED','READY','RECORDING','DISABLED','ERROR','EMPTY',
    'CANCELLED','PAUSED','WAITING_SPEECH','CHECKING_SPEECH','WAITING_AUDIO_IDLE',
    'CONVERSATION','PREPARING_SPEECH','CONFIRMING_SPEECH'))


def enum(value):return value if isinstance(value,str) and value in ENUMS else 'OTHER'


def describe(values):
    values=sorted(values)
    if not values:return dict(count=0)
    def q(p):return values[min(len(values)-1,int((len(values)-1)*p))]
    return dict(count=len(values),minimum=values[0],p50=q(.5),p95=q(.95),maximum=values[-1])


def main():
    raw=SOURCE.read_bytes();samples=json.loads(raw)['samples']
    rows=[]
    for sample in samples:
        native=sample['native'];components=sample['components']
        rows.append(dict(mono=sample['observed_mono'],startup=sample['startup_sha256'],
            boot=sample['board_boot_id'],frames=native['frames'],paint_at=native['paint_at'],
            phase=enum(sample['phase']),playing=bool(sample['playing']),visible=native.get('visible'),
            recording=enum(components.get('local_recording',{}).get('state')),
            transcription=enum(components.get('local_transcription',{}).get('state')),
            task=enum(components.get('board_processing',{}).get('task_state')),
            listening=enum(sample.get('listening',{}).get('state')),
            evaluate_ms=native['evaluate_ms'],submit_ms=native['submit_ms'],callback_ms=native['gtk_callback_ms'],
            paint_age_ms=max(0.,(sample['observed_mono']-native['paint_at'])*1000.),
            gui_faults=sample['runtime_faults']['count'],stale_frames=native.get('stale_frames'),
            dropped_seconds=native.get('elapsed_dropped_seconds'),
            queue_capacity=sample['safe_capture'].get('input_queue',{}).get('capacity_frames'),
            queue_peak=sample['safe_capture'].get('input_queue',{}).get('peak_frames'),
            audio_underrun=sample.get('audio_output',{}).get('turn_underrun_packets')))
    windows=[];groups=defaultdict(list)
    for before,after in zip(rows,rows[1:]):
        dt=after['mono']-before['mono'];df=after['frames']-before['frames']
        if before['startup']!=after['startup'] or before['boot']!=after['boot'] or dt<=0 or df<0:
            raise ValueError('Unmatched source/process clock window')
        stable=all(before[key]==after[key] for key in ('phase','playing','transcription','task','recording','listening'))
        label='/'.join(before[key] for key in ('phase','transcription','task','recording','listening')) if stable else 'TRANSITION'
        window=dict(start_mono=before['mono'],end_mono=after['mono'],seconds=dt,completed_frames=df,
            completion_rate=df/dt,label=label,stable_endpoints=stable,
            note='Endpoint states do not prove no intermediate state transition')
        windows.append(window);groups[label].append(window)
    grouped={name:dict(windows=len(values),seconds=sum(x['seconds'] for x in values),
        completed_frames=sum(x['completed_frames'] for x in values),
        weighted_completion_rate=sum(x['completed_frames'] for x in values)/sum(x['seconds'] for x in values),
        window_rates=describe([x['completion_rate'] for x in values])) for name,values in groups.items()}
    elapsed=rows[-1]['mono']-rows[0]['mono'];completed=rows[-1]['frames']-rows[0]['frames']
    result=dict(schema='aura.native-live-sparse-fps-audit.v1',source_file=str(SOURCE),
        source_sha256=hashlib.sha256(raw).hexdigest(),samples=len(rows),elapsed_seconds=elapsed,
        completed_frames=completed,weighted_completion_rate=completed/elapsed,
        visible_samples=sum(row['visible'] is True for row in rows),gui_faults_max=max(row['gui_faults'] for row in rows),
        groups=grouped,all_window_completion_rates=describe([x['completion_rate'] for x in windows]),
        sparse_latest_callback_samples={key:describe([row[key] for row in rows])
            for key in ('evaluate_ms','submit_ms','callback_ms','paint_age_ms')},
        queue_capacities=sorted({row['queue_capacity'] for row in rows if row['queue_capacity'] is not None}),
        actual_target=16,physical_scanout_measured=False,complete_per_frame_p95_available=False,
        interpretation='Actual business window renders substantially below configured16; exact scheduling/CPU cause still unconfirmed',
        limitations=['2-second sparse observations; window counts are completions, not screen scanout',
            'Stable endpoint labels can contain unseen intermediate transitions',
            'Latest callback samples are not all-frame latency quantiles',
            'No production CPU/GUI-stage trace in this saved source'],
        private_dialogue_or_pcm_read_or_exported=False,device_access=False)
    (HERE/'LIVE_FPS_ANALYSIS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    (HERE/'LIVE_FPS_WINDOWS.json').write_text(json.dumps(windows,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(rate=result['weighted_completion_rate'],elapsed=elapsed,frames=completed,groups=grouped)))


if __name__=='__main__':main()
