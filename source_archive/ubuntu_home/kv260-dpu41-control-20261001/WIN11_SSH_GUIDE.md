# Win11 直连 KV260

当前配置：Win11 以太网 `192.168.50.1`、掩码 `255.255.255.0`；板卡 `192.168.50.2/24`。此直连连接无需填写默认网关和 DNS。板端 ping Win11 已通过；IPv4 SSH 服务响应正常。用户随后已确认 Win11 SSH 登录成功。

## 登录

在 Win11 打开 PowerShell：

```powershell
ssh root@192.168.50.2
```

首次出现主机身份确认提示时确认目标是直连的板卡，再输入 `yes`。随后输入板卡 root 密码；输入时不显示字符。密码不要发送到聊天。若密码未知，可通过已连接的串口另行设置，本次未修改密码。

如果连接失败，在 PowerShell 检查并保留输出：

```powershell
Test-NetConnection 192.168.50.2 -Port 22
```

## 已核实的主机密钥变化

Win11 报告旧 `known_hosts` 第 2 行与备用卡当前 RSA 密钥不一致。通过独立串口读取板端 RSA 公钥并计算 SHA-256，确认与 Win11 显示完全一致：

```text
SHA256:+cA3ZLx8WYwZMvqJNEFiPHal6a9Hg+S3/H99r8e7P98
```

证据：[rsa_public_key.output](evidence/test_card_board_20261001/09-ssh-hostkey.rsa_public_key.output)。只读取公钥，未读取或修改私钥。

在 Win11 PowerShell 移除该 IP 的旧记录，然后重新连接：

```powershell
ssh-keygen -R 192.168.50.2
ssh root@192.168.50.2
```

确认新提示指纹与上方一致后输入 `yes`，再输入板卡 root 密码。未关闭主机身份检查；用户随后确认 Win11 SSH 登录成功。

## 网络配置及恢复

板端配置文件为 `/etc/systemd/network/10-kv260-win11-direct.network`：

```ini
[Match]
Name=eth0

[Network]
Address=192.168.50.2/24
DHCP=no
```

若以后改接有 DHCP 的路由器，可在串口 root 终端将此文件重命名为 `10-kv260-win11-direct.network.disabled`（先确认该备份文件不存在），然后执行 `networkctl reload`、`networkctl reconfigure eth0`，恢复原 `80-wired.network` 的 DHCP 配置。此恢复尚未执行。
