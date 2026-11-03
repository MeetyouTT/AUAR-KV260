from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
ROOT=Path('/out');v=json.loads((ROOT/'narrow_data'/'RESOURCE_FIGURE_INPUT.json').read_text());rows=v['samples'];s=v['summary'];t0=s['resource_start_monotonic_s']
font_manager.fontManager.addfont('/fonts/NotoSansCJK-Regular.ttc')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':10.5,'axes.unicode_minus':False,'svg.fonttype':'path'})
time=np.array([r['board_monotonic_s']-t0 for r in rows]);cpu=np.array([r['cpu']['cpu'] for r in rows]);cores=sorted(k for k in rows[0]['cpu'] if k!='cpu')
matrix=np.array([[r['cpu'][k] for r in rows] for k in cores]);available=np.array([r['memory_kib']['MemAvailable']/1048576 for r in rows]);total=np.array([r['memory_kib']['MemTotal']/1048576 for r in rows]);used=total-available
fig,ax=plt.subplots(3,1,figsize=(10.5,9),sharex=True,gridspec_kw={'height_ratios':[1.1,.75,1.05]});fig.subplots_adjust(left=.12,right=.87,top=.86,bottom=.20,hspace=.30)
fig.suptitle('收尾性能测量 板卡资源180秒实测',fontsize=17,y=.97)
ax[0].set_title('90个实际采样点 | 目标间隔2秒 | 各图按资源窗口自身T0绘制',fontsize=10.5,pad=13)
ax[0].plot(time,cpu,color='#1657B8',lw=1.2,label='整板CPU');ax[0].axhline(cpu.mean(),color='#C03737',ls='--',lw=1,label=f'采样均值 {cpu.mean():.2f}%');ax[0].set_ylim(0,100);ax[0].set_ylabel('整板CPU占用（%）');ax[0].legend(loc='best',fontsize=9)
mesh=ax[1].pcolormesh(np.r_[0,time],np.arange(len(cores)+1)-.5,matrix,cmap='YlOrRd',vmin=0,vmax=100,shading='flat');ax[1].set_yticks(range(len(cores)));ax[1].set_yticklabels(cores);ax[1].set_ylabel('各CPU核心');box=ax[1].get_position();cax=fig.add_axes([.888,box.y0,.015,box.height]);fig.colorbar(mesh,cax=cax,label='单核忙时（%）')
ax[2].plot(time,used,color='#1657B8',label='已用：总量 - MemAvailable',lw=1.2);ax[2].plot(time,available,color='#268A45',label='可用：MemAvailable',lw=1.2);ax[2].plot(time,total,color='#71828D',ls=':',label='Linux可见总量',lw=1);ax[2].set_ylim(0,float(total.max())*1.08);ax[2].set_ylabel('系统内存（GiB）');ax[2].set_xlabel('距资源采样实际起点的时间（s）');ax[2].legend(loc='center right',fontsize=9)
for a in [ax[0],ax[2]]:a.grid(True,color='#DDDDDD',lw=.55);a.set_axisbelow(True)
for a in ax:a.set_xlim(0,max(180,float(time[-1])))
notes=['CPU全部在线核心合计100%；热力图每核单独为100%。内存未与RSS或CMA重复相加。',f"资源与主模型窗口起点相差 {s['start_offset_s']:.3f}s，按单调时钟标记重叠 {s['overlap_s']:.3f}s。",'转轴停止；重叠时段主GUI记录为PAUSED、mic=false。此图不代表全功能验收通过。']
for y,n in zip([.125,.075,.025],notes):fig.text(.10,y,n,fontsize=9.2,color='#444444')
folder=ROOT/'narrow_figures';folder.mkdir(exist_ok=True)
for suffix in ['.png','.svg']:fig.savefig(folder/('03_KV260_resource_180s'+suffix),dpi=240,facecolor='white')
print(json.dumps({'figure':'03_KV260_resource_180s','samples':len(rows),'CPU_mean':float(cpu.mean()),'CPU_max':float(cpu.max()),'minimum_available_GiB':float(available.min()),'new_board_access':False}))
