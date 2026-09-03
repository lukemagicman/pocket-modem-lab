# UFI003 第二根棒 Debian 只读基线

用途：验证 `MPSS.DPM.2.0.2.c1-00178-M8936FAAAANUZM-1` 在原始 NV/MCFG 状态下是否发布 IMS QMI services。

## 结论

- Debian 12、Linux 6.7 已启动，内部QMI端口为 `/dev/wwan0qmi0`。
- 实际运行固件：`UFI003_CT 20211210 1 [Nov 04 2016 02:00:00]`。
- QMI service list 不含 `0x12 IMSS`、`0x1e IMSA`、`0x1f IMSP`。
- 当前active software MCFG：`Commercial-SRLTE-SS-CT`。
- 已装但inactive的VoLTE候选：`Commercial-Reliance`。
- 当前ModemManager状态为 `sim-missing`；不影响QMI service-publication基线，但会影响后续真实IMS注册。

## 数据来源

- 第二根棒原厂 `modem.bin`、`modemst1/2`、`fsg`、`fsc` 备份。
- 设备运行时 `qmicli --get-service-version-info`、DMS revision和PDC只读查询。
- 原始备份目录：`D:\4G\UFI003-analysis\backup\second_stick`。

## 安全边界

本基线阶段没有修改PDC、NV、QCN或SIM。恢复点为第二根棒全量EDL备份及SHA256 manifest。

## Reliance PDC A/B结果

在相同MPSS、相同NV/校准数据、无SIM状态下：

1. 停用 `Commercial-SRLTE-SS-CT`。
2. 激活设备中已存在的 `Commercial-Reliance`。
3. modem子系统重启后，QMI列表立即新增：
   - `ims (1.0)`，对应IMSS/IMS Settings（0x12）
   - `imsp (1.0)`（0x1f）
   - `imsa (1.0)`（0x1e）
4. 整机冷重启后，active profile自动恢复为CT SRLTE，三个IMS服务同步消失。

结论：MCFG/PDC配置能够直接或通过MPSS feature gate控制IMS QMI service publication；SIM不是这些服务出现的必要条件。另有启动期自动MCFG选择/持久化机制需要继续定位。

## Selected-config持久化结果

- PDC Get Selected确认冷启动基线为active CT、无pending。
- Set Selected Reliance后变为active CT、pending Reliance。
- Activate后变为active Reliance、无pending，IMS三服务出现；说明标准PDC选择流程本身有效。
- 该选择可跨modem子系统重启，但整机重启后仍恢复CT且IMS三服务消失。
- 下一项最有区分力的实验是：开机前禁用ModemManager，冷启动后立即读取PDC。它能把覆盖源一刀切分为userspace侧或modem/NV/platform侧。

## ModemManager隔离实验结果

- ModemManager在冷启动前被禁用；启动后复核为`disabled/inactive`。
- 即便如此，PDC仍恢复`Commercial-SRLTE-SS-CT`，pending为空，IMS三服务缺失。
- 所以覆盖源不是Debian ModemManager，而在MPSS/EFS/NV或更早的平台选择路径。
- 实验后ModemManager已恢复`enabled/active`。
- Reliance active与冷启动CT active两种状态的modemst1/2、fsg、fsc完整SHA256全部相同，说明当前PDC选择没有落盘到这些分区。
- 最快工程路线：安装一个可回滚的启动钩子，在ModemManager接管前重放Reliance Set Selected+Activate。

## 启动钩子最终验证

- 已安装并启用`ufi003-reliance-mcfg.service`。
- 该MPSS Activate后会主动断开QMI端点；修正版等待端点重启，并使用新的PDC连接复核Reliance active后才退出成功。
- 已连续完成两次修正版冷启动验证：两次均从CT自动切至Reliance，服务`status=0/SUCCESS`，ModemManager正常active。
- 两次均确认`ims (1.0)`、`imsp (1.0)`、`imsa (1.0)`存在。
- 本地安装包及回滚说明位于`D:\4G\UFI003-analysis\boot_hook_reliance`。
