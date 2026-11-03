"""Recompute figures from saved board observations and public SFace outputs.

Runs in the existing Ubuntu Vitis AI CPU image; no board or inference requests.
"""
from pathlib import Path
import csv, json, hashlib, time
from datetime import datetime, timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT=Path('/out');FIG=OUT/'性能曲线';DAT=OUT/'数据'
FIG.mkdir(exist_ok=True);DAT.mkdir(exist_ok=True)
font_manager.fontManager.addfont('/fonts/NotoSansCJK-Regular.ttc')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':11,'axes.unicode_minus':False,
 'svg.fonttype':'none','axes.edgecolor':'#222222','axes.linewidth':.8,'savefig.facecolor':'white'})
BLUE='#1657B8';GREEN='#268A45';ORANGE='#CC6E17';RED='#CC3333'
sources=[];figures=[]

def read(path,scope,original):
    p=Path(path);b=p.read_bytes()
    sources.append({'read_path':str(p),'original_path':original,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'scope':scope})
    return json.loads(b)

def csvfile(name,rows):
    with (DAT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def canvas(title,subtitle,xlabel,ylabel):
    fig,ax=plt.subplots(figsize=(10.5,6.7))
    fig.subplots_adjust(left=.105,right=.965,top=.84,bottom=.24)
    fig.suptitle(title,fontsize=17,y=.97)
    ax.set_title(subtitle,fontsize=10.5,pad=13)
    ax.set_xlabel(xlabel);ax.set_ylabel(ylabel)
    ax.grid(True,color='#D7D7D7',linewidth=.55,alpha=.8);ax.set_axisbelow(True)
    return fig,ax

def save(fig,name,notes,scope):
    for y,s in zip([.125,.075,.03],notes):fig.text(.105,y,s,fontsize=9.5,color='#404040')
    fig.savefig(FIG/(name+'.png'),dpi=240)
    fig.savefig(FIG/(name+'.svg'))
    figures.append({'name':name,'scope':scope,'notes':notes});plt.close(fig)

def main():
    started=time.monotonic()
    live=read('/evidence/yunet-live-validation-full.json','Historical 30-minute KV260 YuNet/YOLO live observation, not current release',
      'E:/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_live_baseline/evidence/yunet-live-validation-full.json')
    assert live['complete'] and live['passed'] and len(live['samples'])==360
    assert live['model_sha256']=='54d348bfeee01756a98bda4103c056a2d5e469a26ea887822da6edc28bdbbbee'
    rows=[]
    for i,s in enumerate(live['samples']):
        h=s['health'];d=h['dpu_schedule'];face=h['face_targets'];yu=d['optional']['yunet']
        row={'sample':i+1,'elapsed_s':s['elapsed_s'],'cpu_percent':s['cpu_pct_board'],
             'yolo_calls':d['primary_calls'],'yunet_calls':yu['calls'],'yunet_latest_full_path_ms':face['last_inference_ms'],
             'primary_observation_age_ms':h['observation_age_ms'],'face_source_age_ms':face['source_age_ms'],
             'yunet_skipped':yu['skipped'],'yunet_budget_exceeded':yu['budget_exceeded'],
             'kernel_warnings':s['kernel']['warnings'],'camera_error_present':int(bool(h['camera_error'])),
             'detector_error_present':int(bool(h['detector_error'])),'yolo_interval_hz':None,'yunet_interval_hz':None}
        if rows:
            prev=rows[-1];dt=row['elapsed_s']-prev['elapsed_s'];assert dt>0
            for model in ['yolo','yunet']:
                count=row[model+'_calls']-prev[model+'_calls'];assert count>=0
                row[model+'_interval_hz']=count/dt
        rows.append(row)
    csvfile('DPU视觉_360个原始采样点.csv',rows)
    t=np.array([r['elapsed_s']/60 for r in rows]);lat=np.array([r['yunet_latest_full_path_ms'] for r in rows])
    assert np.isfinite(lat).all()
    scope='历史KV260实板：约30分钟，每5秒健康快照；非本轮重跑或逐次完整推理日志'
    fig,ax=canvas('DPU YuNet检测耗时随运行时间变化','历史KV260实板记录 | 360个健康快照 | 未对曲线进行平滑','观察时间（min）','最近一次完整检测耗时（ms）')
    ax.plot(t,lat,color=BLUE,lw=1,marker='.',ms=2.8,label='快照记录的最近一次耗时')
    ax.axhline(lat.mean(),color=RED,ls='--',lw=1.2,label='快照均值 %.2f ms'%lat.mean())
    ax.set_xlim(0,30);ax.set_ylim(bottom=0);ax.legend(loc='best',fontsize=9)
    save(fig,'01_DPU_YuNet_30分钟耗时曲线',[
      '每个点来自约5秒一次健康采样，表示采样时最近一次完整检测路径耗时。',
      '包含预处理、DPU调用与后处理；360个快照不等于全部4259次YuNet调用的逐次计时。',
      '历史模型/版本；均值仅针对这些快照，不能作为当前最终版或纯DPU核耗时。'],scope)

    seconds=rows[-1]['elapsed_s']-rows[0]['elapsed_s']
    rates={model:(rows[-1][model+'_calls']-rows[0][model+'_calls'])/seconds for model in ['yolo','yunet']}
    fig,ax=canvas('DPU联合视觉处理频率随运行时间变化','历史KV260实板记录 | 359个相邻计数窗口 | 每窗约5秒','观察时间（min）','实际完成调用频率（Hz）')
    for model,color in [('yolo',BLUE),('yunet',GREEN)]:
        ax.plot(t[1:],[r[model+'_interval_hz'] for r in rows[1:]],lw=1,color=color,label=f'{model.upper()}：全窗 {rates[model]:.2f} Hz')
    ax.set_xlim(0,30);ax.set_ylim(bottom=0);ax.legend(loc='best')
    save(fig,'02_DPU_联合视觉处理频率曲线',[
      '每窗频率 = 相邻快照中已完成调用计数差 / 实际时间差；首个快照没有窗口频率。',
      'YOLO与YuNet是不同调度任务；该频率反映所记录业务，不能作为单模型满载最大FPS。',
      '保留启动阶段波动；本轮仅重算既有实板记录，未访问维护中的KV260。'],scope)

    fig,ax=canvas('视觉观测与人脸结果源龄随运行时间变化','历史KV260联合视觉记录 | 360个快照 | 两种时效定义分别呈现','观察时间（min）','结果/来源图像的年龄（ms）')
    ax.plot(t,[r['primary_observation_age_ms'] for r in rows],color=BLUE,lw=1,label='主视觉观测年龄')
    ax.plot(t,[r['face_source_age_ms'] for r in rows],color=ORANGE,lw=1,label='YuNet人脸结果源龄')
    ax.set_xlim(0,30);ax.set_ylim(bottom=0);ax.legend(loc='best')
    save(fig,'03_视觉_观测年龄与人脸源龄曲线',[
      '主视觉观测年龄与人脸结果源龄来自健康接口的两个独立字段，不能互相替代。',
      '图中保留全部高值，不把源龄等同模型执行时长，也不把它写成识别准确率。',
      '历史实板观察；当前发布版的场景、负载与时效需在正式后测中另行记录。'],scope)

    cpu=np.array([np.nan if r['cpu_percent'] is None else r['cpu_percent'] for r in rows])
    fig,ax=canvas('联合视觉运行期间的整板CPU占用曲线','历史KV260实板记录 | 359个有效CPU区间 | 四核合计100%','观察时间（min）','整板CPU占用（%）')
    ax.plot(t,cpu,color=BLUE,lw=1,label='相邻采样间CPU占用')
    ax.axhline(live['cpu_pct_board_observation'],color=RED,ls='--',lw=1.2,label='原记录整窗 %.2f%%'%live['cpu_pct_board_observation'])
    ax.set_xlim(0,30);ax.set_ylim(0,100);ax.legend(loc='best')
    save(fig,'04_系统_30分钟CPU曲线',[
      'CPU按/proc/stat区间差分；首个样本没有有效区间，保留缺失，不填0。',
      '四核总量归一到100%；DPU任务忙时、FPGA静态资源占比与该CPU指标含义不同。',
      '此图只对应所保存的历史业务版本，不用于宣称当前完整玩偶/LLM联合稳定性。'],scope)

    quality=read('/public_report/sface-evaluation-report.json','Public held-out SFace quality, host FP32 and INT8 simulation',
      'E:/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/evidence/sface-evaluation-report.json')
    arrays={}
    for name in ['test_pairs.npy','test_fp32.npy','test_int8_simulation.npy']:
        p=Path('/public')/name
        sources.append({'read_path':str(p),'original_path':'/home/ghmd/aura-dpu-vision-20261021/work/public-faces/'+name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'scope':'Saved public LFW outputs; not private enrollment data'})
        arrays[name]=np.load(p,allow_pickle=False)
    pairs=arrays['test_pairs.npy'];labels=pairs[:,2].astype(bool)
    assert pairs.shape==(1000,3) and labels.sum()==500 and labels[:500].all() and not labels[500:].any()
    results={};score_rows=[{'pair':i+1,'same_identity':int(labels[i])} for i in range(len(pairs))]
    for key,file in [('fp32','test_fp32.npy'),('int8_simulation','test_int8_simulation.npy')]:
        feat=arrays[file];norms=np.linalg.norm(feat,axis=1,keepdims=True)
        assert np.isfinite(feat).all() and (norms>1e-8).all()
        normalized=feat.astype(np.float64)/norms
        scores=(normalized[pairs[:,0]]*normalized[pairs[:,1]]).sum(axis=1)
        original=quality['models'][key]['held_out_at_train_selected_threshold'];threshold=original['threshold']
        accept=scores>=threshold;correct=accept==labels
        fa=int(accept[~labels].sum());fr=int((~accept[labels]).sum())
        assert fa==original['false_accepts'] and fr==original['false_rejects']
        assert abs(correct.mean()-original['accuracy'])<1e-12
        block=correct.reshape(10,100).mean(axis=1)*100
        cumulative=np.cumsum(correct)/np.arange(1,1001)*100
        thresholds=np.r_[np.inf,np.sort(np.unique(scores))[::-1],-np.inf]
        roc=[(float((scores[~labels]>=v).mean())*100,float((scores[labels]>=v).mean())*100) for v in thresholds]
        results[key]={'scores':scores,'correct':correct,'block':block,'cumulative':cumulative,'roc':roc,'threshold':threshold,'accuracy':float(correct.mean()),'false_accepts':fa,'false_rejects':fr}
        for i,row in enumerate(score_rows):row.update({key+'_cosine':float(scores[i]),key+'_correct':int(correct[i])})
    csvfile('SFace_1000对公开测试_逐对分数.csv',score_rows)
    csvfile('SFace_每100对及累计准确率.csv',[{'pairs_checked':(i+1)*100,'fp32_block_accuracy_percent':float(results['fp32']['block'][i]),'int8_block_accuracy_percent':float(results['int8_simulation']['block'][i]),'fp32_cumulative_accuracy_percent':float(results['fp32']['cumulative'][(i+1)*100-1]),'int8_cumulative_accuracy_percent':float(results['int8_simulation']['cumulative'][(i+1)*100-1])} for i in range(10)])
    qscope='公开LFW开发测试集1000对：主机FP32与INT8量化模拟输出；非1000对实板或现场身份验收'
    colors=[('fp32','FP32',BLUE,'o'),('int8_simulation','INT8模拟',GREEN,'s')]
    fig,ax=canvas('SFace验证准确率变化：每100对独立统计','固定训练集阈值 | 公开测试1000对 | 10个独立分组，未调整样本顺序','已检查的配对数量（对）','本组100对判断准确率（%）')
    for key,label,color,marker in colors:ax.plot(np.arange(100,1001,100),results[key]['block'],color=color,marker=marker,ms=4,lw=1,label=label)
    ax.axhline(98.8,color=RED,ls='--',lw=1.2,label='两者整体准确率 98.80%')
    ax.set_xlim(50,1050);ax.set_ylim(94,100.6);ax.legend(loc='best')
    save(fig,'05_SFace_每100对独立准确率曲线',[
      '前500对为同人正对，后500对为异人负对；分组波动受原始排列和样本构成影响。',
      '阈值来自独立训练集，重新计算后的误接收/误拒绝和整体准确率与历史报告一致。',
      'INT8为主机量化模拟；不用于宣称DPU现场准确率随运行时间提升或存在比赛总得分。'],qscope)

    fig,ax=canvas('SFace验证准确率变化：累计统计','同一1000对原始顺序 | 每个点累计至当前配对 | FP32与INT8模拟','累计已检查配对数（对）','累计判断准确率（%）')
    for key,label,color,marker in colors:ax.plot(np.arange(1,1001),results[key]['cumulative'],color=color,lw=1,label=f'{label}：最终98.80%')
    ax.axhline(98.8,color=RED,ls='--',lw=1.0,label='最终整体准确率')
    ax.set_xlim(1,1000);ax.set_ylim(min(94,float(min(r['cumulative'].min() for r in results.values()))-1),100.5);ax.legend(loc='best')
    save(fig,'06_SFace_累计准确率曲线',[
      '累计准确率 = 截至当前配对的正确判断数 / 已检查配对数；不等同每100对的独立准确率。',
      '前500正对、后500负对；样本构成改变会影响累计曲线形状，不能解释为模型在线学习。',
      '固定训练集阈值；主机FP32/INT8模拟公开评测，当前现场验收另测。'],qscope)

    fig,ax=canvas('SFace公开测试ROC曲线','500正对 + 500负对 | 同一1000对测试输出 | 阈值扫描仅用于作图','误接收率 FAR（%）','真接收率 TAR（%）')
    for key,label,color,marker in colors:
        roc=np.array(results[key]['roc']);ax.plot(roc[:,0],roc[:,1],color=color,lw=1.3,label=label)
        original=quality['models'][key]['held_out_at_train_selected_threshold']
        ax.scatter([original['false_accept_rate']*100],[original['true_accept_rate']*100],color=color,s=34,marker=marker,zorder=4)
    ax.set_xlim(-.4,10);ax.set_ylim(85,100.5);ax.legend(loc='lower right')
    save(fig,'07_SFace_低误接收区间ROC曲线',[
      '图示FAR 0%-10%的局部范围；散点为原训练集选定阈值在测试集上的工作点。',
      '不在测试集重新选择正式阈值；ROC为重算的公开输出统计，不是新增实板推理。',
      '负对仅500对，最小非零FAR分辨率为1/500=0.2%；不能据此宣称极低现场FAR。'],qscope)

    fig,ax=canvas('SFace阈值与误接收/误拒绝的关系','同一公开1000对测试集 | FP32/INT8模拟 | 用于解释阈值取舍','余弦相似度阈值','错误率（%）')
    thresholds=np.linspace(.15,.65,101)
    for key,label,color,_ in colors:
        scores=results[key]['scores'];far=[(scores[~labels]>=v).mean()*100 for v in thresholds];frr=[(scores[labels]<v).mean()*100 for v in thresholds]
        ax.plot(thresholds,far,color=color,ls='-',lw=1.2,label=label+' FAR')
        ax.plot(thresholds,frr,color=color,ls='--',lw=1.2,label=label+' FRR')
    ax.set_ylim(0,35);ax.legend(loc='upper center',ncol=2,fontsize=9)
    save(fig,'08_SFace_阈值与错误率曲线',[
      '实线为异人误接收率，虚线为同人误拒绝率；仅展示0%-35%错误率区间。',
      '正式报告使用独立训练集既定阈值：FP32 %.4f，INT8模拟 %.4f。'%(results['fp32']['threshold'],results['int8_simulation']['threshold']),
      '该曲线解释已保存公开输出，不改变当前现场配置，也不调整现役身份阈值。'],qscope)

    metrics={'board_observation':{'points':360,'duration_s':live['elapsed_observation_s'],'snapshot_latency_mean_ms':float(lat.mean()),'snapshot_latency_median_ms':float(np.median(lat)),'snapshot_latency_p95_ms':float(np.percentile(lat,95)),'snapshot_latency_max_ms':float(lat.max()),'counter_window_yolo_hz':rates['yolo'],'counter_window_yunet_hz':rates['yunet'],'cpu_original_whole_window_percent':live['cpu_pct_board_observation'],'yunet_budget_exceeded_final':rows[-1]['yunet_budget_exceeded'],'yunet_skipped_delta':rows[-1]['yunet_skipped']-rows[0]['yunet_skipped']},
      'sface':{k:{x:r[x] for x in ['threshold','accuracy','false_accepts','false_rejects']} for k,r in results.items()},
      'run':{'utc':datetime.now(timezone.utc).isoformat(),'environment':'Ubuntu existing Vitis AI 3.0 CPU container; matplotlib '+matplotlib.__version__,'seconds':time.monotonic()-started,'board_accessed':False,'new_model_inference':False,'figure_count':len(figures)}}
    (DAT/'计算结果.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'曲线来源与图注.json').write_text(json.dumps({'sources':sources,'figures':figures},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metrics,ensure_ascii=False))

if __name__=='__main__':main()
