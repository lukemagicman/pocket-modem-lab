# Device research

本目录保存 UFI003 / MSM8916 的底层研究脚本、脱敏实验结果和交接结论，覆盖：

- GPT 分区结构与 EDL 写入块分析；
- boot、kernel 与 device tree 对 SIM/UIM 路径的影响；
- QMI PDC/MCFG 选择与 IMS 服务发布；
- ModemManager、AT 与 QMI 的只读状态交叉验证。

## 风险分级

- `baseline_20260902/`、`sim_diagnosis_20260902/`：已脱敏的观察记录，主要用于复核结论。
- `tools/at_status_query.py`、`tools/pdc_gi_probe.py`：以只读查询为主，仍需核对目标端口。
- `boot_hook_reliance/`：会改变运行时 PDC/MCFG 选择，应先阅读目录说明并准备恢复步骤。
- `fix_gpt.py`、`build_edl_gpt.py`、`flash_debian.sh`：涉及分区和刷写材料，错误使用可能导致设备无法启动。

部分脚本是实验现场记录，保留了原工作区路径常量。仓库不提供这些路径所指向的固件、镜像、备份或第三方工具；使用前必须改为自己的本地路径，并核对输入文件哈希与目标硬件版本。

## 未纳入 Git 的材料

原始 eMMC/分区备份、boot/rootfs 镜像、运营商 MBN/MCFG、EDL 工具副本、Android Platform Tools、Debian 软件包及反编译中间文件均被排除。它们可能包含设备数据、受第三方许可约束，或不适合 Git 版本管理。

