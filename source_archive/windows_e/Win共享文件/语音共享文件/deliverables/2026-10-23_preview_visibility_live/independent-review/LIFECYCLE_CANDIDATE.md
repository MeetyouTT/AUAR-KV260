# 相机预览可见性候选与离线验证

后续补一项现役freshness契约回归后为**15项全部通过**（`lifecycle-tests-final.log`）：连续30轮frame_visible=false仍保持DrawingArea visible，不循环unmap/attach；由Stack/对话框父级控制真实map。baseline/候选该行原本就是True，本次未改2源业务SHA。下文14项为首轮结果；主任务另已报告5项真实离屏Gtk/Gst/X11通过，本副任务未接板复跑。

按主任务授权，仅修改`candidate/aura/tools/board_avatar_gtk.py`和`board_camera_preview.py`；基线7源SHA核对通过。未访问UART/板卡、未开窗口/音频/模型、未改正式源码或共享入口。完整补丁见`candidate.patch`，当前SHA见`candidate-manifest.json`。

## 实现

- vision和large DrawingArea均连接unmap→detach。large关闭重复detach幂等；仅移除对应name，不影响另一输出。
- map按每name的递增代次运行现役50ms bind，仍检查realized/mapped、sync并重新绑定XID。unmap使旧代次失效，同XID重映射也不会执行过时callback。
- 没有输出的work迭代不读services或RawFrame，清reader/last_key以便重新attach后重新取得同一仍新鲜的帧；不停止相机采集、YOLO/YuNet/SFace或身份服务。
- detach先在全局回调锁内pop使旧output退休，再在全局锁外对该output的lifecycle_lock串行执行Gst NULL和handler/probe断开。push和owner重绑使用相同lifecycle_lock，Gst状态调用不持全局锁，避免与handoff互等。
- 按name+output对象身份拒绝旧snapshot、旧handoff与过时bus错误。推流中退休导致的FLUSHING被忽略；当前有效output返回失败仍抛出错误。NULL后断开handoff/probe，打断output→pipeline→Python callback→output环，避免反复map积累注册。
- `read`只增加sink_active、active_outputs及明确非物理扫描率的measurement_scope；原可见ref/250ms期限/像素格式/分辨率/管线顺序/角色8fps/音频保持。

## 已执行验证

`python3 -B -m unittest discover -s /home/ghmd/aura-video-cpu-20261023/tests -p test_preview_lifecycle.py -v`：**14项全部通过**，0.014秒量级，标准库，无GI/Gst/PIL/native库或设备依赖。测试运行真实候选worker方法，GTK只提取真实attach/detach方法并用假GI窗口/延迟回调承载。

覆盖：

1. map→unmap→同XID重map重新绑定，旧50ms回调在未映射或新代次时丢弃；realized=false不绑定。
2. vision关闭而large保持、关闭large不动vision、重复关闭、当前像素bytes/header/frame_id/PTS保持。
3. 零输出3轮不调用services/RawReader，重新打开同epoch重新读当前帧。
4. 退休handoff/probe不写引用，退休期间旧FLUSHING忽略；真实当前FLUSHING仍报错。
5. 并发detach与push完成，不持全局锁调用Gst；owner重绑途中退休不重启PLAYING；handler/probe仅清理一次。

首次测试夹具的AST包装ClassDef缺lineno，在import阶段失败；已用`ast.fix_missing_locations`纠正，原日志保存在`lifecycle-tests-fixture-error.log`。这不是候选业务失败。最终`lifecycle-tests.log`保留全部14项结果。

## 尚未验证

没有真实GTK map/unmap、Gst NULL/PLAYING、handler解除或X11显示实测；假Gst并发不能证明真实Gst没有死锁。需要主任务按受保护GUI-only流程验证：自然空闲；切vision/main及large关闭/重新打开；保持camera PID/unit/单DPU owner、身份/偏好/音频不变；显示恢复、ref时效、真实CPU、源SHA与回退均核对后才能保留。

特别注意：隐藏vision时ui_runtime.frame_visible=false/ref=None是有意的显示状态，重新map收到新帧后再允许当前图动作；hands-free业务attention仍来自独立services.identity_snapshot。此候选未承诺CPU下降比例、DPU长尾改善或物理显示帧率。
