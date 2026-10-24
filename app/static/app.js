// PD Downloader 前端邏輯

let currentMetadata = null;
let currentMode = "video"; // 'video' or 'audio'
let selectedFormat = null;
let activeEventSource = null;
let currentFinishedFilepath = null;

// DOM 元素
const urlInput = document.getElementById("urlInput");
const clearBtn = document.getElementById("clearBtn");
const pasteBtn = document.getElementById("pasteBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const analyzeLoading = document.getElementById("analyzeLoading");
const errorMessage = document.getElementById("errorMessage");
const errorText = document.getElementById("errorText");

const resultSection = document.getElementById("resultSection");
const metaThumb = document.getElementById("metaThumb");
const metaDuration = document.getElementById("metaDuration");
const metaExtractor = document.getElementById("metaExtractor");
const metaUploader = document.getElementById("metaUploader");
const metaTitle = document.getElementById("metaTitle");

const tabVideo = document.getElementById("tabVideo");
const tabAudio = document.getElementById("tabAudio");
const videoFormatsList = document.getElementById("videoFormatsList");
const audioFormatsList = document.getElementById("audioFormatsList");
const outputExtSelect = document.getElementById("outputExtSelect");
const startDownloadBtn = document.getElementById("startDownloadBtn");
const downloadBtnText = document.getElementById("downloadBtnText");

const progressSection = document.getElementById("progressSection");
const progressTitle = document.getElementById("progressTitle");
const progressStatus = document.getElementById("progressStatus");
const progressPercent = document.getElementById("progressPercent");
const progressBar = document.getElementById("progressBar");
const liudingRunner = document.getElementById("liudingRunner");
const liudingFigure = document.getElementById("liudingFigure");
const statSpeed = document.getElementById("statSpeed");
const statSize = document.getElementById("statSize");
const statEta = document.getElementById("statEta");
const finishedActions = document.getElementById("finishedActions");
const saveFileBtn = document.getElementById("saveFileBtn");
const openFolderActionBtn = document.getElementById("openFolderActionBtn");
const settingsBtn = document.getElementById("settingsBtn");

// 設定 Modal 相關元素
const settingsModal = document.getElementById("settingsModal");
const closeSettingsBtn = document.getElementById("closeSettingsBtn");
const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
const currentActiveDirDisplay = document.getElementById("currentActiveDirDisplay");
const chooseFolderBtn = document.getElementById("chooseFolderBtn");
const openCurrentFolderBtn = document.getElementById("openCurrentFolderBtn");
const settingsNotice = document.getElementById("settingsNotice");
const shortcutButtonsList = document.getElementById("shortcutButtonsList");
const navUpBtn = document.getElementById("navUpBtn");
const browserCurrentPath = document.getElementById("browserCurrentPath");
const fsFolderList = document.getElementById("fsFolderList");
const applyBrowsedDirBtn = document.getElementById("applyBrowsedDirBtn");
const manualPathInput = document.getElementById("manualPathInput");
const applyManualPathBtn = document.getElementById("applyManualPathBtn");

let browsedParentPath = null;
let currentlyBrowsingPath = "";

const historyEmpty = document.getElementById("historyEmpty");
const historyList = document.getElementById("historyList");
const refreshFileListBtn = document.getElementById("refreshFileListBtn");
const openFolderFromListBtn = document.getElementById("openFolderFromListBtn");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");

// 初始化事件
document.addEventListener("DOMContentLoaded", () => {
  loadHistory();

  // 清空按鈕
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      urlInput.value = "";
      urlInput.focus();
      if (errorMessage) errorMessage.classList.add("hidden");
      if (resultSection) resultSection.classList.add("hidden");
      currentMetadata = null;
    });
  }

  // 貼上按鈕
  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        analyzeUrl();
      }
    } catch (err) {
      console.warn("無法存取剪貼簿: ", err);
      urlInput.focus();
    }
  });

  // Enter 鍵觸發解析
  urlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      analyzeUrl();
    }
  });

  analyzeBtn.addEventListener("click", analyzeUrl);

  // Tab 切換
  tabVideo.addEventListener("click", () => switchTab("video"));
  tabAudio.addEventListener("click", () => switchTab("audio"));

  // 下載按鈕
  startDownloadBtn.addEventListener("click", triggerDownload);

  // 設定下載資料夾
  settingsBtn.addEventListener("click", openSettingsModal);
  closeSettingsBtn.addEventListener("click", closeSettingsModal);
  cancelSettingsBtn.addEventListener("click", closeSettingsModal);
  chooseFolderBtn.addEventListener("click", chooseFolderNative);
  openCurrentFolderBtn.addEventListener("click", () => openDownloadFolder());
  openFolderActionBtn.addEventListener("click", () => openDownloadFolder(currentFinishedFilepath));
  navUpBtn.addEventListener("click", () => {
    if (browsedParentPath) loadFsBrowse(browsedParentPath);
  });
  applyBrowsedDirBtn.addEventListener("click", () => {
    if (currentlyBrowsingPath) applyDirectory(currentlyBrowsingPath);
  });

  // 手動路徑輸入套用
  if (applyManualPathBtn && manualPathInput) {
    applyManualPathBtn.addEventListener("click", () => {
      const p = manualPathInput.value.trim();
      if (p) {
        applyDirectory(p);
        loadFsBrowse(p);
      }
    });
    manualPathInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const p = manualPathInput.value.trim();
        if (p) {
          applyDirectory(p);
          loadFsBrowse(p);
        }
      }
    });
  }

  // 歷史紀錄重新整理與開啟目錄
  refreshFileListBtn.addEventListener("click", loadHistory);
  if (openFolderFromListBtn) {
    openFolderFromListBtn.addEventListener("click", openDownloadFolder);
  }
  refreshHistoryBtn.addEventListener("click", () => {
    loadHistory();
    historySection.scrollIntoView({ behavior: "smooth" });
  });

  // 目標環境切換按鈕 (Mac / Windows / NAS)
  const tabMac = document.getElementById("tabPlatformMac");
  const tabWin = document.getElementById("tabPlatformWin");
  const tabNas = document.getElementById("tabPlatformNas");
  const autoCheckbox = document.getElementById("autoDownloadCheckbox");

  if (tabMac) tabMac.addEventListener("click", () => setTargetPlatform("mac"));
  if (tabWin) tabWin.addEventListener("click", () => setTargetPlatform("windows"));
  if (tabNas) tabNas.addEventListener("click", () => setTargetPlatform("nas"));

  if (autoCheckbox) {
    autoCheckbox.addEventListener("change", (e) => {
      autoDownloadEnabled = e.target.checked;
      localStorage.setItem("pd_auto_download", autoDownloadEnabled ? "true" : "false");
    });
  }

  updatePlatformTabUI();
});

