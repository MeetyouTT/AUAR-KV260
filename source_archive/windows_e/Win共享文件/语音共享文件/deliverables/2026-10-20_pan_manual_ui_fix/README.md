# 手动调轴按钮变灰：独立控制进程修复

用户按一次右转后按钮变灰。故障前实读：界面仍响应、序列2856→2858、GUI195564/相机106060 active；手动模块FAULT/ACK mismatch。1430→1450µs，接受3条指令，240.99ms后停止，最终flags0/lease0/epoch9/ACK3，输出关闭。不是把“服务active”当作点动成功。

原控制线程和GTK/音频共享Python解释器，负载下100ms续期可能被延误；这是当前最可能的原因。原版本只保存STOP后的状态，未保存异常COMMIT前后寄存器，因此不能把原次失败的具体硬件原因断言为已证实。此次改为独立进程持有Native唯一锁并续期，GUI仅发送有期限的新意图；保留100ms硬件租约、步长和范围，不通过延长租约绕过故障。补存异常前后寄存器、尝试序号、ACK间隔和COMMIT耗时。

新增“重新连接”：仅重新核验接口，清空旧请求，不自动重放、ARM或转动。IPC请求过期拒绝、子进程退出后停止并等待显式重新连接。中位仍待用户自行调好后给出读数，自动跟随保持关闭。

修复已安装，实板点动回归通过。347项主机回归、23项KV260软件测试通过；实进程测试使用模拟100ms硬件租约，刻意让父进程GIL繁忙350ms，子进程仍完成点动，停止、旧IPC拒绝、子进程被终止后显式重连且不重放通过。GTK实际控件模拟检查通过，硬件为Fake，另有下面的真实实板结果。

真实GUI负载下依次点动1470、1450、1455、1450µs，各约2秒，接受42/41/41/41条，共165条，四次全部完成并回READY，无ACK异常，每段STOP读回flags0/lease0。随后显式重新连接，backend206103→207278，读数仍1450，history为空且未追加动作。最终只读复核：GTK206098、其控制子进程207278、监督195564→206028，相机106060约9.93Hz/identity=true/无错误，原230项组件SHA保持；联合VART和HDMI2秒设置保持。

最终flags0/lease0、width1450/reference1455/epoch13/ACK41。reference1455仅为最后一次台架初始化点，不是机械中位；中位继续待用户明确确认。诊断字段max_ack_gap_ms记录前次ACK结束到本次提交开始的空档，结合各段max_commit_ms，可得ACK间隔的保守上界均小于73ms；未将空档字段单独误作完整ACK间隔。

原43份交付冻结文件保留不改。此目录保存新的源码和故障/修复证据；原GUI/语音/身份230项组件保持，更新只涉及原附加模块及新增独立进程模块/测试和启动manifest，保留HDMI2秒设置。不改Windows回执。

- [原故障状态及停止请求](evidence/fault/response.json)、[部署计划](deployment-plan.json)
- [独立控制进程](source/board/motion/manual_process.py)、[控制器](source/board/motion/manual.py)、[底层适配及诊断](source/board/motion/manual_vsrv.py)、[界面扩展](source/tools/pan_controls.py)
- [实际部署结果](evidence/results/deployment-result.json)、[板端23项软件测试](evidence/results/board-tests.txt)
- [四次实板点动及重连完整记录](evidence/results/regression.json)、[最后只读核验](evidence/verify/response.json)
- [Windows保留与回退](Windows_接入说明.md)、[冻结清单](verification.json)
