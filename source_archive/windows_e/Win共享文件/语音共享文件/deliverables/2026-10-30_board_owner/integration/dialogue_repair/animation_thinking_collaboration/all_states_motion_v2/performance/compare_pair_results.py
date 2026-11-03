"""Summarize public, isolated preview process metrics, never production data."""
import argparse
import json
from pathlib import Path
from statistics import median

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    for name in ('a1','b1','b2','a2'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--output',type=Path,default=HERE/'PAIRED_COMPARISON.json')
    args=parser.parse_args();rows={};reports={}
    for label in ('A1','B1','B2','A2'):
        report=json.loads(getattr(args,label.lower()).read_text(encoding='utf-8'))
        if (report.get('status')!='NUMERIC_PASS_IMAGES_REQUIRE_REVIEW' or
            report.get('microphone_opened') is not False or report.get('audio_device_opened') is not False or
            report.get('camera_opened') is not False or report.get('network_or_model_calls')!=0):
            raise ValueError('Only complete no-device public preview reports are comparable')
        perf=report['paired_performance']
        if perf['run_label']!=label or perf['plan_seconds']!=24 or report['native_target_fps']!=16:
            raise ValueError('Mismatched run label/plan/target')
        expected='v17_baseline' if label.startswith('A') else 'motion_candidate'
        if perf['variant']!=expected:raise ValueError('Variant does not match ABBA order')
        reports[label]=report
        memory=perf['own_memory_samples']
        def peak(key):
            values=[sample[key] for sample in memory if key in sample]
            return max(values)/1024. if values else None
        rows[label]=dict(process_cpu_percent=perf['process_cpu_percent'],
            process_cpu_excluding_capture_percent=perf['process_cpu_excluding_capture_percent'],
            rss_peak_mib=peak('Rss_kib'),pss_peak_mib=peak('Pss_kib'),
            native_callback_fps=report['native_swap_callback_fps'],
            callback_p95_ms=perf['callback_interval_ms']['p95'],callback_p99_ms=perf['callback_interval_ms']['p99'],
            capture_cpu_ms=perf['capture_cpu_ms'],capture_wall_ms=perf['capture_wall_ms'],
            dropped_elapsed_seconds=perf['native_elapsed_dropped_seconds'])
    first=reports['A1']['paired_performance']
    if any(report['paired_performance']['plan']!=first['plan'] or
           report['paired_performance']['measurement_script_sha256']!=first['measurement_script_sha256']
           for report in reports.values()):raise ValueError('Different state plan or measurement script')
    for group in (('A1','A2'),('B1','B2')):
        if reports[group[0]]['overlay_pins']!=reports[group[1]]['overlay_pins']:
            raise ValueError('Source changed within a paired variant')
    summaries={}
    for name,group in (('baseline',('A1','A2')),('motion',('B1','B2'))):
        summaries[name]={key:median(rows[label][key] for label in group)
            if all(rows[label][key] is not None for label in group) else None for key in rows[group[0]]}
    delta={key:(summaries['motion'][key]-summaries['baseline'][key])
        if summaries['motion'][key] is not None and summaries['baseline'][key] is not None else None
        for key in summaries['baseline']}
    result=dict(schema='aura.all-state-motion-paired-comparison.v1',
        status='COMPLETE_REQUIRES_OWNER_RESOURCE_AND_VISUAL_REVIEW',order=['A1','B1','B2','A2'],
        runs=rows,median=summaries,delta_motion_minus_baseline=delta,
        process_cpu_unit='percentage points of one CPU; 100 means one full CPU',
        memory_unit='Own preview process MiB; not whole-board or complete GPU memory',
        callback_measurement='Native swap submissions; not physical scanout or business-load FPS',
        strict_16fps_acceptance_passed=False,natural_motion_visual_review_passed=False,
        native_target_fps=16,production_modified=False)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
