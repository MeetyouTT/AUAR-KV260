"""Bounded read-only capture of live dashboard telemetry during root probes."""
import datetime
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'aura/tools'))
from model_runtime_dashboard import Sampler


def main():
    sampler=Sampler();samples=[];end=time.monotonic()+16
    try:
        while time.monotonic()<end:
            at=time.monotonic();samples.append(sampler.sample())
            time.sleep(max(0,min(1.5,end-time.monotonic())-(time.monotonic()-at)))
    finally:sampler.close()
    output=HERE/'actual_live_phases.json'
    states={key:sorted({row['state'] for s in samples for row in s['tasks'] if row['id']==key})
            for key in ('llm','tts','host')}
    maximum={key:max((row['gpu_pct'] for s in samples for row in s['tasks']
                      if row['id']==key and row['gpu_pct'] is not None),default=None)
             for key in ('llm','tts','host')}
    value=dict(status='ACTUAL_READ_ONLY_LIVE_PHASES',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        samples=samples,observed_states=states,maximum_wddm_gpu_percent=maximum,
        model_requests_sent_by_monitor=False,board_connected_by_monitor=False)
    output.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(output=str(output),observed_states=states,maximum_gpu_percent=maximum),ensure_ascii=True))


if __name__=='__main__':main()
