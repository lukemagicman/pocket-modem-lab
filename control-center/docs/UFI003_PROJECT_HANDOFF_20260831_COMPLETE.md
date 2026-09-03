# UFI003 / OpenStick Control Center 完整跨电脑交接

> 交接日期：2026-08-31（北京时间）  
> 目标：换电脑后，让新的 Codex 不依赖原对话即可理解现状、连接设备、验证基线并继续开发。  
> 当前原则：设备没有用于本轮验证的有效 SIM/eSIM；禁止把“可见卡状态”视为用户授权，禁止未经确认进行 APDU、AKA、蜂窝负载或 eSIM 写入。

## 1. 新电脑上的 Codex 先做什么

1. 解压交接包到独立目录，不要直接覆盖设备文件。
2. 完整阅读本文件、`project/PROJECT_HISTORY_README.md`、`vowifi/WiFi_Calling_只读能力审计_20260831.md`。
3. 向 Luke 询问当前设备连接方式、IP 与密码。交接包故意不保存明文密码。
4. 先做只读检查：控制台 HTTP、`/api/health`、`/api/uplink`、`/api/wifi`。
5. 对照 `MANIFEST_SHA256.txt` 验证文件完整性。
6. 在任何部署前保存设备当前文件，并建立带日期的恢复点。
7. 没有 Luke 明确授权时，不碰 SIM/eSIM/APDU/PDC/NV/QCN/固件，不主动制造蜂窝、短信、温度或流量负载。

可直接给新 Codex 的第一条消息：

```text
请完整阅读本压缩包中的 UFI003_PROJECT_HANDOFF_20260831_COMPLETE.md 和 README.md。先只读核对设备当前状态与文件哈希，不要写入设备，不要访问 SIM/APDU/eSIM/PDC/NV/固件，也不要执行蜂窝、短信、温度或流量负载。先向我汇报当前状态、差异、风险与下一步方案，得到确认后再修改。
```

## 2. 项目定位

硬件为 UFI003 / MSM8916 OpenStick。目标不是传统路由器后台，而是低信息噪音、强状态表达、可在 Windows/iPad/手机使用的蜂窝终端控制台，视觉方向接近 Clash Verge、macOS 设置和现代桌面消息客户端。

长期功能范围：

- USB、Wi-Fi、蜂窝网络管理；
- 短信会话、通讯录、发送、删除、置顶、失败重试；
- 通知/邮件自动转发；
- eUICC/eSIM 管理；
- 温度、流量、存储、系统诊断；
- sing-box/代理与未来远程出口；
- USB Reverse Internet；
- WiFi Calling / VoWiFi 可行性研究；
- 产品化所需的备份、回滚、安全和批量部署。

## 3. 2026-08-31 收尾时的真实设备状态

以下状态在交接文件生成前通过设备 HTTP API 重新读取，不是历史推断：

- 当前控制台：`http://192.168.137.28:8080/`
- 活动上游：`usb0`
- USB 地址：`192.168.137.28/24`
- Windows ICS 网关/DNS：`192.168.137.1`
- Internet：`true`
- 连通检查：`passed`
- USB 角色：`uplink`
- Wi-Fi 热点：关闭
- Wi-Fi 自动连接：关闭
- 蜂窝接口：离线
- 设备温度：约 `49 °C`
- 可用存储：约 `2.3 GB`
- 健康状态：`healthy=true`
- 7 项必要服务正常：Web、短信收件、通知、自动蜂窝、Windows RNDIS、mDNS、防火墙。
- sing-box、轻量 SOCKS、HTTP Proxy 在收尾时为禁用/停止；这与 2026-08-30 的旧记录不同，以本节实时结果为准。

当前 USB 上网路径：

```text
Clash Verge Meta Tunnel
  -> Windows Internet Connection Sharing
  -> OpenStick RNDIS / usb0
  -> 192.168.137.28
```

注意：USB 作为上行时，旧管理地址 `192.168.68.1` 通常不再使用。换电脑后 Windows ICS 可能重新分配地址，必须先从新电脑的网卡/共享状态确认，不能盲目写死 `192.168.137.28`。

## 4. 当前部署基线与哈希

设备端主要路径：

```text
/usr/local/share/openstick-ui/index.html
/usr/local/sbin/openstick-sms-web.py
/usr/local/sbin/openstick-uplink-manager.py
/var/backups/openstick-ui/
```

当前基线：

