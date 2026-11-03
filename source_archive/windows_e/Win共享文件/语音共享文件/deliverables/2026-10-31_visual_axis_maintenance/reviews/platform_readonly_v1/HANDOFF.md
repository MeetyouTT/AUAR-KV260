# v24下一轮只读平台核对

**已核验主窗口新投影，脚本已离线验证并可交主窗口串行执行；本窗口没有访问设备。恢复候选仍用R2，未部署或启用运动。**

## 新证据确认了什么

`evidence/root_readonly_v24_1793520246085075300.json`的SHA为`ec2541900e745d39941d940e396deae0d11e606321a70b5b494323d5d4005b89`，与主窗口提供值一致。该次投影确认：

- 同owner前后、380组件及GUI before指纹通过；camera229296/birth2474670、supervisor330179、GTK330183。
- PAUSED/enabled=false/mic=false；follow=false、manual=FAULT、pulse=null。
- 身份后端DPU_SFACE_INT8、ready=true、identity_error_present=false；声纹未标定。
- 固件/VART、实体位置、方向及随轴安装没有在该次验证；detector_error_present也是null，均保留未知。

本次不再把旧benchmark观察当作当前固件实测。新投影是其保存时点证据，不能替代脚本运行时的前后owner检查。v24保存的pan配置仍引用旧5515启动，这是已知配置边界；当前机械FAULT的完整现场原因仍需分项核对。

## 可执行材料

- [probe_bundle/run_readonly_probe.py](probe_bundle/run_readonly_probe.py)
- 同目录的[probe_policy.json](probe_bundle/probe_policy.json)
- 两文件包[axis_v24_readonly_probe_v1.zip](axis_v24_readonly_probe_v1.zip)；SHA与清单见[probe_bundle_manifest.json](probe_bundle_manifest.json)。

主窗口把这两个已核验的普通文件放入它选择的独立板端目录，保持相邻。**本目录没有传输、安装或SSH执行器。** 主窗口在该目录执行一次：

```sh
python3 -B run_readonly_probe.py
```

脚本只向stdout输出一份投影JSON，不自行落盘。主窗口可沿用既有脱敏回执保存方式。不要运行模板文件，也不要导入/运行待核验的`run_face_motion.py`、驱动、bench或Native库。若进程/启动已变，不改本冻结policy的PID/boot来“放行”；先由主窗口提供新的完整只读owner与版本证据，再另存新的核对策略。

## 精确检查范围

1. 固定v24 startup SHA、有效GUI配置SHA、GUI before与手动配置；三进程的PID/birth/命令哈希及boot前后检查。预检查不符立即返回CONTEXT_MISMATCH/UNAVAILABLE，后续发生变化则清空该轮观测并返回CONTEXT_CHANGED。
2. 只读`/proc/device-tree/fpga-full/firmware-name`、FPGA manager state、`/etc/vart.conf`、`/sys/firmware/fdt`及已知板卡CID。前后平台变化时返回PLATFORM_CHANGED，不拿变化前结果做资格判断。
3. 46个固定文件指纹：GUI运动来源与配置副本、有效GUI配置、手动配置实际引用的face配置和方向文件、控制器清单、固件清单、手动release清单、25个控制器清单项、4个wide runtime文件、3个固件driver文件及context validator源码。
4. 手动release清单字节匹配后，再按该已固定清单的3个payload哈希核对其独立目录中的libvsrv/driver/transport。未匹配清单时不跟随该声明读取payload。
5. 两次已有的`127.0.0.1:8790/health`，每次超时0.8秒、正文有大小限制。仅投影相机/身份可用性与分别定义的计数；核对相机PID/boot及service/camera epoch一致，缺失、倒退、NaN/Inf、布尔冒充计数均不生成零错误或有效差值。

读取对象是固定普通文件与sysfs/proc元数据。符号链接叶节点、字符设备和未列入策略的路径被拒绝；文件和总读取有字节预算。脚本只使用Python标准库，不导入被核对源码、MMIO/VART驱动或模型，不开新相机，不获取face-stream，不发服务命令、寄存器写、信号、绑定更新或运动命令。错误仅为固定枚举，不输出异常文本、路径内容、媒体、姓名、个人ID、向量或模板。

