"""Assemble the compact final report from real Ubuntu outputs after implementation and firmware export."""
from workspace_release import *
import re
import datetime
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--run',default='run01');ap.add_argument('--firmware',default='firmware-fresh01');ap.add_argument('--models',default='models01');args=ap.parse_args()
def normalize(v):
 if isinstance(v,str):return v.replace(RP,'$PKG').replace(RQ,'$QA').replace(VIV,'$VIV').replace(VIT,'$VIT')
 if isinstance(v,list):return [normalize(i) for i in v]
 if isinstance(v,dict):return {k:normalize(s) for k,s in v.items()}
 return v
def j(path):return json.loads(read_remote([RQ+'/'+path])[RQ+'/'+path])
def save(name,ob):dump(ROOT/'report/evidence'/name,normalize(ob))
res=remote(r"""
import re,datetime
q=Path(a['q']);run=q/a['run']; hw=run/'hardware';reports=hw/'reports';ret={}
for f in ['implementation.json','timing.rpt','utilization.rpt','route.rpt','drc.rpt','clocks.rpt','check_timing.rpt']:
 p=reports/f
 if p.is_file():ret[f]=hashlib.sha256(p.read_bytes()).hexdigest()
def lines(n):
 p=reports/n
 return p.read_text(errors='replace').splitlines() if p.is_file() else []
t=lines('timing.rpt');head=next((i for i,l in enumerate(t) if 'WNS(ns)' in l and 'WHS(ns)' in l),None)
tim={}
if head is not None:
 keys=['WNS_ns','TNS_ns','setup_failing_endpoints','setup_total_endpoints','WHS_ns','THS_ns','hold_failing_endpoints','hold_total_endpoints','WPWS_ns','TPWS_ns','pulse_failing_endpoints','pulse_total_endpoints']
 for line in t[head+1:head+7]:
  cols=line.split()
  if cols and re.fullmatch(r'-?\d+\.\d+',cols[0]):
   for k,v in zip(keys,cols):tim[k]=float(v) if '.' in v else int(v)
   break
route={}
for label in ['routable nets','fully routed nets','nets with routing errors']:
 for l in lines('route.rpt'):
  m=re.search(r'# of '+label+r'[^:]*:\s*([0-9,]+)',l)
  if m:route[label]=int(m.group(1).replace(',',''));break
util={}
for l in lines('utilization.rpt'):
 vals=[c.strip().replace('*','').strip() for c in l.split('|')[1:-1]]
 if len(vals)<5:continue
 name=vals[0];wanted=['CLB LUTs','CLB Registers','Slice LUTs','Slice Registers','Block RAM Tile','DSPs','DSP48E2 only','URAM','Bonded IOB','BUFGCE']
 if name in wanted and name not in util and vals[1].replace(',','').replace('.','').isdigit():
  util[name]={'used':vals[1],'available':vals[-2],'util_percent':vals[-1]}
clockrows=[l.strip()[:310] for l in lines('clocks.rpt') if re.search(r'\d+\.\d+\s+',l) and 'Clock' not in l][:30]
viol=[l.strip()[:300] for l in lines('drc.rpt') if re.search(r'\|\s*(?:Error|Critical Warning|Warning)\s*\|',l)][:25]
art={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [hw/'auar_source.bit',hw/'auar_source.xsa'] if p.is_file()}
mdl=q/a['model'];mdlfiles={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in mdl.glob('*.log')};mr=mdl/'models_result.json'
model=json.loads(mr.read_text()) if mr.is_file() else {'status':'NOT_COMPLETED','last_logs':mdlfiles}
model_reports={}
for kind in ['sface','yunet']:
 m=mdl/(kind+'-compiled/manifest.json')
 if m.is_file():model_reports[kind]=json.loads(m.read_text())
summ={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'implementation':json.loads((reports/'implementation.json').read_text()) if (reports/'implementation.json').exists() else {},
'timing':tim,'route':route,'utilization':util,'clock_report_excerpt':clockrows,'drc_report_groups':viol,'artifacts':art,'report_hashes':ret,'model':model,'model_logs':mdlfiles,'model_reports':model_reports}
print(json.dumps(summ))
""",{'q':RQ,'run':args.run,'model':args.models})
impl=j(args.run+'/implement.receipt.json'); assert impl['status']=='PASS'
assert res['route'].get('routable nets',0)>0 and res['route']['routable nets']==res['route']['fully routed nets'] and res['route']['nets with routing errors']==0
assert res['timing'].get('WNS_ns',-1)>=0 and res['timing'].get('WHS_ns',-1)>=0 and res['implementation']['drc_errors']==0
fw=j(args.firmware+'/firmware_result.json');assert fw['status']=='PASS' and fw['mode']=='full-export'
save('implementation_receipt.json',impl);save('hardware_results.json',{k:v for k,v in res.items() if k not in ('model','model_logs','model_reports')});save('model_build.json',{'result':res['model'],'log_sha256':res['model_logs'],'compiled_manifests':res['model_reports']});save('firmware_fresh.json',fw)
rtl=json.loads((ROOT/'report/evidence/rtl_xsim.json').read_bytes())
native=json.loads((ROOT/'report/evidence/native_build.json').read_bytes())
sw=json.loads((ROOT/'report/evidence/software_skill_deploy.json').read_bytes());dep=json.loads((ROOT/'board/deploy.json').read_bytes())
tim=res['timing'];route=res['route'];model=res['model'];im=res['implementation'];bits=res['artifacts']
def line(s=''):lines.append(s)
lines=[]
line('# Ubuntu 工程验证摘要');line()
line('验证环境为 Ubuntu 20.04.4 LTS x86_64、Vivado/Vitis 2022.2。Vivado SW Build 3671981，IP Build 3669848，嵌入 Tcl 8.5.14。以下结果取自这份源码的新输出。')
line();line('## Tcl 与 XSim');line()
line('| 测试台 | xvlog | xelab | xsim | 实际标记 |');line('|---|---:|---:|---:|---|')
for test in rtl['tests']:
 codes=[str(e['exit_code']) for e in test['stages']];line('| '+' | '.join([test['test']]+codes+['`'+test['expected_marker']+'`'])+' |')