| 组件 | 交接包文件 | SHA-256 |
|---|---|---|
| WebUI | `project/current/openstick-ui-v8-product-polish.html` | `274cf0110a83137c95425cc44ce2ef049572d622f64e124956b40197ac92b773` |
| 后端 | `project/current/openstick-sms-web-uplink-phase4-vowifi-prereq.py` | `75ed4e604dc1307781425be008d98b612c2e2075c4125bd9cc2afafc5ecf54e5` |
| Uplink Manager | `project/current/openstick-uplink-manager.py` | `5ef3150a850fafb1a50981ea25a4b987882d07ea93ef57b2822bced9527719d5` |
| Windows ICS Guard | `project/current/openstick-windows-ics-guard.ps1` | `9397b3225ee7afa3ebf2b71b4160ae20bbb4af0a92e2b37c8c6c9b9202051bfb` |
| 上一版后端 | `project/rollback/openstick-sms-web-uplink-phase4-wifi-default-off.py` | `6c80dd9c34058805b2299f39a0eab667dce545627e06122c45af29715b3a24b4` |

WebUI 已通过 HTTP 下载字节哈希与本地文件比对，结果完全一致。

设备恢复点中最相关的目录：

```text
/var/backups/openstick-ui/pre-vowifi-poc-phase0-20260831/
/var/backups/openstick-ui/pre-uplink-status-merge-20260831/
/var/backups/openstick-ui/pre-wifi-default-off-20260831/
/var/backups/openstick-ui/pre-ics-success-test-20260831/
/var/backups/openstick-ui/pre-usb-reverse-phase4-20260831/
```

`pre-uplink-status-merge-20260831/openstick-sms-web.py` 已下载到交接包，哈希为上一版后端的 `6c80...24b4`。

## 5. 今天完成的 WebUI / UX 工作

### 5.1 短信页

短信页从普通后台表单改成桌面消息客户端结构：

- 三栏布局：左侧会话、中间对话、右侧通讯录；
- 三栏之间可拖动改变宽度，拖动时不出现突兀蓝色条纹；
- 左侧会话和右侧通讯录各自滚动；
- 新建短信改为左栏右下角悬浮加号；
- 输入号码或文字时提供通讯录候选；
- 通讯录固定在右侧，新建联系人通过简洁入口和抽屉/编辑界面完成；
- 联系人字段保持轻量，避免设备存储浪费；
- 对话底部可直接输入并发送短信，不再弹资费二次确认；
- 时间移到气泡外，降低权重；时间按设备系统时间/北京时间呈现，不显示 `UTC-07:00`；
- 发送失败错误放到气泡外，气泡只保留短信正文；
- 发送失败有红色状态、简化错误文案和圆形重试按钮；
- 删除不再长期显示 `×`，改为右键菜单/长按滑动入口；
- 新增会话/联系人置顶入口；
- 弹窗遮罩减淡，避免整页变黑；
- 桌面、iPad、手机响应式布局均有过程和最终截图。

短信已有功能不能因后续视觉修改被破坏：读取、联系人、新建、发送、刷新、删除、置顶、失败重试、邮件自动转发、USB/设备状态。

### 5.2 总览与设计系统

- 页面主体扩宽，减少宽屏无意义留白；
- 去除重复标题和传统 Admin Template 感；
- 统一字体、间距、12–16 px 容器圆角、8–10 px 控件圆角、浅蓝灰边框和克制阴影；
- 统一状态语言，区分 USB 管理、Modem、蜂窝服务、短信服务；
- 无 SIM、无服务、连接中、漫游、错误等采用完整空状态/提示；
- 顶部显示设备系统时间，而不是浏览器自身时区；
- 温度和流量监控各自拥有时间窗口控制，坐标以当前实时为主；
- 可用存储补充总容量；
- 诊断页展示必要服务明细，可展开查看真实服务名和状态；
- 无 SIM 提醒可关闭，蜂窝恢复时自动消失，未来再次异常会重新出现；
- 移动网络普通模式占满宽度，不为隐藏高级参数保留空列；
- 高级 Modem/QMI/AT 信息折叠到高级模式；
- 完成桌面宽屏、iPad 横屏、iPad 竖屏、390 px 手机检查。

## 6. USB Reverse Internet / Uplink Manager

### 6.1 能力审计

- `wcn36xx` 报告不支持 AP+STA 并发；Wi-Fi 上游与热点只能互斥；
- Windows RNDIS、Linux USB Gadget、NetworkManager 与路由基础可用；
- 不能直接把 `usb0` 从管理下游改上游而没有回滚，否则容易丢失控制台连接。

### 6.2 实现

