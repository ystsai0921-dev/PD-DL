FROM python:3.11-slim

# 安裝 ffmpeg 與基礎系統工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式原始碼
COPY . .

# 建立預設下載掛載點
RUN mkdir -p /downloads

# 設定環境變數
ENV DOWNLOAD_DIR=/downloads
ENV PYTHONUNBUFFERED=1

# 服務埠
EXPOSE 8000

# 啟動指令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
