# Pocket Modem Lab Android Client

面向 UFI003 原生 Android 4.4.4（API 19）的轻量控制中心实验项目。

## 当前用途

- 读取脱敏后的 SIM、运营商、网络类型和服务状态。
- 通过 Android 短信 Provider 读取短信列表。
- 监听新短信广播并保持本地服务可用。
- 在 `127.0.0.1:18081` 提供只读 HTTP 页面/API，通过 ADB 端口转发验收。

当前版本不发送短信、不切换 SIM、不修改网络模式、不操作 eSIM/MCFG/NV/QCN，也不对局域网开放端口。

## 数据来源

- Android `TelephonyManager` 与 `ServiceState`。
- Android `content://sms` Provider。
- 本机对 UFI003 原厂 Android 4.4.4 的只读 ADB 审计结果。

## 构建与验证

项目使用纯 Java、无第三方运行库，最低兼容 API 19。构建需要 JDK 17 与 Android SDK；仓库自带 Gradle Wrapper，首次构建会下载 Gradle 8.2。

本机可运行：

```powershell
.\build-local.ps1
```

如 Android SDK 不在默认位置，请创建不提交到 Git 的 `local.properties`：

```properties
sdk.dir=C\:\\path\\to\\Android\\Sdk
```

实机交付包不纳入 Git；请从源码构建或从可信发布页获取。

- SHA-256：`9984B5E45AEEB59EEE11D93E68822E6C8C0D0E1B32C228C98EA42BBBD658B45E`
- 已在目标 Android 4.4.4 棒子上安装并启动。
- 已验证开机约 27 秒后自动拉起服务。
- 已验证 health、status、messages 三个只读接口。
- 已完成 480×854 实机截图检查：`qa/device-main.png`。

验收接口：

- `/api/health`
- `/api/status`
- `/api/messages?limit=50`

短信正文只经设备本机回环地址返回；正式对局域网开放前必须增加认证与敏感字段保护。

## 当前结论

Android 普通 APK 路线已证明能直接读取系统短信 Provider，并能做开机常驻和本机 Web API。外部卡槽实际未插卡；基带仍能从厂商 SIM 开关当前选中的逻辑通道 1 读取一张中国电信 UICC（SPN、EF_AD 和短信存储参数均有实时读取记录），因此这不是简单的属性缓存。该通道可能连接主板内置/焊接卡或云卡模块，但目前电话框架仍处于无服务，尚不能证明真实入站短信；进一步切换其他逻辑通道需单独授权。