- 新增只读 `GET /api/uplink`；
- 新增受管理员保护的 `POST /api/uplink/usb`，支持 prepare/enable/disable；
- `openstick-usb-uplink` 使用 DHCP、`autoconnect=no`；
- 启用前建立 30 秒 systemd 独立回滚任务；
- 激活失败、DNS/HTTPS 检查失败会恢复原 RNDIS 管理网络；
- Windows 侧 `openstick-windows-ics-guard.ps1` 在未确认时自动关闭 ICS 并恢复；
- Windows ICS 私有网关不响应 ICMP 只作为诊断，不直接判定断网；最终以 DNS 和轻量 HTTPS 204 检查为准。

### 6.3 实际验证

- 无 ICS 失败演练两次，约 11–12 秒恢复控制台；
- WLAN -> RNDIS 能获得地址，但 Windows 直连出口受 Clash 影响，完整 HTTPS 检查失败并自动回滚；
- 最终使用 `Meta Tunnel -> RNDIS` 成功，设备获得 `192.168.137.28/24`，DNS/HTTPS 通过；
- 修复 API 状态合并后，不再出现“Uplink Manager 已在线、页面仍 limited/not_run”的矛盾。

## 7. Wi-Fi 默认行为

Luke 明确要求 Wi-Fi 默认关闭，由本人决定是否开启：

- `openstick-failsafe` 的 `connection.autoconnect=no`；
- 手动开启仍可用，但重启后不会自行开启；
- 热点关闭时修改 SSID/密码/信道只保存配置，不顺带开启；
- 当前 `/api/wifi`：`connected=false`、`autoconnect=false`。

后续不要把 Wi-Fi 关闭误判为故障，也不要为了网络测试自动打开。

## 8. WiFi Calling / VoWiFi 研究状态

### 8.1 只读审计结论

- TUN、XFRM/ESP、AES/GCM、NAT、conntrack、USB 外部上游和资源基础通过；
- QMI Voice 可读取；IMS/IMSA/IMSP 查询返回 `InvalidServiceType`；
- 当前激活 PDC 为 `Commercial-CSFB-SS-CU`；
- 设备没有 ePDG、IMS、IKE/IPsec 用户态栈或活动 XFRM 隧道；
- 因此不能靠 WebUI 增加一个开关直接得到 WiFi Calling。

### 8.2 Phase 0

- 保存了系统、网络、QMI 能力和部署基线；
- Modem 报告 UIM 1.36、AUTH 1.3；
- qmicli 有 UIM logical channel/raw APDU，但没有现成 Authenticate 命令组；
- 曾只读看到 UIM Card Status 中有 USIM ready。Luke 没有授权把它用于本阶段，因此没有读取 IMSI/ICCID、没有发送 APDU。

### 8.3 Phase 1 无卡开发

- 完成 SIM Backend 抽象；
- 完成 QMI UIM logical-channel/raw-APDU 骨架；
- 默认 `allow_card_io=False`；
- 完成 AKA 响应解析和不保存挑战材料的 Mock Backend；
- RAND、AUTN、RES、CK、IK、AUTS 不进入日志；
- Python 标准库离线测试 12/12 通过；
- 没有把 Phase 1 SIM 代码部署到棒子。

参考实现判断：

- `pagecat/vowifi_gateway` 功能完整但容器/Fedora/Asterisk 体系对 MSM8916 过重，且示例会打印敏感 AKA/IKE 材料；
- `fasferraz/SWu-IKEv2` 可学习流程，但使用 PC/SC/AT+CSIM、GPL-3.0，并存在调试输出/回退材料风险；
- strongSwan 的 SIM/AKA 插件边界更成熟，`get_quintuplet()` 与 USIM AKA 数据匹配，但要评估许可证并开发定制 QMI 插件；
- 测试卡确认前不选定最终隧道引擎。若运营商为 classic EAP-AKA，可优先评估 strongSwan 自定义 SIM backend；若要求 EAP-AKA'，需要重新评估实现能力。

## 9. 今天明确没有做的事

- 没有短信真实发送/接收验证；
- 没有蜂窝注册或蜂窝流量负载；
- 没有温度压力测试；
- 没有 eSIM 下载、安装、启停、删除或 Profile 写入；
- 没有 USIM/ISIM 应用识别、IMSI/ICCID/EID 读取；
- 没有发送 APDU 或运行 AKA；
- 没有 PDC、NV、QCN、基带固件写操作；
- 没有安装 strongSwan/pagecat/SWu-IKEv2 到设备；
- 没有伪造 IMS/ePDG/蜂窝状态。

## 10. 部署与回滚规则

### 10.1 每次部署前

