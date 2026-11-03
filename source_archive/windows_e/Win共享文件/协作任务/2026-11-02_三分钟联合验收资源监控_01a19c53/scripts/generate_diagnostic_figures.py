"""Plots from previously recorded short numeric diagnostics, no live device access."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager

ROOT=Path('/out');DATA=ROOT/'diagnostic_data';FIG=ROOT/'diagnostic_figures';FIG.mkdir(exist_ok=True)
font_manager.fontManager.addfont('/fonts/NotoSansCJK-Regular.ttc')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':10.5,'axes.unicode_minus':False,'svg.fonttype':'path'})
v=json.loads((DATA/'DIAGNOSTIC_INPUT.json').read_text());phases=v['phases'];rows=v['samples']
labels=['A：监听开启','B：监听暂停','C：恢复开启'];colors=['#1657B8','#268A45','#CC6E17'];images=[]
COMMON='既有短时诊断记录；非三分钟联合验收，视觉与右向转轴问题仍待处理。'

def canvas(title,subtitle,axes=1,height=6.5):
 fig,axs=plt.subplots(axes,1,figsize=(10.5,height),squeeze=False);ax=axs[:,0]
 fig.subplots_adjust(left=.12,right=.96,top=.84,bottom=.23,hspace=.38);fig.suptitle(title,fontsize=16.5,y=.97);ax[0].set_title(subtitle,fontsize=10.2,pad=13)
 for a in ax:a.grid(True,color='#DDDDDD',lw=.55);a.set_axisbelow(True)
 return fig,ax
def save(fig,name,notes):
 for y,s in zip([.125,.075,.025],notes):fig.text(.105,y,s,fontsize=9.3,color='#404040')
 for ext in ['.png','.svg']:fig.savefig(FIG/(name+ext),dpi=240,facecolor='white')
 images.append({'name':name,'kind':'short_diagnostic','notes':notes});plt.close(fig)

x=np.arange(3);rates=[p['software_preview_counter_rate_hz'] for p in phases]
fig,ax=canvas('短时诊断：监听开关与软件预览计数','同一版本、同一视觉页 | 每段24点、约6秒 | 原采集约250ms间隔')
bars=ax[0].bar(x,rates,color=colors,width=.56)
for bar,p in zip(bars,phases):
 rate=p['software_preview_counter_rate_hz'];ax[0].text(bar.get_x()+bar.get_width()/2,rate+.35,f"{rate:.2f} 次/s\nΔ={p['preview_counter_delta']}，{p['span_s']:.3f}s",ha='center',fontsize=10)
ax[0].set_xticks(x);ax[0].set_xticklabels(labels);ax[0].set_ylabel('软件预览计数变化速率（次/s）');ax[0].set_ylim(0,max(rates)*1.32)
save(fig,'D01_监听切换与软件预览计数',['速率=同一段首末displayed_frames计数差/对应单调时钟跨度；不是屏幕物理刷新率。',
 '此对照只反映这次条件下的同期变化；未直接测量像素重影或完整录音质量。',COMMON])

fig,ax=canvas('短时诊断：视觉结果时效曲线','72个原始数值快照 | 横轴保留段间切换间隔 | 未补造缺失数据',axes=2,height=8)
for p,label,color in zip(phases,labels,colors):
 group=[r for r in rows if r['phase']==p['phase']];t=[r['elapsed_s'] for r in group]
 for a,key in zip(ax,['raw_header_age_ms','face_source_age_ms']):
  y=[r[key] if type(r.get(key)) in (int,float) else np.nan for r in group];a.plot(t,y,lw=1.15,marker='.',ms=3,color=color,label=label);a.axvspan(t[0],t[-1],color=color,alpha=.055)
ax[0].set_ylabel('原始帧头龄期（ms）');ax[1].set_ylabel('人脸结果来源龄期（ms）');ax[1].set_xlabel('距首个诊断快照的时间（s）')
for a in ax:a.set_ylim(bottom=0);a.legend(loc='upper right',fontsize=8.5,ncol=3)
save(fig,'D02_视觉时效短时曲线',['两类龄期含义不同；快照龄期不能解释为完整视频显示延迟或纯DPU推理耗时。',
 '人脸来源龄期缺失时留空；仅绘制记录中的有效数字，未将缺失值按0ms处理。',COMMON])

fig,ax=canvas('短时诊断：进程CPU与主线程排队','与监听A—B—C段对应 | CPU单核为100% | 排队字段只对应主线程',axes=2,height=8)
for i,(role,label,color) in enumerate([('GUI','GTK界面与业务','#1657B8'),('camera','相机与视觉服务','#CC6E17')]):
 cpu=[p[role+'_cpu_percent_single_core_100'] for p in phases];wait=[p[role+'_main_rq_wait_percent_of_elapsed'] for p in phases]
 bars=ax[0].bar(x+(i-.5)*.30,cpu,.30,label=label,color=color);ax[1].bar(x+(i-.5)*.30,wait,.30,label=label,color=color)
 for bar,value in zip(bars,cpu):ax[0].text(bar.get_x()+bar.get_width()/2,value+2,f'{value:.1f}',ha='center',fontsize=9)
ax[0].set_ylabel('进程CPU（单核100%）');ax[1].set_ylabel('主线程排队等待/观察时长（%）')
for a in ax:a.set_xticks(x);a.set_xticklabels(labels);a.set_ylim(bottom=0);a.legend(fontsize=9,loc='upper right')
ax[0].set_ylim(0,210);ax[1].set_ylim(0,40)
save(fig,'D03_监听切换与CPU调度记录',['CPU由进程utime+stime差分计算，多线程进程可超过100%；不是整板归一占用率。',
 '排队比例=主线程schedstat等待时间差/观察时长；不代表该进程所有热线程的等待。',COMMON])

processes=sorted(v['process_snapshot']['processes'],key=lambda r:r['cpu_percent_single_core_100'],reverse=True)[:7]
fig,ax=canvas('短时诊断：连续聆听时的进程CPU快照',f"原始观察跨度 {v['process_snapshot']['duration_s']:.3f} 秒 | 进程元数据来源已保留")
fig.subplots_adjust(left=.245)
ys=np.arange(len(processes));values=[r['cpu_percent_single_core_100'] for r in processes]
bars=ax[0].barh(ys,values,color=['#8797A2' if r['category']=='this_metadata_probe' else '#1657B8' for r in processes])
ax[0].set_yticks(ys);ax[0].set_yticklabels([r['label'] for r in processes]);ax[0].invert_yaxis();ax[0].set_xlabel('进程CPU占用（单核100%）');ax[0].set_xlim(0,max(values)*1.23)
for bar,value in zip(bars,values):ax[0].text(value+1,bar.get_y()+bar.get_height()/2,f'{value:.2f}%',va='center',fontsize=9.5)
save(fig,'D04_连续聆听进程CPU短时快照',['进程统计包含其相关线程，不能拆作某一模型的精确占用；音频前端身份由命令指纹核对。',
 '测量探针自身也列入图中；这是单段CPU观测，不是长时间稳定性或完整资源验收。',COMMON])

manifest={'kind':'existing_short_diagnostic_not_formal_180s_acceptance','selected_numeric_input':'diagnostic_data/DIAGNOSTIC_INPUT.json','selected_numeric_input_sha256':hashlib.sha256((DATA/'DIAGNOSTIC_INPUT.json').read_bytes()).hexdigest(),'original_sources':v['original_sources'],'figures':images,'board_calls_for_plotting':0,'new_model_inference':False,'formal_180s_resource_status':'NOT_MEASURED','DPU_hardware_busy_status':'NOT_MEASURED'}
(ROOT/'DIAGNOSTIC_FIGURE_SOURCES.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'figures':len(images),'samples':len(rows),'software_preview_rates_hz':rates,'no_new_board_access':True},ensure_ascii=False))
