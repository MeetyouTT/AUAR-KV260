# Ubuntu Codex SSH 远程协作接入

请为 Windows Codex 接入当前 Ubuntu 开发环境准备原生 SSH 远程协作。本次先完成连接准备，暂不覆写或重启板卡。

1. 查明当前 Ubuntu 的用户名、可从 Windows 访问的 IP、SSH 端口、实际项目目录，以及 codex 的路径和版本。确认该用户已登录 Codex；不要输出或复制登录令牌、auth.json、私钥。
2. 检查 SSH 服务。必要时在现有权限范围内安装、启用 OpenSSH Server，保留已有配置和其他用户的访问方式。不要关闭现有会话或更改网络拓扑。
3. 在 Windows 共享目录中找到 `协作任务/2026-10-30_Codex跨机协作/windows-codex.pub`，将这份公钥去重追加到当前开发用户的 `~/.ssh/authorized_keys`，设置正确权限。如果公钥尚未出现，先完成其他检查，等待 Windows 侧准备；不要自行生成另一份 Windows 密钥。不要开放 root 密码登录。
4. 确认 SSH 登录后的 shell 可以直接找到 codex。原生连接由 Windows 应用通过 SSH 启动服务，不要自行把 app-server 端口暴露到局域网。保留当前登录凭据，不把 auth.json 放入共享目录。
5. 将以下非秘密接入资料写入同一目录的 `ubuntu-registration.json`。临时文件写完后原子重命名，避免 Windows 读到半个 JSON。不要覆盖 Windows 的公钥或准备记录。

```json
{
  "schema_version": 1,
  "host": "填 Windows 可达的 Ubuntu 开发环境地址",
  "port": 22,
  "user": "填开发用户名",
  "project_path": "填实际项目绝对路径",
  "codex_path": "填 codex 可执行文件绝对路径",
  "codex_version": "填实际版本",
  "ssh_host_key_sha256": "填 ED25519 SSH 主机公钥的 SHA256 指纹",
  "ready": false,
  "blockers": []
}
```

`host` 应是 Ubuntu 开发环境的地址，不要误填 KV260 板卡地址。不确定 Windows 路由时，在附加字段 `candidate_addresses` 列出候选地址并保持 `ready: false`。`ready: true` 表示 Ubuntu 侧准备完成，不能代替 Windows 侧 SSH 实测。读取 `/etc/ssh/ssh_host_ed25519_key.pub` 的指纹即可，不读取或复制对应私钥。如果确需调整防火墙，应只允许 Windows 的实际来源地址访问 SSH，不扩大为公网访问；无法确认时报告阻塞点。

6. 完成后报告准备结果。现有 Ubuntu 对话是否能通过远程连接接续，需要连接后确认，不宣称会自动同步。后续分工是 Ubuntu 负责板端编译和部署；Windows 负责 27B、OmniVoice 与接口联调。业务处理和记忆存储最终全部在板端。

这次共享目录仅用于交换接入资料。连接成功后，优先通过可访问的远程 Codex 会话传递任务和读取结果。

官方接入依据：[SSH 远程项目](https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host)。
