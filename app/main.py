import os
import sys
import uuid
import asyncio
import subprocess
import threading
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models import VideoMetadata, DownloadRequest, TaskProgress
from app.downloader import (
    extract_video_info,
    run_download,
    cleanup_part_files,
    tasks_progress,
    tasks_lock,
    get_download_dir,
    set_download_dir,
    clean_error_message,
    format_bytes
)

app = FastAPI(title="PD Downloader", version="0.1.0")

# 允許跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AnalyzeRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>萬能影音下載器 Web 正在啟動...</h1>"


@app.post("/api/analyze", response_model=VideoMetadata)
async def api_analyze(req: AnalyzeRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="請提供影片網址")
    
    url = req.url.strip()
    try:
        # 在執行緒池中非同步執行 yt-dlp 資訊提取
        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(None, extract_video_info, url)
        return metadata
    except Exception as e:
        cleaned = clean_error_message(str(e))
        raise HTTPException(status_code=500, detail=f"解析失敗: {cleaned}")


@app.post("/api/download")
async def api_download(req: DownloadRequest):
    task_id = str(uuid.uuid4())
    
    with tasks_lock:
        tasks_progress[task_id] = TaskProgress(
            task_id=task_id,
            url=req.url,
            title="準備下載中...",
            status="pending",
            percent=0.0
        )

    # 啟動背景線程執行下載
    thread = threading.Thread(target=run_download, args=(task_id, req), daemon=True)
    thread.start()

    return {"task_id": task_id, "status": "started"}


@app.get("/api/progress/{task_id}", response_model=TaskProgress)
async def api_get_progress(task_id: str):
    with tasks_lock:
        task = tasks_progress.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="找不到該任務")
        return task


