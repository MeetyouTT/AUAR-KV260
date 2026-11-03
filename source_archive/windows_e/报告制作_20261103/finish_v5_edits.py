from pathlib import Path
from docx import Document
from datetime import datetime
import hashlib,json,sys
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5\v5_contribution_bjt_simsun')
before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'qa').glob('page-*.png')}
(R/'qa/reviewed_pages_before_final_time_check.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
changes={'10月23日窄版':'联合窄版 E01','10月28日宽版':'联合宽版 E02','历史 10 月 31 日另一个 30.004 s 窗口中':'历史北京时间 2026 年 10 月 31 日另一个 30.004 s 窗口中'}
p=R/'report/technical_report.md';t=p.read_text(encoding='utf-8')
for a,b in changes.items():
 if a in t:
  assert t.count(a)==1,(a,t.count(a))
  t=t.replace(a,b)
 else:assert t.count(b)==1,(b,t.count(b))
p.write_text(t,encoding='utf-8')
p=R/'evidence/timezone_display.json';v=json.loads(p.read_text(encoding='utf-8'))
v['historical_resource_observation']={'host_started_beijing':'2026-10-31T19:24:52.244001+08:00','host_finished_beijing':'2026-10-31T19:25:31.930541+08:00','source_start_utc':'2026-10-31T11:24:52.244001+00:00','source_end_utc':'2026-10-31T11:25:31.930541+00:00','sampled_monotonic_duration_s':30.004396511001687,'note':'Host SSH observation interval includes overhead and differs from sampled monotonic duration'}
v['historical_implementation_reports']='Table headers identify E01/E02 artifacts; unzoned native report wall clocks are retained only in original evidence, not converted by guessing a timezone.'
p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
p=R/'qa/editorial_changes.json';v=json.loads(p.read_text(encoding='utf-8'));v['final_calendar_check']={'historical_resource_day':'2026-10-31 Asia/Shanghai, confirmed from UTC source','implementation_table':'Identified by E01/E02 artifacts; original directory dates are version labels'};p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'markdown_updated':True,'word':'Rebuild from updated source using tools/build_word.py'},ensure_ascii=False))
