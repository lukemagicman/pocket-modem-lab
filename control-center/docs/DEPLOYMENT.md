# 部署与回滚

## 设备目标路径

| 本地文件 | 设备路径 |
|---|---|
| `frontend/index.html` | `/usr/local/share/openstick-ui/index.html` |
| `backend/openstick-sms-web.py` | `/usr/local/sbin/openstick-sms-web.py` |
| `services/openstick-uplink-manager.py` | `/usr/local/sbin/openstick-uplink-manager.py` |

## 部署顺序

1. 只读确认当前设备 IP、健康接口和 Wi-Fi 状态。
2. 下载设备当前文件并计算 SHA-256。
3. 在 `/var/backups/openstick-ui/` 创建本次恢复点。
4. 新文件上传到 `/tmp/*.new`。
5. 后端先执行 `python3 -m py_compile`。
6. 安装前端、后端；只重启 `openstick-sms-web.service`。
7. 验证服务、HTTP、`/api/health`、`/api/build`、`/api/uplink`、`/api/wifi`。
8. 确认 WebUI、后端、Uplink Manager 哈希与预期一致。

本项目不提供自动无确认部署脚本，避免地址变化或凭据错误时覆盖设备基线。

