# PD Downloader - 萬能影音降階下載器 (Web 版)

全功能影音下載器，搭載現代化 Web 介面。只需貼上影片或音樂網址，即可深度解析該內容並列出從**最高畫質（4K/2K/1080p）到流暢畫質（720p/480p/360p）**的所有降階選項，或提取**高保真 MP3 (320kbps/256kbps/192kbps/128kbps) 與無損音訊**。

---

## ✨ 核心特色

1. **支援各大影音平台（1000+ 平台支援）**
   - 包含 YouTube、Bilibili、Facebook、Instagram、TikTok、Twitter/X、Twitch、SoundCloud、Vimeo 等。
2. **階梯降階畫質自由選擇**
   - 🎬 **視訊模式**：
     - ⭐ **最高畫質 (自動)**：自動抓取最高解析度並合併最佳立體聲音軌。
     - 4K Ultra HD (2160p)
     - 2K Quad HD (1440p)
     - Full HD (1080p)
     - HD (720p)
     - SD 標清 (480p / 360p)
     - 標註每種規格的 fps、編碼格式 (MP4/MKV) 與預估檔案大小。
   - 🎵 **純音樂模式**：
     - ⭐ 最佳原音質 (320 kbps MP3)
     - MP3 320 kbps (頂級音質)
     - MP3 256 kbps (極佳聽感)
     - MP3 192 kbps (推薦高音質)
     - MP3 128 kbps (精簡省空間)
     - M4A / AAC (Apple 高保真)
     - FLAC (無失真無損壓縮)
     - WAV (未壓縮純音頻)
3. **即時下載進度儀表板**
   - 採用 SSE (Server-Sent Events) 技術，即時顯示下載進度百分比、當前傳輸速度 (MB/s)、已下載與總大小、剩餘時間 (ETA)。
4. **雙重儲存機制**
   - 檔案自動儲存在本地專屬 `downloads/` 資料夾中（支援一鍵開啟本機 Finder / 資料夾）。
   - 下載完成後亦提供瀏覽器「另存檔案」按鈕，可直接下載到本機預設下載路徑。
5. **已下載檔案管理**
   - 頁面下方即時顯示本地下載歷史清單，支援直接由瀏覽器另存或刪除檔案。

---

## 🚀 啟動方式

在專案目錄下執行以下指令即可啟動服務：

```bash
./start.sh
```

或使用 Python 直接啟動：

```bash
./venv/bin/python run.py
```

啟動後，系統會自動在預設瀏覽器中開啟 Web 介面：
👉 **http://localhost:8000**

---

## 🛠 技術架構

- **後端引擎**：Python 3 + FastAPI + Uvicorn + yt-dlp + static-ffmpeg
- **前端介面**：HTML5 + Tailwind CSS + Lucide Icons + Vanilla JavaScript (SSE 實時進度串流)
- **檔案處理**：內建靜態 FFmpeg 二進位核心，全自動完成高畫質音畫合成與音訊轉碼
