"""Create a reviewable isolated candidate only after all recorded gates pass."""
from pathlib import Path
import hashlib,json,shutil,zipfile
phase=Path(__file__).parent;base=phase.parent;evidence=base/'evidence/native_integration'
def read(name):return json.loads((evidence/'results'/name).read_text(encoding='utf8'))
images=read('precision-images.json');clock=read('gtk-clock.json');continuous=read('continuous.json')
pipeline=read('precision-validation-result.json');preservation=read('final-preservation.json');worker=read('ui-worker-test.json');adapters=read('adapter-tests.json');cache=read('state-cache.json')
lifecycle=read('gtk-lifecycle.json')
local=json.loads((phase/'local-preservation.json').read_text(encoding='utf8'))
nose=json.loads((phase/'nose-source-comparison.json').read_text(encoding='utf8'))
assert nose['same_white_pixels_all_cases']
for value in (images,clock,continuous,pipeline,preservation,worker,adapters,cache,lifecycle):assert value['status']=='PASS',value.get('status')
assert local['changed']==[] and local['source_psb_unchanged']
assert clock['duration']>=299 and clock['interval_ms']['p99']<62.5
assert not clock['physical_audio_or_touchscreen_acceptance']
for name in ('yuki_host.cpp','gles2_renderer.cpp','gles2_renderer.hpp','tile_uv.hpp','native_yuki.py','egl_window.py'):
    assert hashlib.sha256((phase/'host'/name).read_bytes()).hexdigest()==pipeline['source_hashes'][name],name
lib=evidence/'build_host/libaura_yuki.so'
assert hashlib.sha256(lib.read_bytes()).hexdigest()==pipeline['binary_sha256']['libaura_yuki.so']
profile_path=phase/'runtime_assets/source_profile.json';profile=json.loads(profile_path.read_text(encoding='utf8'))
profile.update(status='ISOLATED_NATIVE_GPU_GATES_PASSED',validation='verification.json; original engine matched viewport10 images,4 masks; native35s; GTK300s',production_deployed=False)
profile_path.write_text(json.dumps(profile,indent=2),encoding='utf8')
report=dict(status='ISOLATED_NATIVE_GATES_PASSED_PRODUCTION_NOT_DEPLOYED',client_date='2026-10-30',character='Yuki yuk_0 / 雪妃',
  format='E-mote EMS3.03 PSB4, not Live2D',upstream_commit='4fbf55aa6009df76ac40dc5f18e3781914bc464f',
  source_profile=profile['profile_id'],source_profile_specific=True,generic_model_equivalence_claim=False,
  image_comparison=images,continuous=continuous,gtk_playback_clock=clock,
  preservation=preservation,local_preservation=local,ui_worker=worker,adapter_tests=adapters,state_cache_regression=cache,gtk_lifecycle=lifecycle,nose_source_comparison=nose,binary_sha256=pipeline['binary_sha256'],
  remaining_acceptance=['visible physical display and actual audio integration after an explicitly selected current deployment entry','hours-long sustained operation and subjective idle/expression feel'],
  production_deployed=False)
