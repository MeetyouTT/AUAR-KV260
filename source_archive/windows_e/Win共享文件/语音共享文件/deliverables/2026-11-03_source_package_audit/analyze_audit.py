"""Create review artifacts from the read-only inventories; does not assemble a release."""
from pathlib import Path
import collections
import csv
import datetime as dt
import hashlib
import json

OUT = Path(__file__).resolve().parent
LIVE = Path(r'E:\Win共享文件\语音共享文件\aura')
OLD = Path(r'E:\AUAR_工程交付_20261102\aura')
RECENT = Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_voice_only_diagnosis')
R4 = Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-02_avatar_animation_optimization\revision4_dialogue_motion')
U = '/home/ghmd/Win共享文件/协作任务/'
SCRATCH = '/home/ghmd/auar-source-v2-20261102'

def load(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

def write_csv(name, rows, columns=None):
    if columns is None:
        columns = list(rows[0])
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

def main():
    wi, ui = load('windows_inventory.json'), load('ubuntu_inventory.json')
    inv = {**wi, **ui}
    manifest = list(csv.DictReader((OUT/'reference/rar_source_manifest.csv').open(encoding='utf-8-sig')))
    recovered = load('nine_component_sources.json')
    overrides = {
        'README.md': ('有旧说明；方案A待定稿', [str(OLD/'readme.md'), U+'2026-11-02_project_structure/runtime_config_readme.md'], '现有README采用旧布局；方案A完整命令、输入及边界尚未封版。'),
        'license': ('正式许可缺口', [str(OLD/'license'), str(OLD/'third_party_notices.md')], '旧license只有归属保留声明；旧notices明确未包含队伍签发的统一公开源码许可。'),
        'third_party_notices.md': ('有材料；范围待定稿', [str(OLD/'third_party_notices.md')], '已有来源说明；角色素材公开再分发依据、最终源版本与完整依赖范围仍待确认。'),
        'checksums.sha256': ('最终封版后生成', [str(OLD/'checksums.sha256')], '已有旧包SHA；不能沿用为方案A最终校验清单。本项为可选。'),
        'src/': ('源码分散；尚未组装', [str(OLD/'src/software'), str(LIVE), str(RECENT), str(R4), SCRATCH+'/src'], '380项运行锁可按旧树371项及已定位9项对齐；其余测试、独立相机、主机和构建源码须按实际引用补齐。'),
        'src/config/readme.md': ('说明材料已有', [U+'2026-11-02_project_structure/runtime_config_readme.md'], '说明稿已在Ubuntu；还不是已落入最终src/config的安装说明。'),
        'src/models/readme.md': ('准备说明待整合', [str(OLD/'src/windows/readme.md'), str(LIVE/'models/vision/README.md'), str(OLD/'models/board_audio_dependencies.json')], 'LLM/TTS、视觉、板端音频各有资料；尚缺方案A统一模型准备顺序和实际调用映射。'),
        'src/models/adapt/': ('适配源码已有；待收拢', [str(OLD/'src/vision_quantization')], '已有YuNet/SFace改写、量化和编译源码；保留真实相对路径及其导入依赖，不要求为目录名重写流程。'),
        'src/models/calibration/': ('校准材料部分已有', [str(OLD/'models/quantization'), str(OLD/'src/vision_quantization/prepare_public_faces.py')], '已有arch、quant_info及报告和数据准备脚本；固定数据取得、容器/挂载、划分与编译配置尚未按新包复跑。'),
        'src/assets/': ('运行素材已有；样例范围待定', [str(OLD/'src/software/assets'), str(OLD/'src/avatar/asset-provenance.json'), str(LIVE/'assets')], '当前发布锁含Yuki EMS/JSON/纹理；历史avatar PNG/RGB565不能替代它。最小有权分发样例及原形象取得来源待定。'),
        'src/tests/bench_identity_stop.py': ('条件项；按原名回收', [str(OLD/'src/vision_quantization/board_fixed_benchmark.py')], '本次范围未定位该同名文件；存在硬件检查/基准源码，须按最终真实测试决定是否需要。'),
        'src/requirements.windows.lock.txt': ('条件项；已有锁定依据', [str(OLD/'src/windows/requirements-5090.txt')], '沿用实际锁文件名称；同时带齐实际上游源码及其安装步骤。'),
        'src/requirements.kv260.lock.txt': ('条件项；依赖锁部分已有', [str(OLD/'models/board_audio_dependencies.json'), str(OLD/'board/readme.md')], '15个音频/ARM依赖有SHA清单；不等于整个ARM软件与系统依赖已锁全。'),
        'src/fpga/': ('硬件源码草稿已有', [SCRATCH+'/src/fpga', str(OLD/'src/fpga')], 'Ubuntu草稿含RTL/BD/IP封装/XDC；新构建尚未执行。'),
        'src/fpga/bd/address_map.json': ('地址定义有；目标文件未见', [SCRATCH+'/src/fpga/bd/system.tcl', str(OLD/'src/fpga/inputs')], 'BD内已有实际地址定义；本次范围未定位独立address_map.json，不把文件名差异直接当功能缺失。'),
        'src/fpga/overlay/': ('固件输入链待闭环', [str(OLD/'src/fpga/overlay'), str(OLD/'build/scripts/pack_firmware.py')], '旧包有base.dtb/base_overlay.dtbo；目标overlay源、base取得方法、工具版本和语义合并尚未闭环。'),
        'src/fpga/overlay/aura-visual-servo.dtsi': ('目标源未定位；需审定', [str(OLD/'src/fpga/overlay'), str(OLD/'build/scripts/pack_firmware.py')], '已有DTBO二进制和相关历史工程；本次核对范围未见方案A目标dtsi，不能宣称整台Ubuntu不存在生成线索。'),
        'src/fpga/overlay/readme.md': ('复现说明待补', [str(OLD/'build/readme.md')], '旧说明采用固定DTBO配对；方案A源到DTBO及base DTB合并说明尚未定稿。'),
        'src/fpga/ip/custom/': ('条件项；封装脚本已有', [SCRATCH+'/src/fpga/ip/ip_config.tcl'], '草稿用真实RTL在本轮输出中封装两个自定义IP；是否另收custom子树按实际路线决定。'),
        'src/fpga/xrt_metadata/': ('条件项；XCLBIN路线未定', [str(OLD/'board/firmware_pairing.json'), str(OLD/'build/scripts/pack_firmware.py')], '现有脚本复制875ca912…XCLBIN；固定取得与元数据重建路线尚未审定，未见完整目标元数据目录。'),
        'src/native/': ('条件项；源码和构建材料已有', [str(OLD/'src/camera/native_operator'), str(OLD/'src/avatar/native_integration'), str(OLD/'src/motion'), str(R4/'candidate/native')], '原生源码在多处；旧脚本默认仍链接预编译.o，R4脚本复用旧.a/.o，新包纯源码重建待验证。'),
        'src/third_party/': ('条件项；上游材料已有', [str(OLD/'src/fpga/vendor'), str(OLD/'src/avatar/deps'), str(OLD/'src/motion/trajectory_src'), SCRATCH+'/third_party/dpu'], '必要上游源码和原始许可按真实依赖收齐；Ubuntu草稿DPU当前位于顶层third_party，须与最终脚本路径一致。'),
        'sim/rtl/vectors/': ('条件项；未见必须外部向量', [str(OLD/'sim/rtl')], '静态检查四份现有TB未见readmem/fopen/include外部输入；不用创建空vectors目录。'),
        'sim/rtl/run.tcl': ('目标入口未定位；有旧实现', ['/home/ghmd/aura-pan-wide-20261028/run_rtl_tests.py', str(OLD/'data/reference/xsim_historical.json')], '四TB及旧运行器/结果存在；尚缺新包OUT/rtl/result.json统一入口及新源指纹绑定。'),
        'build/reproduce.py': ('草稿已有；编排未齐', [SCRATCH+'/build/reproduce.py', str(OLD/'build/scripts/reproduce.py')], '草稿只有Vivado prepare/implement/all；未编排软件、RTL、模型/native，sources()也不覆盖sim。'),
        'build/build.tcl': ('草稿已有；NOT_RUN', [SCRATCH+'/build/build.tcl'], '去旧DCP构建草稿已存在；不接收--rtl-results，尚未生成新综合/实现结果。'),
        'build/export_firmware.py': ('功能材料已有；源链待补', [str(OLD/'build/scripts/fpga.py'), str(OLD/'build/scripts/pack_firmware.py'), str(OLD/'build/original/bitstream_pairing.py')], '有导出、bit/XSA配对和报告代码；旧脚本仍依赖固定XSA/DTBO/XCLBIN，未完成新源码包路线。'),
        'build/prepare_models.py': ('功能材料已有；统一入口未齐', [str(OLD/'src/windows/prepare_weights.py'), str(OLD/'src/vision_quantization')], '已有实际准备/量化脚本；本次未见目标薄编排入口及全流程同版复验。'),
        'build/build_native.sh': ('旧入口已有；纯源码待验', [str(OLD/'build/scripts/native_build.sh'), str(R4/'build.py')], '旧native_build默认链接相机.o，R4链接旧静态库和对象；完整SDK环境下从全部源码构建未在本轮执行。'),
        'build/env.json': ('环境材料有；统一锁待补', [str(LIVE/'config/toolchain_lock.json'), str(OLD/'build/readme.md'), str(OLD/'board/readme.md'), str(OLD/'src/windows/requirements-5090.txt')], '未见最终env.json；版本/补丁/指纹/ABI/频率及固定输入应统一来源。'),
        'board/': ('旧部署定义有；方案A待适配', [str(OLD/'board')], '旧部署保留大量历史绝对路径；尚无方案A安装闭环。'),
        'board/systemd/aura-camera.service': ('真实服务已有；沿用真名', [str(OLD/'board/systemd/aura-camera-ui.service')], '树上名字为示意；实际相机服务是aura-camera-ui.service，不因此新建改名服务。'),
        'board/systemd/aura-business.service': ('真实服务已有；沿用真名', [str(OLD/'board/systemd/aura-avatar-ui.service')], '实际业务/UI服务是aura-avatar-ui.service；有效启动参数及依赖需要按最终布局复核。'),
        'board/systemd/dropins/': ('条件项；追加配置已有', [str(OLD/'board/systemd')], '旧包有56份实际加载追加配置及清单；尚未适配方案A并验收新设备。'),
        'board/udev/': ('条件项；采用情况待确认', [str(OLD/'board/readme.md')], '本次索引未定位独立udev规则；实际不需要则不创建空目录。'),
        'board/system/': ('系统取得链待完善', [str(OLD/'board/config/image_inputs.json'), str(OLD/'board/readme.md')], '已有12项历史文件输入清单及环境说明；它们不等于完整系统镜像/内核/XRT/base DTB来源闭环。'),
        'board/system/image_manifest.json': ('目标系统清单未齐', [str(OLD/'board/config/image_inputs.json'), str(OLD/'board/readme.md')], '需固定镜像、内核/XRT/VART/Python和base DTB来源校验；旧12文件清单用途不同。'),
        'board/system/patches/': ('条件项；补丁范围待确认', [str(OLD/'board/config/public_board_resources.json')], '系统/驱动实际改动须追溯；本次未见统一patches目录，不据此认定所有补丁丢失。'),
        'board/deploy.json': ('旧映射已有；方案A待改', [str(OLD/'board/config/deployment_files.json'), str(OLD/'board/scripts/stage.py')], '旧映射实际归位到多个历史绝对目录；不是方案A运行根/权限/配置/服务/就绪的一体映射。'),
        'board/install.sh': ('目标安装入口未定位', [str(OLD/'board/scripts/stage.py'), str(OLD/'board/startup/launcher.py')], '有离线暂存及启动代码；尚无方案A全新设备安装/模板生成/就绪闭环。'),
        'data/metrics.csv': ('历史指标已有；同版待整合', [str(OLD/'report/performance_metrics.csv'), U+'2026-11-02_dual_reports/metrics.csv'], '有数值和报告；需保持版本/输入/条件/单位/来源，不把分窗样本拼成同一整机性能。'),
        'data/expected/': ('条件项；比对材料已有', [str(OLD/'data/input'), str(LIVE/'data/golden')], '保留真实位置及来源；不从运行根搬走golden来凑顶层目录。'),
        'skill/README.md': ('说明已有；按选定范围定稿', [str(OLD/'skill/readme.md'), U+'2026-11-02_pynq_skill/readme.md'], '新方案主包为PYNQ；旧A/B/C材料可参考，不自动扩充本轮实现范围。'),
        'report/design_report.md': ('源稿已有；最终同版待定', [U+'2026-11-02_dual_reports/amd_design_report.md', U+'2026-11-02_dual_reports/competition_technical_report.md', str(OLD/'report/release_status.md')], '报告源稿、Word/PDF、指标已存在；旧稿待补表述不能覆盖Windows较新人类验收与发布证据。'),
        'report/validation_summary.md': ('历史证据有；最终摘要未齐', [str(OLD/'build/reports'), str(OLD/'data/reference/xsim_historical.json'), str(OLD.parent/'verification/release_receipt.json')], '存在旧仿真/实现/单核离线证据；新方案A统一命令/退出码/源指纹/结果集合仍NOT_RUN。'),
        'report/ai_collaboration.md': ('案例已有；原问答待补', [str(OLD/'report/ai_collaboration'), U+'2026-11-02_dual_reports/materials_to_prepare.md'], '有工程案例和索引；完整真实历史提示/回答/纠错及工具版本仍不齐，不能事后伪造原话。'),
    }
    # Resolve physical evidence without treating illustrative filenames as requirements.
    def find(root_name, rel, directory=False):
        v = inv[root_name]
        rel = rel.rstrip('/')
        valid = rel in v['directories'] if directory else rel in v['files']
        if valid:
            return v['root'].rstrip('\\/') + '/' + rel
        return None

    checklist=[]
    for row in manifest:
        path=row['path']; directory=row['entry_type']=='目录'
        status='条件项；本次范围未定位' if '最终实际使用时' in row['required_if'] else '本次范围未定位；需继续追溯'
        sources=[]; note='文件存在只说明有来源，不等于最终版本或全流程验收通过。'
        scratch_rel=path.rstrip('/')
        stage=find('ubuntu_scratch',scratch_rel,directory)
        if stage:sources.append(stage);status='草稿已收集；未验收'
        if path.startswith('src/') and not path.startswith(('src/fpga/','src/native/','src/third_party/')):
            rel=path[4:]
            if path=='src/':rel=''
            if rel:
                for k,prefix in [('windows_live',''),('windows_delivery','src/software/'),('ubuntu_voice',''),('ubuntu_sharedfolder','')]:
                    value=find(k,prefix+rel,directory)
                    if value:sources.append(value)
                if not sources and '.example.json' in rel:
                    plain=rel.replace('.example.json','.json')
                    for candidate in [plain,plain.replace('.json','.local.json')]:
                        value=find('windows_live',candidate,directory)
                        if value:sources.append(value)
                    if sources:
                        status='真实配置有；模板待脱敏'
                        note='需从最后有效完整配置生成模板并按真实加载器安装；不能用空JSON骨架代替。'
                elif sources and not stage:status='实际源文件或子树已有；版本待收拢'
        elif path.startswith('skill/pynq-contract-testgen'):
            rel=path[len('skill/pynq-contract-testgen'):].lstrip('/')
            sources=[ui['ubuntu_pynq']['root']+('/'+rel.rstrip('/') if rel else '')]
            status='完整离线包已有'
            note='28个源/说明/证据文件；15单元和73生成后模拟用例为已有记录。本轮未复跑，真实PYNQ/跨板未验。'
        elif path=='skill/':
            sources=[ui['ubuntu_pynq']['root'],str(OLD/'skill')];status='Skill材料已有'
        else:
            match=find('windows_delivery',path,directory)
            if match:sources.append(match);status='旧交付材料已有；方案A待适配'
        if path in overrides:
            status,sources,note=overrides[path]
        if path=='src/fpga/constraints/':
            status='XDC已有；名字及引用待统一';sources=[SCRATCH+'/src/fpga/constraints/pins.xdc',str(OLD/'src/fpga/pin.xdc')];note='草稿pins.xdc与原pin.xdc字节相同；最终按文档保留实际命名/调用关系，当前未改名。'
        if path in ['src/config/source_import_manifest.json','src/config/toolchain_lock.json']:
            note+=' 需要脱敏/统一版本来源并与build/env.json对齐。'
        if path=='src/tools/start.ps1':
            status='条件项；现役入口已有';sources=[str(LIVE.parent/'start_inference.ps1'),str(OLD/'src/windows/start_inference.ps1')];note='沿用实际入口真名及位置；不能仅按start.ps1缺失判定无启动脚本。'
        if path=='src/tools/stop.ps1':
            status='条件项；现役入口已有';sources=[str(LIVE.parent/'stop_inference.ps1'),str(OLD/'src/windows/start_inference.ps1')];note='旧独立启动器含Stop动作；最终按真实CLI回收。'
        if path=='src/models/vision/':sources.append(str(LIVE/'models/vision'))
        checklist.append({'target_path':path,'entry_type':row['entry_type'],'required_if':row['required_if'],'review_status':status,'scratch_exact_path_exists':bool(stage),'evidence_paths':' | '.join(dict.fromkeys(sources)),'analysis':note,'execution_this_review':'NOT_RUN'})
    write_csv('方案A_149项审查清单.csv',checklist)
    # Small text hashes only: do not imply all binaries/weights were synchronized.
    a=wi['windows_live']['files'];b=ui['ubuntu_voice']['files']
    diff=[]
    for n in sorted(a.keys() | b.keys()):
        x=a.get(n,{});y=b.get(n,{})
        if n not in a or n not in b or (x.get('sha256') and y.get('sha256') and x['sha256']!=y['sha256']):
            diff.append({'path':n,'windows_exists':n in a,'ubuntu_exists':n in b,'windows_sha256':x.get('sha256','NOT_HASHED'),'ubuntu_sha256':y.get('sha256','NOT_HASHED'),'scope':'小型文本SHA比较；未判定哪份应覆盖哪份，不含所有二进制/权重内容比较'})
    write_csv('Windows与Ubuntu_语音树差异.csv',diff)
    version_rows=[]
    for r in load('runtime_380_comparison.json'):
        if not r['old_snapshot_matches']:
            version_rows.append({'runtime_path':r['runtime_path'],'old_sha256':r['old_snapshot_sha256'],'new_saved_release_sha256':r['expected_sha256'],'matched_sources':' | '.join(recovered.get(r['runtime_path'],[])),'collection_action_this_review':'未复制或组装业务文件；仅定位SHA相符来源'})
    write_csv('较新发布_9项差异及来源.csv',version_rows)
    status_counts=dict(collections.Counter(x['review_status'] for x in checklist))
    latest_status=load('saved_project_status_snapshot.json')
    summary={'schema':'auar-source-package-readonly-audit-1','date':'2026-11-03','timezone':'America/Los_Angeles','manifest_rows':len(checklist),'directory_rows':sum(r['entry_type']=='目录' for r in manifest),'file_rows':sum(r['entry_type']=='文件' for r in manifest),'status_counts':status_counts,'scratch_files':ui['ubuntu_scratch']['file_count'],'baseline_before_thinking_startup_sha256':hashlib.sha256((RECENT/'startup.after.json').read_bytes()).hexdigest(),'latest_saved_startup_sha256':latest_status['startup_sha256_at_latest_saved_board_receipt'],'old_saved_startup_sha256':hashlib.sha256((OLD/'board/config/startup.snapshot.json').read_bytes()).hexdigest(),'old_components_match_latest_saved':371,'old_components_different':9,'changed_components_all_located_by_sha256':all(recovered.get(n['runtime_path']) for n in version_rows),'general_tree_latest_saved_380':{'same':263,'different':61,'missing':56},'small_text_voice_tree_differences':7,'project_execution_status':'NOT_RUN','board_connections':0,'models_called':False,'engineering_package_assembled':False,'scope_notes':'149 rows are design entries, including 62 directories, not 149 files and not a completion percentage. Runtime 380 includes generated libraries/assets; it is a published runtime identity, not a source-only distribution whitelist. Latest saved result is the temporary thinking-test release; this audit does not select it as the submission release.'}
    (OUT/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    report=f'''AUAR·雪妃：方案A源码工程包状况审查
日期：2026-11-03（America/Los_Angeles）

结论
现有材料足以支撑继续整理源码工程包。主要业务源码、独立相机/主机入口、FPGA RTL/BD/IP/XDC、四份测试台、模型适配源码、部署材料、PYNQ离线包和报告资料均已有来源。当前尚未形成文档方案A的最终完整源码包；主要缺口是最终同版收集、无旧二进制依赖的重建链、配置/安装映射、输入来源及最终验收说明。不能把“需要收集”全部说成“尚未开发”，也不能把旧包或单个草稿目录直接视作最终交付。

审查范围与证据口径
用户请求是审查分析，附件作为比对标准。附件里“后续执行/实现/验收”的文字没有被当作本轮执行授权。
本轮通过SSH只读访问Ubuntu文件，扫描Windows现用树、Windows旧交付树、Ubuntu语音树、Ubuntu较早共享文件夹树、Ubuntu硬件草稿和PYNQ离线包；读取最新保存发布清单、源文件及已有结果。没有连接KV260，没有运行doctor/demo/测试、模型、Vivado综合实现、部署/服务/运动或RAR打包。写入的只有本审查目录和审查回执/日志。
D:/Download/rar_source_layout.md与Ubuntu当前rar_source_layout.md原始SHA相同。该方案有149项设计条目：62目录、87文件；目录代表完整实际子树，不能把149当实际文件总数或据此算完成率。
扫描排除了venv、缓存、.git、node_modules、test_tmp及目录符号链接。小于等于2MB的所选文本文件计算SHA；模型/图片/二进制不在普遍逐字节双机同步证明范围内。另对明确的380运行锁、9项差异文件、两份ONNX和旧交付件做了定向SHA核对。所有六份根目录清单均未报告读取错误，已哈希文本未出现读取中变化。

一、已有材料及实际位置
1. Windows现用通用树：{LIVE}
   board/host/common/ui/tools/scripts/config/tests等都有，models/vision下有YuNet与SFace原始ONNX。根依赖文件、主配置、UI schema和运行数据有来源。但这棵通用树不是最终运行版闭包：按较新380项保存发布锁，对应位置263项SHA相同、61项不同、56项不存在。缺项不表示成果丢失，应从已冻结发布和专项交付回收。
2. Windows旧工程交付：{OLD}
   1977个文件、未压缩257,062,175字节。包含完整旧版380组件树src/software、独立src/camera、src/windows、FPGA、原生源码、模型适配、systemd及报告。主RAR实测165,867,671字节，SHA为185cea28db2db1a95d15ac2cc8abd9c47a39e41e033ad3fa506053d9c2a63d00。它是旧工程归档，含XSA/DCP参考、预编译库/对象及生成xmodel等，不符合这次仅源码与重建脚本的收集口径。
3. Ubuntu硬件草稿：{SCRATCH}
   实际24个文件、2,248,968字节，含两个RTL、四个TB、BD生成/系统Tcl、IP封装/XDC、DPU源码组件、reproduce.py/build.tcl及来源记录。不是完整源码包，缺少完整运行src、部署/报告等收集结果。DPU component.xml引用的10个唯一相对文件全部在草稿内；其中dpu_conf绝对引用已有局部修订。这个静态结果不能代替Vivado IP生成/综合通过。
4. Ubuntu当前结构依据：{U}2026-11-02_project_structure/
   文档、树、149项CSV、配置说明和静态检查均在。D盘只有用户这份MD不代表配套材料没有。
5. PYNQ：{ui['ubuntu_pynq']['root']}
   28个文件、86,438字节，脚本/模板/两例/测试/证据/许可均有。已有15项单元、36+37=73项生成后软件模拟及解压复现通过记录。真实PYNQ、实板、跨板与非作者复用未验，本轮未重跑。
6. 报告：{U}2026-11-02_dual_reports/
   AMD/赛事两份源稿、Word/PDF、metrics和来源矩阵有；Windows旧工程另有较新性能附录、布线示意及AI案例材料。旧稿中的待补状态需与Windows较新记录对齐，不能照抄为当前缺陷。

二、最终版本收集是首要问题
本轮较新完整保存发布锁：{RECENT/'startup.after.json'}
SHA：{summary['baseline_before_thinking_startup_sha256']}，380项。
收尾时读取到更晚PROJECT_PROGRESS（更新UTC 2026-11-03 08:50:58），引用2026-11-03_thinking_test/RESULT.json，startup SHA为{summary['latest_saved_startup_sha256']}。该回执在前序380锁基础上仅改变board/runtime/board_dialogue.py（379项保持），其目标SHA为88b9d6e2eb7d6d8199170cfa1712d4a1c2de4227ed5d3c6f57be927a7bee67de。本轮已定位并核对对应源码，9项来源CSV以这个较新源SHA记录。这里只根据保存回执及本地源字节更新审查，不声称重新读取了设备完整启动文件。
旧包startup SHA：{summary['old_saved_startup_sha256']}，380项。
两份锁371项相同，9项不同；9项对应文件均已按目标SHA在Windows专项交付中找到。详细路径见“较新发布_9项差异及来源.csv”。
9项为board_business.py、board_dialogue.py、board_memory_policy.py、board_speaker_business.py、board_avatar_gtk.json、yuki_pair.formal.json、formal_yuki.py、libaura_yuki.so、native_yuki.py。
其中4个业务Python来自近期声纹/称呼及临时思考策略交付，原生渲染库及其5项绑定在R4交付。R4的4份C/C++源文件及构建记录已按该版构建回执SHA核对，不应只回收.so。旧包371项加9项精确来源可以对齐所审查的保存运行锁，但这不是已经组装的源码包，也不能证明全部源码、相机、主机、测试和输入闭包已齐。运行锁含二进制/资源，最终源码包仍须带能重建对应输出的源/构建定义。
voice_only的candidate_runtime单目录同样不能整棵复制：按其后、临时思考前的9a4f…基准，342项存在，337项匹配，5项不同，38项未带齐；切换到更晚7143…基准后，该目录中board_dialogue再多1项版本不同。它是单项变更候选材料，不能替代完整发布。
临时思考版本保留默认关闭策略，当前开机的易失标志临时开启think=true/num_predict=192；重启或Off后关闭。临时运行开关不等于应纳入正式默认设置。最终封版应明确选择源码及默认策略，本轮没有代替用户选择或切换。

三、Windows与Ubuntu来源差异
Windows语音aura与Ubuntu“语音共享文件/aura”的已扫描小型文本有7项SHA不同：tools/model_inference_host.py、tools/voice_startup_guard.py、两份model_inference框架测试、gpu_runtime.local.json、model_inference.local.json、ollama_runtime.local.json。Windows另多一个output/runtime_dashboard_snapshot.json，属于运行快照。本轮未覆盖任一版本。
Ubuntu“共享文件夹/aura”是另一份较早树：Windows有365个额外路径，小型文本共同项684同、36异。后续不能仅凭目录名或“Ubuntu源”认定它是最新。详见差异CSV和原始清单；这些数字不等于全量模型/二进制的内容同步证明。

四、各部分有/缺/待确认
软件与运行根：源码大量已有；缺的是按同一发布选择完整文件并保持src内相对关系。新树不能再次分成各自带aura的kv260/windows根。独立相机和现役Windows入口仍要补收，不能仅用旧package_project白名单。
配置：完整原runtime.sim、runtime.kv260、model_manifest、toolchain_lock及各子系统配置已有；config/readme说明稿已有。多数example模板尚未生成或最后脱敏，env.json未形成统一锁，安装后真实文件名/路径映射未完成。3份本机配置双机不同。不能复制本机私有值或用空骨架代替有效配置。
RTL/BD/IP：RTL、四TB、BD、IP配置与XDC已有。Ubuntu草稿pins.xdc与原pin.xdc同源，最终按真实命名及脚本一致性处理，不为目录重新设计硬件。去旧DCP草稿已有，尚未实际构建。
RTL入口：sim/rtl/run.tcl未定位为已实现目标入口；原run_rtl_tests.py和历史result.json有。新reproduce.py不编排RTL，sources()不包含sim；build.tcl允许的参数只有--out/--stage/--vitis-root，不支持--rtl-results。因此文档的OUT/rtl/result.json与源指纹门禁尚未接通。本轮为NOT_RUN，旧四TB PASS只能作原版本历史证据。
固件链：旧fpga.py/pack_firmware.py/bitstream_pairing已有，旧新目录prepare/从routed DCP导出曾有通过记录；clean_directory_validation明确new_full_synthesis_and_route=false。旧implement仍使用src/fpga/reference/incremental.dcp。pack_firmware仍读取既有wide.xsa比较HWH并复制既有DTBO/XCLBIN/shell.json。缺的是方案A独立源到固件的闭环：目标overlay源/基准DTB取得、dtc/fdt工具版本、语义合并、XCLBIN取得或元数据重建，以及本轮报告/bit/XSA配对。不能把875ca912…简单当官方base shell或删掉这一环节。
原生构建：相机C++、运动C/C++、角色native及上游源码/部分构建定义已有。旧native_build默认链接现有.aarch64.o；R4脚本也复用历史libyuki_core.a、gles2_renderer.cpp.o和diagnostic_api.cpp.o。完整源码/头文件来源可进一步按SHA闭合，但不能把本次链接成功记录称作不依赖旧对象的整包重建。
模型：原始YuNet345,478字节，SHA50ef07f702a31741ca46a4c0d947773b64143b9362780237bf0d427d6c79bab7；SFace38,696,353字节，SHA0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79；均与适配脚本固定输入一致。YuNet/SFace改写/量化/编译源码、quant_info/arch/校准报告有。LLM/TTS固定revision/哈希/准备入口有，板端音频15项依赖有锁；仍待统一准备说明、外部公开数据/路径/容器与许可、YOLOX固定取得和最终同版准备验证。大LLM权重继续在项目外，不因不随包就算源码缺失。
部署与系统：实际aura-camera-ui.service和aura-avatar-ui.service、56份追加配置、旧deployment_files/stage/launcher及固定提示音有。文档里的服务名是示例，不需要新造同名服务。缺的是方案A运行根、模板生成、权限、资源定位与就绪规则的一体映射及install入口。旧12文件image_inputs是历史校验集合，不是系统镜像/内核/XRT/VART/Python/base DTB完整来源清单。新设备/空白卡冷启动未验。
素材：当前380锁是Yuki EMS/JSON/纹理/原生加载方案，旧avatar PNG/RGB565生成流程只覆盖另一类历史素材。真实输入、格式/状态/时序、最小可分发样例和原形象来源必须明确。已有素材不代表已具备公众再分发依据。无需为预算转码/降帧；也不能删除当前真实依赖而宣称原版画面可完整复现。
许可与报告：旧根license是205字节的归属保留声明，notices明确没有队伍正式统一公开源码许可，属于明确待补项。第三方已有不少原始许可，但最终模型/IP/角色美术范围仍需确认。AI案例和索引有；完整真实历史提示/回答/纠错及工具版本仍有缺口。设计稿和指标有，最终同版validation_summary及README尚未封版。

五、功能状态与包状态分别理解
Windows较新PROJECT_PROGRESS记录：转轴已获用户现场认可，记忆基本可用并移出当前阻塞，人脸KNOWN和画外长句声纹称呼有现场确认；短句修复已部署，真人短句及两人切换仍待。R4已部署，实屏观感待确认。R7冷启动候选离线复核通过、尚未实际部署/冷启动。三分钟全功能联合演示未完成。更晚临时思考测试已加载、仅当前开机启用；该测试自己的真实模型探针/58项本地检查属于原回执，本审查未复跑。
这些是保存记录，本轮没有新访问设备。不能用Ubuntu较早“ec12未READY/转轴抖动/真人身份未验”的说明覆盖较新Windows结果；也不能从已有功能推导方案A新源码包已经冷装通过。用户已取消的人脸声纹联绑不应再列为必须开发。

六、体积判断
旧主RAR165,867,671字节；外部音频ZIP197,532,108字节；独立routed DCP125,752,676字节。旧RAR低于200,000,000只证明旧归档大小，不证明这次源码方案已满足单包输入闭包。音频ZIP有16个实际成员，其中15个是锁定依赖，另1个是manifest.json依赖清单；不把成员数与依赖数混同。
现用通用树约7.74GB包含模型、素材、artifacts、文档等，不能用整树体积当源码体积或最终RAR体积。100MB未压缩/200MB压缩是文档目标；本轮没按新收集白名单组装或压缩，无法给出新包最终大小。原始SFace约38.7MB、历史全量帧/缓存、大权重、生成工程/固件的取舍按最终用途和文档口径办理。

七、后续建议顺序（仅列分析结论，本轮未执行）
1. 确定封版基准，按已找到的9项及相机/Windows真实入口建立全源来源映射，保留各自原相对路径；不整棵取通用开发树或单一candidate。
2. 静态收齐配置有效原件/脱敏模板、模型数据取得约定、native全源、IP/工具/系统锁和最小样例；确认团队及第三方许可范围。
3. 完成薄编排和安装映射，让RTL新结果、源码指纹、硬件报告、固件元数据、失败退出码与README参数一致。
4. 在后续明确进入验证阶段后，再做新目录软件/RTL/完整硬件/native/模型准备，以及新Windows/实板冷启动和同版联合验收；结果据实PASS/FAIL/NOT_RUN。
5. 最后生成校验清单、统一验证摘要、精简指标/AI材料并实测源码RAR。当前不需要重写已有业务模块或重复扩展已取消功能。

本目录说明
“方案A_149项审查清单.csv”：逐项状态、条件、来源与限制。
“较新发布_9项差异及来源.csv”：旧包与较新保存380运行锁的9项精确SHA来源。
“runtime_380_comparison.csv/json”：380项逐项对照，便于后续制定实际收集清单。
“Windows与Ubuntu_语音树差异.csv”：小型文本与路径差异，不包含私有配置内容。
“windows_inventory.json / ubuntu_inventory.json / audit_scope.json”：范围、排除项、SHA与元数据证据。
“reference/”：从Ubuntu取回的结构/配置说明副本，仅作本轮审查依据。
“collect_audit.py / analyze_audit.py”：审查辅助脚本，不是工程业务或复现构建入口。
'''
    (OUT/'工程包审查分析.txt').write_text(report,encoding='utf-8-sig')
    print(json.dumps({'rows':len(checklist),'directories':summary['directory_rows'],'files':summary['file_rows'],'all_nine_located':summary['changed_components_all_located_by_sha256'],'output':str(OUT/'工程包审查分析.txt'),'statuses':status_counts},ensure_ascii=False))

if __name__=='__main__':
    main()
