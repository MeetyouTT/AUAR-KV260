"""Bounded phase performance records; no audio, text, images or model work."""
import json
from pathlib import Path
import queue
import threading


def stats(values):
    if not values:return None
    rows=sorted(values);n=len(rows)
    return dict(count=n,p50=rows[n//2],p95=rows[min(n-1,int(n*.95))],
                p99=rows[min(n-1,int(n*.99))],max=rows[-1])


class PerformanceRecorder:
    def __init__(self,path,*,period=5,max_bytes=2*1024*1024):
        self.path=Path(path);self.period=period;self.max_bytes=max_bytes
        self.queue=queue.Queue(maxsize=4);self.error='';self.dropped=0;self.written=0
        self.start=None;self.previous=None;self.groups={};self.last_sequence=None
        self.thread=threading.Thread(target=self.write,name='aura-render-perf-log',daemon=True)
        self.thread.start()

    def observe(self,phase,state,at,sequence,timings):
        key=(phase or 'UNKNOWN',state or 'UNKNOWN')
        if self.start is None:self.start=at
        if at-self.start>=self.period:
            self.flush(at)
        group=self.groups.setdefault(key,dict(frames=0,intervals=[],render=[],public=[],long=0))
        group['frames']+=1
        if self.previous and self.previous[1]==key:
            interval=(at-self.previous[0])*1000
            group['intervals'].append(interval)
            if interval>187.5:group['long']+=1
        group['render'].append(timings.get('total',0));group['public'].append(timings.get('public',0))
        self.previous=(at,key);self.last_sequence=sequence

    def flush(self,at):
        if self.start is None or not self.groups:return
        row=dict(kind='render_performance_v1',start_mono=self.start,end_mono=at,
                 sequence=self.last_sequence,target_fps=8,
                 measurement='actual_native_push_completion_not_physical_scan',
                 phases=[dict(phase=k[0],state=k[1],frames=v['frames'],
                              interval_ms=stats(v['intervals']),render_ms=stats(v['render']),
                              public_ms=stats(v['public']),over_187_5ms=v['long'])
                         for k,v in self.groups.items()])
        try:self.queue.put_nowait(row)
        except queue.Full:self.dropped+=1
        self.groups={};self.start=at

    def status(self):
        return dict(path=str(self.path),written=self.written,dropped=self.dropped,error=self.error,
                    period_seconds=self.period,max_total_bytes=self.max_bytes*2)

    def write(self):
        while True:
            row=self.queue.get()
            if row is None:return
            try:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                if self.path.exists() and self.path.stat().st_size>=self.max_bytes:
                    self.path.replace(self.path.with_name(self.path.name+'.1'))
                with self.path.open('a',encoding='utf-8') as out:
                    out.write(json.dumps(row,separators=(',',':'))+'\n')
                self.written+=1
            except Exception as exc:self.error=type(exc).__name__+': '+str(exc)

    def close(self,at):
        self.flush(at)
        try:self.queue.put(None,timeout=.25)
        except queue.Full:return
        self.thread.join(timeout=2)
