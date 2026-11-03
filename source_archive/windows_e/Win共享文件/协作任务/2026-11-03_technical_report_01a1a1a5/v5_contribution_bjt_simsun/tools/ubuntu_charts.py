from pathlib import Path
import json,csv,sys,os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parent
if ROOT.name=='tools': ROOT=ROOT.parent
rows=list(csv.DictReader((ROOT/'data/live_resources.csv').open()))
rtt=list(csv.DictReader((ROOT/'data/live_rtt.csv').open()))
t=[float(x['time_s']) for x in rows]
song_font=Path(os.environ.get('AUAR_SONG_FONT',r'C:\Windows\Fonts\simsun.ttc'))
if not song_font.is_file():raise FileNotFoundError('Set AUAR_SONG_FONT to the installed Song font file before drawing')
font_manager.fontManager.addfont(str(song_font))
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=str(song_font)).get_name(),'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2,'svg.fonttype':'none','axes.unicode_minus':False})
fig,axs=plt.subplots(2,1,figsize=(9.4,5.7),sharex=True,constrained_layout=True)
axs[0].plot(t,[float(x['cpu_pct']) for x in rows],color='#205c8a',lw=1.6,label='CPU utilization (all 4 cores = 100%)')
axs[0].axhline(79.4334349593,color='#be6334',ls='--',label='Weighted mean 79.43%')
axs[0].set_ylim(0,100);axs[0].set_ylabel('CPU utilization (%)');axs[0].legend(loc='lower right',fontsize=9)
axs[1].plot(t,[float(x['memory_used_gib']) for x in rows],color='#48785a',lw=1.6)
axs[1].set_ylim(0,2);axs[1].set_ylabel('Used memory (GiB)');axs[1].set_xlabel('Elapsed monotonic time (s)')
fig.suptitle('KV260 资源观察 | 北京时间 2026-11-03 21:52:23-21:53:24',fontsize=12)
for ext in ['png','svg']:fig.savefig(ROOT/'figures'/('live_resources.'+ext),dpi=220)
plt.close(fig)
v=[float(x['rtt_ms']) for x in rtt]
fig,ax=plt.subplots(figsize=(9.4,3.8),constrained_layout=True)
ax.plot(range(1,len(v)+1),v,'o-',color='#205c8a',ms=4,lw=1.4)
ax.axhline(1.7365,color='#be6334',ls='--',label='P95 = 1.7365 ms (linear interpolation)')
ax.set_xlabel('ICMP sequence');ax.set_ylabel('Round-trip latency (ms)');ax.set_ylim(0,2.4)
ax.set_title('KV260 to Windows 192.168.50.1 | 30/30 responses | 0% packet loss',fontsize=12)
ax.legend(loc='upper right',fontsize=9)
for ext in ['png','svg']:fig.savefig(ROOT/'figures'/('live_network_rtt.'+ext),dpi=220)
plt.close(fig)
fig,ax=plt.subplots(figsize=(9.4,3.7),constrained_layout=True)
ax.plot(t,[float(x['observation_age_ms']) for x in rows],color='#205c8a',label='Sampled primary observation age')
ax.set_xlabel('Elapsed monotonic time (s)');ax.set_ylabel('Observation age (ms)');ax.set_ylim(0,260)
ax.set_title('KV260 primary vision freshness | 1 Hz health snapshots',fontsize=12)
ax.legend(loc='upper right',fontsize=9)
for ext in ['png','svg']:fig.savefig(ROOT/'figures'/('live_vision_age.'+ext),dpi=220)
print(json.dumps({'tool':'matplotlib','version':matplotlib.__version__,'rows':len(rows),'rtt_samples':len(v),'synthetic_points':0,'artifacts':['live_resources','live_network_rtt','live_vision_age']},indent=2))
