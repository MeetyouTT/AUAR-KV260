# 原生三模型路径：真实推理与业务切换

**新版已实际承接板上相机业务；不再只是候选编译。** root按用户最新要求单终端串行完成，未启动其他代理。当前为`native-live-r4-dc4602e2b2b7398c`，boot`a69299ef-17d0-446f-a0df-56c0a08cd2fb`，camera2174/GUI2206/X1075。

YOLO与YuNet已持续使用DPU，SFace同一原生仲裁下的DPU后端ready。SFace已通过隔离真实模型输出对照，并在180秒业务窗口新增完成46次真实请求。三模型短业务负载通过，**身份精度与更长稳定性仍未验收**。界面进程active/main/IDLE_READY，未主动开麦或播放。

## 实际验证

- 两组相同公开合成输入，旧、新YuNet四头及SFace原始INT8输出逐字节一致；6对比较/16次执行API均确认完成且释放。YOLO两组均为空输出，相同但不能证明非空人体框精度。首次boot对照通过；第二boot的一次旧基准被准入/结果TTL拒绝、已确认关闭。修订为“旧参考先执行、再用真实YOLO建立原100ms窗口”，22项工具检查及第二boot真实对照通过。30ms/5ms/100ms没改，不重试在途或未知作业。
- 60.2647秒真实业务窗口：YOLO9.9395Hz、新primary超限0、optional超限0、结果gap0；SFace新增0。启动和此前失败的primary累计2另保留，没有清零。
- 180.841秒窗口已通过：YOLO9.9369Hz，新增SFace完成46次，新primary/optional超限及gap均0；结果见`final-window.json`。只在同PID累计增量比较，不用累计健康平均掩盖startup耗时，也不将无SFace请求的窗口当满负载。
- 首段15.075秒当前资源点测：整板CPU62.9536%，camera33.2833%/GUI23.4990%/X3.6981%整板；DPU任务busy5.0%、205驱动命令。当前捕获约24.6Hz，旧基线曾约12.5Hz，非相同输入负载，不能声称CPU改善或固定加速比。随后另一15秒点测CPU64.2422%、DPU busy约5%，该段SFace64→64无新增，不能称三模型同时负载。两次统计均已关闭，真实帧推进时计数不再增长，cleanup timer inactive。
- 单一DPU owner实查仅PID2174；当前DSO确实映射到该相机进程。身份配置398ece…与INT8库ee22b…保持。原unit297…及旧覆盖未改，仅添加本任务拥有的启动条件/执行覆盖。
- r4软件：67业务/迁移/真实enabled统计/打包启动检查全过；原237项235通过、2私有ELF跳过。另维护控制16项、修订等价工具22项通过，C++/C ABI沿用已通过的20/8/5＋SAN与12项真CDLL/fake依赖验证。不同套件重复覆盖不相加为独立业务场景数。

## 两次受控重启与失败修复

1. 原boot008f3e1b…的YuNet5fault/4恢复、SFace3fault/2恢复均LATCHED，完整数字prefix归档。第一次维护重启到89760db2…，原服务正确隔离、对照通过。
2. 首次业务启动因包中只含Python、漏带ByteTrack LICENSE/upstream_manifest失败。补齐两份原SHA附件，并在native marker消费前校验；跟踪器移至native接管/业务worker前初始化。旧失败和已消费marker保留，不删除后重试。
3. 第二次受控重启到a69299ef…。旧比较工具把参考执行/同步journal放入当前准入窗口，一次准入/结果TTL拒绝并安全关闭。旧报告未保存完整拒绝Report，因此不能进一步证明具体拒绝阶段或断言该次绝未提交；以“拒绝、未超cap、确认关闭”记录。修订顺序后真实对照再次通过。一次systemd-run启动客户端8秒超时后unit仍运行，未重复启动或kill，取回完成结果确认通过。
4. r3业务启动后，新增metrics名称未加入生产STAGES；一次正常primary拒绝的统计又把计数当作duration，ValueError导致YOLO线程退出。r4注册四个native时长项，primary拒绝改独立计数，并用真实enabled PipelineMetrics＋实际UI循环补回归。此前mock仅记录字符串未覆盖此缺陷。
5. r3正常SIGTERM导出精确seal checkpoint后退出，主周期1/迟到1与旧归档链承接到r4，在**同boot**修复，无第三次reboot、无清恢复预算。初次观察任务在启动控制器仍持锁时被拒，未做任何推理/计数变更；控制器结束后重新启动实际60秒窗口。

## 运行与回退

实际源码`/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura`，库`/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/libaura_native_v2_candidate.so`，SHA c675ba69…保持。222 Python＋ByteTrack两个运行附件共224文件。控制器`/home/root/aura-native-live-20261024/ops/be72669aa53de735/boot_ops.py`。

相机`Restart=no/SendSIGKILL=no/KillMode=process/TimeoutStopSec=infinity`，native入口在完成未知或生命周期不明时保留整个owner进程。未知完成不能靠systemctl kill/timeout或删除锁文件换owner。marker按kernel唯一、同boot精确checkpoint只消费一次，新kernel旧历史单独归档；归档hash链接承接后续checkpoint。

旧码回退命令为`python3 -B .../boot_ops.py --root ... rollback`。控制器先要求owner未fenced，正常关闭、精确checkpoint和旧PID消失后才启旧码；旧码保持两个optional LATCHED并承接累计，不能把回退当解锁。回退hook已软件实跑核验；**本轮没有为演练而停掉当前工作版再实际切回旧码**，真实回退动作尚未验收。

当前还不是长期根治结论：SFace真人持续请求/精度、长尾统计置信度、持续对话与音频、多人与严格同输入CPU/DPU收益均待验。两次软件reboot验证了kernel边界迁移，实际断电冷启动未执行。旧fault、两次部署失败和基准失败都留档，不能用新counter域零值称历史故障消失。
