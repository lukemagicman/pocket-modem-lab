# UFI003 WiFi Calling 只读能力审计

审计时间：2026-08-31  
设备：UFI003 4G Modem Stick / MSM8916 / Debian 13 ARM64  
边界：未进行蜂窝注册、短信发送、eSIM 写入、Modem NV 修改、固件刷写或真实 VoWiFi 测试。

## 结论

USB Reverse Internet 底座已经可用，但当前设备固件与 Linux 用户态尚不具备可直接启用的 WiFi Calling 运行栈。

当前状态应定义为：

- 外部 Internet 上游：已就绪
- Linux IPSec 基础能力：具备
- QMI Voice：可用
- QMI IMS / IMSA / IMSP：当前固件接口不可用
- ePDG / IMS 用户态服务：未安装、未运行
- VoWiFi：当前固件/软件栈不支持直接配置
- 最终硬件能力：仅凭本次只读审计不能判定永久不支持

## 证据

### 外部上游

- 活动上游：`usb0`
- 地址：`192.168.137.28/24`
- 网关与 DNS：`192.168.137.1`
- 真实联网检查：`online`
- HTTPS 检查端点：`https://connect.rom.miui.com/generate_204`

### Modem 与 QMI

- 基带固件：`UFI003_CT 20211210 1 [Nov 04 2016]`
- ModemManager：`1.24.0`
- libqmi/qmicli：`1.36.0`
- QMI 服务包含：WDS、DMS、NAS、WMS、AUTH、VOICE、UIM、PDC、DSD 等。
- `VOICE get-config` 能读取传统语音配置，说明 QMI Voice 通道可用。
- 以下只读 IMS 查询均返回 `InvalidServiceType`：
  - IMS Services Enabled Setting
  - IMSA Registration Status
  - IMSA Services Status
  - IMSP Enabler State

这表明 libqmi 客户端虽然支持这些命令，但当前 Modem 固件没有在该 QMI 控制端口提供相应服务。

### 运营商配置

PDC 中存在 6 个软件配置，当前激活的是：

`Commercial-CSFB-SS-CU`

其名称明确指向中国联通 CSFB。其他配置包含 CT SRLTE、CMCC CSFB 等，但没有发现名称明确的 VoLTE、VoWiFi 或 IMS 配置。

### Linux 网络与 IPSec

内核已启用：

- XFRM / XFRM_USER
- ESP / NET_KEY
- AES / GCM
- conntrack / NAT / masquerade
- IPv4 forwarding

但当前：

- 没有活动 XFRM state/policy
- 没有 UDP 500/4500 监听进程
- 没有 strongSwan、Libreswan、oFono 或厂商 IMS/ePDG 守护进程
- 固件文件中未检出明显的 `IMS`、`ePDG`、`VoWiFi` 字符串；此项不能单独作为不支持的最终证据

## 主要阻塞点

1. 当前基带没有暴露可用的标准 QMI IMS/IMSA/IMSP 服务。
2. 当前激活的是 CSFB 运营商配置，不是明确的 IMS/VoWiFi 配置。
3. Debian 用户态没有 Qualcomm 厂商 IMS、EAP-AKA、ePDG/IKE 与语音集成组件。
4. 没有有效 SIM，无法确认运营商侧是否开通 VoWiFi，也无法进行 IMS/ePDG 注册验证。

## 风险判断

WiFi Calling 不是增加一个 WebUI 开关即可完成。继续底层开发可能涉及兼容基带固件、运营商 MBN、厂商 IMS 二进制、EAP-AKA、ePDG 与 Modem NV；其中刷写固件或修改 NV 具有变砖及丢失蜂窝能力风险，不应在当前阶段进行。

## 建议的安全下一步

在“移动网络”页面增加只读 WiFi Calling 状态卡，不提供虚假开关：

- 外部网络：USB 上游已连接
- IMS 接口：当前固件未提供
- ePDG：未配置
- SIM/运营商：等待有效 SIM 验证
- 当前结论：需要兼容固件与 IMS 运行栈

高级详情中再展示 QMI、PDC、XFRM 等证据。等有有效 SIM、明确兼容固件和完整回滚方案后，再进入真实 VoWiFi 实验。

## Wi-Fi 状态说明

审计时 `wlan0` 热点为关闭状态。用户随后确认这是本人主动关闭，并非 USB 上游或 NetworkManager 故障，因此不列为兼容性风险。
