"""Ship the currently verified source while long-running hardware implementation continues."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
home=Path.home();base=Path(__file__).resolve().parent.parent;q=base/'verification';src=base/'auar_xuefei';out=q/'reviewable-source-01';out.mkdir(exist_ok=False)
tree=out/'auar_xuefei';shutil.copytree(str(src),str(tree))
osenv=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for v in iter(lambda:f.read(1048576),b''):h.update(v)
 return h.hexdigest()
def inv(root):
 return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def run(n,cmd,cwd):
 log=out/(n+'.log')
 with log.open('xb') as f:r=subprocess.run([str(c) for c in cmd],cwd=str(cwd),env=osenv,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(n+' exit '+str(r.returncode))
 return {'name':n,'exit_code':r.returncode,'log_sha256':sha(log)}
mod=read(q/'models01/models_result.json');assert mod['status']=='PASS';write(tree/'report/evidence/model_build.json',{'result':mod})
rr=read(q/'run01/rtl/result.json');assert rr['status']=='PASS';sw=read(tree/'report/evidence/software_skill_deploy.json');assert sw['board']['exact_9a4f'];h=q/'run01/hardware';assert (h/'source_placed.dcp').is_file()
rows=['# Ubuntu 源码及 Tcl 阶段验证','',
'本归档冻结在完成综合、布局和布局后优化，正在布线的阶段。最终 setup/hold、route/DRC、同轮 BIT/XSA 与固件导出尚无回执。完整实现和验包通过后另行交付最终版。','',
'| 项目 | 本阶段实际结果 |','|---|---|']
for test in rr['tests']:
 rows.append('| '+test['test']+' | xvlog / xelab / xsim 退出码分别为 '+', '.join(str(s['exit_code']) for s in test['stages'])+'，'+test['expected_marker']+' |')
rows.extend(['| Vivado 2022.2 Tcl | 从空目录重建 IP、BD、约束和 wrapper。四台复验和错误回执拒绝测试均通过。 |','| 综合和布局 | 已完成。由本轮源码生成的 synth、placed 检查点均位于包外。 |','| 模型 | YuNet 与 SFace 由固定 ONNX、数据和工具镜像量化编译，两个新 xmodel 的哈希在 evidence/model_build.json。 |','| 原生库和业务 | 8 个 AArch64 ELF 从源编译；380 个原组件精确还原 9a4f，224 项相机、56 份服务追加配置、15 个语音输入通过离线核验。 |','| 比赛 Skill | 28 份原文件，15 个单元测试与 73 个 mock 用例通过。 |','| 现场执行 | 真实 KV260、机械转轴及 Windows GPU 推理未执行。 |','','验证底稿位于 report/evidence。本目录中的 hardware_results/implementation/firmware_fresh 结果待最终实现完成后补齐。正式技术文档可从 report/design_report.md、report/dependencies.md 和 data/metrics.csv 取数。'])
(tree/'report/validation_summary.md').write_text('\n'.join(rows)+'\n')
for p in tree.rglob('*.sh'):p.chmod(0o755)
before=inv(tree);(tree/'checksums.sha256').write_text(''.join(v+'  '+k+'\n' for k,v in before.items()));original=inv(tree)
rar=home/'auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar';arc=out/'auar_xuefei_source.rar';events=[]
events.append(run('rar-create',[rar,'a','-ma5','-m5','-r','-idq',arc,tree.name],out))
events.append(run('rar-test',[rar,'t','-idq',arc],out))
expanded=out/'expanded';expanded.mkdir();events.append(run('rar-extract',[rar,'x','-idq',arc,str(expanded)+'/'],out))
p=expanded/tree.name;assert list(expanded.iterdir())==[p] and inv(p)==original
events.append(run('checksums',['sha256sum','--quiet','-c','checksums.sha256'],p))
vit=home/'Xilinx_2022.2/Vitis/2022.2';viv=home/'Xilinx_2022.2/Vivado/2022.2/bin/vivado'
for s in ('software','skill','rtl','prepare'):
 events.append(run(s,[sys.executable,'-B',p/'build/reproduce.py','--stage',s,'--out',out/'regression','--vivado',viv,'--vitis-root',vit],out))
assert inv(p)==original
receipt={'status':'PASS','scope':'interim source RAR / Tcl and preparation from extraction','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rar_sha256':sha(arc),'rar_bytes':arc.stat().st_size,'files':len(original),'checksums':len(before),'single_root':p.name,'full_implementation':'running separately; see final release','steps':events}
write(out/'archive_verification.json',receipt)
folder=home/'下载/AUAR_9a4f_源码与Tcl阶段验证';folder.mkdir(parents=True,exist_ok=False)
for target,source in [('auar_xuefei_source.rar',arc),('archive_verification.json',out/'archive_verification.json'),('验证摘要.md',tree/'report/validation_summary.md')]:shutil.copyfile(str(source),str(folder/target))
(folder/'archive.sha256').write_text(sha(arc)+'  auar_xuefei_source.rar\n')
assert sha(folder/arc.name)==receipt['rar_sha256']
print(json.dumps({'folder':str(folder),'receipt':receipt},ensure_ascii=False),flush=True)
