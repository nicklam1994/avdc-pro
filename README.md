# AVDC-Pro

> AV Data Capture — 元數據刮削器，配合 Emby / Jellyfin / Kodi / Plex 管理本地影片

基於 [wei-xox/AVDC](https://github.com/wei-xox/AVDC)（GUI 版）和 [yyymess/avdc](https://github.com/yyymess/avdc)（命令行版）合併重構。

## ✨ 特性

- 🎯 **智能調度**：Fallback 策略，源失敗才下一個
- 🖥️ **PySide6 現代 GUI**：暗/亮主題切換，動畫過渡
- 📝 **NFO 輸出**：Emby / Jellyfin / Kodi 兼容
- 🖼️ **封面 + 劇照**：自動下載海報、縮略圖、預覽圖
- ⚙️ **CLI + GUI**：命令行和圖形界面雙模式
- 🐳 **Docker 支持**：容器化部署

## 📊 數據源

| 優先級 | 數據源 | 元數據 | 封面 | 劇照 | 狀態 |
|---|---|---|---|---|---|
| 🥇 1 | missav | ⭐⭐⭐ 最全 | ✅ | ❌ | 穩定 |
| 🥇 1 | jav321 | ⭐⭐ | ✅ DMM 高清 | ✅ 8張 | 穩定 |
| 🥈 2 | javbus | ⭐⭐⭐ | ✅ | ✅ 8張 | 穩定 |
| 🥉 3 | javdb | ⭐⭐⭐ | ✅ | ✅ 9張 | 穩定 |
| — | javlib | ⭐⭐ | ✅ | ❌ | ❌ Cloudflare |
| — | fanza | ⭐⭐⭐ | ✅ | ❌ | ⚠️ 需日本 IP |
| — | xcity | ⭐⭐ | ✅ | ❌ | ⚠️ 有限 |
| — | mgstage | ⭐⭐ | ✅ | ❌ | ⚠️ 403 |
| — | fc2 | ⭐⭐ | ✅ | ❌ | ⚠️ 404 |
| — | dlsite | ⭐⭐ | ✅ | ❌ | ⚠️ 需 Playwright |
| — | airav | ⭐⭐ | ✅ | ❌ | ⚠️ 521 |
| — | metajavlib | ⭐⭐ | ✅ | ❌ | ⚠️ 有限 |

### Fallback 策略

```
Layer 1: missav + jav321 (合併) → 成功? 返回 ✅
    ↓ 失敗
Layer 2: javbus → 成功? 返回 ✅
    ↓ 失敗
Layer 3: javdb → 成功? 返回 ✅
    ↓ 失敗
其他啟用源 → 逐個嘗試
```

## 🚀 快速開始

### 安裝

```bash
# 克隆
git clone https://github.com/nicklam1994/avdc-pro.git
cd avdc-pro

# 安裝
pip install -e ".[gui]"

# 重置配置（首次使用）
avdc --reset-config
```

### CLI 使用

```bash
# 單番號刮削
avdc -n SNIS-829

# 批量掃描目錄
avdc /path/to/videos

# 啟動 GUI
avdc --gui

# 調試模式
avdc -d .
```

### GUI 使用

```bash
avdc --gui
```

![GUI 截圖](docs/gui-screenshot.png)

## 📁 項目結構

```
avdc-pro/
├── src/avdc/
│   ├── cli.py                  # CLI 入口 (--gui, -n, --reset-config)
│   ├── config.py               # 配置管理（單例）
│   ├── core/
│   │   ├── dispatcher.py       # Fallback 調度器
│   │   ├── file_manager.py     # 文件操作 + 封面下載
│   │   ├── nfo_writer.py       # NFO 元數據生成
│   │   └── number_parser.py    # 番號提取
│   ├── model/
│   │   └── movie.py            # Movie 數據類
│   ├── scrapers/               # 12 個 Scraper（註冊表模式）
│   │   ├── base.py             # BaseScraper ABC
│   │   ├── missav.py           # 最穩定，元數據最全
│   │   ├── jav321.py           # DMM 高清圖片
│   │   ├── javbus.py           # 備用數據源
│   │   ├── javdb.py            # 需 Playwright
│   │   └── ...
│   ├── gui/
│   │   ├── app.py              # PySide6 應用 + 主題管理
│   │   ├── main_window.py      # 主窗口
│   │   ├── workers.py          # QThread 工作線程
│   │   ├── config_dialog.py    # 設置頁面
│   │   └── widgets/
│   │       ├── sidebar.py      # 圖標側邊欄
│   │       ├── cover_viewer.py # 海報 + 滾動劇照條
│   │       ├── log_viewer.py   # 實時日誌
│   │       └── progress_bar.py # 進度條
│   └── utils/
│       ├── http.py             # HTTP 請求（代理/重試）
│       └── browser.py          # Playwright 瀏覽器引擎
├── tests/
├── docker/
└── .github/workflows/
```

## ⚙️ 配置

配置文件：`config.ini`（首次運行自動生成）

```ini
[common]
main_mode = 1                  # 1=刮削模式, 2=整理模式
success_output_folder = JAV_output
failed_output_folder = failed

[proxy]
proxy = 127.0.0.1:7890         # 代理地址
timeout = 15
retry = 3

[Sources]
missav = 1                     # Priority 1 (固定啟用)
jav321 = 1                     # Priority 1 (固定啟用)
javbus = 1                     # Priority 2
javdb = 1                      # Priority 3
```

## 🖼️ 輸出格式

```
SNOS-257/
├── SNOS-257.nfo              # NFO 元數據
├── poster.jpg                # 海報
├── fanart.jpg                # 藝術圖
├── thumb.jpg                 # 縮略圖
├── fanart-1.jpg ~ 8.jpg      # 劇照
└── SNOS-257.mp4              # 視頻文件
```

## 🐳 Docker

```bash
cd docker
# 編輯 docker-compose.yaml 中的路徑
docker-compose up --build
```

## 🛠️ 開發

```bash
make dev        # 安裝開發依賴
make lint       # 代碼檢查
make test       # 運行測試
make format     # 格式化代碼
```

## 📋 版本歷史

### v1.1.0 (2026-06-23)
- PySide6 現代 GUI（暗/亮主題切換）
- Fallback 調度策略
- 封面 + 劇照自動下載
- 設置頁面數據源優先級

### v1.0.0 (2026-06-22)
- 初始版本
- 12 個數據源
- CLI 工具
- NFO 輸出

## 📄 License

MIT
