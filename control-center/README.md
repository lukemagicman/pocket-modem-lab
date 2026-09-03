# Pocket Modem Lab Control Center

UFI003 / MSM8916 的本地蜂窝终端控制台。项目以桌面端为主，同时支持 iPad 和手机布局。

## 当前稳定版本

`2026.09.01.2`

当前基线包含：

- 产品化 WebUI；
- 短信会话、通讯录和失败重试界面；
- 设备健康、温度、流量、网络和脱敏诊断；
- USB Reverse Internet 管理与失败回滚；
- Wi-Fi 默认关闭、仅手动开启；
- no-SIM VoWiFi 前置代码和离线测试；
- 运行文件版本及 SHA-256 展示。

## 目录

- `frontend/index.html`：当前 WebUI。
- `backend/openstick-sms-web.py`：控制台 HTTP API。
- `services/openstick-uplink-manager.py`：USB 上游切换与回滚。
- `windows/openstick-windows-ics-guard.ps1`：Windows ICS 保护脚本。
- `vowifi/`：严格禁用卡 I/O 的 VoWiFi 前置代码。
- `tests/`：离线回归测试。
- `tools/check.ps1`：一键回归检查。
- `baselines/`：2026-09-01 修改前基线。
- `docs/`：交接、审计与维护说明。

## 一键检查

只检查本地代码：

```powershell
.\tools\check.ps1
```

附加设备只读检查：

```powershell
.\tools\check.ps1 -DeviceUrl http://192.168.68.1:8080
```

检查不会发送短信、启用蜂窝、打开 Wi-Fi、执行 APDU 或写入 eSIM。

## 安全边界

- 未经 Luke 明确授权，不读取或写入 SIM/eSIM，不发送 APDU，不运行 AKA；
- 不修改 PDC、NV、QCN 或基带固件；
- 部署前必须保存设备当前文件和 SHA-256；
- UI、后端与 Uplink Manager 必须作为同一发布版本验证；
- 不把密码、短信正文、电话号码、订阅地址或 Token 提交到 Git。

历史背景见 `docs/UFI003_PROJECT_HANDOFF_20260831_COMPLETE.md`。