function showError(msg) {
  errorText.textContent = msg;
  errorMessage.classList.remove("hidden");
}

function clearError() {
  errorMessage.classList.add("hidden");
  errorText.textContent = "";
}

// 執行解析
async function analyzeUrl() {
  let url = urlInput.value.trim();
  if (!url) {
    showError("請輸入影音網址！");
    return;
  }

  // 自動清理 YouTube 播放清單與追蹤參數，鎖定單一影片
  try {
    const u = new URL(url);
    if (u.hostname.includes("youtu.be")) {
      const vid = u.pathname.replace(/^\//, "");
      if (vid && !vid.startsWith("playlist")) {
        url = `https://www.youtube.com/watch?v=${vid}`;
        urlInput.value = url;
      }
    } else if (u.hostname.includes("youtube.com") && u.searchParams.has("v")) {
      url = `https://www.youtube.com/watch?v=${u.searchParams.get("v")}`;
      urlInput.value = url;
    }
  } catch (e) {}

  clearError();
  resultSection.classList.add("hidden");
  analyzeLoading.classList.remove("hidden");
  analyzeBtn.disabled = true;
  analyzeBtn.classList.add("opacity-50", "cursor-not-allowed");

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "解析影片失敗");
    }

    currentMetadata = data;
    renderMetadata(data);
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showError(err.message || "解析連線失敗，請檢查網址或伺服器狀態。");
  } finally {
    analyzeLoading.classList.add("hidden");
    analyzeBtn.disabled = false;
    analyzeBtn.classList.remove("opacity-50", "cursor-not-allowed");
    if (window.lucide) lucide.createIcons();
  }
}

