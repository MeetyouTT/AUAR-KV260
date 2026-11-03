# 2026-10-17 微力同步pytest缓存权限报错

用户截图显示“项目-暂未完成的列表”，唯一项为 `共享文件夹\aura\.pytest_cache`，提示“没有权限访问该目录”。本轮按缓存同步故障处理，未改业务代码或板端服务。

## 实际检查

Ubuntu的 `/home/ghmd/Win共享文件/共享文件夹/aura/.pytest_cache` 是空普通目录，owner/group均1000/1000（ghmd），权限0775，标准ACL，当前用户可读写/遍历；父路径也可访问。微力进程以UID1000运行。不能据此把根因认定为Ubuntu缓存权限错误，也未取得Windows侧ACL或完整错误日志。

微力 `folder list` 确认当前项目同步根为 `/home/ghmd/Win共享文件`。其实际忽略文件为 `.verysync/ignoreList`，没有现成的pytest缓存规则。共享文件夹下另一份.verysync标记未作为当前配置修改。

查阅官方 [忽略说明](https://www.verysync.com/manual/users/ignoring.html)：普通文件名模式可匹配各层同名目录；忽略列表只在本机生效。依据本机实际文件名ignoreList进行修改，未因手册大小写差异新建另一个文件。

## 修改与验证

在 `/home/ghmd/Win共享文件/.verysync/ignoreList` 末尾追加注释和 `.pytest_cache` 一条规则。原文件完整备份到 `/home/ghmd/aura-sync-inventory-20261017/verysync-cache-fix/`，新增内容、原规则逐字节前缀保留、0600权限保持均通过。SHA256 `bd11eff6d7682560595e663db4cebf25c1caf6ef75ec34150bc7316f6cdfa2a7`，核验见该目录validation.json。

没有删除缓存、修改目录权限、改变同步模式或覆盖任务。未修改源码、模型及其他忽略规则，未重启同步/板端服务。无需运行项目测试。

管理接口查询最初被沙箱回环网络限制，工具授权后完成目录列表读取。CLI collection dump-json语法不支持，改用已有folder list；未输出配置密钥、设备密钥或密码。

Windows端需在“项目→选项设置→忽略列表”添加同一 `.pytest_cache` 并保存，再重新扫描/重试。Windows端忽略尚未修改，界面错误是否消失及最终同步完成状态尚待用户验证，不将Ubuntu文件规则已写入等同于Windows同步完成。
