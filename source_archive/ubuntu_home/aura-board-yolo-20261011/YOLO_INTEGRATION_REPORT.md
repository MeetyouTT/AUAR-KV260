# KV260 YOLO 实时人体检测接入报告

日期：2026-10-11。用户确认上一版相机预览流畅后，要求接入 YOLO。本轮已在现有 KV260 上完成 YOLOX-Nano / B4096 DPU、真实 USB 相机及 GTK 界面的接入；最终真人入镜检出 1 人。当前启用 COCO `person` 类，互动及放大画面显示人体框、置信度、轨迹编号和人数。用户未指定其他类别，采用项目人体检测基线。

## 实现与改动文件

| 文件 | 改动及作用 |
| --- | --- |
| [yolo_dpu.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/yolo_dpu.py) | 新增模型/配置/库 SHA、XIR 输入输出及实时 DPU 指纹校验；原生推理调用、人体筛选、去重和推理实例锁；提供框架插件工厂 |
| [yolox_bridge.cpp](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/native/yolox_bridge.cpp)、[build_yolox.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/native/build_yolox.py) | 新增 Vitis AI 3.0 YOLOvX C++ 桥接及板端原生编译入口；板上构建的 `libaura_yolox.so` 已回读保存 |
| [ui_camera_service.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/ui_camera_service.py) | 接入独立 DPU 检测、启动自检、人体轨迹和状态；复用独立采集/预览，目标选择提交前重查期限和轨迹代次 |
| [board_camera_ui.json](/home/ghmd/Win共享文件/共享文件夹/aura/config/board_camera_ui.json)、[CPU 回退配置](/home/ghmd/Win共享文件/共享文件夹/aura/config/board_camera_ui.cpu_yunet.json) | 显式启用 YOLO 并固定依赖，保留原 YuNet 配置 |
| [board_avatar_gtk.py](/home/ghmd/Win共享文件/共享文件夹/aura/tools/board_avatar_gtk.py) | 放大窗口根据 `count_kind` 显示人数/人脸，避免沿用人脸标签 |
| [相机服务单元](/home/ghmd/Win共享文件/共享文件夹/aura/scripts/board_camera_ui/aura-camera-ui.service)、[启动目录](/home/ghmd/Win共享文件/共享文件夹/aura/scripts/board_ui_startup) | 更新后端描述及启动配置、单元、组件 SHA 清单 |
| [test_yolo_dpu.py](/home/ghmd/Win共享文件/共享文件夹/aura/tests/framework/test_yolo_dpu.py)、[测试图说明](/home/ghmd/Win共享文件/共享文件夹/aura/tests/fixtures/vision/README.md) | 新增 8 项验证与固定人体图，覆盖错误依赖、坐标、无效输出、重复框、人数上限、过期/异常和轨迹再现 |
| [package_board_avatar.py](/home/ghmd/Win共享文件/共享文件夹/aura/tools/package_board_avatar.py) | 补入新代码、原生库、配置、参考图、测试及文档；当前收集 904 文件，无缺失，未重建 217MB 素材包 |
| [BOARD_YOLO.md](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_YOLO.md) | 新增接入说明；同步 README、相机、触屏、框架状态及启动文档 |

执行依据为 ZIP 中当前实施方案、视觉手册的官方人体模型基线和最新项目日志。原 B03/B04 工作包编号仅作追溯；当前按用户安排由 A 负责视觉与 FPGA。当前统一 `runtime.kv260.json` 仍待总集成，本轮实际运行的是 UI 相机适配服务。

采集服务是 `/dev/video0` 的唯一使用者，配置 640×480 YUY2 / 30Hz，统一镜像 BGR。检测按 10Hz 预算消费最新帧；预览独立运行。C++ 桥接使用已安装库处理 letterbox、量化、DPU 执行、解码、NMS 和原图坐标恢复，Python 不二次缩放。人体阈值 0.3、额外人体 NMS IoU 0.45、最多 16 个目标。几何关联复用 A 固定 SHA 的 IoU 基线，轨迹编号不表示身份。

