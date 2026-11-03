"""Prepare report-ready results from closed local records. No device access."""
from pathlib import Path
from datetime import datetime,timezone
import json,csv,hashlib,statistics,shutil
ROOT=Path(__file__).resolve().parent.parent
MAIN=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/performance_measurement_20261102')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def loadlines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
rows=loadlines(ROOT/'data'/'board_numeric.jsonl');start=next(r for r in rows if r['event']=='start');end=next(r for r in rows if r['event']=='end');samples=[r for r in rows if r['event']=='sample']
assert len(samples)==90 and end['stopped_by_signal'] is False
main=json.loads((MAIN/'RESULTS.json').read_text(encoding='utf-8-sig'));assert main['llm_success']==main['tts_success']==5
sources=[{'path':str(ROOT/'data'/'board_numeric.jsonl'),'sha256':sha(ROOT/'data'/'board_numeric.jsonl')}]
for name in ['RESULTS.json','llm_cases.csv','tts_cases.csv','windows_gpu_timeseries.csv']:
 p=MAIN/name;target=ROOT/'data'/('main_'+name);shutil.copyfile(p,target);sources.append({'path':str(p),'local_copy':target.relative_to(ROOT).as_posix(),'sha256':sha(target)})
camera=[{'t':r['camera']['request_finished_monotonic_s'],'v':r['camera']['data']} for r in [start,*samples] if r.get('camera',{}).get('ok') is True]
a,b=camera[0],camera[-1];dt=b['t']-a['t']
def nested(v,path):
 for k in path:v=v[k]
 return v
dpu={}
for label,path in [('YOLOX',['dpu_schedule','primary_calls']),('YuNet',['dpu_schedule','optional','yunet','native_completed']),('SFace',['dpu_schedule','optional','sface','native_completed'])]:
 first=nested(a['v'],path);last=nested(b['v'],path);assert last>=first;dpu[label]={'counter_path':'/'.join(path),'first':first,'last':last,'delta':last-first,'span_s':dt,'rate_hz':(last-first)/dt}
stages={}
pa=a['v']['pipeline_metrics']['stages'];pb=b['v']['pipeline_metrics']['stages']
for name in pa.keys()&pb.keys():
 n=pb[name]['count']-pa[name]['count'];total=pb[name]['total_ms']-pa[name]['total_ms']
 if n>0 and total>=0:stages[name]={'delta_count':n,'delta_total_ms':total,'window_mean_ms':total/n}