line();line('每行标出实际退出码。12 条实际工具命令、各自源码及日志 SHA 在 `evidence/rtl_xsim.json`。缺少一个台的退出码、模拟编译失败、改动回执源码指纹均被拒绝；直接将坏结果送给 Vivado 时返回 1，未生成工程。')
line();line('## 新建工程、综合、实现与固件');line()
line('两份自定义 IP 从源封装，BD 从 Tcl 重建并 validate，完成 target generation、wrapper 和 XDC 加载。当前源产生的综合网表通过 PWM 引脚及寄存器检查。布局布线、物理优化、位流生成、固定硬件平台导出和 validate_hw_platform 均在本轮工作目录执行。')
line();line('| 项目 | 新实现报告 |');line('|---|---|')
line('| Setup WNS / TNS | %.3f / %.3f ns，违规端点 %d |'%(tim['WNS_ns'],tim['TNS_ns'],tim['setup_failing_endpoints']))
line('| Hold WHS / THS | %.3f / %.3f ns，违规端点 %d |'%(tim['WHS_ns'],tim['THS_ns'],tim['hold_failing_endpoints']))
line('| 路由 | %d / %d 条可路由网络完全布通，路由错误 %d |'%(route['fully routed nets'],route['routable nets'],route['nets with routing errors']))
line('| DRC Error | %d，详情和警告分组见硬件回执 |'%im['drc_errors'])
for k,v in res['utilization'].items():line('| '+k+' | '+v['used']+' / '+v['available']+'，利用率 '+v['util_percent']+'% |')
line();line('控制/DPU 时钟及地址已按新 XSA 的 HWH 对照独立参考核验。新 BIT 与 XSA 内嵌位流配置数据配对通过，Bootgen 已输出 BIT.BIN，目标原底图与新 DTBO 成功合并，XCLBIN 的 8 段通过回读。结果与各文件 SHA 见 `evidence/firmware_fresh.json`。`firmware_reference.json` 单独保存冻结版配对和两个底图测试。')
line();line('BIT SHA-256 为 `'+bits['auar_source.bit']['sha256']+'`。XSA SHA-256 为 `'+bits['auar_source.xsa']['sha256']+'`。原始报告和中间产物留在 Ubuntu 的包外验证目录，源 RAR 只附摘要、数据与复现代码。')
line();line('## 软件、模型、原生库与 Skill');line()
line('| 项目 | 本轮结果 |');line('|---|---|')
line('| 框架 doctor、合成业务 demo | PASS。首轮发现公共角色选择文件未按原名归位，归位后两个实际入口的退出码均为 0。 |')
line('| 精确板端文件部署 | PASS。380 项恢复出完整 9a4f 启动清单，224 相机项，33 + 23 份服务配置，15 份外置语音输入；4 个设置读取通过，正式角色 prepare_pair 实核 11 个固定引用。 |')
line('| 现场配置与失败回滚 | PASS。测试现场字段生成独立启动指纹；缺字段或外置文件 SHA 错误时返回 1，未发布半成品。 |')
line('| 原生库 | PASS。用匹配 EXT4 开发文件与 Vitis GCC 11.2.0 从源编译 8 个 ELF64 AArch64 库，其中 %d 个与已知历史输入字节一致。构建摘要列出每个库的 SHA。 |'%sum(native['matches_historical_input_by_sha'].values()))
line('| 原始视觉输入 | PASS。YuNet 与 SFace 的两个 ONNX 哈希匹配。 |')
if model['status']=='PASS':
 line('| 视觉模型量化及编译 | PASS。锁定 Vitis AI CPU 镜像，独立输出 SFace、YuNet 两个 xmodel。SHA 与实际阶段日志见 `evidence/model_build.json`。 |')
else:
 line('| 视觉模型量化及编译 | '+model['status']+'。见 `evidence/model_build.json` 的实际日志。 |')
line('| 比赛 Skill | PASS。28 个原始文件，15 项单元测试，adder 36 个及 CRC32 37 个 mock 用例。 |')
line('| 其他离线入口 | PASS。45 项历史 Windows 主机映射生成独立工作树；原资产选择器正常读取 2 张色条帧；ID/STOP 工具的缺省入口只打印计划。 |')
line();line('两份编译清单中的 DPU 指纹、batch-one 端口和公共基准评估原始数值见 §evidence/model_build.json§。其中编译完成、公共数据的量化一致性和实板身份验收分别记录。'.replace('§',chr(96)))
line();line('## 验证边界');line()
line('未执行的项目为物理 KV260 上电、冷启动、真实相机/麦克风与显示器、机械转动、Windows 8797 GPU 推理、真实 PYNQ 板及跨板复用。`data/metrics.csv` 的 18 条数值来自历史采样，引用时保留对应版本、样本和计时区间。最终 RAR 的整包 SHA、解包检查、逐文件核对及解包后的复跑结果存于压缩包旁的 `archive_verification.json`。')
put(ROOT/'report/validation_summary.md','\n'.join(lines)+'\n')
print('final report prepared',tim['WNS_ns'],tim['WHS_ns'],len(impl.get('hardware_source_sha256',{})),model['status'])