// 渲染解析資訊
function renderMetadata(data) {
  metaTitle.textContent = data.title;
  metaThumb.src = data.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80";
  metaDuration.textContent = data.duration_str;
  metaExtractor.textContent = data.extractor_key || data.extractor || "Video";
  metaUploader.textContent = data.uploader || "";

  renderFormats(data);
}

// 渲染格式清單
function renderFormats(data) {
  // 視訊清單
  videoFormatsList.innerHTML = "";
  if (data.video_formats && data.video_formats.length > 0) {
    data.video_formats.forEach((fmt, idx) => {
      const card = createFormatCard(fmt, idx === 0);
      videoFormatsList.appendChild(card);
      if (idx === 0) selectedFormat = fmt;
    });
  } else {
    videoFormatsList.innerHTML = '<div class="col-span-2 text-center text-slate-500 py-4">無可用視訊格式</div>';
  }

  // 音訊清單
  audioFormatsList.innerHTML = "";
  if (data.audio_formats && data.audio_formats.length > 0) {
    data.audio_formats.forEach((fmt, idx) => {
      const card = createFormatCard(fmt, false);
      audioFormatsList.appendChild(card);
    });
  }

  updateDownloadBtnText();
  if (window.lucide) lucide.createIcons();
}

// 建立格式選項卡片
function createFormatCard(fmt, isSelected) {
  const card = document.createElement("div");
  card.className = `format-card ${isSelected ? "selected" : ""}`;
  card.dataset.id = fmt.id;
  card.dataset.type = fmt.type;

  const badgeHtml = fmt.is_best 
    ? '<span class="ml-2 px-1.5 py-0.5 text-body-text rounded bg-navy-850 text-slate-200 border border-navy-700">推薦</span>'
    : '';

  card.innerHTML = `
    <div class="flex items-center space-x-3 pr-2 overflow-hidden">
      <div class="check-circle">
        <i data-lucide="check" class="w-3.5 h-3.5 ${isSelected ? 'block' : 'hidden'}"></i>
      </div>
      <div class="overflow-hidden">
        <div class="flex items-center flex-wrap">
          <span class="text-body-text font-medium text-slate-100">${fmt.label}</span>
          ${badgeHtml}
        </div>
        <div class="text-body-text text-slate-400 mt-0.5 flex items-center space-x-2">
          ${fmt.format_note ? `<span>${fmt.format_note}</span>` : ''}
          ${fmt.filesize_str ? `<span>· 大小: ${fmt.filesize_str}</span>` : ''}
        </div>
      </div>
    </div>
    <div class="text-right flex-shrink-0">
      <span class="text-body-text uppercase px-2 py-0.5 rounded bg-navy-950 text-slate-300 border border-navy-800">
        ${fmt.ext}
      </span>
    </div>
  `;

  card.addEventListener("click", () => {
    const parent = fmt.type === "video" ? videoFormatsList : audioFormatsList;
    parent.querySelectorAll(".format-card").forEach(c => {
      c.classList.remove("selected");
      const icon = c.querySelector(".check-circle i");
      if (icon) icon.classList.add("hidden");
    });

    card.classList.add("selected");
    const checkIcon = card.querySelector(".check-circle i");
    if (checkIcon) checkIcon.classList.remove("hidden");

    selectedFormat = fmt;
    updateDownloadBtnText();
  });

  return card;
}

