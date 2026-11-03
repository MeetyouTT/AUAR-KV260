# 三模型DPU正式版本的运行与回退

当前boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`，camera unit SHA `a29082bae1d382d7a43505d5a1d3a51fa2203081423755900e9d72836385e343`。camera333557、GUI监督333586、Xserver1077，正式身份后端DPU_SFACE_INT8。release：

`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217`

相机使用release内的board_camera_ui.json；身份使用board_identity.sface_int8.json。新私有数据库model binding为sface-int8-12b2ff5c7de15713/128维，保留原登记身份ID/称呼、重新计算INT8向量。原Windows库/照片和fallback config保持，不能把旧向量复制到新库。SQL/private photos/原始UART不在共享目录。

只读入口：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/restore_previous.py --check
```

明确回退：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/restore_previous.py --restore
```

回退目标是旧unit048ee59c和YOLO＋YuNet DPU/Windows SFace，不删除或重写新旧数据库；入口绑定当前boot/source/config/preference与空闲状态，并先建立独立restore再协调关原音频、确认PCM关闭、切相机并恢复GUI。--check已实板通过；成功后没有为测试手动命令而撤销当前版本。

若用户更改config/偏好、boot变化、正在录音/播放或手动运动，校验可能拒绝；先重新核对实际状态，不绕过校验。后续Windows GUI/语音发布保留本camera unit、runtime和新identity config，不使用历史整机release覆盖。

新identity阈值0.50/margin0.10是固定实验值；通过5个旧登记独立留出正帧及本次确认本人一分钟检查，尚没有陌生人/多用户误接收率验收。95/105是该已知本人窗口中的接受率，不是通用识别准确率；长期/强音视频负载/冷启动继续单独记录。