```text
1. 读取设备当前文件并计算 SHA-256。
2. 保存到 /var/backups/openstick-ui/<明确名称-日期>/。
3. 新文件先传到 /tmp/*.new。
4. Python 先 py_compile，HTML/JS 先做本地解析检查。
5. install 覆盖后只重启相关服务。
6. 验证 systemd active、HTTP 200、API、哈希与管理链路。
7. 失败立即使用本次恢复点回滚。
```

不要使用 `git reset --hard`、不要清空整个项目目录、不要覆盖设备唯一分区。`D:\codex` 当时是没有 commit 的大范围工作树，不能把它误当成这个项目的独立 Git 仓库。

### 10.2 当前后端快速回滚逻辑

若最新版后端造成问题，可恢复：

```text
/var/backups/openstick-ui/pre-uplink-status-merge-20260831/openstick-sms-web.py
  -> /usr/local/sbin/openstick-sms-web.py
  -> 重启 openstick-sms-web.service
```

执行前仍应核对当前路径、哈希和连接方式。交接包的 `project/rollback/` 有同哈希副本。

## 11. 安全与凭据

- 交接包不存明文 SSH/WebUI 密码；新电脑需要向 Luke 获取。
- 当前会话中曾使用用户提供的 SSH 凭据成功连接，但不应把聊天里的凭据继续扩散到压缩包。
- 邮箱授权码、通知 Token、代理订阅/节点密钥、eSIM 信息均不应进入日志、截图或交接文档。
- 控制台仍是本地 HTTP；只应在受信任 USB/本地管理网络访问。
- 不要把 SSH、WebUI 或代理入口暴露到蜂窝公网。

## 12. 关键文件导航

```text
README.md                                      包说明
UFI003_PROJECT_HANDOFF_20260831_COMPLETE.md    本文件
MANIFEST_SHA256.txt                            完整性清单

project/PROJECT_HISTORY_README.md              8/31 分阶段技术历史
project/current/                               当前部署源码
project/rollback/                              上一版可回滚后端
project/ui-baselines/                          UI 原始、v7、v7.1、v8 基线
project/backend-history/                       Phase 3/4 后端演进
project/screenshots/                           少量最终响应式检查图

vowifi/WiFi_Calling_只读能力审计_20260831.md
vowifi/phase0/                                 能力基线与部署副本
vowifi/phase1-nosim/                           SIM Backend、测试、参考评估

requirements/                                 用户原始任务与实施文档
context/                                      2026-08-30 项目交接和风险背景
```

## 13. 下一步建议

### 不插卡也能继续

1. 为 Uplink 状态合并补充更多纯函数测试；
2. 为 SIM Backend 增加严格 TLV/APDU 模糊测试，不连接设备；
3. 整理 future strongSwan plugin 的 C 接口设计，只写设计不安装；
4. 对 WebUI 做桌面/iPad/手机静态视觉检查；
5. 增加版本号、构建信息、导出脱敏诊断；
6. 把本项目建立为独立 Git 仓库，首次提交只纳入交接包中的干净源码，不纳入秘密或缓存。

### 插入明确测试卡后

必须再次得到 Luke 授权，并按递进方式进行：

1. 只读确认卡槽、USIM/ISIM AID 与运营商；
2. 不打印敏感数据地验证 logical channel；
3. 用测试向量/受控挑战验证单次 AKA，日志只留状态和长度；
4. 判断 classic AKA 还是 AKA'；
5. 再决定 strongSwan 插件或其他隧道实现；
6. 最后才涉及 ePDG 发现、IKEv2、策略路由和 UI 状态。

### 产品化优先级

稳定性与恢复 > 安全与可维护性 > UI 完善 > 新功能。不要因为“能跑”就跳过长时间运行、断线恢复、USB 拔插、温控、升级回滚和唯一分区保护。

## 14. 接手验收清单

- [ ] 能阅读本交接文件和哈希清单；
- [ ] 已从 Luke 获取新电脑上的设备连接信息；
- [ ] 控制台 HTTP 可访问；
- [ ] `/api/health`、`/api/uplink`、`/api/wifi` 已只读保存；
- [ ] 当前设备文件已下载并与包内基线比较；
- [ ] 已确认 Wi-Fi 关闭是用户预期；
- [ ] 没有把历史 sing-box 状态当成当前状态；
- [ ] 没有碰 SIM/APDU/eSIM/PDC/NV/固件；
- [ ] 在修改前已向 Luke说明目标、改动、风险和回滚；
- [ ] 修改后分别检查桌面、iPad 横竖屏和手机。

完成以上步骤后，项目即可在新电脑上安全续接。
