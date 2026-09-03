# UFI003 Android Control Center v0.1.0 验收记录

日期：2026-09-03（Asia/Shanghai）

## 设备基线

- SoC：Qualcomm MSM8916
- 系统：Android 4.4.4 / API 19
- ABI：armeabi-v7a
- 固件：UFI003 原厂 userdebug/test-keys
- 外部卡槽：用户确认未插卡
- 当前逻辑 UICC 通道：厂商 SIM 开关通道 1；基带实时读取为 46011（中国电信），SIM READY，疑似主板内置/焊接卡或云卡模块
- 当前蜂窝状态：信号约 -64 dBm，但 Android 电话框架无服务、网络类型 Unknown

## APK 验收

- 包名：`com.luke.openstick`
- 版本：`0.1.0-readonly`
- 文件：`dist/OpenStick-Control-readonly-v0.1.0.apk`
- SHA-256：`9984B5E45AEEB59EEE11D93E68822E6C8C0D0E1B32C228C98EA42BBBD658B45E`
- APK v1/v2 签名校验：通过
- 最低系统版本：API 19
- `SEND_SMS` 权限：未声明

## 实机结果

- ADB 安装：成功
- 进程与 HTTP 服务启动：成功
- `/api/health`：成功，readonly
- `/api/status`：成功，SIM READY / 46011 / serviceState 1
- `/api/messages?limit=50`：成功，当前 0 条
- 普通重启后自动启动：成功；厂商系统约在开机 27 秒发送 BOOT_COMPLETED
- 480×854 页面视觉检查：通过

## 未验证与边界

- 未发送任何短信。
- 未做单次入站短信实测；当前逻辑 UICC 未注册业务网络。
- 未切换 SIM/eSIM Profile，未修改网络模式/APN。
- 未取得 root，未刷 boot/system/modem，未写 NV/QCN/EFS/MCFG。
- 原厂 Android 缺少 IMS Binder 服务、IMS APK 和 IMS daemon；本 APK 无法补齐 VoLTE/VoWiFi。