// 切換 Tab
function switchTab(mode) {
  currentMode = mode;
  if (mode === "video") {
    tabVideo.classList.add("active");
    tabAudio.classList.remove("active");
    videoFormatsList.classList.remove("hidden");
    audioFormatsList.classList.add("hidden");
    document.getElementById("formatExtSelector").classList.remove("hidden");

    // 恢復視訊選中項
    const selected = videoFormatsList.querySelector(".format-card.selected") || videoFormatsList.querySelector(".format-card");
    if (selected) {
      const id = selected.dataset.id;
      selectedFormat = currentMetadata.video_formats.find(f => f.id === id);
    }
  } else {
    tabAudio.classList.add("active");
    tabVideo.classList.remove("active");
    videoFormatsList.classList.add("hidden");
    audioFormatsList.classList.remove("hidden");
    document.getElementById("formatExtSelector").classList.add("hidden");

    // 恢復音訊選中項
    let selected = audioFormatsList.querySelector(".format-card.selected");
    if (!selected) {
      selected = audioFormatsList.querySelector(".format-card");
      if (selected) {
        selected.classList.add("selected");
        const icon = selected.querySelector(".check-circle i");
        if (icon) icon.classList.remove("hidden");
      }
    }
    if (selected) {
      const id = selected.dataset.id;
      selectedFormat = currentMetadata.audio_formats.find(f => f.id === id);
    }
  }
  updateDownloadBtnText();
}

function updateDownloadBtnText() {
  if (!selectedFormat) {
    downloadBtnText.textContent = "立即開始下載";
    return;
  }
  downloadBtnText.textContent = `下載 ${selectedFormat.label}`;
}

// 觸發下載
async function triggerDownload() {
  if (!currentMetadata || !selectedFormat) {
    showError("請先選擇要下載的畫質或格式！");
    return;
  }

  const payload = {
    url: currentMetadata.url,
    type: currentMode,
    format_id: selectedFormat.id,
    resolution: selectedFormat.resolution || null,
    audio_bitrate: selectedFormat.abr || null,
    target_ext: currentMode === "video" ? outputExtSelect.value : selectedFormat.ext
  };

  progressSection.classList.remove("hidden");
  finishedActions.classList.add("hidden");
  progressTitle.textContent = currentMetadata.title;
  progressStatus.textContent = "正在發送請求至下載引擎...";
  updateLiudingProgress(0, "downloading");
  statSpeed.textContent = "--";
  statSize.textContent = "-- / --";
  statEta.textContent = "--";
  progressSection.scrollIntoView({ behavior: "smooth" });

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "無法發起下載");
    }

    const taskId = data.task_id;
    listenToProgress(taskId);
  } catch (err) {
    progressStatus.textContent = `下載失敗: ${err.message}`;
    progressStatus.className = "text-xs text-red-400 font-medium";
  }
}

// 監聽 SSE 進度
function listenToProgress(taskId) {
  if (activeEventSource) {
    activeEventSource.close();
  }

  activeEventSource = new EventSource(`/api/progress/${taskId}/sse`);

  activeEventSource.onmessage = (event) => {
    try {
      const task = JSON.parse(event.data);
      if (task.error) {
        progressStatus.textContent = `錯誤: ${task.error}`;
        progressStatus.className = "text-xs text-red-400 font-medium";
        updateLiudingProgress(task.percent || 0, "failed");
        activeEventSource.close();
        return;
      }

      statSpeed.textContent = task.speed_str || "--";
      statSize.textContent = `${task.downloaded_str} / ${task.total_str}`;
      statEta.textContent = task.eta_str || "--";

      if (task.status === "downloading") {
        updateLiudingProgress(task.percent, "downloading");
        progressStatus.textContent = "柳丁努力牽引下載中...";
        progressStatus.className = "text-body-text text-amber-200";
      } else if (task.status === "processing") {
        updateLiudingProgress(task.percent || 99, "processing");
        progressStatus.textContent = "正在合成音訊與轉碼封裝...";
        progressStatus.className = "text-body-text text-amber-300 animate-pulse";
      } else if (task.status === "finished") {
        updateLiudingProgress(100, "finished");
        if (task.note) {
          progressStatus.textContent = task.note;
          progressStatus.className = "text-body-text text-amber-300 font-medium";
        } else {
          progressStatus.textContent = "下載與處理已完成！柳丁順利完成任務";
          progressStatus.className = "text-body-text text-white font-medium";
        }
        
        saveFileBtn.href = `/api/files/download/${taskId}`;
        if (task.filename) {
          saveFileBtn.setAttribute("download", task.filename);
        }
        currentFinishedFilepath = task.filepath || null;
        finishedActions.classList.remove("hidden");

        // 若啟用本機電腦模式自動存檔，完成後自動觸發瀏覽器下載至 Mac / Windows
        if (isAutoDownloadEnabled()) {
          setTimeout(() => {
            saveFileBtn.click();
          }, 600);
        }
        
        activeEventSource.close();
        loadHistory();
      } else if (task.status === "failed") {
        updateLiudingProgress(task.percent || 0, "failed");
        progressStatus.textContent = `下載失敗: ${task.error || "未知錯誤"}`;
        progressStatus.className = "text-body-text text-red-300";
        activeEventSource.close();
      }
    } catch (e) {
      console.error("SSE parse error", e);
    }
  };

  activeEventSource.onerror = (err) => {
    console.warn("SSE 連線中斷", err);
  };
}