@app.get("/api/progress/{task_id}/sse")
async def api_progress_sse(task_id: str):
    """Server-Sent Events 即時推送進度"""
    async def event_generator():
        while True:
            with tasks_lock:
                task = tasks_progress.get(task_id)
            
            if not task:
                yield f"data: {{\"error\": \"任務不存在\"}}\n\n"
                break

            data = task.model_dump_json()
            yield f"data: {data}\n\n"

            if task.status in ["finished", "failed"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/files/download/{task_id}")
async def api_browser_download(task_id: str):
    with tasks_lock:
        task = tasks_progress.get(task_id)
        if not task or not task.filepath or not os.path.exists(task.filepath):
            raise HTTPException(status_code=404, detail="檔案不存在或尚未完成下載")
        
        return FileResponse(
            path=task.filepath,
            filename=task.filename or os.path.basename(task.filepath),
            media_type="application/octet-stream"
        )


class SettingsRequest(BaseModel):
    download_dir: str


@app.get("/api/settings")
async def api_get_settings():
    return {"download_dir": get_download_dir()}


@app.post("/api/settings")
async def api_save_settings(req: SettingsRequest):
    if not req.download_dir or not req.download_dir.strip():
        raise HTTPException(status_code=400, detail="路徑不可為空")
    try:
        saved_path = set_download_dir(req.download_dir.strip())
        return {"status": "success", "download_dir": saved_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法設定該路徑: {str(e)}")


@app.post("/api/settings/choose-folder")
async def api_choose_folder():
    """喚起 macOS 原生對話框選擇下載儲存資料夾"""
    try:
        import sys
        if sys.platform == 'darwin':
            # 乾淨呼叫 choose folder，避免 System Events 權限阻擋
            script = 'set folderPath to POSIX path of (choose folder with prompt "請選擇 PD Downloader 下載檔案儲存資料夾：")\nreturn folderPath'
            proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=False)
            chosen = proc.stdout.strip()
            if chosen and os.path.isdir(chosen):
                saved = set_download_dir(chosen)
                return {"status": "success", "download_dir": saved}
            elif proc.returncode != 0 and ("canceled" in proc.stderr.lower() or "-128" in proc.stderr):
                return {"status": "canceled", "download_dir": get_download_dir()}
            elif proc.returncode != 0:
                # 備援機制：使用 Python 內建 tkinter NSOpenPanel
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                chosen = filedialog.askdirectory(title="請選擇 PD Downloader 下載儲存資料夾")
                root.destroy()
                if chosen and os.path.isdir(chosen):
                    saved = set_download_dir(chosen)
                    return {"status": "success", "download_dir": saved}
            return {"status": "canceled", "download_dir": get_download_dir()}
        else:
            # 其他作業系統備援
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            chosen = filedialog.askdirectory(title="請選擇 PD Downloader 下載儲存資料夾")
            root.destroy()
            if chosen and os.path.isdir(chosen):
                saved = set_download_dir(chosen)
                return {"status": "success", "download_dir": saved}
            return {"status": "canceled", "download_dir": get_download_dir()}
    except Exception as e:
        return {"status": "error", "message": str(e), "download_dir": get_download_dir()}


@app.get("/api/fs/browse")
async def api_fs_browse(path: str = None):
    """取得資料夾清單供網頁內直接滑鼠點選瀏覽 (全面支援本機電腦與所有磁碟)"""
    home = os.path.expanduser("~")
    
    # 常用快速捷徑 (本機電腦硬碟 + 家目錄 + 常用資料夾 + 外接磁碟)
    quick_shortcuts = [
        {"name": "💻 本機硬碟 (Macintosh HD)", "path": "/"},
        {"name": "🏠 家目錄 (~)", "path": home},
        {"name": "📥 下載 (Downloads)", "path": os.path.join(home, "Downloads")},
        {"name": "🖥️ 桌面 (Desktop)", "path": os.path.join(home, "Desktop")},
        {"name": "🎬 影片 (Movies)", "path": os.path.join(home, "Movies")},
        {"name": "🎵 音樂 (Music)", "path": os.path.join(home, "Music")},
        {"name": "📄 文件 (Documents)", "path": os.path.join(home, "Documents")},
    ]
    # 外接磁碟 (如 資料碟、隨身碟、外接SSD)
    if os.path.exists("/Volumes"):
        try:
            for v in sorted(os.listdir("/Volumes")):
                vpath = os.path.join("/Volumes", v)
                if os.path.isdir(vpath) and not v.startswith("."):
                    quick_shortcuts.append({"name": f"💾 {v}", "path": vpath})
        except Exception:
            pass

    current = os.path.abspath(path.strip()) if path and path.strip() else get_download_dir()
    if not os.path.isdir(current):
        current = home

    folders = []
    parent = os.path.dirname(current) if current != "/" else None

    try:
        for item in sorted(os.listdir(current)):
            if item.startswith("."):
                continue
            item_path = os.path.join(current, item)
            try:
                if os.path.isdir(item_path):
                    folders.append({"name": item, "path": item_path})
            except Exception:
                pass
    except Exception:
        pass

    return {
        "current_path": current,
        "parent_path": parent,
        "folders": folders,
        "shortcuts": [s for s in quick_shortcuts if os.path.exists(s["path"])],
        "active_download_dir": get_download_dir(),
        "is_darwin": sys.platform == "darwin",
    }


@app.get("/api/downloads")
async def api_list_downloads():
    """列出下載資料夾中已存在的檔案，並自動排除或清理暫存殘留檔"""
    download_dir = get_download_dir()
    if not os.path.exists(download_dir):
        return []

    items = []
    for fname in os.listdir(download_dir):
        if fname.startswith(".") or fname.endswith(('.part', '.ytdl', '.temp')):
            continue
        fpath = os.path.join(download_dir, fname)
        if os.path.isfile(fpath):
            stat = os.stat(fpath)
            items.append({
                "filename": fname,
                "size": stat.st_size,
                "size_str": format_bytes(stat.st_size),
                "created_time": stat.st_mtime,
            })
    
    # 按照最新修改時間倒序
    items.sort(key=lambda x: x["created_time"], reverse=True)
    return items


@app.get("/api/downloads/file/{filename}")
async def api_download_existing_file(filename: str):
    download_dir = get_download_dir()
    fpath = os.path.join(download_dir, filename)
    if not os.path.exists(fpath) or not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="檔案不存在")
    return FileResponse(path=fpath, filename=filename, media_type="application/octet-stream")


@app.delete("/api/downloads/{filename}")
async def api_delete_file(filename: str):
    download_dir = get_download_dir()
    fpath = os.path.join(download_dir, filename)
    if os.path.exists(fpath) and os.path.isfile(fpath):
        os.remove(fpath)
        return {"status": "deleted", "filename": filename}
    raise HTTPException(status_code=404, detail="檔案不存在")


@app.post("/api/open-folder")
async def api_open_folder(request: Request = None):
    """在 macOS Finder 或檔案總管中直接開啟下載目錄 (可反白選取指定檔案)"""
    download_dir = get_download_dir()
    filepath = None
    if request:
        try:
            body = await request.json()
            filepath = body.get("filepath")
        except Exception:
            pass

    try:
        if sys.platform == 'darwin':
            if filepath and os.path.exists(filepath):
                subprocess.run(['open', '-R', filepath], check=False)
            else:
                subprocess.run(['open', download_dir], check=False)
        elif sys.platform == 'win32':
            if filepath and os.path.exists(filepath):
                subprocess.run(['explorer', f'/select,"{os.path.normpath(filepath)}"'], check=False)
            else:
                os.startfile(download_dir)
        elif os.environ.get('DISPLAY'):
            subprocess.run(['xdg-open', download_dir], check=False)
        else:
            return {"status": "success", "message": f"NAS 伺服器運作中，檔案儲存於：{download_dir}", "path": download_dir}
        return {"status": "success", "path": download_dir}
    except Exception as e:
        return {"status": "error", "message": str(e), "path": download_dir}
