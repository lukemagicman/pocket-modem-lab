# EDL GPT blobs

为 4 GB UFI003 eMMC（`0x760000` 个 512-byte sectors）生成的 OpenStick GPT 主、备写入块。

- `gpt_primary_34sectors.bin`：从 sector `0` 写入，共 34 sectors。
- `gpt_backup_33sectors.bin`：从 sector `7733215`（`0x75ffdf`）写入，共 33 sectors。
- 分区条目、GPT header CRC32 和 partition-array CRC32 均重新计算。
- 来源：`openstick/base/gpt_both0_fixed.bin`。
