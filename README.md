# AVDC-Pro

> AV Data Capture — 元数据刮削器，配合 Emby/Jellyfin/Kodi/Plex 管理本地影片

基于 [wei-xox/AVDC](https://github.com/wei-xox/AVDC)（GUI 版）和 [yyymess/avdc](https://github.com/yyymess/avdc)（命令行版）合并重构。

## ✨ 特性

- 🔍 **12 个数据源**：javbus, javdb, javlib, jav321, fanza, airav, avsox, xcity, mgstage, fc2, dlsite, metajavlib
- 📦 **模块化架构**：Scraper 注册表 + 抽象基类 + 策略模式调度
- 📝 **NFO 输出**：生成 Emby/Jellyfin/Kodi 兼容的元数据文件
- 🐳 **Docker 支持**：开箱即用的容器化部署
- ⚙️ **CLI 工具**：单番号 / 批量扫描两种模式
- 🔧 **可配置**：12 个数据源可独立启用/禁用，命名规则可自定义

## 🚀 快速开始

```bash
# 安装
pip install -e .

# 单番号刮削
avdc -n SNIS-829

# 批量扫描当前目录
avdc .

# 扫描指定目录
avdc /path/to/videos

# 调试模式
avdc -d .
```

## 📁 项目结构

```
avdc-pro/
├── src/avdc/
│   ├── cli.py              # CLI 入口
│   ├── config.py            # 配置管理（单例）
│   ├── core/
│   │   ├── dispatcher.py    # 番号→Scraper 调度器
│   │   ├── file_manager.py  # 文件/目录操作
│   │   ├── nfo_writer.py    # NFO 元数据生成
│   │   └── number_parser.py # 番号提取
│   ├── model/
│   │   └── movie.py         # Movie 数据类
│   ├── scrapers/            # 12 个 Scraper（注册表模式）
│   │   ├── base.py          # BaseScraper ABC
│   │   ├── javbus.py
│   │   ├── javdb.py
│   │   └── ...
│   └── utils/
│       ├── http.py          # HTTP 请求（代理/重试/UA池）
│       └── naming.py        # 文件命名规则引擎
├── tests/
├── docker/
└── .github/workflows/
```

## ⚙️ 配置

复制 `src/avdc/data/config.ini` 到工作目录，按需修改：

```ini
[common]
main_mode = 1                  # 1=刮削模式, 2=整理模式
success_output_folder = JAV_output
failed_output_folder = failed

[proxy]
proxy = 127.0.0.1:7890         # 代理地址
timeout = 7
retry = 3

[Sources]
javbus = 1                     # 1=启用, 0=禁用
javdb = 1
fanza = 1
# ... 更多数据源
```

## 🐳 Docker

```bash
cd docker
# 编辑 docker-compose.yaml 中的路径
docker-compose up --build
```

## 🛠️ 开发

```bash
make dev        # 安装开发依赖
make lint       # 代码检查
make test       # 运行测试
make format     # 格式化代码
```

## 📄 License

MIT
