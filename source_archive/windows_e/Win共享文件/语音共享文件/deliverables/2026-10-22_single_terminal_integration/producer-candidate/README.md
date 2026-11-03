# SFace独立裁剪供给候选

状态：软件候选，56项回归通过（原标定/影子46项＋新增供给10项）。旧Windows正式身份处理继续按原周期/错误路径工作；新增准备线程从FaceTargetService的明确单目标回调获取同一不可变源帧引用，准备合格裁剪，再向同一个SFaceShadow投递。没有新相机、第二个DPU runner/owner或独立身份库。

默认关闭。启用要求已有`dpu_sface_shadow.enabled=true`且`compare_cosine=false`，额外配置`dpu_sface_producer={enabled:true,interval_ms:500}`。间隔只接受500～5000ms，表示准备节奏，不保证推理频率。producer启用后原extractor不再向shadow重复投递；原Windows的对齐、PNG和特征请求保持原行为。本候选不自动配置或切换模型。

回调只做有界字段检查、复制少量face/key和非阻塞置换一个pending，CPU对齐/模糊度/pose准备在独立线程。最多一个准备中和一个最新pending；源时间、相机/目标代次在准备前后复核，shadow原有目标/TTL/计时保护保持。质量字段传给已有RAM标定ticket；没有图片、向量、名称、数据库或网络写入口。

关闭先要求准备线程退出，再关闭shadow；若准备/native未退，不谎报shutdown_ready，也不通过第二owner绕开。重启/超时的最终过程由主任务统一管理。新增代码不改变20ms估计、30ms硬上限或YOLO guard。

主要变更为`board/identity/sface_producer.py`、`camera_faces.py`和`live.py`。其余7源码沿用冻结标定候选，以完整overlay供集成。原库/阈值保持，新功能默认关闭；本目录尚未生产部署或证明三模型长期稳定。合并后的13源码在主任务单终端目录中另有101项测试和板端导入证据，不把这些导入检查写成真实SFace推理或现场阈值验收。

回归用合成像素/向量与模拟远端。新增测试覆盖Windows特征调用阻塞时仍有3次独立供给、无重复offer、latest-only/非阻塞回调、质量票据、目标/TTL失效、异常隔离和关闭。首轮因缺工具依赖、远端fixture模块和未ready投递条件而失败，结果保留；补齐fixture/工具并确认ready后投递，最终56项通过，日志见`test-results.txt`。没有用真实人脸或远端请求作该软件回归。

下一关是保持原业务的隔离运行验收、有效人脸覆盖与真实完成速率，再进入现场INT8登记/阈值和独立验证。0.5/1/2Hz均须实测，不把软件供给增加直接当DPU利用率或身份准确率提升。