cpu=[r['cpu']['cpu'] for r in samples];available=[r['memory_kib']['MemAvailable']/1024 for r in samples];used=[(r['memory_kib']['MemTotal']-r['memory_kib']['MemAvailable'])/1024 for r in samples]
resource_t0=start['monotonic_s'];resource_end=resource_t0+end['elapsed_s'];main_t0=main['board_start_monotonic_s'];main_end=main['board_end_monotonic_s']
s={'scope':'AXIS_STOPPED_PERFORMANCE_MEASUREMENT_NOT_FULL_JOINT_FUNCTION_ACCEPTANCE','created_host_utc':datetime.now(timezone.utc).isoformat(),'resource_samples':90,'resource_elapsed_s':end['elapsed_s'],'resource_start_monotonic_s':resource_t0,'resource_end_monotonic_s':resource_end,'resource_first_host_receipt_utc':start['host_received_utc'],'resource_last_host_receipt_utc':end['host_received_utc'],'main_start_monotonic_s':main_t0,'main_end_monotonic_s':main_end,'start_offset_s':resource_t0-main_t0,'overlap_s':max(0,min(resource_end,main_end)-max(resource_t0,main_t0)),'cpu_total_percent':{'mean':statistics.mean(cpu),'median':statistics.median(cpu),'max':max(cpu)},'memory_available_min_mib':min(available),'memory_used_max_mib':max(used),'dpu_counter_span_s':dt,'dpu':dpu,'pipeline_window_means':stages,'DPU_hardware_utilization':'NOT_PROVIDED','conditions':{'axis_stopped':True,'visual_services_continue':True,'main_gui_samples':main['gui_sample_count'],'main_listening_state_counts':main['listening_state_counts'],'main_mic_open_samples':main['microphone_open_samples'],'resource_and_main_windows_are_different':True,'visual_and_axis_issues_fixed':False},'sources':sources}
(ROOT/'data'/'PERFORMANCE_SUMMARY.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
table=[]
def add(item,result,basis):table.append({'指标':item,'实测结果':result,'统计口径与范围':basis})
for model in ['YOLOX','YuNet','SFace']:
 d=dpu[model];add(model+'业务计数频率',f"{d['rate_hz']:.3f} 次/s",f"计数增加{d['delta']} / {dt:.6f}s；"+('primary_calls' if model=='YOLOX' else 'native_completed')+'；非独立满载FPS')
for name,label in [('yolo.native_and_decode','YOLOX原生调用与解码阶段'),('yolo.path','YOLOX检测路径'),('yunet.native_lease','YuNet原生临界区'),('sface.native_lease','SFace原生临界区')]:
 v=stages[name];add(label+'均值',f"{v['window_mean_ms']:.3f} ms",f"窗口Δtotal_ms/Δcount，n={v['delta_count']}；不是纯DPU硬件内核时间")
add('整板CPU',f"采样均值 {statistics.mean(cpu):.2f}% 观测最大 {max(cpu):.2f}%",'90点，目标2秒间隔；全部在线核心合计100%')
add('系统可用内存最小值',f"{min(available):.3f} MiB（{min(available)/1024:.3f} GiB）",'Linux MemAvailable；不与进程RSS重复相加')
def voice_item(label,path,scale,unit,basis,digits=3):
 v=main
 for key in path:v=v[key]
 add(label,('中位数 %.*f %s 范围 %.*f–%.*f %s'%(digits,v['median']/scale,unit,digits,v['min']/scale,digits,v['max']/scale,unit)),basis)
voice_item('27B完整LLM RPC',['llm','rpc_ms'],1000,'s','5次有效暖态请求，含网络、准入与完整响应')
voice_item('27B首个JSON内容',['llm','first_content_ms'],1000,'s','服务首个非空JSON内容；不是声学首声')
voice_item('27B JSON解码速率',['llm','decode_tokens_per_second'],1,'token/s','eval_count/eval_duration；含完整JSON输出token')
voice_item('OmniVoice16完整TTS RPC',['tts_metrics','rpc_ms'],1000,'s','5次有效暖态请求，cache_hit均false；不含播放')
voice_item('OmniVoice16 RPC实时率',['tts_metrics','rpc_real_time_factor'],1,'', '完整RPC秒数/返回PCM秒数',4)
add('TTS返回音频时长',f"{main['tts_metrics']['audio_seconds']['min']:.2f}–{main['tts_metrics']['audio_seconds']['max']:.2f} s",'24kHz 单声道 s16le；本轮未播放')
add('Windows设备显存观测峰',f"{main['windows_gpu']['used_mib']['max']:.0f} MiB",'180个1秒设备快照，含桌面和其他进程；不是保证峰值')
add('Windows设备最少空闲显存',f"{main['windows_gpu']['free_mib']['min']:.0f} MiB",'同上；非模型专属分配')
add('DPU硬件利用率','未提供','只读驱动统计为空；不以CPU%或静态资源替代')
with (ROOT/'性能指标表.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
para=f"在原视觉服务持续运行、转轴停止条件下，板端180秒采样90点，整板CPU均值{statistics.mean(cpu):.2f}%。YOLOX、YuNet、SFace业务计数率分别为{dpu['YOLOX']['rate_hz']:.3f}、{dpu['YuNet']['rate_hz']:.3f}、{dpu['SFace']['rate_hz']:.3f}次/s。27B暖态JSON解码中位{main['llm']['decode_tokens_per_second']['median']:.2f} token/s，OmniVoice16 RPC实时率中位{main['tts_metrics']['rpc_real_time_factor']['median']:.4f}，均为5次有效请求。主观测段监听暂停；本次为性能测量。"
lines=['收尾性能测量结果 可并入技术设计报告','','一 作品概述 性能指标建议正文',para,'','二 性能验证与测量条件',f"本次在原运行版本、原模型与原参数下测量，转轴保持停止，原视觉服务持续运行。板卡采集90点、实际时长{end['elapsed_s']:.3f}s；主模型窗口时长{main['actual_seconds']:.3f}s。主窗口180个GUI快照全部为main/IDLE、PAUSED、mic=false、follow=false，运行故障计数0。不得按交接前的监听开启状态描述本次测量。",f"两侧使用同一boot的板端单调时钟，但起点不同：主窗口T0={main_t0:.9f}，板卡资源T0={resource_t0:.9f}，相差{s['start_offset_s']:.3f}s，按起止标记重叠{s['overlap_s']:.3f}s；不作同起止180s处理。资源最后一段不在主GUI观测覆盖内。板卡墙钟未用于对齐。",f"DPU计数采用最早与最后成功8790快照的差分，分母为{dt:.6f}s。YOLOX使用primary_calls，YuNet与SFace使用native_completed。阶段耗时使用同窗口累计total_ms与count的差分均值，未把进程累计均值或滚动256点P95当作完整窗口的分布。",'YOLOX native_and_decode含解码，YuNet和SFace native_lease为现有原生临界区墙钟耗时，均不表述为纯DPU硬件内核时延。硬件利用率接口本次未提供。','27B为原27.3B IQ4_XS模型，context=2048、num_predict=120、think=false、JSON输出；OmniVoice为原16步、24kHz单声道s16le配置。两模型预先驻留，生产前缀缓存保留。计划各6组公开输入，其中第4组因当前业务或后台请求活跃跳过，实际各5次均成功；不得写成6次或6/6。', '首内容为软件首个JSON内容时间，解码吞吐包含JSON token；TTS RPC实时率包含网络、准入和返回传输，全部TTS样本cache_hit=false。未进行ASR新录音、播放或声学首声测量，也不据旧GUI缓存补入这些指标。','','三 可编辑性能结果表']
for r in table:lines.append(r['指标']+'：'+r['实测结果']+'。'+r['统计口径与范围']+'。')
lines+=['','四 图表与结论使用范围','板卡资源图按其自身采样T0绘制；DPU及语音核心图由主性能测量窗口生成，引用同一批闭合原始数值。','视觉异常及右向转轴断续仍为待处理问题，本次STOP态性能结果不构成全功能、跟随稳定性或整机验收通过结论。','小样本指标采用中位数和实际范围描述；不据5次请求作精确尾延迟、准确率或长期稳定性保证。','','五 原始来源与校验']
for r in sources:lines.append(r['path']+'\nSHA256 '+r['sha256'])
(ROOT/'可插入技术报告的性能小节.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
resource_input={'summary':s,'samples':samples,'resource_start':start,'main_results':main}
(ROOT/'data'/'RESOURCE_FIGURE_INPUT.json').write_text(json.dumps(resource_input,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'report_text':str(ROOT/'可插入技术报告的性能小节.txt'),'table':str(ROOT/'性能指标表.csv'),'summary':str(ROOT/'data'/'PERFORMANCE_SUMMARY.json'),'overview_character_count':len(para),'DPU_rates':{k:v['rate_hz'] for k,v in dpu.items()},'resource_elapsed_s':end['elapsed_s'],'CPU_mean':statistics.mean(cpu)},ensure_ascii=False))
