六文件发布/已知字节恢复模板说明（仅root审核后使用）

入口 six_file_transaction_template.py；本子代理仅在Windows自己的camera目录生成与测试，没有SSH或执行目标事务。模板不是服务/恢复平台，只处理已审过的相机六文件。原Native reader、完整checkpoint/history下界语义验证、正常服务停止/启动、GUI重绑均由root单独负责。

模板默认dry-run。显式 --apply 才写入；--recover 本身仍dry-run，只有 --apply --recover 才将已准备事务完成到同一after字节。没有自动重试、自动恢复原before、服务/模型/运动命令、Native库/上下文导入或checkpoint/marker写入。

根预置条件
1. 当前实际boot/相机owner必须新鲜读回；GUI正常停止，全部其他writer（含不使用此锁的身份/轴/其他对话）均真正冻结。不得将旧a6d4/903c、1332/79866、25/26等历史观测直接填为current。
2. root正常停止届时实际相机owner，取得其fresh final；用原reader与原全history规则验证后，将真实验证结果按原字节存为只读receipt并记录SHA。不能复制或编辑checkpoint内容、复用已消费seed、删除marker或改变Native计数。
3. source unit仍是原六Native C/C++/object清单7cf7…，operator.so仍704f…，原Native Python222、operator7闭包完整。原单位定义证据在NATIVE_UNIT_PROVENANCE.json/FILES_VERIFIED.json；模板执行前会重新以文件SHA验证，不加载库。
4. 原六文件reference快照和after payload已准备并钉SHA；backup_dir必须在AURA外。原校验扫描AURA.rglob('*.py')，在AURA内放before.py备份会增加第223个源码成员。

合同与原reader归一化receipt
CONTRACT_EXAMPLE_DO_NOT_EXECUTE.json、ROOT_VALIDATION_RECEIPT_EXAMPLE_DO_NOT_EXECUTE.json只是格式示例，含显式占位符，不能执行。root应从fresh原receipt逐项映射，不得为使模板通过而填造status。
root_validation_receipt是原真实验证结果的归一化薄封装：schema=aura-camera-six-file-root-validation-1，status=ORIGINAL_READER_AND_HISTORY_VALIDATED，expected与contract完全相等，fresh_checkpoint亦相等；normal_camera_stop_confirmed、gui_stopped_confirmed、all_other_writers_frozen均须来自实际证据。original_reader_receipt钉原始原reader结果文件及SHA。本模板只核这份证据的字节pin，不重写也不代替原语义验证。
observed_mono_ns必须在板上原语义验证完成后取得，不能使用Windows monotonic或板墙钟。默认有效期最多60秒；中断后可以重新完成root前置检查并生成fresh归一化receipt，原始reader证据仍按实际pin保留。新boot、仍存活的source owner、服务cgroup有进程、Native库仍映射、C-unit/库hash变化、fresh final已消费或源owner不同均拒绝。
six_file_plan_sha256由 contract_plan_identity(contract) 计算：canonical JSON hash覆盖六目标/所有before-after与payload/reference pin、fresh seed、expected owners、freeze/lock pin、方向和backup路径，仅排除root_validation_receipt自身以避免哈希循环。归一化receipt须包含它，防止验证后换计划。
coordination_lock是root事先创建、全体协作writer约定使用的稳定锁文件pin；模板以fcntl.flock独占它。freeze_guard是root协调冻结后的稳定字节pin。锁不会自动冻结不遵守锁的其他程序，所以其冻结是强前置条件，不能仅凭锁获取成功推定。

精确变更边界
写集固定六路径：原ui_camera_service.py、camera-python-manifest.json、board_camera_ui.proposed.json、OPS/meta.json、native_entry_pan_face_v5.py、operator runtime-manifest.json。候选只能是v3 UI 7d4773…或回滚时原UI9d714…。
222成员集合和其他221项真实字节不变；APP源只改UI SHA常量；op7集合和其他6项（含Native source-manifest、so、settings、recovery/operator/rollback代码）保持；proposed config只改Python manifest SHA和本次fresh seed；meta只改candidate UI pin及UI/manifest/config三项protected pin。checkpoint_output目录与原Native前驱库/297…→7cf7…正式loader合同保持。
外层face-source-v17 entry、其11项manifest、camera_wrapper和service argv均不变。GUI及selected source-count/owner不在此写集内，由root在新owner恢复后按届时真实状态重建，不固定25/26。

两阶段文件提交
prepare先核全六before/payload，独占创建0700 backup目录；将六原字节和六after副本分别O_EXCL写入/fsync，再写不可覆盖PLAN。每个目标同目录创建唯一.stage文件（不以.py结尾），保留uid/gid/mode并fsync。全部原备份/after副本durable之前绝不替换目标。
commit每项前重新核lifecycle/freeze、全六当前SHA向量，并紧邻rename核目标SHA与inode/大小/mtime/uid/gid/mode；写独占intent/fsync，原子os.replace，再fsync目标目录和独占done收据。全部六after和闭包通过才写committed收据。
这是冻结writer条件下的应用层SHA/inode CAS加内核atomic rename，POSIX并没有任意digest-CAS原语。不能声称可防住一个忽略冻结、在最终CAS与rename间主动写同一文件的root程序；发现不受控writer时必须先协调冻结。

显式已知字节恢复
--recover读取原durable PLAN，要求合同完全匹配、六before/after备份均按SHA验证、残留stage只能是其已知after字节。每个目标只允许原计划before或after；任何unknown target/stage都会拒绝，绝不覆盖/清除未知字节。缺失stage可从durable after副本O_EXCL重建；然后仅完成到同一after。旧收据和before备份不覆盖。
若中断发生在全部备份/PLAN写完以前，目标尚未改变；没有PLAN时模板拒绝恢复，root审阅后可保留这个未提交目录并另用新唯一事务目录。模板不会擅自删除它或盲目重试。
root先运行同合同默认dry-run，必要时 --recover dry-run检查混合状态；确认后才显式加 --apply。若lifecycle receipt在提交中超期，保留已知混合状态，完成fresh前置检查/receipt后再显式 --apply --recover，不放宽年龄或Native规则。

安全回滚
safe_rollback_payload(original_six,fresh_pin)只用原six代码/原222manifest生成after：proposed config的seed换为本次最新fresh pin，meta对应config保护SHA重算，其他原字节保留。它不会将原备份中含旧c6或其他旧seed的config/meta直接恢复。
若新owner已经启动或消费了发布前final，必须先正常停止该新owner，取得它的最新final并重新跑原reader/history验证；new fresh pin必须归属于这个实际停止的owner。模板的owner/boot与marker检查也会拒绝旧已消费前驱。
rollback方向合同还必须钉 rollback_predecessor_plan（原发布durable PLAN）。每个rollback-before只能是该原计划已知before/after，且original_reference必须对应原before备份。不能将一个新发现的未知hash贴为before便覆盖它。rollback本身有独立新backup_dir/新after/新归一化receipt；若中断，再对这份rollback合同进行同样 --recover 完成，不回放更早seed。

本地验证
test_six_file_transaction.py使用camera目录内生成的隔离临时文件，不调用目标CLI/live_guard；10项通过：正常全备份、备份中断无目标写、staging中断、第三次替换中断显式恢复、unknown before、途中unknown writer、unknown stage均保留、回滚原代码+freshseed和meta一致、root attestation计划身份绑定、rollback-before必须是原已知字节。目标Linux生命周期/文件布局与原reader归一化适配尚须root审阅并dry-run，本交付不宣称已部署或已测CPU收益。
