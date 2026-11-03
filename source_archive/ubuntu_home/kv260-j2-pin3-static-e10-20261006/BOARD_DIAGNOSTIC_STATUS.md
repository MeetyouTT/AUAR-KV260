# J2.3/E10 板端固定电平诊断

2026-10-06 08:03 UTC：本固定电平诊断已停止并卸载，转为独立J2.3/E10连续PWM。此前用户实测固定低0V、固定高3.3V通过；实体目标J2.3/HDA12/SOM240_1 D20/E10，用户确认仅接仪表。当前PWM项目 `/home/ghmd/kv260-j2-pin3-pwm-e10-20261006`、BUILD `2a3aca85`，约50Hz/1.5ms、波形待实测。不扩大为原J2.1或全部FPGA硬件验收。

应用 `aura-pin3-static`、固件 `aura_pin3_static.bit.bin`，BUILD `3eaeabab`，boot `2a95bf6d-fea6-46e7-88aa-12f92eb40551`。加载、访问器SCRATCH、STOP、只读inspect均rc0、status4，PL0实际99999999Hz；period/pulse均9999900，RUN_FRAMES0、PULSE_US100000。内部低电平状态不代替实际测量。

## 操作与证据

- 原J2.1 STOP：`/home/ghmd/kv260-j2-pwm-continuous-20261005/evidence/20261006T071804.304364Z-uart-stop`，status4。
- 原程序恢复基线：`/home/ghmd/kv260-j2-pwm-continuous-20261005/evidence/20261006T071845.524169Z-uart-restore`，确认 `kv260-benchmark-b4096` 活动；之后没有START旧PWM。
- 上传：`evidence/20261006T071859.445791Z-uart-stage`，48帧/56683字节，SHA `225abede15ab10eebb1973a15276eee4718a6c69f670250b8f6f6e204cef3b7b`。
- 首次加载中断：`evidence/20261006T072131.616725Z-uart-load-idle`。仅PREPARE完成，随后串口出现FSBL System Reset、U-Boot SOFT reset，未收到EXTRACT结果。未安装或加载新程序，未卸载基线。复位原因未知，询问用户是否按过Reset尚未收到回答；不能归因于尚未运行的新PWM逻辑。
- 启动恢复：`evidence/20261006T072428.461238Z-uart-boot-inspect` 取消跨复位的残留未完整输入，确认实时U-Boot提示符并只读查询bootcmd；`evidence/20261006T072441.342126Z-uart-boot-resume` 执行默认boot，没有改写启动配置或烧写。终端控制字节造成新增恢复工具行首提示符匹配漏报，保留90秒超时原件；修正匹配，原始记录离线重放通过，见 `evidence/boot-prompt-parser-review.json`。
- 新启动只读状态：`evidence/20261006T072634.241017Z-uart-state`，新boot `2a95bf6d-fea6-46e7-88aa-12f92eb40551`，基线正常、dfx-mgr active，未访问MMIO。pstore空且无持久历史journal，复位原因未定位。
- 新会话归档：`evidence/20261006T072658.706402Z-uart-restage`，相同字节数/SHA，独立目录，未访问MMIO或改变PL。
- 加载成功：`evidence/20261006T072715.677046Z-uart-load-idle`，prepare/extract/install/unload/load全部通过，BUILD `3eaeabab`、status4、start_sent=false。
- SCRATCH：`evidence/20261006T072800.428569Z-uart-scratch`；STOP：`evidence/20261006T072835.747569Z-uart-stop`；inspect：`evidence/20261006T072907.133186Z-uart-inspect`。同一boot/BUILD/status4全部通过，控制台回显恢复。
- 加载后用户报告固定低0V：`evidence/20261006T073420Z-fixed-low-user-measurement.json`。START `evidence/20261006T073448.836198Z-uart-start` 与inspect `evidence/20261006T073508.847504Z-uart-inspect` 同boot/BUILD、status7，确认持续高；用户报告3.3V：`evidence/20261006T073633Z-fixed-high-user-measurement.json`。测量来源为用户万用表，触点未独立核验。
- 本程序STOP `evidence/20261006T075814.719275Z-uart-stop`、restore `evidence/20261006T075839.409366Z-uart-restore`通过，之后新PWM加载并START，记录见新PWM项目的 `BOARD_TEST_STATUS.md`。本程序不再活动；上述电压属于历史固定电平实测。

## 测量计划与限制

固定电平测试已完成，万用表黑笔J2 GND、红笔J2.3，用户低0V、高3.3V。下一步独立构建J2.3/E10 PWM，50Hz/20ms/高脉宽1.5ms，占空比7.5%，实际高低电平预期0/3.3V，万用表直流平均约0.25V；PWM周期和脉宽须由新位流的实际示波器测量确认。加载前0V未计入本诊断；旧J2.1低幅值原因仍未定位，也不能据此判断FPGA损坏。

## 更新文件

本目录：`PHYSICAL_CONNECTION.json`、`PREPARATION_STATUS.json`、`PIN_MAPPING_REVIEW.json`、`CURRENT_BENCH.json`、`README.md`、`BOARD_DIAGNOSTIC_STATUS.md`；新增 `scripts/uart_boot_recovery.py`，更新 `scripts/connector_mapping.py` 的板端状态字段。串口工具生成/更新 `CURRENT_BOARD_STAGE.json`、`CURRENT_BOARD_STATE.json`、`CURRENT_BOOT_RECOVERY_INSPECT.json`、`CURRENT_BOOT_RECOVERY_RESUME.json`、`CURRENT_SCRATCH.json`、`CURRENT_STOP.json`、`CURRENT_INSPECT.json` 和对应证据。旧连续PWM目录的 `CURRENT_BENCH.json`、`CURRENT_STOP.json`、`CURRENT_RESTORE.json`、`CONTINUOUS_VERIFICATION.json` 同步为停止/不活动。项目日志：`/home/ghmd/AMD_Smart/logs/daily/2026-10-06-J2-PIN3-E10.md`。
