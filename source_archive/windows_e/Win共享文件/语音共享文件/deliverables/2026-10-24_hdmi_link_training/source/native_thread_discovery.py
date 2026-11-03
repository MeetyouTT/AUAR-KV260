"""Bounded optional C ABI probes identify threads, then remove both probes."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request

BOOT='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
LIBRARY=Path('/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/libaura_native_v2_candidate.so')
LIBRARY_SHA='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
FUNCTION_FILE_OFFSET=35536
SOURCE=Path(__file__).resolve()
TOKEN=hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16]
GROUP='aura_ident_'+TOKEN
TRACE=Path('/sys/kernel/tracing/instances')/GROUP
ROOT=Path('/home/root/aura-display-sequence-20261024/thread-discovery')/TOKEN


def append_definition(interface,text):
    # tracefs is non-seekable. Text-mode append may lseek during open and
    # fail before writing; use one raw append write without O_TRUNC instead.
    raw=text.encode();fd=os.open(str(interface),os.O_WRONLY|os.O_APPEND|os.O_CLOEXEC)
    try:assert os.write(fd,raw)==len(raw)
    finally:os.close(fd)


def event_rows(text):
    pattern=re.compile(r'-(\d+)\s+\[(\d+)\]\s+\S+\s+(\d+)\.(\d+):\s+(native_entry|native_exit):\s+(.*)$')
    result=[]
    for line in text.splitlines():
        match=pattern.search(line)
        if not match:continue
        tid,cpu,seconds,fraction,event,body=match.groups()
        item=dict(tid=int(tid),cpu=int(cpu),mono_ns=int(seconds)*10**9+int(fraction.ljust(9,'0')[:9]),event=event)
        runner=re.search(r'runner=(0x[0-9a-f]+|[0-9]+)',body)
        if runner:item['runner_id']=int(runner.group(1),0)
        result.append(item)
    return result


def calls(rows):
    pending={};result=[]
    for row in rows:
        if row['event']=='native_entry':
            pending[row['tid']]=row
        elif row['tid'] in pending:
            entry=pending.pop(row['tid'])
            if row['mono_ns']>=entry['mono_ns']:
                result.append(dict(tid=row['tid'],runner_id=entry.get('runner_id'),
                    enter_ns=entry['mono_ns'],return_ns=row['mono_ns']))
    return result


def identify(rows,reports):
    windows=calls(rows);matches={};ambiguous=set()
    for kind,report in reports:
        if not report.get('start_ns') or not report.get('after_unlock_ns'):continue
        found=[window for window in windows if window['enter_ns']<=report['start_ns']+2000
            and window['return_ns']>=report['after_unlock_ns']-2000]
        if len(found)!=1:continue
        value=dict(tid=found[0]['tid'],runner_id=found[0]['runner_id'])
        if kind in matches and matches[kind]!=value:ambiguous.add(kind)
        else:matches[kind]=value
    return {key:value for key,value in matches.items() if key not in ambiguous}


def main():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert hashlib.sha256(LIBRARY.read_bytes()).hexdigest()==LIBRARY_SHA
    assert not TRACE.exists()
    interface=Path('/sys/kernel/tracing/uprobe_events')
    assert GROUP not in interface.read_text()
    ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def camera():
        with opener.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
        return dict(observed_mono_ns=time.monotonic_ns(),pid=h['pid'],frames=h['detected_frames'],primary_overruns=h['dpu_schedule']['primary_period_overruns'],
            optional=h['dpu_schedule']['optional'],owner_fenced=h['dpu_schedule']['owner_fenced'])
    before=camera();assert before['pid']==1291 and not before['owner_fenced']
    tids=sorted(int(p.name) for p in Path('/proc/1291/task').iterdir())
    owner_filter=' || '.join('common_pid == '+str(tid) for tid in tids)
    definitions=[('p','native_entry','runner=%x1:u64'),('r','native_exit','ret=$retval:s32')]
    registered=[];created=False;reports=[]
    report=dict(scope='BOUNDED_C_ABI_THREAD_IDENTIFICATION_NOT_MODEL_BENCHMARK',boot=BOOT,
        model_instances_created=0,source_or_model_changes=0,probes_removed=False,trace_instance_removed=False)
    try:
        TRACE.mkdir();created=True
        (TRACE/'tracing_on').write_text('0');(TRACE/'buffer_size_kb').write_text('64')
        (TRACE/'trace_clock').write_text('mono')
        for typ,name,fetch in definitions:
            append_definition(interface,typ+':'+GROUP+'/'+name+' '+str(LIBRARY)+':'+hex(FUNCTION_FILE_OFFSET)+' '+fetch+'\n')
            registered.append(name)
            event=TRACE/'events'/GROUP/name
            (event/'filter').write_text(owner_filter);(event/'enable').write_text('1')
        started=time.monotonic();(TRACE/'tracing_on').write_text('1')
        time.sleep(3)
        for unused in range(5):
            h=camera();assert h['pid']==before['pid']
            for kind,job in h['optional'].items():reports.append((kind,job.get('last_native_report') or {}))
            time.sleep(.1)
        report['duration_seconds']=time.monotonic()-started
    finally:
        if created:
            (TRACE/'tracing_on').write_text('0')
            text=(TRACE/'trace').read_text();(ROOT/'trace.private.txt').write_text(text)
            rows=event_rows(text);report['numeric_events']=rows
            report['identified_threads']=identify(rows,reports)
            for name in registered:(TRACE/'events'/GROUP/name/'enable').write_text('0')
            TRACE.rmdir();report['trace_instance_removed']=not TRACE.exists()
        for name in reversed(registered):
            append_definition(interface,'-:'+GROUP+'/'+name+'\n')
        report['probes_removed']=GROUP not in interface.read_text()
        after=camera();report['same_camera_pid']=before['pid']==after['pid']
        report['new_primary_overruns']=after['primary_overruns']-before['primary_overruns']
        report['new_optional_overruns']={kind:after['optional'][kind]['overruns']-job['overruns'] for kind,job in before['optional'].items()}
        report['counter_window_seconds']=(after['observed_mono_ns']-before['observed_mono_ns'])/1e9
        report['yolo_hz_counter_window']=(after['frames']-before['frames'])/report['counter_window_seconds']
        report['passed']=bool(report.get('identified_threads',{}).get('yunet') and report['probes_removed']
            and report['trace_instance_removed'] and report['same_camera_pid']
            and report['new_primary_overruns']==0 and not any(report['new_optional_overruns'].values()))
        (ROOT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
