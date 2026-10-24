#!/usr/bin/env bash
# PD Downloader 一鍵啟動腳本

export COPYFILE_DISABLE=1

# 移動至腳本所在目錄
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 清理外接磁碟上的 AppleDouble ._*.pth 檔案防護
find ./venv/lib/python*/site-packages -name "._*.pth" -exec rm -f {} + 2>/dev/null

echo "啟動 PD Downloader..."
./venv/bin/python run.py
