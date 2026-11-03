# 采集回调单次冗余复制移除候选

结果：基于当前保留YuNet UI源码的独立候选，**只删除一处NumPy数组`.copy()`**；8项软件回归通过，两个基线的补丁均在临时目录dry-run和实际应用通过。没有连接板卡/UART、操作生产服务、更新共享入口或修改原冻结诊断4源码。

修改前后：

```python
# before
image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3).copy()
# candidate
image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)
```

`data`仍由`buffer.extract_dup`取得独立BGR字节；新`image`只是其只读视图。后面的原`cv2.flip(image,1)`产出独立、连续的镜像数组，发布到原latest与原FaceTarget路径。原640×480×3/长度检查、时间戳位置与字段语义、frame ID、镜像方向、metadata、人脸offer、EOS和错误流保持。

可确认的源码事实是：每个接受的640×480 BGR帧少一次**921,600字节数组复制与分配**。extract_dup、flip、预览绘制/发布仍有原有内存工作；不能据此直接宣称CPU降低某百分比或DDR带宽减少某数值。本包没有板端性能实测。

## 版本与补丁

| 项目 | SHA256 |
| --- | --- |
| 保留YuNet UI基线 | `890fea726de2c6d29581ab2ee4c36db5e36df52f3e84ee20cd634fc8961ec2ce` |
| 本包candidate UI | `d74e30250e94584217c90eba9efaed41413e72d64505eeecd20d7cce66e7de45` |
| 冻结诊断UI基线 | `e7771f01e0e47e6aa629be74fca74f30803a6ec9ed1a48b97b71de3cc452260f` |
| 对诊断基线应用同一行补丁后 | `a911631f2784af73a721960af7223256aa4273bfe045b113143eba3e22209227` |

`candidate/aura/board/vision/ui_camera_service.py`只对应保留YuNet基线，`production.patch`是其最小差异。`diagnostic.patch`是同一处删除应用到诊断基线的小补丁，不提供或覆盖第二份完整诊断源。不得用本包candidate整文件覆盖已经合并其他功能的UI；由主任务先核对目标SHA，在独立候选应用对应补丁。

`patch-manifest.json`含 `software_tests_passed=8`、基线/候选SHA与未实测标志。`patch-validation.json`记录两补丁在临时目录精确应用的结果；原基线文件没有修改。

## 软件验证

`python3 -B run_tests.py`使用已有Vitis AI CPU容器、只读源码挂载、无网络，仅合成BGR数组。测试从真实完整UI源码的AST提取原nested capture callback执行，使用真实NumPy/OpenCV flip与模拟GStreamer输入，不是另写一套处理函数作自证。

8项测试实际通过，见 `test-results.txt`：

- 只改一处copy，精确基线SHA；所有像素逐值等价、镜像方向与连续布局一致。
- bytes输入视图只读，真实flip输出own data、不共享原输入内存。
- 删除原data/image引用后结果仍有效；可变模拟输入之后被覆盖也不影响已发布source。
- 640×480/长度门、错误/停止流、metadata、同一source传人脸路径及EOS行为保持。
- 诊断基线应用同一行补丁后输出等价、原stage metrics仍产生，补丁内容精确一致。

这些是主机软件行为测试，不等同板端OpenCV/GStreamer运行、整机长稳或性能验收。下一步由主任务在原音频/USB状态恢复并通过预检后选择可回退窗口，保持同输入、模型、频率与业务，比较CPU核秒、callback wall、帧龄、有效检测/人脸消费和错误；未测前不报告加速收益。本包不会自行部署、提频或新建DPU owner。
