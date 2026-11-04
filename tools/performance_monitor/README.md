# AURA 双端性能监视器

在 Windows 上同时查看本机模型服务与 KV260 板卡的性能。Windows 与板卡保持同屏，支持最近 60 秒趋势、进程和服务查询、排序以及任务详情。

## 可以查看什么

| 设备 | 观测内容 |
|---|---|
| Windows | 整机与进程 CPU、工作集内存、WDDM GPU 与专用显存、NVIDIA 整卡状态、进程与服务。 |
| Windows 模型服务 | 项目 Ollama、27B 语言模型、OmniVoice、请求宿主、GPU 调度、排队与完成计数。具体状态取决于项目健康接口。 |
| KV260 | 整机 CPU、内存、运行时间、进程与 systemd 服务，以及项目功能对应的进程组。 |
| KV260 项目 | 相机、YOLO/YuNet/SFace 调用速率、角色界面帧率、音频前端、聆听、播放、转轴跟随和分段耗时。具体字段取决于板端接口。 |

## 运行条件

- Windows 10/11，Python 3.9 或更新版本，安装时包含 Tcl/Tk。Python 代码只使用标准库，无需 `pip install`。
- Windows OpenSSH 客户端可通过 `ssh.exe` 调用；板卡已有 SSH 公钥登录，并且主机指纹已核验。
- 板卡有 Python 3、Linux `/proc`；服务列表使用 systemd。采样代码经 SSH 标准输入运行，无需在板卡另装监控服务。
- NVIDIA 整卡指标需要已有驱动提供 `nvidia-smi`。缺少该命令时，其余指标仍可使用。

工具本身不需要 Vivado、模型权重或 Codex。未连接板卡时，Windows 侧仍可观测。

## 启动

在本目录双击 **打开性能监视器.cmd**，或打开 PowerShell 执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_model_dashboard.ps1
```

如果 Python 没有加入 PATH，显式指定解释器：

```powershell
.\start_model_dashboard.ps1 -VoicePython 'C:\Python312\python.exe'
```

要监视已经部署的 AURA 项目，传入包含 `aura` 子目录的原项目根目录：

```powershell
.\start_model_dashboard.ps1 -ProjectRoot 'E:\Win共享文件\语音共享文件' -VoicePython 'C:\Python312\python.exe'
```

`-ProjectRoot` 用于识别该项目的 Python 进程，并读取 `aura/config/board_dialogue_model.json` 中的模型名。启动器也可复用该项目 `model_inference.local.json` 中已有的 `voice_python` 路径。工具不会修改这些配置。

没有原项目目录时，可以单独运行本工具。若需判断项目模型驻留状态，将 `aura/config/board_dialogue_model.example.json` 复制为同目录的 `board_dialogue_model.json`，把 `model` 改为自己项目的 Ollama 模型名。缺少该配置时，模型归属相关状态可能显示未知。

也可直接运行 Python：

```powershell
$env:AURA_MONITOR_PROJECT = 'E:\Win共享文件\语音共享文件'
python -B -X utf8 .\aura\tools\model_runtime_dashboard.py
```

F11 进入全屏，Esc 退出全屏。重复启动会显示已有窗口。“暂停显示”冻结画面，但采样继续运行。

## 连接 KV260

将 [SSH 配置示例](config/ssh_config.example) 合并到 `%USERPROFILE%\.ssh\config`，替换板卡地址、账号和已有私钥路径。采样器使用的 SSH 别名是 `aura-kv260`。

在终端先确认主机指纹并建立自己的免交互连接，然后检查：

```powershell
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes aura-kv260 "python3 --version"
```

界面显示“未连接”时，先检查网线、地址、SSH 登录和主机指纹。SSH 断开后会清除上一连接的采样基线，避免把旧指标当作当前数据。关闭窗口会结束本工具的 SSH 采样会话。

## 项目接口与适配位置

| 位置 | 当前读取来源 |
|---|---|
| Windows | 11435 `/api/ps` 为项目 Ollama，11434 `/api/ps` 为其他 Ollama，8797 `/health` 为模型宿主；8791/8792/8795 用于标识历史服务。 |
| KV260 | 板内 8783 `/api/state` 为界面状态，8790 `/health` 为相机状态；通过 SSH 在板内访问。 |
| Windows 配置 | `model_runtime_dashboard.py` 中的 `TASKS`、`Sampler.sample()`、`local_json()`。HTTP 地址白名单为本机回环与项目主机地址 `192.168.50.1`。 |
| 板端配置 | `runtime_board_monitor.py` 中的 SSH 别名，`runtime_board_probe.py` 中的接口和进程角色映射。 |

这些项目专用接口不是通用设备自动发现协议。换端口、网段或业务版本时，需要相应适配。接口未提供或返回 403 时，界面显示未知或遥测受限；不会发起推理以补齐指标。

## 指标口径

- 两端 CPU 的 100% 均表示整台设备的全部逻辑处理器容量。首次采样、设备重启或进程身份变化后，需要新的有效差分样本。
- 任务组优先划分模型工作进程，再划分宿主进程；共享工作线程不重复叠加进程资源。
- 内存为工作集/RSS；不同进程的共享页面可能重复计入。
- Windows 任务 GPU 使用该组最忙物理引擎的占用；整卡指标来自 `nvidia-smi`，二者不直接相加。
- 板卡视觉调用速率、界面帧率来自项目计数差分，不代表 DPU 硬件利用率。
- `—` 表示该指标不可取得。端口监听、进程存在、模型驻留与“正在推理”分别判断。
- 健康请求往返耗时、上次 GPU 排队等待和模型实际推理耗时分别展示。

## 检查与导出

在本目录运行原有回归检查：

```powershell
python -B -m unittest discover -s .\aura\tools -p 'test_*runtime*.py' -v
```

导出三次实际采样（结果默认保存在已忽略的 `aura/output`）：

```powershell
.\start_model_dashboard.ps1 -Snapshot -ProjectRoot 'E:\Win共享文件\语音共享文件' -VoicePython 'C:\Python312\python.exe'
```

也可通过 `-SnapshotPath` 指定 JSON 输出路径，或用 `-Screenshot 'C:\Temp\aura-monitor.png' -CloseAfter 20` 截取本工具窗口并自动关闭预览。`-View` 可选 `overview`、`windows`、`board`、`inventory`。

## 数据与源码

默认只读取系统资源与白名单状态字段，不发送生成、预热、加载或卸载请求，不启停业务服务，不操作电机，不读取对话原文、音频、身份模板、业务数据库或模型权重。趋势保留在本工具进程内存中；快照和截图仅在显式指定时落盘。导出的快照包含进程名、PID、服务和资源指标，应按自己的分享范围处理。

本目录包含四个运行模块、两份原有检查、启动器与配置示例。运行模块来自现有双端监视器；公开副本为项目根目录增加了 `AURA_MONITOR_PROJECT` 环境变量入口，其他运行逻辑保留。[源码清单](SOURCE_MANIFEST.json) 记录原始与公开文件的 SHA256；[本次验证](VALIDATION.md) 记录发布前检查。