let serverRuntimeMode = "macos";
let selectedPlatform = localStorage.getItem("pd_target_platform") || detectClientPlatform();
let autoDownloadEnabled = localStorage.getItem("pd_auto_download") !== "false";

function detectClientPlatform() {
  const ua = navigator.userAgent || "";
  if (/Macintosh|Mac OS X/i.test(ua)) return "mac";
  if (/Windows|Win32|Win64/i.test(ua)) return "windows";
  return "nas";
}

function isAutoDownloadEnabled() {
  return autoDownloadEnabled && (selectedPlatform === "mac" || selectedPlatform === "windows");
}

function setTargetPlatform(plat) {
  selectedPlatform = plat;
  localStorage.setItem("pd_target_platform", plat);
  updatePlatformTabUI();
  loadFsBrowse("", plat);
}

function updatePlatformTabUI() {
  const tabMac = document.getElementById("tabPlatformMac");
  const tabWin = document.getElementById("tabPlatformWin");
  const tabNas = document.getElementById("tabPlatformNas");
  const autoCheckbox = document.getElementById("autoDownloadCheckbox");

  const activeClass = "bg-navy-600 border border-blue-500 text-white shadow-sm font-semibold";
  const inactiveClass = "text-slate-400 hover:text-white border border-transparent";

  if (tabMac) tabMac.className = `py-2 px-2 rounded-md font-medium flex items-center justify-center space-x-1 transition ${selectedPlatform === "mac" ? activeClass : inactiveClass}`;
  if (tabWin) tabWin.className = `py-2 px-2 rounded-md font-medium flex items-center justify-center space-x-1 transition ${selectedPlatform === "windows" ? activeClass : inactiveClass}`;
  if (tabNas) tabNas.className = `py-2 px-2 rounded-md font-medium flex items-center justify-center space-x-1 transition ${selectedPlatform === "nas" ? activeClass : inactiveClass}`;

  if (autoCheckbox) {
    autoCheckbox.checked = autoDownloadEnabled;
  }
}

// 開啟本機資料夾 (可反白選取特定檔案)
async function openDownloadFolder(filepath = null) {
  if (serverRuntimeMode === "nas") {
    alert("目前服務運行於 NAS 伺服器，檔案已儲存於 NAS 中。\n\n如需存入目前這台電腦，請在下載完成卡片點擊「另存檔案至瀏覽器」或開啟「自動另存至本機電腦」！");
    return;
  }
  try {
    const payload = (typeof filepath === "string" && filepath) ? { filepath } : {};
    const res = await fetch("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "error") {
      alert(`開啟資料夾失敗，路徑位於：\n${data.path}`);
    }
  } catch (e) {
    alert("無法呼叫系統開啟資料夾");
  }
}

// 開啟設定下載資料夾 Modal
async function openSettingsModal() {
  settingsNotice.classList.add("hidden");
  settingsNotice.textContent = "";
  settingsModal.classList.remove("hidden");
  updatePlatformTabUI();
  await loadFsBrowse("", selectedPlatform);
  if (window.lucide) lucide.createIcons();
}

// 關閉設定 Modal
function closeSettingsModal() {
  settingsModal.classList.add("hidden");
}

