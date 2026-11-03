# 返场固定轨迹接入、试验中止修复与观察待答

主机UTC2026-10-27 02:51起（本地10月26日）。用户问下一步、说在镜头前，并确认当前仍为此前1420正前。读取新boot da36c36a，联合固件/camera54394/GUI54429保持；30分钟监测实际1800.002s/360样本/30kernel窗完成，无USB或读取错误，primary2/optional0保留。8.032s人脸只读93个不同READY源、图龄p50 40/p95 83ms，12UNCONFIRMED/3EXPIRED包，目标在线内。

独立新增固定轨迹真实寄存器adapter、现场参考receipt与board CLI，默认PLAN；文件/平台/服务检查不MMIO，执行须本boot观察/脉宽一致、独占transport/operation锁、不可复用输出文件。不走face submit或制造源时间。13入口/ACK区间检查通过，adapter初16后18回归，板端纯模型98ACK通过。批读不能知道lease寄存器精确采样点，使用批读始末/到期上下界；native最后写Q09仍未闭环。现役r15没有修改。

根据用户原话当前参考声明，先BIND/REFERENCE1420再STOP，0 ARM/COMMIT，默认1500不作实体位置。第一轮2s5us真实31ACK后core误报UNEXPECTED_PWM_WIDTH，停止width1416/target1415。取完整trace确认ACK30/31目标1415但width1416、间隔13.816ms；preflight已知旧width被上层post错误遗漏。修core后保留未知width拒绝，独立相位模型重现旧失败/新98ACK成功。复用原≤5us有限台架1416→1420、48ACK回位STOP，不声称新外部标定。

第二轮2s5us v2真实98ACK/1.963095954s，1420→1415→1420，首变化target提交161.223ms，实际间隔10.949/20.033/28.994ms min/median/max，最终1420/flags0/lease0/epoch4/ack98。用户“幅度太小或没看清”，实体平滑未验证。

据用户反馈做同限速的5s15us可见试验（1420→1405→1420，仍1402..1420窗口，期望10us/s，上限20/100/800不变）。23项模型过，但实板首版0.083624856s/4ACK、全部1420保持，在开始偏转前SUBMISSION_SPACING_NO_CATCHUP中止。两次实际submit耗25.876/29.568ms，旧for循环追旧slot造成短间隔。最新真实STOP width/target1420、epoch5、ack4；没有完成15us往返。两项失败属于新增测试程序缺陷，不能包装为已定位原r15机械问题。

visible-r2改真实时间选最新到期点，ACK后≥20ms再发，跳旧点不追赶；最多248命令，原5s截止/计划40ms尾部预留/1us步长/100ms lease/20ms余量/初23ms及真失效STOP不放宽。29项过：实测延迟回放245ACK/跳3点；重复10～35ms抖动127ACK/跳121；持续慢提交143ACK/跳105；均模型返回1420，101ms真lease过期仍STOP。当前3.004s只读CPU75.69%、负载约5.07，USB0/计数2保持；未改CPU优先级或重启业务。

visible-v2已实际传输并板端文件/平台检查、纯寄存器248ACK模型过，最后真实STOP复核1420，0新增ARM/COMMIT。包manifest6b9cddcfeb78cd49708a01b9f99e5b20f894448818849376556a6a596bc09b83，core fedbf189…，adapter/计划与15us首版逐字相同。板端R/state.json更新FIXED_TESTS_STOPPED_VISIBLE_R2_AWAITING_OBSERVER。**此版尚未实体执行**。

重试准备阶段3秒无READY脸，脚本在MMIO前拒绝，未改receipt；随后当前私有camera帧未见人脸，已询问用户是否仍在设备旁能观察，未把无脸当作明确离开或用检测替代人工许可。当前仍停止，旧本boot观察/参考保持，但不可伪造新的答复或把到期许可直接复用。实体5s复验与r15真人联动、本boot GUI绑定均未完成，manual仍FAULT/automaticfalse。

代码、全部数字trace与原话见[共享接入记录](/home/ghmd/Win共享文件/协作任务/2026-10-26_返场固定轨迹与实板接入/README.md)。仅主终端UART/实板，子终端本地数学/驱动/真实延迟回放和审阅；无图像、UART、姓名、录音共享，无Windows代回执。
