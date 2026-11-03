"""Package verified actual-run figures and numeric provenance, no historic substitutes."""
from pathlib import Path
import json,hashlib,zipfile

ROOT=Path(__file__).resolve().parent.parent

def main():
 data=ROOT/'data';fig=ROOT/'figures'
 s=json.loads((data/'RESOURCE_SUMMARY.json').read_text(encoding='utf-8'))
 source=json.loads((ROOT/'FIGURE_SOURCES.json').read_text(encoding='utf-8'))
 render=json.loads((ROOT/'RENDER_RECEIPT.json').read_text(encoding='utf-8'))
 assert render['exit_code']==0 and s['observer_completed'] is True
 assert all((fig/(r['name']+'.png')).is_file() for r in source['figures'])
 def metric(path,precision=2):
  value=s
  for k in path:value=value.get(k,{}) if isinstance(value,dict) else None
  return f'{value:.{precision}f}' if type(value) in (int,float) else '未取得'
 lines=[
  'AUAR·雪妃 三分钟联合验收资源图',
  '运行编号：'+s['run_id'],
  '本包仅使用该轮START_GATE之后的实测数据。历史30分钟记录及离线检查未混入。',
  '',
  '采样范围与口径',
  f"功能观察计划窗口180秒；资源原始采样{s['raw_samples']}点，图中对齐后{s['plotted_samples']}点。",
  f"相对功能观察起点的资源数据覆盖：{s['plotted_first_s']:.3f}–{s['plotted_last_s']:.3f}秒；实际覆盖跨度{s['plotted_span_s']:.3f}秒。",
  '板卡CLOCK_MONOTONIC用于曲线对齐；板卡系统日期异常，未据其墙钟确定采样日期，也未改时钟。',
  '每2秒采集资源；GUI和Windows模型活动引用主验收窗口的原始数值记录，采样粒度不同。',
  '',
  '可写入报告的本轮资源统计',
  '整板CPU：均值'+metric(['cpu_percent','mean'])+'%，P95 '+metric(['cpu_percent','p95'])+'%，最大'+metric(['cpu_percent','max'])+'%。',
  '系统已用内存：均值'+metric(['memory_used_gib','mean'])+' GiB，最大'+metric(['memory_used_gib','max'])+' GiB。',
  '系统可用内存：最低'+metric(['memory_available_gib','min'])+' GiB。',
  'CPU以全部在线核心合计100%为口径；P95为资源采样值的百分位数，不是全部推理的延迟百分位数。',
  ''
 ]
 for model,stats in s.get('DPU_model_counters',{}).items():
  hz=stats.get('whole_observed_hz')
  lines.append(f"{model}业务调用："+(f'{hz:.3f} Hz（计数首末差/实际观测跨度）。' if type(hz) in (int,float) else '计数不连续，见数据明细。'))
 lines.extend([
  'DPU调用频率反映三模型在本次业务中的调度，不是独立满载FPS，也不是硬件利用率。',
  '识别准确率、LLM稳态tokens/s和声学首声延迟须使用各自的独立测试；本轮资源曲线不替代这些测试。',
  '健康接口中的最近一次耗时只是周期快照，不能解释为每次推理的完整日志。',
  'GUI软件状态和Windows模型准入活动不等同GPU/DPU硬件kernel的执行时间线。',
  'ECAPA仍在ARM CPU；未额外启动DPU runner、模型请求、录音、运动或设备配置操作。',
  '本包不单独作全部功能验收通过的结论，功能完整播放ACK及现场反馈由主验收窗口记录。',
  '',
  '图表索引与图注'
 ])
 for item in sorted(source['figures'],key=lambda r:r['name']):
  lines.append(item['name']+'.png')
  lines.extend('  '+note for note in item.get('notes',[]))
 lines.extend(['','PNG可直接插入Word；SVG保留矢量信息。原始JSONL、数值CSV和来源SHA256随包保存。',
  '未取得的指标：'+', '.join(s.get('unmeasured',[])),
  '故障预检日志和Ubuntu离线验证文件保留在工作目录，未当作本轮性能证据打包。'])
 (ROOT/'图表索引与测量说明.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
 files=[fig/(r['name']+suffix) for r in source['figures'] for suffix in ['.png','.svg']]
 for name in ['acceptance_board_numeric.jsonl','main_functional_events.jsonl','main_windows_models.jsonl','used_START_GATE.json','used_handoff_metadata.json','RESOURCE_SUMMARY.json','资源采样汇总.csv','DPU任务频率.csv','本轮对话软件计时.csv','头像软件帧计数速率.csv','MAIN_DATA_COPY_PROVENANCE.json','MODEL_LAYOUT_EVIDENCE.json']:
  p=data/name
  if p.is_file():files.append(p)
 for name in ['FIGURE_SOURCES.json','RENDER_RECEIPT.json','图表索引与测量说明.txt']:
  files.append(ROOT/name)
 for name in ['board_monitor.py','watch_start_gate.py','generate_resource_figures.py']:
  files.append(ROOT/'scripts'/name)
 manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
 ledger=ROOT/'文件校验_SHA256.json';ledger.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');files.append(ledger)
 package=ROOT/'三分钟联合验收_资源曲线与原始数据.zip'
 with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(files):z.write(p,p.relative_to(ROOT).as_posix())
 with zipfile.ZipFile(package) as z:assert z.testzip() is None
 receipt={'package':str(package),'bytes':package.stat().st_size,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'files':len(files),'png_figures':len(source['figures']),'actual_measurement_figures':sum(r.get('kind')=='actual_measurement' for r in source['figures']),'logical_structure_figures':sum(r.get('kind')=='logical_structure' for r in source['figures']),'run_id':s['run_id'],'zip_crc_check':'PASS'}
 (ROOT/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