// 載入資料夾目錄樹與捷徑 (純滑鼠瀏覽，支援指定平台)
async function loadFsBrowse(targetPath = "", platform = "") {
  try {
    const plat = platform || selectedPlatform;
    const url = `/api/fs/browse?platform=${encodeURIComponent(plat)}${targetPath ? `&path=${encodeURIComponent(targetPath)}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();

    currentlyBrowsingPath = data.current_path;
    browsedParentPath = data.parent_path;

    updatePlatformTabUI();

    // 自適應運行環境 (NAS / Mac / Windows / Linux)
    if (data.runtime_info) {
      serverRuntimeMode = data.runtime_info.server_mode || data.runtime_info.mode || "macos";
      const envModeTitle = document.getElementById("envModeTitle");
      const envModeDesc = document.getElementById("envModeDesc");
      const nativePickerWrapper = document.getElementById("nativePickerWrapper");
      const chooseFolderBtnText = document.getElementById("chooseFolderBtnText");
      const shortcutsLabel = document.getElementById("shortcutsLabel");
      const manualPathLabel = document.getElementById("manualPathLabel");
      const manualPathInput = document.getElementById("manualPathInput");
      const openCurrentFolderBtn = document.getElementById("openCurrentFolderBtn");
      const openCurrentFolderText = document.getElementById("openCurrentFolderText");

      if (envModeTitle) envModeTitle.textContent = data.runtime_info.mode_title || "運行環境";
      if (envModeDesc) envModeDesc.textContent = data.runtime_info.mode_desc || "";

      if (manualPathInput && data.runtime_info.placeholder) {
        manualPathInput.placeholder = data.runtime_info.placeholder;
      }

      if (nativePickerWrapper) {
        if (data.runtime_info.can_native_pick) {
          nativePickerWrapper.classList.remove("hidden");
          if (chooseFolderBtnText && data.runtime_info.native_pick_label) {
            chooseFolderBtnText.textContent = data.runtime_info.native_pick_label;
          }
        } else {
          nativePickerWrapper.classList.add("hidden");
        }
      }

      if (shortcutsLabel) {
        shortcutsLabel.textContent = plat === "nas" ? "NAS 常用位置捷徑：" : `${plat === "mac" ? "Mac" : "Windows"} 本機常用位置捷徑：`;
      }

      if (manualPathLabel) {
        manualPathLabel.textContent = plat === "nas" ? "手動指定 NAS 伺服器路徑：" : `手動指定 ${plat === "mac" ? "Mac" : "Windows"} 本機路徑：`;
      }

      if (openCurrentFolderBtn) {
        if (data.runtime_info.can_native_pick) {
          openCurrentFolderBtn.classList.remove("hidden");
          if (openCurrentFolderText) {
            openCurrentFolderText.textContent = plat === "mac" ? "在 Finder 開啟" : "在檔案總管開啟";
          }
        } else {
          openCurrentFolderBtn.classList.add("hidden");
        }
      }
    }

    // 更新可點擊麵包屑路徑顯示
    browserCurrentPath.innerHTML = "";
    const isNas = plat === "nas";
    const baseRootPath = isNas ? "/downloads" : "/";
    const parts = data.current_path.split("/").filter(Boolean);

    const rootSpan = document.createElement("span");
    rootSpan.className = "cursor-pointer hover:underline text-blue-400 font-bold px-1 rounded hover:bg-navy-850";
    rootSpan.textContent = isNas ? "📦 NAS 下載區 (/downloads)" : (plat === "windows" ? "💻 系統磁碟 (C:)" : "💻 根目錄 /");
    rootSpan.onclick = () => loadFsBrowse(baseRootPath, plat);
    browserCurrentPath.appendChild(rootSpan);

    let accumulated = "";
    parts.forEach((p) => {
      accumulated += "/" + p;
      if (isNas && accumulated === "/downloads") {
        return;
      }
      const thisPath = accumulated;
      const sep = document.createElement("span");
      sep.className = "text-slate-600 select-none";
      sep.textContent = "›";
      browserCurrentPath.appendChild(sep);

      const partSpan = document.createElement("span");
      partSpan.className = "cursor-pointer hover:underline text-slate-200 hover:text-white px-1 rounded hover:bg-navy-850 truncate max-w-[120px]";
      partSpan.textContent = p;
      partSpan.onclick = () => loadFsBrowse(thisPath, plat);
      browserCurrentPath.appendChild(partSpan);
    });

    if (manualPathInput) {
      manualPathInput.value = data.current_path;
    }
    currentActiveDirDisplay.textContent = data.active_download_dir;

    // 處理上一層按鈕狀態
    if (browsedParentPath) {
      navUpBtn.disabled = false;
      navUpBtn.classList.remove("opacity-50", "cursor-not-allowed");
    } else {
      navUpBtn.disabled = true;
      navUpBtn.classList.add("opacity-50", "cursor-not-allowed");
    }

    // 渲染常用快速捷徑
    shortcutButtonsList.innerHTML = "";
    if (data.shortcuts && data.shortcuts.length > 0) {
      data.shortcuts.forEach(s => {
        const btn = document.createElement("button");
        btn.type = "button";
        const isActive = s.path === data.active_download_dir;
        btn.className = `px-3 py-1.5 rounded border text-body-text flex items-center space-x-1.5 transition ${
          isActive 
            ? "bg-navy-600 border-blue-500 text-white font-medium" 
            : "bg-navy-950 hover:bg-navy-850 border-navy-800 text-slate-200"
        }`;
        btn.innerHTML = `<i data-lucide="folder" class="w-3.5 h-3.5 text-slate-400"></i><span>${s.name}</span>`;
        btn.addEventListener("click", async () => {
          await applyDirectory(s.path);
          await loadFsBrowse(s.path, plat);
        });
        shortcutButtonsList.appendChild(btn);
      });
    }

    // 渲染子資料夾清單 (點擊進入)
    fsFolderList.innerHTML = "";
    if (data.folders && data.folders.length > 0) {
      data.folders.forEach(f => {
        const row = document.createElement("div");
        row.className = "flex items-center justify-between p-2 rounded hover:bg-navy-850 cursor-pointer transition text-body-text group border border-transparent hover:border-navy-800";
        row.innerHTML = `
          <div class="flex items-center space-x-2 truncate pr-2">
            <i data-lucide="folder" class="w-4 h-4 text-slate-400 group-hover:text-blue-400 transition-colors"></i>
            <span class="text-slate-200 group-hover:text-white truncate">${f.name}</span>
          </div>
          <span class="text-slate-400 text-body-text group-hover:text-slate-200 flex-shrink-0">進入 →</span>
        `;
        row.addEventListener("click", () => {
          loadFsBrowse(f.path);
        });
        fsFolderList.appendChild(row);
      });
    } else {
      fsFolderList.innerHTML = '<div class="p-3 text-center text-slate-500 text-body-text">（此目錄下無其他子資料夾）</div>';
    }

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("載入目錄瀏覽失敗", err);
  }
}

