import os
import re
import math
import json
import shutil
import threading
from typing import Dict, Any, Optional, Callable
import yt_dlp
import static_ffmpeg

from app.models import FormatOption, VideoMetadata, DownloadRequest, TaskProgress

# 確保 ffmpeg 在環境路徑中
static_ffmpeg.add_paths()
FFMPEG_EXE = shutil.which("ffmpeg")
FFMPEG_DIR = os.path.dirname(FFMPEG_EXE) if FFMPEG_EXE else None

CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))
DEFAULT_DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)


def get_download_dir() -> str:
    """取得當前設定的下載資料夾路徑，並驗證寫入權限"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                d = data.get("download_dir")
                if d and os.path.isdir(d):
                    # 測試資料夾是否具備實際寫入權限 (防止 macOS 外接硬碟或無權限資料夾導致 0% 報錯)
                    test_f = os.path.join(d, ".perm_test")
                    try:
                        with open(test_f, "w") as tf:
                            tf.write("ok")
                        os.remove(test_f)
                        return os.path.abspath(d)
                    except Exception:
                        pass
        except Exception:
            pass
    return DEFAULT_DOWNLOAD_DIR


def set_download_dir(new_path: str) -> str:
    """設定並儲存新的下載資料夾路徑"""
    abs_path = os.path.abspath(os.path.expanduser(new_path.strip()))
    os.makedirs(abs_path, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"download_dir": abs_path}, f, ensure_ascii=False, indent=2)
    return abs_path


# 記憶體內保存任務進度
tasks_progress: Dict[str, TaskProgress] = {}
tasks_lock = threading.Lock()


def format_bytes(bytes_num: Optional[float]) -> str:
    if not bytes_num or bytes_num <= 0:
        return "未知大小"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def clean_error_message(msg: str) -> str:
    """清理 ANSI 逃脫字元與錯誤標籤"""
    if not msg:
        return "解析時發生非預期錯誤，請檢查網址或伺服器連線。"
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', msg)
    cleaned = re.sub(r'\[[0-9;]*m', '', cleaned)
    cleaned = cleaned.replace('ERROR:', '').strip()
    if "The page needs to be reloaded" in cleaned:
        return "YouTube 伺服器要求重整頁面 (The page needs to be reloaded)，請稍後再試或重新貼上網址解析。"
    if "403" in cleaned or "Forbidden" in cleaned:
        return "YouTube 伺服器拒絕存取串流 (HTTP 403: Forbidden)。已啟動自動防封鎖修正，請重新點擊下載試試看。"
    return cleaned if cleaned else "解析時發生非預期錯誤，請稍後重試。"


def get_ydl_base_opts() -> dict:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'extract_flat': False,
        'noplaylist': True,  # 貼單支影片若含有 list= 參數，優先抓取該影片本身
        'continuedl': True,  # 支援斷點續傳
        'retries': 20,
        'fragment_retries': 20,
        'file_access_retries': 10,
        'retry_sleep': 2,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'formats': ['missing_pot'],
            }
        },
    }
    if FFMPEG_DIR:
        opts['ffmpeg_location'] = FFMPEG_DIR
    return opts


def normalize_url(url: str) -> str:
    """自動清理帶有播放清單參數的單一影片網址，避免遍歷播放清單導致被封鎖"""
    import urllib.parse as urlparse
    url = url.strip()
    try:
        parsed = urlparse.urlparse(url)
        # 處理 youtu.be/VIDEO_ID?list=...
        if 'youtu.be' in parsed.netloc:
            vid = parsed.path.strip('/')
            if vid and not vid.startswith('playlist'):
                return f"https://www.youtube.com/watch?v={vid}"
        # 處理 youtube.com/watch?v=VIDEO_ID&list=...
        elif 'youtube.com' in parsed.netloc and '/watch' in parsed.path:
            qs = urlparse.parse_qs(parsed.query)
            if 'v' in qs and qs['v']:
                vid = qs['v'][0]
                return f"https://www.youtube.com/watch?v={vid}"
    except Exception:
        pass
    return url


def extract_video_info(url: str) -> VideoMetadata:
    """提取影片資訊與所有降階畫質/音質選單"""
    url = normalize_url(url)
    
    # 僅使用已知可用且能提取 4K/1080p 的客戶端 (android, android_vr, ios)，徹底杜絕 TV/Web 造成的 Reload 報錯
    client_candidates = [
        ['android'],
        ['android_vr'],
        ['ios'],
    ]
    
    info = None
    last_err = None
    
    for clients in client_candidates:
        try:
            ydl_opts = get_ydl_base_opts()
            if clients is not None:
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'player_client': clients,
                        'formats': ['missing_pot'],
                    }
                }
            else:
                ydl_opts['extractor_args'] = {
                    'youtube': {
                        'formats': ['missing_pot'],
                    }
                }
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                candidate_info = ydl.extract_info(url, download=False)
            if candidate_info:
                info = candidate_info
                # 檢查是否已取得高於 360p 的高清格式，若有則直接採用
                raw = info.get('formats', [])
                if any((f.get('height') or 0) > 360 for f in raw):
                    break
        except Exception as e:
            last_err = e
            continue
        
    if not info:
        if last_err:
            raise last_err
        raise ValueError("無法解析該網址的內容，請確認網址是否正確或支援。")

    # 若解析到的是 playlist，取第一個或主要資訊
    if 'entries' in info and info['entries']:
        first_entry = list(info['entries'])[0]
        if first_entry:
            info = first_entry

    title = info.get('title', '未知標題')
    uploader = info.get('uploader') or info.get('channel') or info.get('creator') or '未知上傳者'
    duration = info.get('duration') or 0
    duration_str = format_duration(duration)
    thumbnail = info.get('thumbnail')
    extractor = info.get('extractor', '未知平台')
    extractor_key = info.get('extractor_key', extractor)

    raw_formats = info.get('formats', [])
    
    # 解析視訊畫質降階梯隊 (4K, 2K, 1080p, 720p, 480p, 360p, 240p, 144p)
    # 按解析度高度 (height) 分組，每組挑出最佳的格式
    resolution_buckets: Dict[int, list] = {}
    
    for f in raw_formats:
        height = f.get('height')
        # 排除縮圖故事板 (mhtml) 與非視訊格式，只納入正常視訊 (>= 144p)
        vcodec = f.get('vcodec')
        if (
            height and height >= 144 
            and f.get('protocol') != 'mhtml'
            and vcodec and vcodec != 'none'
        ):
            if height not in resolution_buckets:
                resolution_buckets[height] = []
            resolution_buckets[height].append(f)

    # 排序解析度由大到小
    sorted_heights = sorted(resolution_buckets.keys(), reverse=True)
    top_res_str = f" {sorted_heights[0]}p" if sorted_heights else ""
    
    video_formats = []
    
    # 預設添加一個「最佳全能畫質」選項
    video_formats.append(FormatOption(
        id="best",
        type="video",
        label=f"⭐ 最高畫質 (自動{top_res_str}視訊+最佳音訊)",
        ext="mp4",
        resolution=sorted_heights[0] if sorted_heights else None,
        is_best=True,
        format_note="自動匹配最高畫質並合併立體聲"
    ))

    def get_resolution_name(h: int) -> str:
        if h >= 4320:
            return f"8K Ultra HD ({h}p)"
        elif h >= 2160:
            return f"4K Ultra HD ({h}p)"
        elif h >= 1440:
            return f"2K Quad HD ({h}p)"
        elif h >= 1080:
            return f"Full HD ({h}p)"
        elif h >= 720:
            return f"HD ({h}p)"
        elif h >= 480:
            return f"SD 標清 ({h}p)"
        else:
            return f"流暢 ({h}p)"

    for h in sorted_heights:
        bucket = resolution_buckets[h]
        # 排序策略：優先選擇有 filesize 的、fps 較高的、ext 為 mp4 的
        bucket.sort(key=lambda x: (
            x.get('filesize') or x.get('filesize_approx') or 0,
            x.get('fps') or 0,
            1 if x.get('ext') == 'mp4' else 0,
            x.get('tbr') or 0
        ), reverse=True)
        
        best_for_h = bucket[0]
        fps = best_for_h.get('fps')
        fps_str = f" {fps}fps" if fps and fps > 30 else ""
        
        # 估算檔案大小
        filesize = best_for_h.get('filesize') or best_for_h.get('filesize_approx')
        if not filesize and duration and best_for_h.get('tbr'):
            # tbr 是 kbit/s
            filesize = int(best_for_h['tbr'] * 1024 / 8 * duration)

        vcodec = best_for_h.get('vcodec', '')
        vcodec_simple = vcodec.split('.')[0] if vcodec else ''
        
        notes = []
        if fps_str:
            notes.append(fps_str.strip())
        if vcodec_simple and vcodec_simple != 'none':
            notes.append(vcodec_simple)

        video_formats.append(FormatOption(
            id=f"res_{h}",
            type="video",
            label=f"{get_resolution_name(h)}{fps_str}",
            ext="mp4",
            resolution=h,
            fps=fps,
            filesize_approx=filesize,
            filesize_str=format_bytes(filesize) if filesize else "預估大小",
            format_note=", ".join(notes) if notes else None,
            vcodec=vcodec_simple
        ))

    # 解析音訊選單降階梯隊
    audio_formats = [
        FormatOption(
            id="audio_best",
            type="audio",
            label="⭐ 最佳原音質 (最高品質 MP3)",
            ext="mp3",
            abr=320,
            is_best=True,
            format_note="原聲最高採樣率轉碼 (320kbps)"
        ),
        FormatOption(
            id="audio_320",
            type="audio",
            label="MP3 - 320 kbps (頂級音質)",
            ext="mp3",
            abr=320,
            format_note="發燒級高保真"
        ),
        FormatOption(
            id="audio_256",
            type="audio",
            label="MP3 - 256 kbps (極佳音質)",
            ext="mp3",
            abr=256,
            format_note="接近無損聽感"
        ),
        FormatOption(
            id="audio_192",
            type="audio",
            label="MP3 - 192 kbps (標準高音質)",
            ext="mp3",
            abr=192,
            format_note="均衡清晰，最推薦"
        ),
        FormatOption(
            id="audio_128",
            type="audio",
            label="MP3 - 128 kbps (省空間音質)",
            ext="mp3",
            abr=128,
            format_note="檔案小，便於傳輸"
        ),
        FormatOption(
            id="audio_m4a",
            type="audio",
            label="M4A / AAC (高保真原格式)",
            ext="m4a",
            abr=256,
            format_note="Apple 裝置原生支援，音質極純"
        ),
        FormatOption(
            id="audio_flac",
            type="audio",
            label="FLAC (無失真無損壓縮)",
            ext="flac",
            format_note="發燒友無損珍藏"
        ),
        FormatOption(
            id="audio_wav",
            type="audio",
            label="WAV (未壓縮純波形)",
            ext="wav",
            format_note="無壓縮原始音軌"
        )
    ]

    return VideoMetadata(
        url=url,
        title=title,
        uploader=uploader,
        duration=duration,
        duration_str=duration_str,
        thumbnail=thumbnail,
        extractor=extractor,
        extractor_key=extractor_key,
        video_formats=video_formats,
        audio_formats=audio_formats
    )


def sanitize_filename(name: str) -> str:
    # 移除或替換檔名不合法字元
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def extract_video_id_from_url(url: str) -> Optional[str]:
    """從常見 YouTube 或影音網址中提取 video id"""
    import urllib.parse as urlparse
    if not url:
        return None
    try:
        parsed = urlparse.urlparse(url)
        if 'youtu.be' in parsed.netloc:
            return parsed.path.strip('/').split('/')[0]
        elif 'youtube.com' in parsed.netloc:
            qs = urlparse.parse_qs(parsed.query)
            if 'v' in qs and qs['v']:
                return qs['v'][0]
    except Exception:
        pass
    return None


def cleanup_part_files(directory: str, video_id: Optional[str] = None, title: Optional[str] = None):
    """
    清理下載資料夾中殘留的 .part、.ytdl、.temp 檔案與 macOS 伴隨檔 (._*.part)
    - 若指定 video_id 或 title：僅精確清理屬於該影片的未完成暫存檔
    - 若皆未指定：清理該目錄下所有未完成的 .part 檔
    """
    if not directory or not os.path.isdir(directory):
        return
    try:
        for fname in os.listdir(directory):
            is_temp = (
                fname.endswith('.part')
                or fname.endswith('.ytdl')
                or fname.endswith('.temp')
                or ('.part' in fname and fname.startswith('._'))
            )
            if not is_temp:
                continue

            matched = False
            if video_id and f"[{video_id}]" in fname:
                matched = True
            elif title and title[:30] in fname:
                matched = True
            elif not video_id and not title:
                matched = True

            if matched:
                full_path = os.path.join(directory, fname)
                try:
                    if os.path.isfile(full_path) or os.path.islink(full_path):
                        os.remove(full_path)
                except Exception:
                    pass
    except Exception:
        pass


def run_download(task_id: str, req: DownloadRequest):
    """執行下載任務的後台線程函數"""
    target_vid = extract_video_id_from_url(req.url)
    with tasks_lock:
        task = tasks_progress.get(task_id)
        if not task:
            return

    def progress_hook(d):
        with tasks_lock:
            cur = tasks_progress.get(task_id)
            if not cur:
                return

            status = d.get('status')
            if status == 'downloading':
                cur.status = "downloading"
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0

                if total > 0:
                    cur.percent = round((downloaded / total) * 100, 1)
                    cur.total_str = format_bytes(total)
                else:
                    cur.percent = 0.0
                    cur.total_str = "計算中..."

                cur.downloaded_str = format_bytes(downloaded)
                cur.speed_str = f"{format_bytes(speed)}/s" if speed else "--"
                cur.eta_str = f"{int(eta)}s" if eta else "--"

            elif status == 'finished':
                cur.status = "processing"
                cur.percent = 99.0
                cur.speed_str = "處理中"
                cur.eta_str = "完成中"

    download_dir = get_download_dir()
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'outtmpl': os.path.join(download_dir, '%(title).120B [%(id)s].%(ext)s'),
        'progress_hooks': [progress_hook],
    })

    try:
        if req.type == "audio":
            # 純音樂下載
            audio_format = req.target_ext or "mp3"
            abr = str(req.audio_bitrate or 320)
            
            if req.format_id == "audio_m4a":
                audio_format = "m4a"
            elif req.format_id == "audio_flac":
                audio_format = "flac"
            elif req.format_id == "audio_wav":
                audio_format = "wav"

            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': abr,
            }]
        else:
            # 視訊下載
            res = req.resolution
            target_ext = req.target_ext or "mp4"

            if req.format_id == "best" or not res:
                # 最高畫質 + 最高音質合併 (不再限定 ext 確保抓到真正的 4K/2K/1080p，再由 ffmpeg 合成)
                ydl_opts['format'] = "bestvideo+bestaudio/best"
            else:
                # 階梯畫質：小於等於指定解析度
                ydl_opts['format'] = (
                    f"bestvideo[height<={res}]+bestaudio/"
                    f"best[height<={res}]/"
                    f"best"
                )

            ydl_opts['merge_output_format'] = target_ext

        # 開始下載
        target_url = normalize_url(req.url)
        info = None
        
        # 下載客戶端候選清單 (嚴格排除 tv 與 web_safari，以杜絕 The page needs to be reloaded)
        dl_client_candidates = [
            ['android'],
            ['android_vr'],
            ['ios'],
        ]
        
        # 畫質與格式下載候選清單：
        # 1. 音訊：優先嘗試 bestaudio，若遇 GVS PO Token / 403 斷流，自動降階至 18/best (由相容串流擷取原音)
        # 2. 視訊：優先嘗試使用者選擇的畫質 (如 4K/1080p/720p)，若 403 斷流自動降階至相容格式 (18: 360p)
        format_candidates = [(ydl_opts['format'], False)]
        if req.type == "audio":
            format_candidates.append(("18/best", True))
        elif req.type == "video" and (req.format_id == "best" or (req.resolution and req.resolution > 360)):
            format_candidates.append(("18/best", True))

        last_dl_err = None
        is_fallback_used = False
        for fmt, is_fallback in format_candidates:
            ydl_opts['format'] = fmt
            for clients in dl_client_candidates:
                try:
                    current_opts = dict(ydl_opts)
                    extractor_youtube = {
                        'player_client': clients,
                    }
                    # 只有視訊下載且非降階模式時，才嘗試解鎖 missing_pot 以探索 4K/1080p DASH 串流；
                    # 音訊下載若啟用 missing_pot 會強制命中需 GVS PO Token 的 251 串流導致 403 報錯
                    if req.type == "video" and not is_fallback:
                        extractor_youtube['formats'] = ['missing_pot']
                    current_opts['extractor_args'] = {'youtube': extractor_youtube}

                    with yt_dlp.YoutubeDL(current_opts) as ydl:
                        info = ydl.extract_info(target_url, download=True)
                    if info:
                        is_fallback_used = is_fallback
                        break
                except Exception as dl_err:
                    last_dl_err = dl_err
                    # 遇到高畫質被 403 斷流或下載中斷時，立即清除該影片留下的 .part 暫存檔，防止垃圾檔案殘留
                    cleanup_part_files(download_dir, video_id=target_vid)
                    continue
            if info:
                break

        if not info:
            cleanup_part_files(download_dir, video_id=target_vid)
            if last_dl_err:
                raise last_dl_err
            raise RuntimeError("下載執行失敗，未能取得影片資料。")

        if info:
            if 'entries' in info and info['entries']:
                info = list(info['entries'])[0]

            filename = ydl.prepare_filename(info)
            # 若經過轉檔，副檔名可能變更
            base, _ = os.path.splitext(filename)
            actual_ext = req.target_ext if req.type == "video" else (
                "m4a" if req.format_id == "audio_m4a" else (
                    "flac" if req.format_id == "audio_flac" else (
                        "wav" if req.format_id == "audio_wav" else "mp3"
                    )
                )
            )
            candidate_file = f"{base}.{actual_ext}"
            final_file = candidate_file if os.path.exists(candidate_file) else filename

            # 下載完成後，徹底清理同影片殘留的任何未完成 .part 暫存檔
            resolved_vid = info.get('id') if isinstance(info, dict) else target_vid
            cleanup_part_files(
                download_dir, 
                video_id=resolved_vid, 
                title=info.get('title') if isinstance(info, dict) else None
            )

            with tasks_lock:
                task = tasks_progress.get(task_id)
                if task:
                    task.status = "finished"
                    task.percent = 100.0
                    task.filepath = final_file
                    task.filename = os.path.basename(final_file)
                    if os.path.exists(final_file):
                        task.file_size_str = format_bytes(os.path.getsize(final_file))
                    task.speed_str = "已完成"
                    task.eta_str = "0s"
                    if is_fallback_used:
                        if req.type == "audio":
                            task.note = "⚠️ 提示：YouTube 伺服器對獨立音訊串流實施限制 (HTTP 403)，已自動由原片擷取最佳原音並轉檔完成。"
                        else:
                            task.note = "⚠️ 提示：YouTube 伺服器對此影片高畫質 (DASH) 串流實施限制 (HTTP 403)，已自動為您無損儲存為 360p 完整影片。"

    except Exception as e:
        cleanup_part_files(download_dir, video_id=target_vid)
        with tasks_lock:
            task = tasks_progress.get(task_id)
            if task:
                task.status = "failed"
                task.error = clean_error_message(str(e))
