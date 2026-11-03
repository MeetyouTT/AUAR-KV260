"""Bounded numeric diagnostics; packet count is never advertised as source FPS."""
from collections import Counter,deque


class InputTiming:
    def __init__(self):
        self.counts=Counter();self.tracking=Counter();self.last_raw=self.last_used=None
        self.first_source=self.last_source=self.last_arrival=None
        self.windows={name:deque(maxlen=256) for name in
            ('source_age_ms','anchor_age_ms','source_interval_ms','delivery_interval_ms','publish_to_consume_ms')}
        self.recent=deque(maxlen=32)
    def observe(self,p,decision,now_ms):
        state=p.get('state','INVALID');self.counts['packets']+=1;self.counts['state_'+state]+=1
        tracking=p.get('face_tracking') or {};reason=tracking.get('reason','UNAVAILABLE')
        self.tracking[reason]+=1
        source=p.get('source_mono_ms');fid=p.get('source_frame_id')
        if state!='READY' or type(source) is not int or type(fid) is not int:return
        key=(p.get('service_epoch'),p.get('camera_epoch'),fid,source)
        if key==self.last_raw:self.counts['duplicate_ready_packets']+=1;return
        self.last_raw=key;self.counts['distinct_ready_sources']+=1
        anchor=p.get('face_detection_mono_ms');age=now_ms-source
        self.windows['source_age_ms'].append(age)
        if self.last_source is not None and source>self.last_source:
            self.windows['source_interval_ms'].append(source-self.last_source)
            self.windows['delivery_interval_ms'].append(now_ms-self.last_arrival)
        if self.first_source is None:self.first_source=source
        self.last_source,self.last_arrival=source,now_ms
        if type(anchor) is int:self.windows['anchor_age_ms'].append(now_ms-anchor)
        published=p.get('evaluated_mono_ms')
        if type(published) is int:self.windows['publish_to_consume_ms'].append(now_ms-published)
        if age>=250:self.counts['image_expired_on_receipt']+=1
        if type(anchor) is int and now_ms-anchor>=500:self.counts['anchor_expired_on_receipt']+=1
        control=decision.get('control') or {}
        if control.get('new_source') and key!=self.last_used:
            self.last_used=key;self.counts['admitted_distinct_sources']+=1
        self.recent.append(dict(source_frame_id=fid,source_mono_ms=source,received_mono_ms=now_ms,
            source_age_ms=age,anchor_age_ms=now_ms-anchor if type(anchor) is int else None,
            decision=decision.get('reason'),tracking_reason=reason,
            detector_snapshot_wait_ms=tracking.get('snapshot_wait_ms'),
            tracking_elapsed_ms=tracking.get('elapsed_ms')))
    def snapshot(self):
        summary={}
        for name,values in self.windows.items():
            if values:
                ordered=sorted(values);n=len(ordered)
                summary[name]=dict(window_count=n,p50=ordered[(n-1)//2],
                    p95=ordered[min(n-1,(95*n+99)//100-1)],maximum=ordered[-1])
        return dict(counts=dict(self.counts),tracking_packet_reasons=dict(self.tracking),
            recent_distinct_source_timing=list(self.recent)[-8:],distributions=summary,
            scope='distinct READY sources and admitted-source counts; rolling 256-source timing; not mechanical latency')
