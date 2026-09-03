# Reliance active时EFS分区只读快照

用途：在 PDC Set Selected + Activate 已使 `Commercial-Reliance` 成为 active、但
尚未整机重启时，读取 `modemst1`、`modemst2`、`fsg`、`fsc`。用于与冷启动恢复
CT后的快照逐字节对比，定位PDC选择状态是否写入这些持久分区。

数据来源：第二根 UFI003 当前 eMMC 分区，只读采集。

