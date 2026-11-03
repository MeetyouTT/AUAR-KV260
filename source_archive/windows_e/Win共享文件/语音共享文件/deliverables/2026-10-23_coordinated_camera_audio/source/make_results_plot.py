"""Export measured live-window results; this is not a same-input speedup plot."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('reports',type=Path);p.add_argument('baseline',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();data=json.loads(a.reports.read_text());base=json.loads(a.baseline.read_text())
a.output.mkdir(parents=True,exist_ok=True)
rows=[{'label':'Original 120s','yolo':base['yolo_hz'],'yunet':base['yunet_hz'],
       'cpu':base['cpu_window']['cpu_percent_of_board'],'passed':base['passed'],'window_seconds':base['observed_seconds']}]
for r in data['reports']:
    if r.get('observed_seconds') is None:continue
    nominal=int(r['scope'].split('_DUAL_MODEL_')[1].split('S_')[0])
    rows.append({'label':'Recovery '+str(nominal)+'s','yolo':r['observed_yolo_hz'],
        'yunet':r['observed_yunet_hz'],'cpu':r['cpu_window']['cpu_percent_of_board'],'passed':r['passed'],'window_seconds':r['observed_seconds']})
with (a.output/'measured-windows.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['label','window_seconds','yolo','yunet','cpu','passed']);writer.writeheader();writer.writerows(rows)
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,3,figsize=(13.2,3.9),gridspec_kw={'width_ratios':[1.15,1,1.55]})
xs=list(range(len(rows)));width=.34
for offset,key,color,label in [(-width/2,'yolo','#2563eb','YOLO'),(width/2,'yunet','#059669','YuNet')]:
    bars=axes[0].bar([x+offset for x in xs],[r[key] for r in rows],width,color=color,label=label)
    axes[0].bar_label(bars,fmt='%.2f',fontsize=8,padding=2)
axes[0].set_ylabel('Completed observations / second');axes[0].set_ylim(0,13);axes[0].legend(loc='upper left',ncol=2,frameon=False)
bars=axes[1].bar(xs,[r['cpu'] for r in rows],.6,color='#64748b');axes[1].bar_label(bars,fmt='%.2f',fontsize=8,padding=2)
axes[1].set_ylabel('Board CPU (%)');axes[1].set_ylim(0,100)
for axis in axes[:2]:
    axis.set_xticks(xs);axis.set_xticklabels([r['label'] for r in rows],rotation=32,ha='right');axis.grid(axis='y',alpha=.15);axis.set_axisbelow(True)
for r in data['reports']:
    if not r.get('samples'):continue
    samples=r['samples'];seconds=samples[-1]['elapsed_s']
    if seconds<500:continue
    axes[2].plot([s['elapsed_s'] for s in samples],[s['face_source_age_ms'] for s in samples],
        linewidth=.8,label=str(round(seconds))+'s, gap count='+str(r['freshness_final']['counters']['observed_gap_intervals']))
axes[2].axhline(1000,color='#dc2626',linestyle='--',linewidth=1)
axes[2].text(5,1030,'TTL = 1000 ms',fontsize=7,color='#dc2626')
axes[2].set_xlabel('Elapsed observation time (s)');axes[2].set_ylabel('YuNet latest-result source age (ms)')
axes[2].set_ylim(0,1400);axes[2].legend(loc='upper right',fontsize=7,frameon=False);axes[2].grid(alpha=.15)
fig.suptitle('KV260: coordinated camera/audio handoff and bounded failed-round recovery',fontsize=11)
fig.text(.02,.01,'Different live windows; no same-input speedup claim. Sparse ages cover observation windows; gap counters also include startup.',fontsize=8,color='#475569')
fig.tight_layout(rect=[0,.07,1,.94])
for ext in ('png','svg','pdf'):fig.savefig(a.output/('runtime-results.'+ext),dpi=220,facecolor='white')
print(json.dumps({'windows':len(rows),'outputs':['measured-windows.csv','runtime-results.png','runtime-results.svg','runtime-results.pdf']}))
