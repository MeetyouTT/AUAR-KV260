# r14：首次PWM必须覆盖下一完整帧

仅本地主机候选，未上板、未进行实体转动。由冻结r12独立复制，原r12和未完成r13未修改；部署manifest继承的r12路径/指纹仍待主端重新生成。

## 已确认的问题与范围

实际30秒报告经timeline/final events去重共56条：28次ARM中，12次是区内预备、全部没有COMMIT，不能称为实体反复启停。其余16段包括两段仅一条首COMMIT，租期6ms、11ms；之后读回分别width1454/target1453和width1416/target1415，目标未在下一帧输出。全部停机原因：SOURCE_HORIZON20、SOURCE_LEASE_EXPIRED6、SOURCE_SUBMISSION_EXPIRED1、OPERATOR_STOP1。packet reason计数会重复，不作为停机次数。

首COMMIT先输出当前width，20ms后下一PWM帧才应用新target。允许首租期小于一帧，会报告目标接受，却只短暂输出旧width。这个缺口与真实输入/500ms检测锚更新迟造成的必要停止分别处理，不延长源有效期。

## 最小改动

- `pwm_budget.py`：纯常量，下一帧20ms；首次最小lease23ms，覆盖下一帧及<=1.6ms完整脉冲并留余量。既有提交余量20ms与预检3ms保留。
- `continuous_session.py`：首PWM前每tick及submit前预检。原deadline剩余不足46ms时保持无PWM等待；pva与当前读回width一致、速度/加速度归零，不累计未执行轨迹。真正新源/锚有效才重新从静止起步；同锚、重复包均不扩期。区内、丢脸、换人及原到期规则保持。
- `deadline_driver.py`：`submit(..., *, minimum_lease_ms=0)`。首次输出由session传23，已经输出的后续续租仍传默认0。最后COMMIT前检查父driver实际写入的lease值；IO耗时缩短至23ms以下时不发COMMIT，沿父异常流程STOP，验证flags/lease归零后按原`SUBMISSION_TOO_LATE`返回。真实IO异常或STOP失败仍抛出，不转成干净成功。
- `run_face_motion.py`/`session_shutdown.py`：控制退出时先记录pre-stop状态，再执行并验证session.close，最后关闭HTTP reader。reader.close可能等待另一线程buffered read锁；不能让它阻塞在显式STOP之前。reader清理错误单独记录，不覆盖原控制异常或STOP失败；快照异常也不阻止STOP。这是代码路径保证，不把此前一次诊断超时直接定因为reader.close。

父driver的原lease公式、20ms提交余量、250ms图像/500ms锚、post-ARM真新图、每源4us、速度/加速度/jerk、方向和人脸边界均未放宽。最后native写入内暂停的Q09竞态仍不属于软件绝对截止保证。

## 验证

原89项回归保留，加26项针对性回归，共115项主机测试；涵盖短首租期、完整帧首次生效、无未执行pva积累、原截止、真新锚恢复、同锚/重复不能扩期、区内/丢脸/换人、后续续租、最终写前拒绝、真实IO/STOP失败传播，以及reader明确阻塞/抛错时STOP优先、状态采样失败仍STOP与原异常优先级。

`python3 -B replay_initial_pwm_budget.py --compare`对同一Ruckig+20ms latch软件模型做4组成对比较：r12首租6/11/19ms分别1 COMMIT、1旧width脉冲、0新width输出；r14对应0 COMMIT、0PWM。充分59ms首租期两版都正确在下一帧输出+1us，行为相同。这是合成软件复现，不是板端波形、实体首动延迟或真人平顺验收。

`HOST_VALIDATION_R14.json`和`INITIAL_PWM_REPLAY.json`记录实际运行结果；主端负责manifest、传输和任何板端验证。
