# Codex Windows 与 Ubuntu SSH 协作接入

Windows 通过原生 SSH 远程项目连接 Ubuntu 开发环境。Ubuntu 侧负责板端编译和部署，Windows 侧负责 27B 与 OmniVoice 模型接口和联调。本目录只用于一次性交换接入资料以及保留接入验证证据。

最新接入状态：Ubuntu 注册资料已完成，本机 SSH/Codex 验证已由用户确认，不重复安装或登录。UTC11:34:44.967–11:37:44.982 同窗抓包已对齐 Windows 三次探针，Ubuntu TCP22/SYN/SYN-ACK均0，Windows源为TUN的172.18.0.1，ready=false。结论和逐端口证据见 [TCP22入站与回包](Ubuntu_TCP22入站与回包.md) 及 `ubuntu-tcp22-paired-analysis.json`。当前排查Windows转发/物理出站及上游路径，不把Windows GPU准入不足混入SSH阻塞，也不重复部署已验收的板端r3补丁。

- [Ubuntu 接入提示词](Ubuntu接入提示词.md)：粘贴给现有 Ubuntu Codex。
- `windows-codex.pub`：Windows 专用公钥，可安装到 Ubuntu 开发用户的 authorized_keys。私钥留在 Windows 用户目录，不进入共享目录。
- `ubuntu-registration.json`：由 Ubuntu 返回的连接信息和主机公钥指纹；不包含密码、令牌或私钥。
- `windows-preparation.json`：Windows 密钥和准备状态。
- `windows-connection.json`：SSH 连接验证结果；仅配置好别名不代表验证成功。

Windows 已准备专用密钥后，使用本机 Python 运行 `connect_windows.py`，核对主机指纹，保留现有 SSH 配置并追加 `aura-ubuntu` 别名，然后只读检查远程 Codex、登录状态和项目目录。接入资料缺失或未 ready 时，脚本不写 SSH 配置。元数据不会作为本机命令执行。

SSH 实测通过后，在应用的 Settings → Connections → SSH 中添加 `aura-ubuntu`，选择 Ubuntu 返回的实际项目目录。确认当前应用可以访问远程项目和目标会话之后，再启用会话之间的任务传递。现有独立 Ubuntu 会话能否接续需实测；不能假定同账号自动同步。

共享目录不保存 auth.json、私钥、大语言模型权重或 Ollama 模型数据。此接入任务不修改板卡运行服务、FPGA、摄像头或机械控制。

依据：[官方 SSH 远程连接说明](https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host)。Computer Use 的[操作规则](C:/Users/35870/.codex/plugins/cache/openai-bundled/computer-use/26.1023.51421/docs/guidance.md)禁止自动操作 ChatGPT 桌面应用 UI，因此应用内添加连接由用户完成；命令行侧配置和 SSH 验证由 Windows Codex 完成。
