import os
import sys
import webbrowser
import threading
import time
import uvicorn

# 設置環境變數防範 macOS AppleDouble
os.environ["COPYFILE_DISABLE"] = "1"

def open_browser(url: str):
    time.sleep(1.5)
    print(f"\n🚀 已在瀏覽器中開啟: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8000
    app_url = f"http://localhost:{port}"
    
    print("=" * 60)
    print("       🎬 PD Downloader - 萬能影音下載器 Web 服務")
    print("=" * 60)
    print(f" Web 介面網址: {app_url}")
    print(f" 本地下載資料夾: {os.path.abspath('downloads')}")
    print("=" * 60)

    # 背景自動開啟瀏覽器
    threading.Thread(target=open_browser, args=(app_url,), daemon=True).start()

    # 啟動 FastAPI 服務 (開啟 reload 以便代碼更新即時生效)
    uvicorn.run("app.main:app", host=host, port=port, reload=True, log_level="info")
