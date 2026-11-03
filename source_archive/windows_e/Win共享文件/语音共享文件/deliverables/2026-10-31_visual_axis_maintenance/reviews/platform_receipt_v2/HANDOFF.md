# 实板只读回执核对与V2路径纠正

**本次最新有效证据确认：正在加载benchmark B4096，VART也指向benchmark；不能开启转轴。** wide四件固件在盘上匹配，独立控制器25项及手动3个payload均匹配。三项UNAVAILABLE来自V1探针的目录推导错误，不能据此宣称驱动文件缺失。

本窗口只核查本地源码、固定枚举投影和离线候选。未导入运动驱动、访问设备/模型、写寄存器、切固件/VART或重启任何服务。角色动画继续由原窗口维护，GUI/控制器R2候选未改、未部署。

## 新回执及已确认边界

主窗口保存的`root_platform_readonly_v24_1793522299017286000.json` SHA256：`18de8abae51cb20911051ebf8026fb82bdd190378b02205065bb74afaf064f9e`，本地逐字节核验通过。主窗口预先核验了冻结的V1 script/policy，回执为ROOT_READONLY_EXECUTED。

| 项目 | 本次结果 | 能说明什么 |
| --- | --- | --- |
| owner/startup/固定上下文 | 前后匹配、同owner、平台稳定；观测有效 | 该244.131ms只读轮次上下文可对应；后续变更前仍须现读 |
| 原业务守卫 | 前后PAUSED、mic=false、playing=false；运动/服务命令0、生产写0 | 本轮没有改变v24业务范围或启动运动 |
| 实际加载固件/VART | BENCHMARK_B4096/BENCHMARK_B4096，operating=true，exact-wide=false | 是本次新实测；operating不代表VSRV/wide可用 |
| wide文件 | shell/xclbin/dtbo/bit四项MATCH | 成套文件在盘上，不表示已加载 |
| GUI/配置与独立控制器 | GUI before及清单匹配，控制器25项全MATCH | R2的实际before基线已闭合，三源码候选不需因本回执改动 |
| 手动release | 清单及其3个payload全MATCH | 与独立固件driver目录分别核对，不能相互替代 |
| 当前绑定 | manual boot=false、FDT=false、direction boot=false | 当前启动配置资格不成立；只改boot不会解决平台/FDT/实体参考 |
| effective face配置 | 引用清单匹配true | 有效引用内容可对应，不代表该旧启动配置现在可运动 |
| 当前实体位置/方向 | reference、direction、angle、driver register build均null | 没有位置或角度新证明，不用旧wide1500填充 |

该脚本只核对固定46项及owner/startup，没有再次扫描全部380组件；先前全380核对另在ec254190…投影中保留。最新回执没有改变v24部署或真人验收结论。

health两次同相机上下文通过：相机/检测/身份error_present=false、身份ready=true/backend=DPU_SFACE_INT8；脸worker故障0，YuNet/SFace native_failures均0。primary_period_overruns累计5、窗口增量0，必须保留历史5；身份processed增量0不意味着识别故障，也不证明识别准确。该短轮次不是长期或机械验收。

## 三项UNAVAILABLE的纠正

**V1错误由本窗口引入。** V1按`candidate-manifest.json`同目录推导了driver文件，实际打包器使用`driver/`，`validated_context()`也校验该子目录并返回它。原冻结脚本、policy、28项测试和实机回执全部保留；V2另存，不修改旧包。

| 原index | V1请求位置 | 正确契约位置 | 正确位置现场结果 |
| --- | --- | --- | --- |
| 42 | `release-6a4b645a5bbfd35c/vsrv_driver.py` | `release-6a4b645a5bbfd35c/driver/vsrv_driver.py` | 未读/null |
| 43 | `release-6a4b645a5bbfd35c/libvsrv.so` | `release-6a4b645a5bbfd35c/driver/libvsrv.so` | 未读/null |
| 44 | `release-6a4b645a5bbfd35c/vsrv_transport.py` | `release-6a4b645a5bbfd35c/driver/vsrv_transport.py` | 未读/null |

前缀为`/home/root/aura-pan-wide-20261028/`。期望SHA分别仍为4f48ad87…、c21f7a90…、97f1ff27…，没有放宽校验。

依据链：[driver_layout_proof.json](evidence/driver_layout_proof.json)。从原bench按已有打包器的两处文本变换重建wide源码，得到SHA`c9e91f74…`，与固件清单及本次板端index45的MATCH一致。AST确认其第44行使用`driver = root / 'driver'`，第52行返回driver。只解析源码，未导入或执行bench。

## 可供主窗口复读的纠正包

[axis_v24_readonly_probe_v2.zip](axis_v24_readonly_probe_v2.zip)只含`run_readonly_probe.py`与相邻`probe_policy.json`，清单和SHA见[probe_bundle_v2_manifest.json](probe_bundle_v2_manifest.json)。主窗口选择新的独立目录放置这两个已核验普通文件，串行执行：

```sh
python3 -B run_readonly_probe.py
```

V2只更正3个指纹路径和策略revision；43项其余路径、所有期望SHA、boot/PID/birth/命令/startup、只读IO和输出规则保持。检查程序AST除冻结policy哈希常量外完全相同，沿用已验证的28项IO边界；新增6项布局/回执/假文件测试全部通过，复现了旧policy的3项UNAVAILABLE并验证新位置。没有重复R2的8项GUI＋41项控制测试。

原28项使用与policy一致的假文件系统，验证了IO边界，但没有独立证明打包目录，所以未发现这个路径错误。本次增加了板端已匹配源码SHA及打包器的独立布局依据，避免继续用policy自身作为路径正确性的唯一依据。

这仍是46项固定指纹＋3项手动payload的只读复核，不是三个路径一匹配就放行运动。V2尚未实板运行，正确位置存在性和字节匹配保持未验证；即使全MATCH，benchmark加载状态和当前启动资格仍需解决。

## 与视觉识别共存的下一步

具体分阶段顺序及失败停止条件见[COEXISTENCE_RECOVERY.md](COEXISTENCE_RECOVERY.md)，机器可读门槛见[RECOVERY_GATES.json](RECOVERY_GATES.json)。先补正确driver位置和当前相机源闭包证据，再由主窗口使用已有受控流程，正常释放/封存DPU owner、成套恢复wide/DT/VART、恢复相机并重新验证当前owner与SFace图库绑定。不能把本次health投影拼成Native检查点，不能重用旧1500或只改boot/FDT字段。

恢复后先保证无运动输出及新鲜人脸/识别数据，再由主窗口安排本次物理参考与方向核验和受控随动。运动锁只是匿名视觉连续性；SFace 0.85、图库版本/源龄、未标定声纹和个人权限保持原边界。登记/模板更新与主动随动先安排在不同窗口，不把现有手动路径的两枚举检查推定为自动随动也已具备完整互斥。