// 套用指定路徑為下載目錄
async function applyDirectory(selectedPath) {
  if (!selectedPath) return;
  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ download_dir: selectedPath })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "設定失敗");
    }

    currentActiveDirDisplay.textContent = data.download_dir;
    showSettingsNotice(`✓ 已成功將下載儲存位置導引至：\n${data.download_dir}`, false);
    loadHistory();
  } catch (err) {
    showSettingsNotice(err.message || "設定失敗，請確認該資料夾是否具備讀寫權限", true);
  }
}

// 喚起原生 macOS Finder 視窗選取 (純滑鼠瀏覽)
async function chooseFolderNative() {
  showSettingsNotice("正在彈出系統 Finder 視窗，請在視窗中點選資料夾並按「選擇」...", false);
  try {
    const res = await fetch("/api/settings/choose-folder", { method: "POST" });
    const data = await res.json();
    if (data.status === "success" && data.download_dir) {
      currentActiveDirDisplay.textContent = data.download_dir;
      showSettingsNotice(`✓ 已成功在系統視窗中選取並導引至：\n${data.download_dir}`, false);
      loadHistory();
      loadFsBrowse(data.download_dir);
    } else if (data.status === "canceled") {
      showSettingsNotice("已取消選擇資料夾，維持原設定", false);
    } else {
      showSettingsNotice("可在下方「常用位置」或「資料夾目錄瀏覽」直接滑鼠點選資料夾", false);
    }
  } catch (err) {
    showSettingsNotice("可在下方「常用位置」或「資料夾目錄瀏覽」直接滑鼠點選資料夾", false);
  }
}