(phase/'verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
maes=[v['mae'] for v in images['images']]
text=f'''雪妃单角色板端原生替换验证，2026-10-30

结论：三项技术工作在隔离候选中完成并通过本轮验证，可进入实际界面的接入与体验验收。现役服务未切换。
雪妃素材是 E-mote/FreeMote 的 EMS/PSB，不是 Live2D；最终方案为 C++ 求值核心 + GLES2 + GTK 原生 EGL 子窗口。
固定上游：NekoMote 4fbf55aa6009df76ac40dc5f18e3781914bc464f；设备为 KV260，Mali-400 MP / GLES2。

1. 网格、表情与待机
通用 meshCombinator 解析/求值保留，导入43节点/122控制，16项单元验证通过，300次热求值堆分配0。
完整原始PSB在原 FreeMote 3.9 驱动中，开/关43项组合记录在0/1/60步、两姿势及真实极端输入下像素完全相同；其可见节点并非全部隐藏。
因此仅为此固定雪妃素材生成显式 profile：使用作者的 mesh.bp 轨道，保留原始模型和额外资源表，避免重复变形。不是对其他 E-mote 模型的通用等价承诺。
最终 profile 的20条时间轴各360步通过，物理保持开启；宿主支持两种待机、六表情、眨眼及100ms表情渐变。
这是宿主能力覆盖；当前产品入口日常由neutral/friendly/happy/excited/sad/low映射四类脸，默认姿势0。六脸/两姿势尚未新增为界面选择控件。
十组同参数原引擎对照（六表情、两姿势、两极端输入），同步57变量，平均像素误差 {min(maes):.3f}～{max(maes):.3f}/255，轮廓边界误差均0像素。
九秒 idle-expression-preview.gif 为实际板端原生输出按作者时间拼接的待机/表情证据，截图读回速度不用于帧率声明。

2. 遮罩与鼻部白块
来源边界已按来源层自己的绘制资源及引用动作展开修正，排除显式子分支；原 UnsupportedMask 拒绝检查保留。
四类原引擎无损遮罩对照通过，平均误差 {min(v['mae'] for v in images['masks']):.3f}～{max(v['mae'] for v in images['masks']):.3f}/255，平坦内部错误0。
此前鼻部白块的透明保护混合参数已修复为 GL_ONE_MINUS_DST_ALPHA，未修改模型或纹理；本次最终场景输出另外留存于 evidence/native_integration/results/final-profile。
十组固定画面的鼻部白色高光位置与原引擎完全相同，正常4像素、害羞0像素，鼻区平均误差0.041～0.098/255。
Mali 片元没有 highp，使用68张带原图邻域的局部纹理和局部UV避免4096图集精度损失；原始像素数据26.15MiB，UV重映射14项测试通过，500热帧堆分配0。

3. 连续渲染、GTK与播放时钟
离屏连续35秒：{continuous['actual_fps']:.2f}fps，P99帧间隔 {continuous['interval_ms']['p99']:.2f}ms。
GTK连续 {clock['duration']:.1f}秒：{clock['actual_fps']:.2f}fps，P99帧间隔 {clock['interval_ms']['p99']:.2f}ms，最长 {clock['interval_ms']['max']:.2f}ms。
打断后闭嘴 {clock['checks']['cancel_close_ms']:.2f}ms，暂停期间播放时钟漂移 {clock['checks']['pause_clock_span_ms']:.3f}ms；旧音频token/旧owner/重复序列拒绝均通过。
使用现役 RealtimeController.portrait_frame 与真实 GstAudioEngine 的同步 fakesink 播放位置，合成24k单声道PCM经现有管线转48k双声道；未打开真实音频设备。
上述GTK帧率按每次EGL交换提交统计；离屏计时等待GPU完成。未测物理屏幕扫描/触屏和实际扬声器同步，五分钟不等于数小时长期验收。
工作线程只传有界数值控制，不在稳态传JPEG或读回GPU；GTK线程独占求值和GL上下文。
原生EGL子窗口按monotonic时限在GTK线程单次调度，避免依赖Cairo queue_draw的帧阶段。隐藏/恢复、12fps切换、禁用/重启及注入失败后的资源释放共10项实机生命周期检查通过。
GLES状态仅在一帧内去重，每帧及resize后从未知状态开始；私有上下文中注入外部GL状态并缩小/恢复尺寸后，与原帧逐像素一致。
真实候选 worker 的无PIL/JPEG元数据分支及取消期间旧帧不发布通过；控制邮箱8项、资源校验与启动回退8项测试通过。

接入产物与边界
isolated-yuki-candidate-20261030.zip 内含四个UI覆盖文件、已验证ARM64动态库、相对路径配置片段、雪妃固定素材、profile、可重建源码及原许可证。
模型资源校验或EGL初始化/绘制失败时回退默认形象，形象按钮可在雪妃/默认间切换。配置相对AURA运行目录解析，进入现有源码哈希记录。
候选基于当前运行入口的精确源码快照，不应覆盖其他入口，也不能使用历史切换脚本。实际接入时需重新读取当前 ExecStart、PID、运行根和完整pin清单，再形成新的固定运行目录。
收尾时发现现役入口已由另一轮工作更新，已重新读取当前运行根并重生成候选。当前10份来源源码、286项组件pin及71个既有共享目标全部核对；渲染/音频相关依赖与实测版本逐字节相同。当前入口复核前后PID保持，最初入口的变化单独归档，不宣称整个工作期间PID恒定。
本任务没有修改现役入口、启动器或源码，也未改变路径/哈希约束。466份冻结源码/依赖/输入哈希未变，原始PSB未改。未访问真实身份数据库、未进行身份联网验收、未开麦、未驱动机械或修改固件。
原始1536方形隐藏画布参考及早期失败记录均保留；公平像素对照改为相同423x438引擎视口，消除网页(-556.5,-549)居中拷贝引入的额外半像素滤波，验收阈值未放宽。

业务迁板协调回执：../2026-10-30_board_owner/coordination/character_ack.json。仅修改上列两个既有共享文件及新增渲染文件，业务主控/记忆/模型推理通道由对侧负责；实际PCM时钟、boot/session/generation/token须由板端适配器校验。双方确认单一发布者与顺序前保持候选，后续实屏或CPU/GPU测试先预约资源窗口。

复现：在包的 source/native_integration/host 上运行 CMake；系统依赖为C++20、pkg-config、GLESv2、libpng，Python GTK3/GI/X11/EGL沿用板端环境。附带源码布局与本次构建一致，无运行时网络下载。
详细机器证据：native_integration/verification.json；原始计时样本、失败迭代与图片：evidence/native_integration/results/。
'''
(phase/'README.txt').write_text(text,encoding='utf8')
old=base/'verification.json'
if not (base/'verification-phase1.json').exists():shutil.copyfile(old,base/'verification-phase1.json')
old_readme=base/'README.txt'
if not (base/'README-phase1.txt').exists():shutil.copyfile(old_readme,base/'README-phase1.txt')
old.write_text(json.dumps(dict(status=report['status'],latest='native_integration/verification.json',report='native_integration/README.txt',historical='verification-phase1.json',production_deployed=False),indent=2),encoding='utf8')
old_readme.write_text('最新：雪妃板端原生三项验证已在隔离候选完成；现役未部署。\n详见 native_integration/README.txt 与 verification.json。\n初轮记录保留为 README-phase1.txt、verification-phase1.json，失败证据未删除。\n',encoding='utf8')
progress=json.loads((phase/'PROGRESS.json').read_text(encoding='utf8'))
progress.update(status='ISOLATED_VALIDATION_COMPLETE',current_phase='three requested native implementation/validation tasks complete; production not deployed',known_remaining=report['remaining_acceptance'],next=['fresh-entry production integration and visible physical experience acceptance when selected'],current_evidence={'final_report':'verification.json','gtk_fps':clock['actual_fps'],'gtk_p99_ms':clock['interval_ms']['p99'],'images_and_masks':'PASS'},production_deployed=False)
(phase/'PROGRESS.json').write_text(json.dumps(progress,indent=2),encoding='utf8')
ui=json.loads((phase/'ui_candidate/manifest.json').read_text(encoding='utf8'))
files={}
def add(path,name):
    assert name not in files,name
    files[name]=Path(path).read_bytes()
def tree(folder,prefix):
    for path in sorted(folder.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and not any(v.startswith('build') for v in path.relative_to(folder).parts):add(path,prefix+'/'+path.relative_to(folder).as_posix())
tree(phase/'ui_candidate/aura','runtime-overlay/aura')
add(lib,'runtime-overlay/aura/tools/libaura_yuki.so')
tree(phase/'runtime_assets','runtime-overlay/aura/assets/yuki')
tree(phase/'candidate_core','source/native_integration/candidate_core')
tree(phase/'host','source/native_integration/host')
tree(base/'deps','source/deps')
tree(phase/'third_party_licenses','source/third_party_licenses')
for name in ('uv_remap_test.cpp','allocation_counter.cpp','tile_uv.hpp'):
    add(phase/'precision_candidate'/name,'source/native_integration/precision_candidate/'+name)
add(base/'agent_audit/frame_export.cpp','source/agent_audit/frame_export.cpp')
add(phase/'README.txt','README.txt');add(phase/'verification.json','verification.json')
add(phase/'entry-rebase.json','entry-rebase.json')
add(phase/'nose-source-comparison.json','nose-source-comparison.json')
for name in ('idle-expression-preview.gif','matched-reference-normal-comparison.png'):
    if (phase/name).exists():add(phase/name,name)
files['native_yuki.config.fragment.json']=json.dumps({'native_yuki':ui['native_config_example']},indent=2).encode()
files['upstream-and-changes.txt']=('Upstream NekoMote AGPL-3.0-only, commit '+report['upstream_commit']+'\nModified: EMS meshCombinator import/evaluation/serialization, mask source boundary, isolated Yuki host and GLES2 backend. All corresponding source is included.\n').encode()
manifest=dict(schema='aura.yuki.isolated_candidate.v1',production_deployed=False,scope='Yuki yuk_0 only; tested on current KV260 Mali-400 GLES2',basis=ui['basis'],binary_sha256=pipeline['binary_sha256'],files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
archive=base/'isolated-yuki-candidate-20261030.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as out:
    for name,data in files.items():out.writestr(name,data)
    out.writestr('manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(archive) as check:
    assert check.testzip() is None
    assert all(hashlib.sha256(check.read(name)).hexdigest()==h for name,h in manifest['files'].items())
(phase/'package-manifest.json').write_text(json.dumps(dict(path=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(files)+1,production_deployed=False),indent=2),encoding='utf8')
print(json.dumps(dict(status=report['status'],package_bytes=archive.stat().st_size,package_files=len(files)+1)))
