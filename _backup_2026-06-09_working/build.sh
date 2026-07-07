#!/bin/bash
export SDK_HOME="$HOME/qsm_software/rk3568_linux_r60_v1.3.2_qsm368zp_d"
BUILDROOT_OUT="$SDK_HOME/buildroot/output/rockchip_rk3568"
QMAKE="$BUILDROOT_OUT/host/bin/qmake"

BLD="/tmp/english_tutor_build"
SRC="$(dirname "$(readlink -f "$0")")"
mkdir -p "$BLD"
cp "$SRC"/*.cpp "$SRC"/*.h "$SRC"/*.pro "$BLD/"
cd "$BLD"

rm -f *.o moc_*.cpp english_tutor .qmake.stash
"$QMAKE" english_tutor.pro && make -j$(nproc) && echo "=== BUILD OK ===" && {
    adb push english_tutor /data/ && adb shell chmod +x /data/english_tutor
    adb shell mkdir -p /data/model

    # Push RKNN runtime libs (new version supporting model v6)
    RKNN_DEMO="/mnt/hgfs/quectel/QSM368ZP-WF-master/examples/rknn/rknn_yolov5_demo/lib"
    [ -f "$RKNN_DEMO/librknnrt.so" ] && adb push "$RKNN_DEMO/librknnrt.so" /data/
    [ -f "$RKNN_DEMO/librga.so" ]    && adb push "$RKNN_DEMO/librga.so" /data/

    [ -d "$SRC/model" ] && adb push "$SRC/model/yolov5s_qsm368zp.rknn" /data/model/ && adb push "$SRC/model/coco_80_labels_list.txt" /data/model/

    # Push chat scenes config
    [ -f "$SRC/scenes.json" ] && adb push "$SRC/scenes.json" /data/

    # 在设备上创建启动脚本
    adb shell "cat > /data/run.sh << 'EOF'
#!/bin/sh
killall weston 2>/dev/null
sleep 1
modetest -M rockchip -w 154:DPMS:0 2>/dev/null
LD_LIBRARY_PATH=/data QT_QPA_PLATFORM=eglfs QT_QPA_EGLFS_KMS_CONFIG=/data/kms.json QT_QPA_EGLFS_ALWAYS_SET_MODE=1 QT_QPA_EGLFS_HIDECURSOR=1 QT_QPA_FONTDIR=/data/fonts /data/english_tutor
echo on > /sys/class/drm/card0-LVDS-1/dpms 2>/dev/null
echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null
weston --tty=1 --idle-time=0 &
EOF"
    adb shell "chmod +x /data/run.sh"

    echo "=== Run app (Ctrl+C to stop, app exit auto-restores desktop) ==="
    adb shell "/data/run.sh"

    sleep 3
    echo "=== Done ==="
}
