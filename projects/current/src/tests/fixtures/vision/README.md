# 人体检测固定测试图

`person_bus.jpg` 用于 YOLOX-Nano 的参考图检查，不是板上摄像头画面。

来源：[Ultralytics YOLOv5 v7.0 的 bus.jpg](https://github.com/ultralytics/yolov5/blob/v7.0/data/images/bus.jpg)，上游许可见 [LICENSE](https://github.com/ultralytics/yolov5/blob/v7.0/LICENSE)。原图 SHA256 为 `33b198a1d2839bb9ac4c65d61f9e852196793cae9a0781360859425f6022b69c`。用 Pillow 转 RGB、等比例 thumbnail 到 416×416 边界，再以 JPEG quality=75 保存为 312×416。

本文件 SHA256 为 `975917d943c3dd367a27c37c4a9b0cdaf28c73ce671c881f6489a18bda20b46f`。启动自检要求至少两个有效人体框、640×480 黑图零人体框；框数不作为数据集精度指标。实时服务只处理独占采集者的实际相机帧，自检图片不会进入实际画面或状态。
