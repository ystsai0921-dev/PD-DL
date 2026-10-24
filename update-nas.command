#!/bin/bash
# ========================================================
# PD Downloader - 一鍵同步更新至家用 NAS (192.168.50.124)
# ========================================================

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo " 🚀 正在打包最新版 PD Downloader..."
echo "========================================================"
tar -czf /tmp/pd-dl.tar.gz \
  --exclude="venv" \
  --exclude="downloads/*" \
  --exclude="._*" \
  --exclude="*.mp4" \
  --exclude="*.mp3" \
  --exclude="*.part" \
  .

echo ""
echo "📦 正在傳送至 NAS (192.168.50.124)..."
echo "（請在提示時輸入 NAS 密碼）"
scp /tmp/pd-dl.tar.gz nanson.tsai@192.168.50.124:~/

echo ""
echo "🔄 正在通知 NAS 進行最新版 Docker 建置與無縫重啟..."
ssh -t nanson.tsai@192.168.50.124 "mkdir -p /volume1/home/nanson.tsai/PD-DL && tar -xzf /volume1/home/nanson.tsai/pd-dl.tar.gz -C /volume1/home/nanson.tsai/PD-DL && cd /volume1/home/nanson.tsai/PD-DL && sudo /usr/local/AppCentral/docker-ce/bin/docker-compose up -d --build"

echo ""
echo "========================================================"
echo " 🎉 更新完成！"
echo " 請打開瀏覽器檢查 NAS 最新版：http://192.168.50.124:8000"
echo "========================================================"
