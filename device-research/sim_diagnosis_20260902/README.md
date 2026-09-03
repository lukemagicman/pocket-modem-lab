# 第二根UFI003 SIM missing诊断

目标：在不发送APDU、不修改SIM/NV/QCN/设备树的前提下，区分ModemManager
误判、基带UIM状态、射频功能状态和物理SIM电气故障。

数据来源：设备运行时只读`mmcli`、QMI UIM/DMS/NAS、AT状态、内核日志、
regulator debug信息。

用户随后确认测试时卡槽内没有插SIM卡。因此`no-atr-received`、
`UimUninitialized`和`CME ERROR 10`均符合空卡槽预期，不构成设备故障证据。
取消UIM电源循环和硬件/设备树故障追查。下一步应断电插入目标SIM，再重新采集
UIM、DMS、NAS和IMS注册状态。
