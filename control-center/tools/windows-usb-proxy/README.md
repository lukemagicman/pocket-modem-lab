# OpenStick Windows USB 下载代理

## 用途

当 Windows ICS 无法稳定转发时，把 OpenStick 的 eSIM HTTPS 下载请求经 USB 转入电脑上的 Clash HTTP 代理。

链路：

`OpenStick 192.168.137.28 -> Windows 192.168.137.1:17897 -> Clash 127.0.0.1:7897 -> Internet`

## 安全边界

- 只监听 USB 私有地址 `192.168.137.1`，不监听 WLAN 或公网地址。
- 不包含订阅、代理密码、eSIM 激活码或卡片标识。
- 仅转发 TCP；SM-DP+ 内容仍由 HTTPS 加密。
- 关闭程序后代理立即失效。

## 启动

确认 Clash Verge 正在运行，Windows 的 `以太网 6` 地址为 `192.168.137.1`，然后执行：

```powershell
py -3.14 .\openstick-usb-proxy.py
```

保持窗口运行，完成 eSIM 下载后按 `Ctrl+C` 关闭。

## 验证

控制台 `/api/esim-network` 应显示：

```json
{"interface":"usb0","safe_for_download":true,"transport":"usb_proxy"}
```
