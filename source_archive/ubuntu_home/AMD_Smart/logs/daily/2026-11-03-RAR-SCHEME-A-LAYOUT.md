# RAR提交结构修订：方案A运行根

日期：2026-11-03（America/Los_Angeles）。用户要求“把改完的结果给我”；此前“先不构建”的要求继续生效。本轮只更新结构文档和索引。

当前唯一入口：/home/ghmd/Win共享文件/协作任务/2026-11-02_project_structure/rar_source_layout.md。采用方案A，src对应原aura运行根，board/host/common/ui/tools/scripts/config/models/assets/data/hardware/tests保持同级关系，不再按src/kv260/aura、src/windows/aura拆分。顶层board用于部署定义，data用于投稿指标，skill用于赛事经验包，分别与src下的运行内容区分。

修正主配置缺失、默认配置和model_manifest的原名、相对配置参数、UI与运行数据遗漏、四个真实RTL bench名称，并规定result.json由本轮仿真生成，历史PASS不得充当前置凭据。将旧doctor/package_project明确限定为框架用途，不能作为整机发布真源或READY判据；原生、模型准备、固件导出仍为待真实验收的入口。PYNQ完整离线包保留，额外工程Skill按成熟度取舍。保留必要xrt_metadata条件分支，不未经追溯把875ca912…当官方输入，也不按pyi/log后缀整体剔除必要文件。

新增runtime_config_readme.md，说明PROJECT_ROOT、两套加载体系、十个顶层键与嵌套校验、example到实际文件名映射、正确doctor/demo参数及现有CLI范围；未生成业务配置骨架。新增evidence/scheme_a_source_audit.json，只读解析现有Python/JSON并登记SHA，确认运行根表达式、CLI自身sys.path处理、model_manifest固定路径、旧白名单范围及candidate/tests四个真实bench，不执行导入、doctor、demo或测试。

旧v2_119entries文档及派生文件已复制至archive保留。重新生成rar_source_tree.txt、rar_source_manifest.csv、rar_source_requirements.csv、rar_source_budget.csv和rar_source_validation.json；149项设计路径（62目录、87文件，目录代表完整实际子树）、15项映射、英文命名/父路径/唯一性/本地链接及100MB预算加总检查通过。预算给模型输入45MB，以容纳选定且允许分发的原始模型；总量仍只是规划，非RAR实测。

未改变现役业务源码或配置，未移动真实aura树，未运行工程构建、模型推理、录放音、运动、Windows服务或板卡操作，未制作工程RAR或上传。先前孤立源码/脚本草稿仍未实跑；历史DCP/旧bundle/IP头文件引用、模型闭包、XCLBIN/base DTB来源和完整构建/部署待验。更新共享入口和项目导航，Windows同步收件未确认。

## 素材收集口径补充，保持149项结构

用户提供历史avatar目录约424MB的盘点，并表示按老师“源码＋脚本”的建议没有必要为素材体积专门转码。只读检查prepare_avatar_frames.py和board_export.py，确认RGB565确由已有PNG生成，后者还生成manifest和C头；前者从原视频/原帧处理，部分流程依赖外部matting工程。因此不启动WebP/降帧改造，不整目录收全量历史帧和可再生缓存；保留实际生成/加载源码、资源定义、小型可用样例的收集位置，明确原版画面仍需可取得的输入，不能凭脚本还原缺失原件。未转码、生成或改动任何素材。

在同一rar_source_layout.md补入README必含清单、验证摘要必须登记的真实四tb/工具/资源时序信息、包外RTL结果的目标参数合同（OUT/rtl/result.json与--rtl-results，尚未实现实跑），将15MB标为最小样例收集预算而非现有资源体积。原目录总量/简单相加不能当RAR实测。本轮只改文档说明和预算标签，结构仍149项；重建接口和渲染均未验，不向现役系统/设备发送任何操作。
