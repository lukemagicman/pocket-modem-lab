# UFI003 Reliance MCFG 启动钩子

## 目的

第二根棒在整机启动时由MPSS侧恢复`Commercial-SRLTE-SS-CT`，导致
IMS/IMSP/IMSA QMI服务消失。本钩子在ModemManager接管前检查PDC software
配置；若不是现有`Commercial-Reliance`，则执行Set Selected和Activate，等待
基带重启完成后再允许ModemManager启动。

## 文件

- `ufi003-select-reliance.py`：通过设备现有libqmi GI接口执行检查、选择和激活。
- `ufi003-reliance-mcfg.service`：systemd oneshot服务，排序在ModemManager之前。
- QMI字符设备不生成systemd device unit，因此由Python脚本最多等待40秒设备节点，
  避免systemd等待不存在的`dev-wwan0qmi0.device`。

## 预期影响

- 首次或每次CT冷启动时会多一次基带子系统重启，预计增加10–20秒。
- 该MPSS在Activate后会主动断开QMI端点而不返回常规完成指示；脚本等待12秒后
  使用新的PDC连接复核Reliance确为active，复核成功才放行ModemManager。
- 不加载外部MCFG，不修改SIM，不直接写NV/QCN或eMMC EFS分区。
- 目标ID是设备中已存在的`Commercial-Reliance`：
  `F8:65:20:0A:37:94:52:73:8A:56:9B:AD:C1:3E:ED:9F:EB:5C:6C:F4`。

## 安装位置

- `/usr/local/sbin/ufi003-select-reliance`
- `/etc/systemd/system/ufi003-reliance-mcfg.service`

## 回滚

先执行`systemctl disable --now ufi003-reliance-mcfg.service`。确认不再启用后，
可移除上面两个安装文件并执行`systemctl daemon-reload`。即使不移除文件，禁用
服务也会停止开机切换；下次冷启动将自然恢复CT。