function showSettingsNotice(msg, isError) {
  settingsNotice.textContent = msg;
  settingsNotice.className = `text-body-text p-2.5 rounded border whitespace-pre-wrap ${
    isError 
      ? "bg-red-950/60 border-red-800 text-red-200" 
      : "bg-navy-950 border-navy-800 text-slate-200"
  }`;
  settingsNotice.classList.remove("hidden");
}

// 載入歷史與本機已下載檔案
async function loadHistory() {
  try {
    const res = await fetch("/api/downloads");
    if (!res.ok) return;
    const files = await res.json();

    if (!files || files.length === 0) {
      historyEmpty.classList.remove("hidden");
      historyList.innerHTML = "";
      return;
    }

    historyEmpty.classList.add("hidden");
    historyList.innerHTML = "";

    files.forEach(f => {
      const item = document.createElement("div");
      item.className = "flex items-center justify-between p-3 rounded-lg bg-navy-950 border border-navy-800 hover:border-navy-700 transition";
      
      const isAudio = f.filename.endsWith(".mp3") || f.filename.endsWith(".m4a") || f.filename.endsWith(".flac") || f.filename.endsWith(".wav");
      const iconName = isAudio ? "music" : "video";

      item.innerHTML = `
        <div class="flex items-center space-x-3 overflow-hidden text-body-text w-full">
          <div class="w-8 h-8 rounded bg-navy-900 flex items-center justify-center flex-shrink-0 text-slate-300 border border-navy-800">
            <i data-lucide="${iconName}" class="w-4 h-4"></i>
          </div>
          <div class="overflow-hidden flex-1">
            <p class="text-body-text text-slate-100 truncate font-medium" title="${f.filename}">${f.filename}</p>
            <p class="text-body-text text-slate-400 text-xs mt-0.5">${f.size_str}</p>
          </div>
        </div>
      `;

      historyList.appendChild(item);
    });

    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error("載入下載歷史失敗", e);
  }
}

// 更新柳丁牽引進度條與卡通動作狀態
function updateLiudingProgress(percent, status = "downloading") {
  const clamped = Math.max(0, Math.min(100, Number(percent) || 0));
  if (progressBar) {
    progressBar.style.width = `${clamped}%`;
    progressBar.style.background = "linear-gradient(90deg, #fef08a 0%, #fde047 30%, #facc15 65%, #eab308 90%, #d97706 100%)";
  }
  if (progressPercent) {
    progressPercent.textContent = `${clamped.toFixed(1)}%`;
  }

  if (liudingRunner) {
    // 讓繩索起始端緊扣黃色進度條前端，柳丁在前方拉動，且不超出右側邊界
    liudingRunner.style.left = `clamp(0px, calc(${clamped}% - 8px), calc(100% - 78px))`;
  }

  const eyeNormal = document.getElementById("liudingEyeNormal");
  const eyeDizzy = document.getElementById("liudingEyeDizzy");

  if (!liudingFigure) return;

  if (status === "finished") {
    liudingFigure.className = "liuding-celebrate";
    if (eyeNormal) eyeNormal.classList.remove("hidden");
    if (eyeDizzy) eyeDizzy.classList.add("hidden");
  } else if (status === "processing") {
    // 轉碼停滯原地時：旋轉掙扎且汗滴四射
    liudingFigure.className = "liuding-sweating";
    if (eyeNormal) eyeNormal.classList.add("hidden");
    if (eyeDizzy) eyeDizzy.classList.remove("hidden");
  } else if (status === "failed") {
    liudingFigure.className = "";
    if (eyeNormal) eyeNormal.classList.remove("hidden");
    if (eyeDizzy) eyeDizzy.classList.add("hidden");
  } else {
    // 正常下載前進：前傾搖擺牽引
    liudingFigure.className = "liuding-pulling";
    if (eyeNormal) eyeNormal.classList.remove("hidden");
    if (eyeDizzy) eyeDizzy.classList.add("hidden");
  }
}
