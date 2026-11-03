"""Analyze saved, numeric-only stage samples; never connects to a device."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


STAGES = ('commands','controller_read','settings','runtime_widgets',
          'business_widgets','presentation','business_public')
PHASES = frozenset(('IDLE','THINKING','THINKING_FEEDBACK','VOICE_PREPARING',
                   'VOICE_STARTING','SPEAKING','ACTION'))


def number(value):
    return value if type(value) in (int,float) and math.isfinite(value) and 0 <= value <= 9007199254740991 else None


def quantiles(values):
    values = sorted(value for value in values if value is not None)
    if not values:
        return dict(samples=0)
    def at(fraction):
        index = (len(values)-1)*fraction
        low, high = math.floor(index), math.ceil(index)
        return values[low]*(high-index)+values[high]*(index-low) if low != high else values[low]
    return dict(samples=len(values), min=min(values),p50=at(.5),p95=at(.95),max=max(values))


def analyze(source):
    payload = json.loads(source.read_text(encoding='utf-8'))
    rows = []
    for value in payload['samples']:
        native = value.get('native', {})
        native = native if isinstance(native, dict) else {}
        stages = value.get('ui_stage_timings_ms', {})
        stages = stages if isinstance(stages, dict) else {}
        pin = value.get('startup_sha256')
        rows.append(dict(observed_mono=number(value.get('observed_mono')),
            startup_sha256=pin if isinstance(pin,str) and re.fullmatch('[0-9a-f]{64}',pin) else None,
            frames=number(native.get('frames')),visible=native.get('visible') is True,
            phase=value.get('phase') if value.get('phase') in PHASES else 'UNKNOWN',
            ui_tick_ms=number(value.get('ui_tick_ms')),
            stages={key:number(stages.get(key)) for key in STAGES},
            gtk_callback_ms=number(native.get('gtk_callback_ms')),
            native_age_ms=number(native.get('age_ms'))))
    windows = []
    for before, after in zip(rows,rows[1:]):
        if (not before['startup_sha256'] or before['startup_sha256'] != after['startup_sha256']
                or not before['visible'] or not after['visible']
                or any(row[key] is None for row in (before,after) for key in ('observed_mono','frames'))):
            continue
        elapsed = after['observed_mono']-before['observed_mono']
        frames = after['frames']-before['frames']
        if elapsed > 0 and frames >= 0:
            windows.append(dict(seconds=elapsed,frames=frames,completion_rate=frames/elapsed))
    elapsed = sum(window['seconds'] for window in windows)
    frames = sum(window['frames'] for window in windows)
    longest = []
    for row in sorted((row for row in rows if row['ui_tick_ms'] is not None),
                      key=lambda row:row['ui_tick_ms'],reverse=True)[:5]:
        stages = {key:value for key,value in row['stages'].items() if value is not None}
        longest.append(dict(observed_mono=row['observed_mono'],phase=row['phase'],
            ui_tick_ms=row['ui_tick_ms'],stages_ms=stages,
            dominant_stage=max(stages,key=stages.get) if stages else None))
    return dict(schema='aura.ui-stage-numeric-analysis.v1',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        sample_count=len(rows),stage_sample_count=sum(any(value is not None for value in row['stages'].values()) for row in rows),
        sampled_latest_ui_tick_ms=quantiles([row['ui_tick_ms'] for row in rows]),
        sampled_latest_ui_stage_ms={key:quantiles([row['stages'][key] for row in rows]) for key in STAGES},
        sampled_latest_native_callback_ms=quantiles([row['gtk_callback_ms'] for row in rows]),
        sampled_latest_native_age_ms=quantiles([row['native_age_ms'] for row in rows]),
        visible_same_startup_windows=dict(count=len(windows),seconds=elapsed,completed_frames=frames,
            completion_rate=frames/elapsed if elapsed else None,
            sampled_window_rates=quantiles([window['completion_rate'] for window in windows])),
        longest_sampled_ui_ticks=longest,
        limitations=['Latest cached values are sampled, not a complete UI/native callback trace.',
                     'Completion count rate is not physical display scanout FPS.',
                     'Seven stage timers end before bridge.publish; publication cost is not included.',
                     'Long stage timing includes scheduling and lock waits; it does not alone prove CPU cost.'],
        device_access=False,raw_business_fields_exported=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = analyze(args.source)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(args.output),samples=result['sample_count'],
        stage_samples=result['stage_sample_count'],ui_tick_ms=result['sampled_latest_ui_tick_ms'],
        completion=result['visible_same_startup_windows'])))


if __name__ == '__main__':
    main()
