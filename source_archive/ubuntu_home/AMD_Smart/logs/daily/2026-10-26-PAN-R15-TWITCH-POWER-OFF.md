# 真人抽动/延迟失败、r15修复与断电交接

用户返场同意小步恢复1420参考。旧manual仅1445..1465，与STOP1402不兼容；本轮新增明确用户在场1402..1420窄manual profile，不扩大PL1400..1600。manual_release.py仅加入此窄授权choice并按真实observed predecessor bounds校验，7项过。两次执行前置参数/依赖路径错误均在终止manual owner/写运动前拒绝：缺output、缺driver_root导入；保留失败。补齐后完整预检通过，复用已有每段2秒≤5us bench，使用batch读回串行1402→1407→1412→1417→1420，四段成功/STOP1420，手动后端正常释放/重连，camera/UI未重启。用户确认“看到小幅移动，已经停住”，不是新机械零位或外部波形标定。

第一次r14/v17真人30秒全inside、0COMMIT/0target变化、8预ARM；用户“重新来”后做第二次30秒（actual控制28.036s），左右都触发234ACK/99target变化/14ARM，range1402..1449，最终1426 flags0 lease0 epoch1145 ack5。用户反馈“舵机有抽动，有延迟响应…整个审查”，明确实体失败。child有有限30s duration，结束恢复原face config与startup pins；不是留下无限无人跟随。

取完整数值轨迹并过滤GUI开测初段上一轮同r14旧报告（6旧/空snapshot），当前28事件完整=14ARM+14STOP，STOP5horizon/4submission/3lease/1ticklate/1operator。重建220/234命令，其余14因bounded live trace缺失，不能冒称全波形。新源间隔中位81/p95114/max7695ms，图龄71/p95124，锚龄240/p95367/max490；7.7s空档无合格face，不能延长旧源许可。10/14段可用完整ACK前缀证明firsttarget提交，ARM→提交起点197..338ms/中位256；第一右越线接收→首提交268、对应捕获→首提交363ms，非机械首动。当前jerk800/acc100从静止到0.5us舍入阈值理论下界155.763ms，不包括确认/输入/tick/PWM/机械死区。

明确r14软件反例：COMMIT10.000、真实硬截止10.230、源截止10.250，ACK快照后Python暂停25/80ms，旧外层用laternow+cachedlease虚构逾期STOP。真实本轮last报警仅超0.68031ms，是排查依据但缺原采样时刻，不能断言现场2次postguard都假。r15疑似越期只fresh read一次，严格核对owner/epoch/ack/target/flags/lease与原deadline，真实过期/IO错误/无法证明仍STOP，不重COMMIT/不续期。14新增driver回归＋8paired过。

另一实测缺口：主控制线程publish最大57.868ms、轮101.135ms，触发CONTROL_TICK_LATE。r15新增latest-only后台文件writer；主线程只生成不可变有界JSON，最多1 pending；STOP先于close/join，writer确认退出后才最终同步proof。初稿显式finally close覆盖controlerror的反例已独立复现并修复close_after_stop，9writer行为检查过。整合138主机回归通过。

KV260无动作隔离8组driver模型通过；17710B同报告12对文件对照主线程中位5.777→2.624ms、max22.279→12.881，另注入50ms慢写main submit0.087..0.156ms。只说明PS写入成本隔离，不是实体平顺/机械延迟改善。最终r15配置切换24control/11source/259GUI pins通过、oldr14收据有效、STOP1426，camera720342/GUI772087和原计数保留，无新ARM/COMMIT。manifest c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de；前r14 d7bdb957…保留。

用户于主机UTC约15:19报告断电，立即停止所有UART/板卡/运动尝试；本地确认没有run_board/transfer进程仍在运行。没有取得断电后的新checkpoint，不把旧16a07283 boot/1426参考直接迁到新boot。r15尚未真人测试。物理位置断电后未知；只读音频观察/事件记录器无法承诺跨断电继续，恢复后重新核对owner和运行状态。

下一步先新boot/板身份/固件FDT/DPU唯一owner/故障历史/STOP/当前位置，恢复有限无输出连接。再用固定小幅轨迹与真人同条件对照区分执行链路和视觉控制；需要实测画面位移/脉宽、最小可见步长、左右行程，不能把DS3230商家3us死区/180°和GPIO lastwidth当机械量测。OneEuro/Ruckig已有，优先消除误停/IO抢占再调标定后的增益、起步和提前减速，不堆滤波或盲加积分/过期预测。

完整分析、代码/指纹、主机与KV260回执、真人失败与断电边界见[共享r15复核](/home/ghmd/Win共享文件/协作任务/2026-10-26_抽动延迟全链路复核_r15/README.md)。Windows接收/运行/实体验收未代写，未共享图像、身份库、录音、权重或原始UART。
