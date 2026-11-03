# YuNet输入编码最小候选

依据主端同fid板端profile中layout/normalize与encode的真实成本实现。仅本机源码与合成验证，未接板、未改冻结v15或启用生产优化。

`install(DpuYuNet, output_transform, measure=None)`在原构造结束后，仅将native_critical=True、fix7及NHWC[1,320,320,3]实例的detector.net换成FastYuNetNetwork；非native/legacy跳过，独立CPU fallback.net不变。原YuNetCompat.detect、resize/blob、decode/NMS不复制或改写。forward始终传递原_admission_check对象给原_native_scheduled，不生成新期限、owner或提交路径。

setInput只接受真实uint8→OpenCV默认blob产生的float32[1,3,320,320]整数域，检查有限/0..255/整数后提升uint16，原位加一、右移、clip127，最后形成连续NHWC int8。失败清除本次缓存，旧tensor不再可用。全256值、随机/饱和/非连续/resize BGR输入与原normalize/encode逐byte相同；None、原异常、错误输出名、无guard和不支持backend检查覆盖。6项检查通过。[结果](TEST_RESULTS.json)

微基准：`python3 -B board_benchmark.py --runtime-root ACTUAL_AURA_RUNTIME_ROOT --iterations 20 --max-seconds 12`。真实原YuNetNetwork/encode与FastNet分别测完整resize/blob及setInput/forward；两边同一Fake native执行、相同identity输出转换，Fast严格验证计入。隔离子进程OpenCV1线程、最多20帧/14秒预算，不打开DPU/模型/相机/MMIO。主机结果仅供核对，不替代板端成本。[主机结果](HOST_BENCHMARK.json)

v16中先安装stage profiler，再把现有runtime.yunet_outputs与stage.measured注入本适配。新增stage名为fast_input_encode和fast_network_forward；derived decode统计需在v16副本children中加入这两项，避免把Fast native调度错计为decode。冻结v15不动。

输入量化字节等价不表示模型/端到端性能已经验收，需主端板端微基准决定是否启用。不要省略uint16提升，也不要将分数/预归一化输入偷偷截断成整数。
