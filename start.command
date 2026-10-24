#!/bin/bash

# 切換到此腳本所在的目錄
cd "$(dirname "$0")" || exit 1

# 防止 macOS 產生 AppleDouble ._* 隱藏檔案
export COPYFILE_DISABLE=1

# 清理可能存在的 ._*.pth 檔案防護
find ./venv/lib/python*/site-packages -name "._*.pth" -exec rm -f {} + 2>/dev/null

echo "=================================================="
echo "          🎬 PD Downloader 萬能下載器"
echo "=================================================="
echo "正在啟動伺服器，稍後將自動為您開啟瀏覽器介面..."
echo "如需結束程式，請在此終端機視窗按 Ctrl + C"
echo "=================================================="
echo ""

# 啟動主服務
./venv/bin/python run.py

echo ""
echo "伺服器已停止。按任意鍵關閉視窗..."
read -n 1 -s