观测源超过 250ms 不再叠加框，超过 750ms 清空人数和目标能力；检测异常保持预览、明确显示错误。`ctypes.CDLL` 调用释放 GIL；不会自动切换成 CPU。`/run/aura-person-dpu.lock` 协调本项目的 DPU 使用者。

## 板端依赖与发布

- PetaLinux 2022.2 / aarch64 / Python 3.9.9 / OpenCV 4.5.2 / Vitis AI 3.0。
- 当前官方应用 `kv260-benchmark-b4096`，DPUCZDX8G_ISA1_B4096，1 CU、300MHz；实时与模型指纹均为 `0x101000056010407`。输入 INT8 NHWC `[1,416,416,3]`、三个 85 通道输出头。
- 使用板上预置 `/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel`，2127303 字节，SHA256 `def64abdeeccbd020cb651913ba907464c1a1786e30ba7d4aa077b601388950a`；prototxt SHA256 `371c5979ac0ec1558455e86459b498cbeaa50852c90b722c31712a84904db7bf`。
- 本轮另下载 [官方 KV260 模型包](https://github.com/Xilinx/Vitis-AI/blob/v3.0/model_zoo/model-list/pt_yolox-nano_coco_416_416_1G_3.0/model.yaml)，包 MD5 `a13348e3ffd758531989b5dccac3b794` 与清单一致。该包 xmodel SHA `8493a85c05caba4457eb646b030abc511a7cf6eab2695eb309b62b4864d80c44` 与板上预置文件不同；未替换板上模型，不将下载包的字节当作部署证据。本轮未训练、量化或编译新的神经网络模型。
- 原生库 27136 字节，SHA256 `14524ca6364f7ecab3464999a1f20271d9f3b13e80684859f6da1573caf6efa8`。板上原生构建并回读；依赖现有 Vitis AI / OpenCV / glog 开发库，没有安装系统依赖。
- [配套更新包](/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-yolo-update-0da0dc7f7289d5b7.zip)：128039 字节，SHA256 `14417489c66bd8aa1a66c819b4ee6e8eff3bc14c14691f0e97df5167d85a21b1`；32 个载荷及 manifest，含 26 个运行文件。
- 更新 ID `0da0dc7f7289d5b7`，启动 ID `40f5d358d1c0d7ba`。工作站 [发布清单](manifest.json) 和 [包回读结果](package_validation.json) 记录全部文件大小/SHA；42KB 增量传输仅复用板上 SHA 验证相同的种子文件。

部署目录 `/home/root/aura-yolo-20261011/update-0da0dc7f7289d5b7`，备份位于其 `backup/`。原运行根目录仍为 `/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009`。部署先核对旧文件/服务单元 SHA，备份后只停止自身相机与 GUI，安装、自检并启动；[管理脚本](manage_yolo.py) 的 `--phase rollback` 可按本包 SHA 恢复此前文件和两个单元。回退脚本已准备，本轮成功后没有执行回退。

本包依赖原有素材、触摸模块、Vitis AI 库、固定板上模型及 A 的固定关联代码，不是空卡完整镜像。旧 217MB 素材包未重建，不能单独代表本次版本。收集器源码已同步，完整重打包单列。

## 实测结果

[主机日志](host-framework-tests.log)：126 项框架测试通过；[目标板部署结果](evidence/20261011T115732.399537Z-deploy/status.json)：68 项软件测试、资源预检和启动预检通过。

固定图最终去重后检出 4 人体，黑图 0。最初原生库输出 6 个候选，查看参考图发现嵌套重复框，增加人体 NMS 后最终自检为 4。首次 24 次固定图原生测试中位耗时 7.35ms、P95 10.36ms；这是该固定图检测调用的耗时，不是实时链路总延迟。[原生测试证据](evidence/20261011T114921.591458Z-probe/probe.json) 保留初始候选结果，[最终自检](evidence/20261011T120839.771421Z-final/status.json) 记录去重后的结果。

同一 boot、接入前后各 120 次短采样，镜头当时朝向桌面设备：

| 指标 | 接入前 CPU YuNet | 接入后 DPU YOLOX |
| --- | ---: | ---: |
| 采样时长 | 10.54s | 9.42s |
| 实际预览 | 12.34fps | 12.66fps |
| 实际采集 | 12.52Hz | 12.53Hz |
| 实际检测 | 9.58Hz | 9.98Hz |
| API 已发布帧龄，中位数 / P95 | 206.5 / 305ms | 174.5 / 255ms |
| 采集出队到原生视频入口帧龄，中位数 / P95 | 74.35 / 129.17ms | 62.32 / 94.59ms |
| 相机进程 CPU，单核满载=100% | 125.8% | 65.1% |
| GUI 进程 CPU，同上 | 166.1% | 187.8% |
| 空画面样本 | 0 / 120 | 0 / 120 |

[接入前采样](/home/ghmd/aura-board-ui-design-20261009/evidence/20261011T110156.613986Z-preview-profile/preview-profile.json)、[接入后采样](evidence/20261011T115732.399537Z-deploy/profile.json)。结果支持本次短窗口内预览未出现帧率下降；采样不足以证明长期或所有场景表现。帧龄以 appsink 出队时间为起点，不是传感器曝光到物理屏幕的端到端延迟。30Hz/10Hz 是配置预算，不能当作实际帧率。

板端原生操作验证了放大窗口 960×550、返回、连续五次诊断且 GUI 不重启、设置保留。实际窗口 [主界面截图](evidence/20261011T115732.399537Z-deploy/main_screenshot.jpg)、[放大截图](evidence/20261011T115732.399537Z-deploy/screenshot.jpg) 对应当时桌面/人数 0 场景。该轮使用 XTest 按钮操作，没有重新验收真人手指触控。

最后追加 20 秒真实入镜观察：[watch.json](evidence/20261011T120839.771421Z-final/watch.json)。154 个新鲜状态样本无相机、检测或预览错误；同一相机 PID/代次下采集帧 7328→7579、检测 5135→5335、预览 7326→7578。最近实际检测调用耗时中位数 10.66ms、P95 18.85ms；这个指标包含适配器检测调用，不是全链路总延迟。

保存的 [同源实际相机图](evidence/20261011T120839.771421Z-final/real-positive.jpg) 已人工查看：有真人上半身，绿色 `person #45 0.75` 框。对应 `source_kind=actual` 快照人数 1、目标 CONFIRMED、DPU READY；图像与快照均为 camera_epoch `6703db36f45145aca88946333b0f6bb4`、frame_id `7327`、captured_mono_ms `50797627`。这证明真实相机的人体正向识别，仍不构成多人精度或身份验收。

## 运行保持与独立核验

最终 [状态](evidence/20261011T120839.771421Z-final/status.json)：相机 PID 370400，GUI PID 370411，监督进程 370403；两个服务 active/running/enabled、NRestarts=0。相机唯一占用者为 370400。boot ID 保持 `9223af18-5113-4486-822f-29ec94d03d3e`，service_epoch `935ee8298c7f481293bb51017a74ecbb`。音量 18%、非静音、全屏、非省电及本机 8790 连接保持。

本轮未重启整板、未重新加载 PL、未发舵机命令。显示/DFX 进程及显示服务、触摸自载配置、触摸模块的保护 SHA 检查通过；当前版本冷启动仍未验收。

[独立核验脚本](verify_evidence.py) 重新读取 9 个 UART 会话的 96 份响应，长度/SHA 均相符。其中 95 份成功，1 份为首次原生链接失败的保留证据；没有将失败记录当作通过。首次失败因缺少 `-lvitis_ai_library-dpu_task`，在补入链接库后原生构建和推理通过，初次探针未停止既有相机。5 个返回工件、32 个包载荷、26 个源码/板端运行文件 SHA、启动源码清单、服务状态及设置一致性通过。[核验结果](validation_final.json)、[主机验证](host_validation.json)。

## 仍待工作

- 多人、遮挡、远距离、低照度的精度和长期稳定性；现场手动目标选择验收。
- ByteTrack、身份识别、正式自训练/量化/编译模型，以及向统一视觉主服务交接相机和 DPU 所有权。
- 新版本整板正常启动/断电冷启动、实际面板端到端延迟；真实 ASR/VLM/TTS、PL 与机构联动仍按其他工作包验收。

当前可直接在屏幕互动页查看识别人数，点“放大画面”观察人体框；无需另开摄像头或推理进程。
