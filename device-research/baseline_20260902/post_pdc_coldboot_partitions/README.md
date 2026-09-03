# PDC实验后EFS分区只读快照

用途：在 Reliance Set Selected + Activate、随后整机冷启动恢复 CT 后，读取
`modemst1`、`modemst2`、`fsg`、`fsc`，与第二根棒刷机前原厂备份按有效长度比较。

数据来源：第二根 UFI003 当前 eMMC 分区，只读采集。未向这些分区写入数据。

