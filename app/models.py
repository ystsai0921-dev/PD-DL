from typing import List, Optional
from pydantic import BaseModel, Field


class FormatOption(BaseModel):
    id: str = Field(..., description="格式唯一標識符")
    type: str = Field(..., description="'video' 或 'audio'")
    label: str = Field(..., description="顯示標籤，如 '1080p Full HD' 或 'MP3 320kbps'")
    ext: str = Field(..., description="檔案副檔名，如 'mp4', 'mp3'")
    resolution: Optional[int] = Field(None, description="解析度高度，如 2160, 1080, 720")
    fps: Optional[int] = Field(None, description="幀率，如 60, 30")
    filesize_approx: Optional[int] = Field(None, description="預估大小 (bytes)")
    filesize_str: Optional[str] = Field(None, description="格式化大小，如 '150.2 MB'")
    format_note: Optional[str] = Field(None, description="畫質附註，如 'HDR', '60fps'")
    vcodec: Optional[str] = Field(None, description="視訊編碼")
    acodec: Optional[str] = Field(None, description="音訊編碼")
    abr: Optional[int] = Field(None, description="音訊位元率 (kbps)")
    is_best: bool = Field(False, description="是否為推薦最佳選項")


class VideoMetadata(BaseModel):
    url: str
    title: str
    uploader: Optional[str] = "未知上傳者"
    duration: Optional[int] = 0
    duration_str: Optional[str] = "00:00"
    thumbnail: Optional[str] = None
    extractor: Optional[str] = "未知平台"
    extractor_key: Optional[str] = ""
    video_formats: List[FormatOption] = []
    audio_formats: List[FormatOption] = []


class DownloadRequest(BaseModel):
    url: str
    type: str = Field("video", description="'video' 或 'audio'")
    format_id: str = Field("best", description="選擇的格式 ID 或畫質標籤")
    resolution: Optional[int] = Field(None, description="指定解析度 (720, 1080, 2160 等)")
    audio_bitrate: Optional[int] = Field(None, description="指定音訊位元率 (128, 192, 320 等)")
    target_ext: Optional[str] = Field("mp4", description="指定輸出格式 (mp4, mkv, mp3, m4a 等)")


class TaskProgress(BaseModel):
    task_id: str
    url: str
    title: str
    status: str = "pending"  # pending, downloading, processing, finished, failed
    percent: float = 0.0
    speed_str: str = "--"
    eta_str: str = "--"
    downloaded_str: str = "--"
    total_str: str = "--"
    filename: Optional[str] = None
    filepath: Optional[str] = None
    file_size_str: Optional[str] = None
    note: Optional[str] = None
    error: Optional[str] = None
