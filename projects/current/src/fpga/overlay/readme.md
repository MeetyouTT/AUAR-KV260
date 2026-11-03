# KV260 wide 固件组成

`aura-visual-servo.dtsi` 保留原 overlay 的目标、fixups、时钟、中断、ZOCL 和显示节点。`shell.json` 使用 XRT_FLAT，单槽。`build/export_firmware.py` 实际调用 dtc、fdtoverlay、xclbinutil 和完整导出时的 Bootgen。合并后从 FDT 二进制重新解析关键节点。源 BIT 和 XSA 内嵌 BIT 的配置数据必须配对，HWH 中的地址与时钟与 `src/fpga/bd/address_map.json` 的独立参考比对。

原 KV260 底图 SHA-256 为 `22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762`，本机固定文件为 `$HOME/aura-system-pan-20261028/fresh-base.dtb`。包内 `board/system/validation_base.dts` 是脱敏合并测试数据，保留设备结构。不能用它替换可启动系统镜像。

默认从 `src/fpga/xrt_metadata` 的 8 个段重建 XCLBIN，逐段回读并校验，导出时记录新的 UUID。若要使用冻结的原容器，给出 `--xclbin <文件>`，其 SHA 必须为 `875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3`。编译、合并与固件配对各自写入独立日志。

## 取得相同版本的 fdtoverlay

上游归档 SHA 与发布站的清单一致。本轮将已有工具的 109 个源文件与官方归档逐一比较，全部一致，并在 Ubuntu 从该归档重新构建 fdtoverlay。

```sh
curl -fL https://www.kernel.org/pub/software/utils/dtc/dtc-1.7.2.tar.xz -o "$OUT/dtc-1.7.2.tar.xz"
echo "92d8ca769805ae1f176204230438fe52808f4e1c7944053c9eec0e649b237539  $OUT/dtc-1.7.2.tar.xz" | sha256sum -c -
tar -xJf "$OUT/dtc-1.7.2.tar.xz" -C "$OUT"
make -C "$OUT/dtc-1.7.2" fdtoverlay
export DTC17="$OUT/dtc-1.7.2"
export LD_LIBRARY_PATH="$DTC17/libfdt${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

上述构建使用宿主机 C 编译器和 make。将新 fdtoverlay 的绝对路径传给固件导出入口。来源及发布校验清单见 [kernel.org DTC 目录](https://www.kernel.org/pub/software/utils/dtc/) 和 [SHA-256 清单](https://www.kernel.org/pub/software/utils/dtc/sha256sums.asc)。
