"""Compare the fixed public Small 3/2/2/3 pilot without transcript disclosure."""
import argparse
import json
from pathlib import Path
import statistics

ORDER=[3,2,2,3]
IDS=['P00','S01']


def summarize(rows):
    wall=[row['decode_wall_ms'] for row in rows]
    cpu=[row['decode_process_cpu_ms'] for row in rows]
    return dict(samples=len(rows),mean_decode_wall_ms=statistics.mean(wall),
        median_decode_wall_ms=statistics.median(wall),min_decode_wall_ms=min(wall),max_decode_wall_ms=max(wall),
        mean_decode_process_cpu_ms=statistics.mean(cpu),
        aggregate_real_time_factor=sum(wall)/(sum(row['audio_seconds'] for row in rows)*1000))


def compare(value):
    if value.get('status')!='PUBLIC_ABBA_COMPLETE' or value.get('order')!=ORDER or len(value.get('results',[]))!=4:
        raise ValueError('complete_fixed_abba_required')
    slots=value['results']
    if [slot['threads'] for slot in slots]!=ORDER:
        raise ValueError('abba_order_changed')
    for slot in slots:
        if slot.get('status')!='PUBLIC_ASR_SLOT_MEASURED' or [row['id'] for row in slot['measurements']]!=IDS:
            raise ValueError('same_fixed_measured_case_order_required')
        if [row['id'] for row in slot['warmups']]!=IDS:
            raise ValueError('two_explicit_warmups_required')
        for warm,measured in zip(slot['warmups'],slot['measurements']):
            if any(warm[key]!=measured[key] for key in ('wav_sha256','pcm_sha256','samples','rate','audio_seconds')):
                raise ValueError('warmup_complete_pcm_changed')
    by_case={}
    for case_id in IDS:
        rows=[next(row for row in slot['measurements'] if row['id']==case_id) for slot in slots]
        identity={(row['wav_sha256'],row['pcm_sha256'],row['samples'],row['rate'],row['audio_seconds']) for row in rows}
        if len(identity)!=1:
            raise ValueError('identical_complete_pcm_required')
        by_case[case_id]=dict(raw_hash_equal=len({row['result_sha256'] for row in rows})==1,
            normalized_hash_equal=len({row['normalized_sha256'] for row in rows})==1,
            threads3=summarize([rows[0],rows[3]]),threads2=summarize([rows[1],rows[2]]))
    groups={str(threads):[row for slot in slots if slot['threads']==threads for row in slot['measurements']]
            for threads in (2,3)}
    aggregates={key:summarize(rows) for key,rows in groups.items()}
    baseline=aggregates['3']['mean_decode_wall_ms'];candidate=aggregates['2']['mean_decode_wall_ms']
    return dict(status='DESCRIPTIVE_PUBLIC_ABBA_COMPARISON',by_case=by_case,aggregates=aggregates,
        observed_two_vs_three_wall_change_percent=(candidate/baseline-1)*100,
        all_normalized_results_equal=all(row['normalized_hash_equal'] for row in by_case.values()),
        warmup_to_measurement_normalized_equal=all(warm['normalized_sha256']==measured['normalized_sha256']
            for slot in slots for warm,measured in zip(slot['warmups'],slot['measurements'])),
        background_counter_changed=any(slot['background_counter_changed'] for slot in slots),
        constructor_and_warmup_excluded=True,timed_samples_per_thread_setting=4,
        actual_microphone_or_endpoint_latency_measured=False,physical_screen_fps_measured=False,
        causal_gain_claimed=False,independent_asr_process=True,
        production_asr_also_resident=True,reference_text_is_human_gold=False,
        slot_resources=[dict(threads=slot['threads'],constructor_total=slot['constructor_total'],
            process_cpu_seconds=slot['process_cpu_seconds'],slot_wall_seconds=slot['slot_wall_seconds'],
            peak_rss_kib=slot['process_peak_rss_kib'],measurement_before=slot['measurement_window_before'],
            measurement_after=slot['measurement_window_after']) for slot in slots])


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('result',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    value=compare(json.loads(args.result.read_text(encoding='utf-8-sig')))
    with args.output.open('x',encoding='utf8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(value))
