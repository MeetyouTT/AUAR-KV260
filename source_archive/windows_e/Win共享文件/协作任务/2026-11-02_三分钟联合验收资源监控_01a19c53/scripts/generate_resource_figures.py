"""Render only actual gated acceptance records. No hardware access or inference."""
from pathlib import Path
from datetime import datetime,timezone
import json,csv,hashlib,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch

ROOT=Path('/out');DATA=ROOT/'data';FIG=ROOT/'figures'
FIG.mkdir(exist_ok=True)
font_manager.fontManager.addfont('/fonts/NotoSansCJK-Regular.ttc')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':10.5,'axes.unicode_minus':False,'svg.fonttype':'path','axes.linewidth':.8})
BLUE='#1657B8';GREEN='#268A45';ORANGE='#CC6E17';RED='#CC3333';GREY='#667784'
SOURCES=[];IMAGES=[]

def loadlines(name,optional=False):
 p=DATA/name
 if optional and not p.is_file():return []
 raw=p.read_bytes();SOURCES.append({'path':'data/'+name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 return [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]

def read_json(name,optional=False):
 p=DATA/name
 if optional and not p.is_file():return {}
 raw=p.read_bytes();SOURCES.append({'path':'data/'+name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 return json.loads(raw)

def field(obj,*keys):
 for k in keys:
  if not isinstance(obj,dict):return None
  obj=obj.get(k)
 return obj

def number(value):return float(value) if type(value) in (int,float) and math.isfinite(value) else np.nan
def nums(rows,*keys):return np.array([number(field(r,*keys)) for r in rows],dtype=float)
def summarize(values):
 a=np.asarray(values,dtype=float);a=a[np.isfinite(a)]
 return {'n':len(a),'mean':float(a.mean()),'median':float(np.median(a)),'p95':float(np.percentile(a,95)),'max':float(a.max()),'min':float(a.min())} if len(a) else {'n':0}

def canvas(title,subtitle,ylabel,axes=1,height=6.5):
 fig,axs=plt.subplots(axes,1,figsize=(10.5,height),sharex=axes>1,squeeze=False)
 ax=axs[:,0];fig.subplots_adjust(left=.105,right=.965,top=.84,bottom=.23,hspace=.38)
 fig.suptitle(title,fontsize=16.5,y=.97)
 ax[0].set_title(subtitle,fontsize=10.3,pad=13)
 for a in ax:a.grid(True,color='#D7D7D7',lw=.55);a.set_axisbelow(True)
 ax[-1].set_xlabel('距本轮功能观察开始的时间（s）')
 if axes==1:ax[0].set_ylabel(ylabel)
 return fig,ax

def save(fig,name,notes):
 for y,s in zip([.125,.075,.025],notes):fig.text(.105,y,s,fontsize=9.3,color='#404040')
 fig.savefig(FIG/(name+'.png'),dpi=240,facecolor='white')
 fig.savefig(FIG/(name+'.svg'),facecolor='white')
 IMAGES.append({'name':name,'notes':notes,'kind':'logical_structure' if name.startswith(('12_','13_')) else 'actual_measurement'});plt.close(fig)

def export_csv(name,rows):
 if not rows:return
 with (DATA/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def role(proc,owner,observer):
 pid=proc.get('pid');script=proc.get('script_basename') or '';comm=proc.get('comm') or ''
 if pid==observer:return '资源观察器'
 if pid==field(owner,'camera_owner','pid'):return '视觉与DPU服务'
 if pid==field(owner,'gtk_owner','pid'):return '界面与板端业务'
 if pid==field(owner,'gui_owner','pid'):return '界面监管进程'
 if 'frontend' in script:return '语音前端'
 if 'audio_worker' in script or 'audio_engine' in script:return '音频播放进程'
 if 'asr' in script:return 'ASR服务进程'
 if 'camera' in script:return '视觉与DPU服务'
 if 'avatar_gtk' in script:return '界面与板端业务'
 if comm in ['Xorg','X','Xwayland']:return '显示服务'
 return script or comm or ('PID '+str(pid))

def structure_figures():
 def box(ax,xy,size,color,title,body,fontsize=11):
  x,y=xy;w,h=size
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',facecolor=color,edgecolor='#8B9AAA',lw=1))
  ax.text(x+w/2,y+h-.035,title,ha='center',va='top',fontsize=12.5,fontweight='bold',color='#183751')
  ax.text(x+w/2,y+h/2-.025,body,ha='center',va='center',fontsize=fontsize,linespacing=1.65)
 def arrow(ax,a,b,label='',color=GREY):
  ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=15,lw=1.5,color=color))
  if label:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.018,label,ha='center',va='bottom',fontsize=9.5,color=color)
 read_json('MODEL_LAYOUT_EVIDENCE.json',True)
 fig,ax=plt.subplots(figsize=(12,7.8));fig.subplots_adjust(left=.025,right=.975,top=.89,bottom=.16)
 ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
 fig.suptitle('AUAR·雪妃 模型部署与资源测量范围',fontsize=18,y=.97)
 ax.add_patch(FancyBboxPatch((.025,.16),.64,.79,boxstyle='round,pad=0.01',facecolor='#F3F6FA',edgecolor=BLUE,lw=1.4))
 ax.text(.345,.91,'KV260板卡',ha='center',fontsize=15,color=BLUE,fontweight='bold')
 box(ax,(.045,.405),(.30,.43),'#DFEAF8','ARM CPU（PS）','Paraformer：语音识别\nECAPA：声纹\nByteTrack：跟踪算法\n采集、预后处理、GTK与播放',10.9)
 box(ax,(.37,.405),(.27,.43),'#E1F1E4','共享DPU（PL）','YOLOX-Nano：人体检测\nYuNet：人脸检测\nSFace：人脸特征\n三模型通过原调度共享DPU',10.8)
 box(ax,(.045,.205),(.595,.14),'#F4EAD8','板卡DDR / 其他PL逻辑','DDR由Linux、CPU与DPU缓冲共同使用；PL承担转轴PWM输出。',10)
 box(ax,(.735,.405),(.245,.43),'#ECE6F7','Windows模型主机','GPU加速\n27B IQ4_XS：文本生成\nOmniVoice16：语音合成\n原模型服务与队列',10.4)
 arrow(ax,(.665,.61),(.733,.61),'局域网')
 ax.text(.5,.045,'测量范围：整板/分核CPU、进程RSS、系统可用内存、视觉调用计数、接口时效和软件活动。',ha='center',fontsize=10.6,color='#334A5A')
 save(fig,'12_模型部署与资源测量范围',['结构依据项目既定部署与源码，不表示图中各模型在本轮持续运行或同时满载。',
  'ByteTrack单列为跟踪算法；ECAPA仍在ARM CPU。GTCRN是否启用以本轮配置和状态为准。',
  'CPU/RSS不能拆算成单个模型的精确占用；DPU调度活动不能替代硬件利用率。'])

 fig,ax=plt.subplots(figsize=(12,7.5));fig.subplots_adjust(left=.03,right=.97,top=.88,bottom=.18)
 ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
 fig.suptitle('语音交互至完整播放回执的逻辑流程',fontsize=18,y=.97)
 xs=[.025,.28,.535,.79];w=.185;h=.23
 labels=[('1  板端采集','麦克风输入\n录音与端点判断'),('2  音频前端','前端处理\nGTCRN启用时参与'),('3  识别与声纹','Paraformer语音识别\nECAPA声纹判定'),('4  上下文构建','会话与记忆上下文\n原业务规则')]
 for x,(title,body) in zip(xs,labels):box(ax,(x,.66),(w,h),'#DFEAF8',title,body,10.5)
 for i in range(3):arrow(ax,(xs[i]+w,.775),(xs[i+1],.775))
 labels2=[('8  匹配完整ACK','提交完整播放回执\n再恢复下一轮聆听'),('7  板端播放','流式音频播放\n口型/头像软件状态'),('6  Windows TTS','OmniVoice16\n音频流返回板端'),('5  Windows LLM','原27B IQ4_XS\n文本生成')]
 for x,(title,body) in zip(xs,labels2):box(ax,(x,.25),(w,h),'#E1F1E4' if x<.535 else '#ECE6F7',title,body,10.5)
 arrow(ax,(xs[3]+w/2,.655),(xs[3]+w/2,.485))
 for i in range(3,0,-1):arrow(ax,(xs[i],.365),(xs[i-1]+w,.365))
 arrow(ax,(xs[0]+w/2,.485),(xs[0]+w/2,.655))
 ax.text(.5,.095,'回执、录音和生成状态由软件采样验证；实物声音、口型与转轴效果由现场反馈补充。',ha='center',fontsize=10.7,color='#334A5A')
 save(fig,'13_语音交互与完整ACK逻辑流程',['本图为业务逻辑；识别、生成、合成与播放允许按原实现重叠，不表示严格串行耗时。',
  '图中的箭头不作时间比例；软件SPEAKING和完整ACK不是外部声学首声测量。',
  '资源采集不主动触发录音、推理或播放，实测状态时间线另见本轮曲线。'])

def main():
 records=loadlines('acceptance_board_numeric.jsonl')
 samples=[r for r in records if r.get('event')=='sample']
 start=next((r for r in records if r.get('event')=='start'),None)
 end=next((r for r in records if r.get('event')=='end'),None)
 if start is None or len(samples)<2:raise RuntimeError('No usable gated acceptance samples; refuse placeholder plots')
 structure_figures()
 functions=loadlines('main_functional_events.jsonl',True)
 windows=loadlines('main_windows_models.jsonl',True)
 owner=read_json('used_handoff_metadata.json')
 gate=read_json('used_START_GATE.json')
 baseline=next((r for r in functions if r.get('event')=='BASELINE'),None)
 t0=baseline.get('board_mono') if baseline else start['monotonic_s']
 all_samples=samples
 samples=[r for r in samples if 0<=r['board_monotonic_s']-t0<=180]
 if len(samples)<2:raise RuntimeError('Insufficient overlap with actual function window')
 t=np.array([r['board_monotonic_s']-t0 for r in samples]);duration=float(t[-1]-t[0])
 subtitle='本轮实际采样 | 目标资源间隔2秒 | 与功能观察按同一板卡单调时钟对齐'
 common='数据只对应本轮观察及实际负载；资源曲线不单独证明全部功能验收通过。'
 cpu=nums(samples,'cpu','cpu');total=nums(samples,'memory_kib','MemTotal')/1048576
 avail=nums(samples,'memory_kib','MemAvailable')/1048576;used=total-avail
 summary={'source_boot_id':start['boot_id'],'run_id':gate['run_id'],'resource_start_monotonic':start['monotonic_s'],
  'main_start_monotonic':t0,'raw_samples':len(all_samples),'plotted_samples':len(samples),'plotted_first_s':float(t[0]),'plotted_last_s':float(t[-1]),'plotted_span_s':duration,
  'observer_completed':end is not None,'observer_elapsed_s':end.get('elapsed_s') if end else None,
  'cpu_percent':summarize(cpu),'memory_used_gib':summarize(used),'memory_available_gib':summarize(avail),
  'observer_work_ms':summarize(nums(samples,'observer_work_ms')),'cpu_basis':'all online CPU cores together equal 100 percent',
  'clock_basis':'board wall UTC untrusted; plots use board CLOCK_MONOTONIC, host UTC receipts retained',
  'dpu_hardware_busy_percentage':'not inferred from CPU or FPGA static resources; raw read-only driver availability retained'}
 summary['observer_end_seen']=end is not None
 summary['observer_stopped_early']=end.get('stopped_by_signal') is True if end else None
 summary['camera_owner_change_samples']=sum(r.get('camera_owner_changed') is True for r in all_samples)
 summary['boot_change_samples']=sum(r.get('boot_changed') is True for r in all_samples)
 summary['sample_interval_s']=summarize(np.diff(t))
 summary['camera_health_ok_samples']=sum(field(r,'camera','ok') is True for r in samples)
 summary['camera_health_failed_samples']=sum(field(r,'camera','ok') is not True for r in samples)
 summary['camera_health_request_ms']=summarize(nums(samples,'camera','request_ms'))
 summary['camera_error_samples']=sum(field(r,'camera','data','camera_error_present') is True for r in samples)
 summary['detector_error_samples']=sum(field(r,'camera','data','detector_error_present') is True for r in samples)
 summary['identity_error_samples']=sum(field(r,'camera','data','identity_error_present') is True for r in samples)
 summary['raw_dpu_stat_paths']=sorted({k for r in samples for k in r.get('dpu_hw_statistics_readonly',{})})
 summary['temperature_sensor_interfaces']=sorted({k for r in samples for k in r.get('thermal',{})})
 summary['unmeasured']=['external acoustic first sound','board electric power','DDR bandwidth','GPU hardware busy percent','DPU hardware busy percent without a documented enabled counter']

 fig,ax=canvas('联合验收期间的整板CPU占用',subtitle,'整板CPU占用（%）')
 ax[0].plot(t,cpu,color=BLUE,lw=1.2,label='整板CPU')
 ax[0].axhline(np.nanmean(cpu),color=RED,ls='--',lw=1.1,label='采样均值 %.2f%%'%np.nanmean(cpu))
 ax[0].set_ylim(0,100);ax[0].set_xlim(0,180);ax[0].legend(loc='best')
 save(fig,'02_整板CPU曲线',['全部在线核心合计归一为100%；CPU忙时排除idle与iowait。',
  '曲线保留实际采样点；未补造缺失点，未用历史记录替代本轮数据。',common])

 cores=sorted(k for k in samples[0]['cpu'] if k!='cpu')
 matrix=np.array([nums(samples,'cpu',k) for k in cores])
 fig,ax=canvas('联合验收期间的各CPU核心占用',subtitle,'CPU核心')
 first_index=all_samples.index(samples[0]);previous_mono=all_samples[first_index-1]['board_monotonic_s'] if first_index else start['monotonic_s']
 edges=np.r_[max(0,previous_mono-t0),t]
 im=ax[0].pcolormesh(edges,np.arange(len(cores)+1)-.5,matrix,cmap='YlOrRd',vmin=0,vmax=100,shading='flat')
 ax[0].set_yticks(range(len(cores)));ax[0].set_yticklabels(cores);ax[0].set_xlim(0,180);ax[0].grid(False)
 fig.colorbar(im,ax=ax[0],label='每个核心忙时（%）',pad=.02)
 save(fig,'03_分核CPU热力图',['每行是实际CPU核心；色块为相邻读取间的平均忙时，宽度按实际时间间隔绘制。',
  '颜色用于显示负载分布；不能把各核心百分比相加当作整板百分比。',common])

 cma_total=nums(samples,'memory_kib','CmaTotal')/1024;cma_free=nums(samples,'memory_kib','CmaFree')/1024;cma_used=cma_total-cma_free
 has_cma=np.isfinite(cma_total).any() and np.nanmax(cma_total)>0
 swap_used=(nums(samples,'memory_kib','SwapTotal')-nums(samples,'memory_kib','SwapFree'))/1048576
 summary['swap_used_gib']=summarize(swap_used)
 summary['cma_pool_used_mib']=summarize(cma_used);summary['cma_pool_free_mib']=summarize(cma_free)
 fig,ax=canvas('联合验收期间的系统内存与CMA池' if has_cma else '联合验收期间的系统内存与余量',subtitle,'系统可见内存（GiB）',axes=2 if has_cma else 1,height=8 if has_cma else 6.5)
 ax[0].stackplot(t,used,avail,labels=['已用：MemTotal - MemAvailable','可用：MemAvailable'],colors=[BLUE,'#C9E2D1'],alpha=.86)
 ax[0].plot(t,total,color=GREY,lw=.8,label='系统可见总量')
 if np.isfinite(swap_used).any() and np.nanmax(swap_used)>0:ax[0].plot(t,swap_used,color=RED,ls='--',lw=1,label='已用交换区')
 ax[0].set_ylabel('系统可见内存（GiB）')
 ax[0].set_xlim(0,180);ax[0].set_ylim(0,max(total)*1.10);ax[0].legend(loc='best',fontsize=9)
 if has_cma:
  ax[1].stackplot(t,cma_used,cma_free,labels=['CMA池已用','CMA池空闲'],colors=[ORANGE,'#F3DDC5'],alpha=.86)
  ax[1].set_ylabel('CMA池（MiB）');ax[1].set_xlim(0,180);ax[1].set_ylim(0,np.nanmax(cma_total)*1.10);ax[1].legend(loc='best',fontsize=9)
 save(fig,'04_系统内存与可用余量',['已用口径包含内核对可回收内存的估计，不能解释为纯应用RSS。',
  'CMA池是内存的子集，含不同使用方；不再次相加，也不当作DPU独占内存。',common])

 roles={};memory_roles={}
 for i,r in enumerate(samples):
  for p in r.get('processes',[]):
   label=role(p,owner,start['pid'])
   roles.setdefault(label,np.zeros(len(samples)))[i]+=number(p.get('cpu_percent_board')) if p.get('cpu_percent_board') is not None else 0
   memory_roles.setdefault(label,np.zeros(len(samples)))[i]+=number(p.get('rss_kib'))/1024
 rank=sorted(roles,key=lambda k:np.nanmean(roles[k]),reverse=True)
 chosen=[k for k in rank if k not in ['资源观察器','sshd','ssh']][:6]
 fig,ax=canvas('主要进程组的CPU占用与RSS',subtitle,'',axes=2,height=8)
 for label in chosen:
  line=ax[0].plot(t,roles[label],lw=1,label=label)[0]
  ax[1].plot(t,memory_roles[label],lw=1,color=line.get_color(),label=label)
 ax[0].set_ylabel('占整板CPU（%）');ax[1].set_ylabel('进程RSS（MiB）');ax[0].legend(loc='best',fontsize=8,ncol=2)
 for a in ax:a.set_xlim(0,180);a.set_ylim(bottom=0)
 save(fig,'05_主要进程CPU与RSS',['按本轮PID角色或脚本名汇总；同一进程可能同时承担界面、业务和模型任务。',
  'RSS可能重复计入共享页；短命进程及采样间启动退出的进程不构成精确服务总量。',common])
 summary['process_cpu_percent_board']={k:summarize(v) for k,v in roles.items()}

 camera=[]
 for r in [start,*all_samples]:
  c=r.get('camera') or {}
  if c.get('ok') is not True:continue
  mono=c.get('request_finished_monotonic_s',r.get('board_monotonic_s',r.get('monotonic_s')))
  x=mono-t0
  if 0<=x<=180:camera.append({'t':x,'data':c.get('data') or {},'request_ms':c.get('request_ms')})
 models={'YOLOX':('dpu_schedule','primary_calls'),'YuNet':('dpu_schedule','optional','yunet','calls'),'SFace':('dpu_schedule','optional','sface','calls')}
 rates={};counter_summary={};ct=np.array([c['t'] for c in camera])
 for model,path in models.items():
  counts=nums(camera,'data',*path)
  if len(counts)<2 or not np.isfinite(counts).any():continue
  delta=np.diff(counts);dt=np.diff(ct);values=np.where((delta>=0)&(dt>0),delta/dt,np.nan)
  rates[model]=values
  valid=np.isfinite(counts)
  first,last=np.flatnonzero(valid)[[0,-1]]
  counter_summary[model]={'first_calls':float(counts[first]),'last_calls':float(counts[last]),'span_s':float(ct[last]-ct[first]),'counter_resets':int(np.sum(delta<0)),'interval_hz':summarize(values)}
  if counts[last]>=counts[first] and ct[last]>ct[first]:counter_summary[model]['whole_observed_hz']=float((counts[last]-counts[first])/(ct[last]-ct[first]))
 summary['DPU_model_counters']=counter_summary
 if rates:
  fig,ax=canvas('DPU三视觉任务实际调用频率','本轮健康计数差分 | 非单模型满载跑分 | 两秒级采样','实际调用频率（Hz）')
  for model,values in rates.items():ax[0].plot(ct[1:],values,lw=1.1,label=model)
  ax[0].set_xlim(0,180);ax[0].set_ylim(bottom=0);ax[0].legend(loc='best')
  save(fig,'06_DPU视觉任务调用频率',['频率 = 相邻有效健康读数的调用计数差 / 实际读取时间差；计数重置不当作负频率。',
   'SFace等任务按需触发；此图反映本次业务调度，不代表独立满载FPS或识别准确率。',common])

 if camera:
  primary_age=nums(camera,'data','observation_age_ms');face_age=nums(camera,'data','face_targets','source_age_ms')
  full_ms=nums(camera,'data','face_targets','last_inference_ms');primary_ms=nums(camera,'data','last_inference_ms')
  has_latency=np.isfinite(full_ms).any() or np.isfinite(primary_ms).any()
  fig,ax=canvas('视觉结果时效与最近检测路径耗时' if has_latency else '视觉结果时效','本轮8790健康快照 | 可见字段独立呈现 | 未平滑','',axes=2 if has_latency else 1,height=8 if has_latency else 6.5)
  if np.isfinite(primary_age).any():ax[0].plot(ct,primary_age,lw=1.1,color=BLUE,label='主视觉观测年龄')
  if np.isfinite(face_age).any():ax[0].plot(ct,face_age,lw=1.1,color=ORANGE,label='人脸结果源龄')
  if has_latency:
   if np.isfinite(full_ms).any():ax[1].plot(ct,full_ms,lw=1.1,color=GREEN,label='YuNet最近完整检测路径')
   if np.isfinite(primary_ms).any():ax[1].plot(ct,primary_ms,lw=1.1,color=BLUE,label='YOLOX主视觉最近检测路径')
   ax[1].set_ylabel('最近路径耗时（ms）')
  ax[0].set_ylabel('观测/源龄（ms）')
  for a in ax:
   a.set_xlim(0,180);a.set_ylim(bottom=0)
   if a.lines:a.legend(loc='best',fontsize=9)
  save(fig,'07_视觉时效与检测快照耗时',['结果源龄与检测执行耗时含义不同；健康快照不是全部推理的逐次执行日志。',
   '完整检测路径包含CPU预后处理；缺失的纯DPU核耗时不由完整耗时推算。',common])
  summary['primary_observation_age_ms']=summarize(primary_age);summary['face_source_age_ms']=summarize(face_age);summary['face_latest_full_path_ms']=summarize(full_ms);summary['primary_latest_inference_ms']=summarize(primary_ms)

 network=[]
 for r in samples:
  counters=r.get('network_counters') or {};network.append([sum(x.get('rx_bytes',0) for x in counters.values()),sum(x.get('tx_bytes',0) for x in counters.values())])
 network=np.array(network,dtype=float);network_rate=np.diff(network,axis=0)/np.diff(t)[:,None]/1024
 network_rate[network_rate<0]=np.nan
 fig,ax=canvas('联合验收期间的板卡网络流量',subtitle,'全部非回环网卡速率（KiB/s）')
 ax[0].plot(t[1:],network_rate[:,0],lw=1.1,color=BLUE,label='接收');ax[0].plot(t[1:],network_rate[:,1],lw=1.1,color=GREEN,label='发送')
 ax[0].set_xlim(0,180);ax[0].set_ylim(bottom=0);ax[0].legend(loc='best')
 save(fig,'08_板卡网络收发速率',['使用/proc/net/dev非回环网卡计数差分，包含正常业务和监测接口通信。',
  '总通信量不能拆作单个模型的传输耗时或网络带宽上限。',common])

 fsamples=[r for r in functions if r.get('event')=='SAMPLE' and type(r.get('board_mono')) in (int,float) and 0<=r['board_mono']-t0<=180]
 if fsamples or windows:
  fig,ax=canvas('联合验收的软件状态与模型请求活动','GUI由主验收窗口采集 | Windows模型服务由主窗口采集 | 非硬件执行时序','活动状态',axes=1,height=7.5)
  signals=[]
  if fsamples:
   ft=np.array([r['board_mono']-t0 for r in fsamples])
   signals.extend([('麦克风打开',ft,[r.get('microphone_open') for r in fsamples]),('录音状态',ft,[r.get('recording_state')=='RECORDING' if r.get('recording_state') is not None else None for r in fsamples]),('识别状态',ft,[r.get('transcription_state')=='TRANSCRIBING' if r.get('transcription_state') is not None else None for r in fsamples]),('对话任务待完成',ft,[r.get('job_pending') for r in fsamples]),('软件播放状态',ft,[r.get('playing') for r in fsamples])])
   signals.append(('自动跟随启用标志',ft,[field(r,'pan','automatic_following') for r in fsamples]))
  if windows:
   baseutc=datetime.fromisoformat(gate['start_not_before_utc'].replace('Z','+00:00'))
   offsets=[]
   for row in fsamples:
    try:offsets.append(datetime.fromisoformat(row['host_observed_utc'].replace('Z','+00:00')).timestamp()-row['board_mono'])
    except (KeyError,TypeError,ValueError):pass
   if offsets:
    baseutc=datetime.fromtimestamp(t0+float(np.median(offsets)),tz=timezone.utc)
    summary['windows_alignment']={'method':'median main-host receipt UTC minus same-record board monotonic; includes transport delay','anchor_count':len(offsets),'estimated_main_t0_host_utc':baseutc.isoformat(),'receipt_offset_spread_s':float(max(offsets)-min(offsets))}
   else:summary['windows_alignment']={'method':'planned host UTC gate; startup skew retained'}
   wt=np.array([(datetime.fromisoformat(r['host_utc'].replace('Z','+00:00'))-baseutc).total_seconds() for r in windows])
   signals.append(('Windows推理请求活动',wt,[bool(r['active']) if type(r.get('active')) in (bool,int,float) else None for r in windows]))
  for i,(label,x,values) in enumerate(signals):
   values=np.array([number(v) if type(v) is not bool else float(v) for v in values])
   ax[0].step(x,i+values*.6,where='post',lw=1.2,label=label)
  ax[0].set_yticks(np.arange(len(signals))+.3);ax[0].set_yticklabels([s[0] for s in signals]);ax[0].set_xlim(0,180);ax[0].set_ylabel('低位=false；高位=true')
  save(fig,'09_软件阶段与Windows请求活动',['各状态按实际字段绘制，未知点留空；软件状态不等同模型硬件执行起止。',
   'Windows以主机接收锚点估计对齐，板端用同boot单调时钟；包含通信与采样误差。',common])

 turns=[]
 for event in [r for r in functions if r.get('event')=='TURN_COMPLETED']:
  group=[r for r in fsamples if r.get('turn_hash')==event.get('turn_hash')]
  valid=[r for r in group if field(r,'ack','turn_hash')==event.get('turn_hash') and field(r,'ack','committed') is True and field(r,'latency','complete') is True and field(r,'latency','error_class')=='none']
  if not valid:continue
  row=valid[0];latency=row['latency'];p=latency.get('prepare') or {}
  result={'ordinal':event.get('ordinal'),'ack_observed_elapsed_s':event['board_mono']-t0}
  for key,value in {'asr_ms':latency.get('asr_ms'),'llm_rpc_ms':p.get('llm_rpc_ms'),'tts_rpc_ms':p.get('tts_rpc_ms'),'first_audio_queued_from_worker_ms':latency.get('first_audio_queued_ms'),'worker_total_ms':latency.get('worker_total_ms'),'llm_calls':p.get('llm_calls'),'tts_calls':p.get('tts_calls')}.items():
   if np.isfinite(number(value)):result[key]=value
  captures=[r.get('recording_metadata') for r in group if type(field(r,'recording_metadata','ended_mono_ms')) in (int,float)]
  if captures:
   ended=captures[0]['ended_mono_ms'];speaking=[r for r in group if r.get('phase')=='SPEAKING' and r['board_mono']*1000>=ended]
   if speaking:result['capture_complete_to_observed_speaking_ms']=speaking[0]['board_mono']*1000-ended
  turns.append(result)
 summary['new_completed_turns_with_attributed_latency']=turns
 if turns and any(any(k in r for k in ['asr_ms','llm_rpc_ms','tts_rpc_ms']) for r in turns):
  fig,ax=canvas('本轮已取得完整播放回执的对话软件计时','只统计本轮新ACK且计时已完成、无错误分类的轮次 | 缺失字段留空','',axes=2,height=8.4)
  x=np.arange(len(turns));width=.23
  for j,(key,label,color) in enumerate([('asr_ms','板端ASR调用',BLUE),('llm_rpc_ms','LLM完整RPC',ORANGE),('tts_rpc_ms','TTS完整RPC累计',GREEN)]):
   a=np.array([number(r.get(key))/1000 for r in turns]);bars=ax[0].bar(x+(j-1)*width,a,width,color=color,label=label)
   for bar,value in zip(bars,a):
    if np.isfinite(value):ax[0].text(bar.get_x()+bar.get_width()/2,value,f'{value:.2f}',ha='center',va='bottom',fontsize=8.5)
  for j,(key,label,color) in enumerate([('first_audio_queued_from_worker_ms','job worker开始→首音频事件入队',BLUE),('capture_complete_to_observed_speaking_ms','录音元数据结束→首次采样SPEAKING',ORANGE)]):
   a=np.array([number(r.get(key))/1000 for r in turns]);ax[1].bar(x+(j-.5)*.30,a,.30,color=color,label=label)
  for a in ax:a.set_ylabel('软件记录的耗时（s）');a.set_xticks(x);a.set_xticklabels(['第'+str(r['ordinal'])+'轮' for r in turns]);a.set_ylim(bottom=0);a.legend(fontsize=8.5,loc='upper right')
  ax[-1].set_xlabel('本轮新完整播放回执对应的轮次')
  save(fig,'14_本轮对话软件计时',['RPC含传输、排队与服务等待；各指标起点不同且存在重叠，不能相加成端到端首声。',
   'ASR从取得完整录音后计时；SPEAKING是约0.5秒间隔观察的软件状态，未声学测量。',
   '仅本轮已归属的少量对话；不作LLM稳态tokens/s、TTS满载或所有场景性能保证。'])
  fields=sorted({k for r in turns for k in r})
  export_csv('本轮对话软件计时.csv',[{k:r.get(k,'') for k in fields} for r in turns])

 frame_samples=[r for r in fsamples if np.isfinite(number(r.get('native_frames')))]
 frame_rates=[];frame_resets=0
 if len(frame_samples)>=2:
  previous=frame_samples[0]
  for row in frame_samples[1:]:
   dt=row['board_mono']-previous['board_mono']
   if dt<2:continue
   delta=row['native_frames']-previous['native_frames']
   if delta<0:frame_resets+=1
   frame_rates.append({'elapsed_s':row['board_mono']-t0,'interval_s':dt,'counter_delta':delta if delta>=0 else '', 'software_counter_rate_hz':delta/dt if delta>=0 else '', 'counter_after':row['native_frames']})
   previous=row
 if frame_rates:
  x=np.array([r['elapsed_s'] for r in frame_rates]);values=np.array([number(r['software_counter_rate_hz']) for r in frame_rates])
  fig,ax=canvas('头像界面帧计数变化速率（软件）','来源：主验收窗口avatar_display.frames | 按实际时间差分','软件帧计数变化速率（次/s）')
  ax[0].plot(x,values,color=BLUE,lw=1.1,label='约2秒跨度计数差分')
  ax[0].set_xlim(0,180);ax[0].set_ylim(bottom=0);ax[0].legend(loc='best')
  save(fig,'15_头像界面软件帧计数速率',['字段为软件头像显示计数；按实际时间差分，计数重置区间留空。',
   '计数速率不等同显示器物理刷新率，也不独立证明声音与口型同步。',common])
  summary['avatar_software_frame_counter']={'source':'avatar_display.frames','first':frame_samples[0]['native_frames'],'last':frame_samples[-1]['native_frames'],'counter_resets':frame_resets,'interval_rate_hz':summarize(values)}
  if not frame_resets:summary['avatar_software_frame_counter']['whole_observed_rate_hz']=(frame_samples[-1]['native_frames']-frame_samples[0]['native_frames'])/(frame_samples[-1]['board_mono']-frame_samples[0]['board_mono'])
  export_csv('头像软件帧计数速率.csv',frame_rates)

 thermal_keys=sorted({k for r in samples for k in (r.get('thermal') or {})})
 valid_thermal=[]
 for key in thermal_keys:
  a=nums(samples,'thermal',key,'celsius')
  if np.isfinite(a).any() and np.nanmax(a)>0:valid_thermal.append((key,a))
 if valid_thermal:
  fig,ax=canvas('联合验收期间的可得温度读数',subtitle,'接口温度（°C）')
  for key,a in valid_thermal:ax[0].plot(t,a,lw=1.1,label=key)
  ax[0].set_xlim(0,180);ax[0].legend(loc='best')
  save(fig,'10_板卡温度曲线',['数值来自实际可读thermal sysfs接口；不由CPU占用推算温度。',
   '传感器名称与原始字段保留在数据文件中；本图不单独证明无降频或长期热稳定性。',common])
 else:summary['temperature']='No readable nonzero sensor values; no temperature curve fabricated'

 frequency_keys=sorted({k for r in samples for k in (r.get('cpu_frequency_khz') or {})})
 freq=[]
 for key in frequency_keys:
  values=[]
  for r in samples:
   try:values.append(float(field(r,'cpu_frequency_khz',key))/1000)
   except (ValueError,TypeError):values.append(np.nan)
  a=np.array(values)
  if np.isfinite(a).any():freq.append((key,a))
 if freq:
  fig,ax=canvas('联合验收期间的CPU频率接口读数',subtitle,'CPU频率（MHz）')
  for key,a in freq:ax[0].step(t,a,where='post',lw=1,label=key)
  ax[0].set_xlim(0,180);ax[0].set_ylim(bottom=0);ax[0].legend(loc='best')
  save(fig,'11_CPU频率接口曲线',['读取scaling_cur_freq，多个核心可能共享同一cpufreq策略和频率。',
   '该接口表示内核频率状态；不等同逐周期测量，也不能单独证明无降频。',common])
  summary['cpu_frequency_mhz']={key:summarize(a) for key,a in freq}
 else:summary['cpu_frequency']='No readable cpufreq values; no frequency curve fabricated'

 fig,axs=plt.subplots(2,2,figsize=(12,7.7));fig.subplots_adjust(left=.08,right=.97,bottom=.14,top=.88,hspace=.38,wspace=.25)
 fig.suptitle('AUAR·雪妃 联合验收资源总览',fontsize=17)
 axs[0,0].plot(t,cpu,color=BLUE,lw=1);axs[0,0].set_title('整板CPU（%）');axs[0,0].set_ylim(0,100)
 axs[0,1].plot(t,used,color=BLUE,label='已用');axs[0,1].plot(t,avail,color=GREEN,label='可用');axs[0,1].set_title('系统内存（GiB）');axs[0,1].legend(fontsize=8)
 for model,values in rates.items():axs[1,0].plot(ct[1:],values,lw=1,label=model)
 axs[1,0].set_title('DPU任务调用频率（Hz）')
 if rates:axs[1,0].legend(fontsize=8)
 if camera:
  axs[1,1].plot(ct,nums(camera,'data','observation_age_ms'),lw=1,color=BLUE,label='主观测年龄');axs[1,1].set_title('主视觉观测年龄（ms）')
 for a in axs.ravel():a.grid(True,color='#DDDDDD',lw=.5);a.set_xlim(0,180);a.set_xlabel('时间（s）')
 fig.text(.08,.055,'本轮资源采样与功能观察对齐；DPU频率来自业务调用计数，不代表硬件忙时或满载FPS。',fontsize=9.5)
 fig.savefig(FIG/'01_联合验收资源总览.png',dpi=240,facecolor='white');fig.savefig(FIG/'01_联合验收资源总览.svg',facecolor='white');plt.close(fig)
 IMAGES.append({'name':'01_联合验收资源总览','notes':['Actual gated observation overview; no inferred DPU busy percentage.'],'kind':'actual_measurement'})

 export_csv('资源采样汇总.csv',[{'elapsed_s':float(t[i]),'cpu_total_percent':float(cpu[i]),'memory_used_gib':float(used[i]),'memory_available_gib':float(avail[i]),'observer_work_ms':samples[i]['observer_work_ms'],**{k+'_percent':float(matrix[j,i]) for j,k in enumerate(cores)}} for i in range(len(samples))])
 export_csv('DPU任务频率.csv',[{'elapsed_s':float(ct[i+1]),**{model+'_hz':float(a[i]) if np.isfinite(a[i]) else '' for model,a in rates.items()}} for i in range(max(0,len(ct)-1))])
 (DATA/'RESOURCE_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'FIGURE_SOURCES.json').write_text(json.dumps({'sources':SOURCES,'figures':IMAGES,'board_controls':0,'model_inference_triggered':False},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'figures':len(IMAGES),'resource_points':len(samples),'run_id':summary['run_id'],'cpu':summary['cpu_percent'],'memory_available_gib':summary['memory_available_gib']},ensure_ascii=False))

if __name__=='__main__':
 import sys
 if '--structure-only' in sys.argv:
  structure_figures()
  (ROOT/'STRUCTURE_SOURCES.json').write_text(json.dumps({'sources':SOURCES,'figures':IMAGES,'kind':'logical_structure_not_performance_measurement'},ensure_ascii=False,indent=2),encoding='utf-8')
  print(json.dumps({'structure_figures':len(IMAGES),'performance_samples_used':0,'board_accessed':False}))
 else:main()
