#!/bin/bash
# UFI003 第二根刷 Debian（EDL 直刷版）
# 用法: bash flash_debian.sh
# 前提: 设备处于 EDL 9008 模式（按住 reset 插入）
# 保留: 原厂 modemst1/modemst2/fsg/fsc 校准分区（从备份刷入新 GPT 位置）

PY="C:/Users/haoranbian/.workbuddy/binaries/python/envs/edl/Scripts/python.exe"
EDL="D:/4G/UFI003-analysis/edl/edl-master/edl.py"
LOADER="D:/4G/UFI003-analysis/edl/MSM8916.mbn"
BASE="D:/4G/UFI003-analysis/openstick_img/openstick/base"
DEB="D:/4G/UFI003-analysis/openstick_img/openstick/debian"
BAK="D:/4G/UFI003-analysis/backup/second_stick"

run() {
    echo ""
    echo ">>> $*"
    "$PY" "$EDL" "$@" --loader="$LOADER" 2>&1 | grep -vE "^Progress|logbuf|fh@" | tail -12
}

echo "=== 1. 确认 EDL 连通 + 当前 GPT ==="
run printgpt

echo ""
echo "=== 2. 写入 openstick GPT (gpt_both0.bin) ==="
run ws 0 "$BASE/gpt_both0.bin"

echo ""
echo "=== 3. 写入 bootloader (sbl1/rpm/tz/hyp/aboot/cdt) ==="
run w sbl1 "$BASE/sbl1.mbn"
run w rpm "$BASE/rpm.mbn"
run w tz "$BASE/tz.mbn"
run w hyp "$BASE/hyp.mbn"
run w aboot "$BASE/aboot.bin"
run w cdt "$BASE/sbc_1.0_8016.bin"

echo ""
echo "=== 4. 从原厂备份恢复校准分区到新 GPT 位置 ==="
run w modemst1 "$BAK/modemst1.bin"
run w modemst2 "$BAK/modemst2.bin"
run w fsg "$BAK/fsg.bin"
run w fsc "$BAK/fsc.bin"

echo ""
echo "=== 5. 写入 boot (kernel+dtb) ==="
run w boot "$DEB/boot.img"

echo ""
echo "=== 6. 写入 rootfs (Debian, 1.93GB, 约2-4分钟) ==="
run w rootfs "$DEB/rootfs.img"

echo ""
echo "=== 7. 重启 ==="
run reset

echo ""
echo "刷机完成！等待设备重启进入 Debian..."
