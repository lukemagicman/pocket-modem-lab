# Pocket Modem Lab

面向 UFI003 / Qualcomm MSM8916 USB 蜂窝终端的实验、控制与可复现研究仓库。

本仓库整理了三个相互关联的工作方向：

- `control-center/`：设备 Web 控制台、短信、网络、代理、eSIM 防护与离线测试。
- `android-client/`：兼容 Android 4.4.4（API 19）的只读设备端客户端。
- `device-research/`：GPT、boot/DT、QMI/PDC/MCFG 与 SIM 路径的研究脚本和脱敏记录。
- `docs/`：产品化风险、安全边界及仓库说明。

## 安全边界

仓库默认以只读检查和可回滚实验为原则。不要在不了解设备备份与恢复流程时写入 boot、GPT、PDC/MCFG、NV、QCN、EFS、SIM 或 eUICC。

以下内容不会进入 Git：

- 原始 eMMC/分区备份、rootfs 与 boot 镜像；
- 调制解调器固件、运营商 MBN/MCFG 和第三方刷机包；
- SDK/JDK/Gradle 缓存、构建产物与 APK；
- 短信正文、电话号码、IMEI/IMSI/ICCID/EID、订阅地址、密钥和密码；
- 仅用于本机交接的工作记忆与绝对路径配置。

这些排除项有的超过 GitHub 文件限制，有的包含个人或设备数据，也可能受第三方许可约束。仓库保留由本人编写的源码、测试、说明和可公开的实验结论。

## 快速开始

Web 控制台的离线检查：

```powershell
cd control-center
.\tools\check.ps1
```

Android 客户端的本机构建：

```powershell
cd android-client
.\build-local.ps1
```

底层研究脚本具有不同风险等级。运行前请先阅读对应目录的 README 和 [安全说明](SECURITY.md)。

## 兼容性说明

部分脚本、服务名、Android 包名和历史文档仍含 `openstick` 字样。这些是已经部署到设备上的兼容标识或上游技术名，并非本项目名称。贸然修改会破坏升级、回滚或 Android 包兼容性。

## 状态

这是实验性个人项目，不保证适用于所有同外观硬件。UFI003 同名设备可能使用不同主板、分区布局和基带固件；执行写操作前必须核对硬件版本并保存可验证的备份。

## 许可

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)，允许个人、教育、公共研究及其他非商业目的使用、修改和分发，禁止商业用途。

由于包含非商业限制，本项目属于 source-available（源码可见），不是 OSI 认可的 open source。第三方名称和材料仍受各自许可证约束；本仓库不授权重新分发固件或其他第三方二进制材料。
