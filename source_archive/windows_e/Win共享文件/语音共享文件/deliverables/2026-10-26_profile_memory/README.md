# 个人档案与长期记忆接入（2026-10-26）

本轮完成了明确授权的个人记忆后端和客户端源码。后续[动画与对话接续轮](../2026-10-26_animation_dialogue/README.md)已将设置页“个人记忆”入口受控合入正式板端UI，完整隐藏GTK及正式原生界面试运行通过；Windows升级到兼容r3。默认访客、监听关闭，没有代用户创建真实个人档案。以下r2检查与旧候选元数据为当轮历史，整个玩偶项目仍未全部完成。

## 已完成的行为

- 默认访客，原匿名会话保留；旧会话不能自动认领为个人档案。
- 在Windows本机显式创建并选择档案后，主机签发绑定设备boot和交互session的短期授权；默认15分钟，最多30分钟。重启服务后需要重新选择，已确认事实仍可跨会话、跨重启保存。
- 已授权档案内的“记住”“更正”“忘记”“查看”作用于个人长期事实，最多12项；“清空本次对话记忆”仍仅清当前会话。“记住本次对话：键=值”可显式选择会话范围；“清空我的长期记忆”清当前档案的可召回事实及相关历史召回。
- 访客及另一档案不能读取或续接个人会话。更正/遗忘会排除该档案各会话中的旧来源，提升版本，使旧生成和旧播放ACK失效。助手仍只有完整播放ACK后进入可召回历史。
- 授权撤销后逐包停止旧PCM投递；客户端切换会作废旧代次、丢弃旧进度及排队ACK。在线释放请求撤销主机授权；断网时本地先停止投递，主机授权最迟按期限失效。
- 本机控制入口验证高熵密钥、来源地址及请求形状；公开语音入口接受有期限的授权令牌，单独上传profile_id、报姓名或人脸/声纹候选均不能解锁档案。服务只保存密钥SHA256校验摘要，摘要本身不能用作登录凭据。
- 板端候选只有在设置页点击“使用授权档案”后才激活已传入的授权；读到授权文件或关闭弹窗均不激活。“切回访客”开启独立匿名对话。授权令牌、档案ID和名称不进入公开状态接口。

当前Windows本机控制密钥位于用户私有目录，ACL仅授予当前用户。共享源码配置含校验摘要及私有文件路径，不包含原密钥。没有创建真实个人档案、采新录音、读个人声纹库或自动绑定历史身份。本轮没有模型迁移，27B/Ollama仍在D盘。

## 验证及运行证据

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 个人事实、授权、隔离、旧ACK与原语音回归 | 303通过，2项Windows平台跳过，27子测试通过 | [verifier.log](verifier.log)、[verifier.xml](verifier.xml) |
| 新增专项 | 43项，包含于上述303项 | [test_profile_memory.py](../../aura/tests/framework/test_profile_memory.py)、[test_profile_frontend.py](../../aura/tests/framework/test_profile_frontend.py) |
| 板端独立候选 | 3项检查通过：交互归属/状态脱敏、切回访客、实际GTK隐藏对话框构建及取消 | [board_candidate_verification.json](board_candidate_verification.json)；不是完整GUI初始化或真人选档验收 |
| Windows真实服务 | 源码指纹一致、个人授权控制configured=true、原公开WAV实际识别/27B/OmniVoice接收完整 | [runtime_verification.json](runtime_verification.json)、[public_voice_after_upgrade.json](public_voice_after_upgrade.json) |
| 原运行库备份 | SQLite一致快照、integrity_check=ok；备份位于原私有运行目录 | [database_backup.json](database_backup.json)，包内不含数据库正文 |

Windows跳过项是原SpeexDSP原生处理和Linux flock采集所有权；两项在[前一轮板端模拟音频补测](../2026-10-26_system_completion/board_audio_auto.json)通过，本轮未改其算法。303项由260项既有回归与43项新增专项组成；另27个子测试单列。全部自动回归使用合成档案/库及测试进程自己的临时回环端口，外部网络禁用。

个人记忆相关表为原SQLite的增量扩展；原匿名历史不搬库、不自动归属。备份和升级证据仅记录元数据，不复制正文到源码包。回滚语义须保留新表、个人归属和遗忘版本；不要直接用不理解个人归属的旧服务打开升级后的库。

## 本机使用入口

使用现有语音Python运行`aura/tools/profile_cli.py`。本机密钥已配置，本轮没有代用户创建档案。常用命令：

```powershell
python aura/tools/profile_cli.py create --name "我的档案" --consent
python aura/tools/profile_cli.py list
python aura/tools/profile_cli.py select --profile-id <上一步的ID>
python aura/tools/profile_cli.py chat-wav <16k单声道PCM16录音.wav>
python aura/tools/profile_cli.py guest
```

CLI的chat-wav仅接收，不播放，也不发送助手播放ACK；它可验证识别与记忆命令，但不能替代完整听音。CLI输出不显示授权令牌；本地短期选择保存在用户私有目录。

板端入口已在接续轮合并；Windows执行`select --profile-id <ID> --board`会通过既有已验证SSH投递绑定当前启动的短期授权。操作员密钥不会送到板端，文件投递不会激活档案，需要用户在玩偶设置页明确选择。目标文件使用实际UI进程的HOME，避免历史`/root`与`/home/root`差异。CLI不启动麦克风或运动。

干净机器先运行`profile_cli.py setup`创建私有密钥与摘要，再重新启动服务；已有密钥可运行`configure`更新摘要。不要把原密钥或短期授权文件放到共享目录、源码包或消息里。启动仍用语音项目的`start_voice.ps1`。

## 剩余工作

1. 正式GUI合并、完整隐藏初始化和正式原生界面状态检查已在[接续轮](../2026-10-26_animation_dialogue/README.md)完成；本目录的旧候选和原源码包作为历史保留。
2. 用户在场后进行实际选档、听音、插话、噪声/旁人和长期使用验收。声纹仍未现场标定，不自动解锁个人记忆。
3. 声纹正式阈值、自动声画归属、真实ASD/视觉问答、转轴期限和平顺跟随仍按原任务继续。当前仅支持明确事实和有来源上下文，后台机器摘要、到期状态/待办及备份恢复删除水位的完整运维能力仍待后续阶段。

原始失败保留：板端候选首轮命名空间导入问题、后台私有密钥读取检查失败。修复后重新验证通过；没有通过放宽密钥ACL、把密钥复制进共享目录或启用未标定声纹来解决。

`source_and_tests.zip`包含显式清单内的源码、修改前备份、板端候选和小型测试报告；`SOURCE_MANIFEST.json`记录每项SHA256。模型、环境、密钥、短期令牌文件、真实录音及任何数据库正文均不打包。
