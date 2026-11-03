# 按用户要求撤回最近三小时的界面/显示启动改动

本地2026-10-20 / UTC21日06:06开始，用户要求“回退至三个小时前”。已撤回05:02安装的HDMI启动补丁并重新加载图形服务，当前回到“演示层→玩偶交流”。**这是按可核验版本记录撤回近期改动，不是完整整机时间快照恢复。实屏闪烁是否消失尚待用户回执。**

## 回退依据与范围

以操作开始UTC06:06计，约三小时前为UTC03:06。没有该秒的整机快照；UTC前日23:58与当日04:51记录均为render24-budget/e06409743174、配置SHA `eb5b8e02…`、启动器`cd168022…`。05:02仅替换了该启动器和Xorg配置，未换GUI/语音业务源码。因此恢复这两份文件并回到日常页面，不擅自退到更早的语音、身份或转轴版本。[时间依据](evidence/timeline.json)。

| 文件 | 回退前 | 已恢复 |
| --- | --- | --- |
| 板端活动startup/launcher.py | ea68cb07… | cd168022… |
| /etc/X11/xorg.conf | 64457c25… | 164afc02… |
| 共享scripts/board_ui_startup/launcher.py | 显示阶段补丁 | 修改前全文SHA61d852c0… |

板端恢复的[启动器](src/restored-board-launcher.py)与[Xorg配置](src/prepatch-xorg.conf)保留在此。共享启动器恢复前后全文均存档，撤回补丁新增的`test_retrain_results.py`已[归档](src/withdrawn-test-retrain-results.py)，避免旧实现下测试预期不一致；保留原17项显示测试。共享README更新为回退状态。此前冻结修复包作为历史证据保留，不修改其内容或清单。

没有更改原GUI组件、模型权重、相机、身份库、对话模型或用户配置。活动runtime仍为原e06409743174，241项组件预检通过，配置SHA不变。用户数据没有执行删除或恢复旧副本。

## 执行与验证

原先为闪烁准备的“关闭输出2秒/切回main”修复命令**没有发送**：连接时板卡正处于一次SOFT重启，串口回车碰上U-Boot倒计时而停止自动启动。确认`ZynqMP>`及原bootcmd后，仅执行`boot`继续现有启动；没有烧写或修改持久启动环境。随后恢复Linux root连接，新boot `c7d18dbf-2cd2-40b1-9534-b3de305e847a`，串口回显已恢复。

先核对并备份当前两个文件，再使用带SHA保护的既有回退器恢复原件。停止GUI、重启Xserver加载原配置，再启动原GUI服务；没有直接重放运动或录音命令。备份路径：`/home/root/aura-ui-time-rollback-20261021/before-2559`。该目录保留回退前新启动器/Xorg/config，原修复候选目录也保留；本轮没有自动重新安装新版。

- [文件回读](evidence/rollback-files.json)及[激活](evidence/activation.json)通过。
- [实际运行核验](evidence/running-verification.json)：GUI监督2680、Xserver监督2672、相机987均active/NRestarts0；相机在本次图形重启前后PID保持，采集12.43Hz/检测9.88Hz、无相机或检测错误，身份识别开启。显示1024×600/59.85。
- 当前为main/presentation、IDLE、error空；免点击对话PAUSED、自动对话STOPPED，未自动开启麦克风。用户可点“恢复免点击”，本轮未做新的语音听音测试。
- [6秒/7次采样](evidence/stability.json)：人物已接收帧2217→2346，约20.3～20.6fps，三个服务PID/重启次数保持，Xorg没有新增日志。这不是物理闪烁或长稳验收。
- 私有截图确认恢复原日常页面，四角浅色；共享仅保存[元数据](evidence/screen-metadata.json)，没有图片或原始UART。
- 原17项显示fixture在恢复后的共享源码通过，全文SHA与修改前记录一致；不把fixture称作冷启动/物理HDMI通过。

回退前的GTK/GStreamer双缓冲假设未在独立主机复现，[结果](evidence/reproduction.json)为三种绘制方式均无覆盖样本，**没有据此部署猜测性的绘制补丁**。回退前100次像素采样和6秒热插拔监测也未观察整屏黑闪或持续热插拔；软件观测不能否定用户的实屏反馈。

## 待确认

已向用户询问回退后实屏是否仍闪，尚未收到回执。此时只可报告近期启动配置已回退、原页面恢复和上述软件检查通过；不能报告花屏/黑角/闪烁根治或三小时前所有内存状态已恢复。转轴没有发命令或解除Boot mismatch保护，CPU优化没有恢复。

[取证来源](evidence/provenance.json)记录各独占UART阶段。Windows回执未代填、同步未确认，模型权重与私有截图均未进入共享交付。