有效face配置与GUI树中的face配置副本分开检查：真实入口由`pan_manual.local.json`里的`face_follow_config`指向旧gui-wide-v1配置。副本匹配不能替代有效引用匹配；有效引用缺失也不会阻止本轮独立读取当前固件/VART信息。

## 如何读输出

- `READONLY_OBSERVED`只表示该轮既定检查有结果，不是“READY”。`motion_qualified`固定false。
- `files`用固定role和数字index列出MATCH/MISMATCH/SIZE_MISMATCH/UNAVAILABLE/NOT_REGULAR/BYTE_LIMIT等。index到固定路径和SHA的对应关系在[probe_file_index.json](probe_file_index.json)，stdout不回传文件内容或任意路径字符串。
- `platform.firmware_kind`与`platform.vart_kind`仅按本次读值返回WIDE_V1/BENCHMARK_B4096/OTHER/UNKNOWN；`vart_exact_wide`另按驱动要求的完整字节比较，空格归类相同不等于精确配置通过。
- `bindings.manual_boot_matches_current`、`manual_fdt_matches_current`及`direction_boot_matches_current`只说明文件绑定是否匹配，不证明实体位置/方向。旧标称1500从未作为当前位置输出。
- owner或平台变化时`observations_valid=false`，平台/文件/health观测清空，不复用部分成功值。读不到的字段保持null/UNKNOWN。
- 该脚本不获取聆听UI状态，输出`listening_state=NOT_READ_BY_THIS_PROBE`；PAUSED由主窗口既有状态投影确认。它也不获取实时脉宽、运动寄存器build、实体角度、方向、声纹授权或当前识别阈值，这些字段保持null。

## 下一阶段门槛

| 阶段 | 要求与仍保留的边界 |
| --- | --- |
| 本轮上下文 | policy、startup/有效GUI配置、前后owner及平台稳定；任何变化先重新取证 |
| 固件配套 | 当前加载WIDE_V1、operating、精确wide VART及成套文件匹配；若本次确认为benchmark，才据新证据安排主窗口已有的受控释放/成套恢复流程 |
| 控制器与驱动闭包 | 25项控制器及其清单、固件与手动payload独立通过。R2新release计划仍为26项，不改冻结旧清单 |
| 当前启动资格 | 重新建立本boot的FDT/方向/相机安装、有效停止参考和STOP收据；不靠改boot字段、加载复位1500或旧用户方向记录代替 |
| 视觉识别协作 | 新鲜同目标像素与实际脸源推进、两帧确认、250ms图像/500ms检测锚门槛、丢脸停止与目标更换需新会话；识别结果单独按源龄、图库版本、0.85阈值检查 |
| 实物与用户体验 | 主窗口统一安排水平回正、范围、停止及识别取样效果。镜头居中不保证脸正面/清晰，不表示生物身份或个人权限已确认 |

如果本轮文件/health全部匹配，也不能跳过当前启动资格与实物门槛。`identity.ready=true`只表示后端可用，未标定声纹限制与原个人权限策略继续保持。

## 离线验证

[28项脚本测试通过](evidence/probe_tests_v1_final.json)，覆盖只读IO面、固定路径、策略篡改、字符设备/链接拒绝、前后owner/平台变化、有效配置与副本区分、隐私过滤、缺失/倒退计数、HTTP错误及字节预算。只使用假文件系统和mock HTTP，未执行实板脚本；早期24项和27项结果保留。

R2的8项GUI＋41项控制结果及源码包原样保留，没有因本轮投影或脚本重复执行这些未变的依赖测试。复跑新脚本测试：`python -B tools/run_probe_tests.py --label probe_recheck`。

当前恢复候选仍见[上一轮R2交接](../v24_compatibility/HANDOFF.md)。本次只新增只读核对材料，不修改GUI/控制器候选、生产源码、相机、记忆/common或冻结发布器。
