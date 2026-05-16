# 📊 Life Tracker

> 自动记录你每天在电脑上做了什么，**AI 生成日报**，Web 后台可视化。

一个完全本地的 macOS 活动监控工具。自动追踪前台应用、窗口标题、闲置时间，定期截屏，并通过 **DeepSeek AI** 生成每日总结报告。

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📊 **窗口追踪** | 每 5 秒记录一次当前活跃的应用和窗口标题 |
| 📸 **自动截图** | 每 5 分钟静默截屏（JPEG 压缩），按日期分类存档 |
| 🤖 **AI 日报** | 调用 DeepSeek API，根据你的活动数据自动生成中文日报总结 |
| 🌐 **Web 后台** | 暗色主题 Dashboard，查看总览/时间轴/日报/截图 |
| 🔒 **隐私优先** | 数据纯本地存储，不记录浏览器 URL，过期自动清理 |

---

## 🔑 配置 API Key

日报功能需要 **DeepSeek API Key**。程序会从以下位置读取：

**方式一（推荐）：** 创建 `~/.hermes/.env` 文件，写入：
```
DEEPSEEK_API_KEY=sk-你的key
```

**方式二：** 设置环境变量：
```bash
export DEEPSEEK_API_KEY=sk-你的key
```

> 💡 DeepSeek API 在国内可直接访问，注册即送额度。  
> 日报只在本地汇总活动摘要后调 API 生成，不会上传截图或隐私数据。

---

## 🚀 快速开始

### 1. 启动

双击桌面 `LifeTracker.command`，或在终端运行：

```bash
cd ~/workspace/life-tracker

# 启动监控（背景运行）
python3 main.py tracker

# 新开终端，启动 Web 后台
python3 main.py dashboard
```

### 2. 打开后台

浏览器访问 **http://127.0.0.1:5001**

### 3. 查看日报

- 在 Web 后台首页点击「生成日报」（AI 实时生成你的今日总结）
- 已生成的日报下方有「重新生成」按钮，可随时更新
- 或终端运行：`python3 main.py summary`

---

## ⚙️ 配置

所有配置可在 Web 后台「配置」页面修改，或直接编辑 `data/config.json`。

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `track_interval` | 5 | 监控轮询间隔（秒） |
| `screenshot_interval` | 300 | 截图间隔（秒） |
| `screenshot_quality` | 60 | JPEG 压缩质量 |
| `screenshot_retention_days` | 30 | 截图保留天数 |
| `idle_threshold` | 120 | 闲置判定阈值（秒） |
| `dashboard_port` | 5001 | Web 后台端口 |

---

## 📁 项目结构

```
life-tracker/
├── main.py              # 命令行入口
├── tracker.py            # macOS 活动监控器
├── database.py           # SQLite 数据库
├── summarizer.py         # DeepSeek AI 日报生成引擎
├── web.py                # Flask Web 后台
├── config.py             # 配置管理
├── templates/            # HTML 模板 (7页)
│   ├── index.html        # 今日总览
│   ├── timeline.html     # 时间轴
│   ├── summaries.html    # 日报列表
│   ├── summary_detail.html
│   ├── screenshots.html  # 截图浏览
│   ├── screenshots_day.html
│   └── config.html       # 配置页
├── static/
│   └── style.css         # 暗色主题样式
├── data/                 # 运行数据（自动生成）
│   ├── life-tracker.db   # SQLite 数据库
│   ├── config.json       # 用户配置
│   └── screenshots/      # 截图目录
└── start.command         # 一键启动脚本
```

---

## 🛠 常用命令

```bash
python3 main.py tracker        # 启动后台监控
python3 main.py dashboard      # 启动 Web 后台
python3 main.py summary        # AI 生成今日日报
python3 main.py batch 7        # 批量生成最近7天日报
python3 main.py status         # 查看今日状态
python3 main.py config         # 查看配置
python3 main.py config track_interval=10  # 修改配置
```

---

## 🔐 隐私说明

- **纯本地运行**，所有数据存储在你的电脑上
- 截图按日期归档，30 天后自动清理
- 不记录浏览器标签页 URL（隐私过滤）
- **唯一网络请求**是调用 DeepSeek API 生成日报，仅发送活动摘要文本（应用名、使用时长、时间线）

---

## ✅ 环境要求

- macOS（使用 AppleScript 监控窗口）
- Python 3.10+
- Flask（自动安装）
- DeepSeek API Key（配置方式见上方「配置 API Key」）

---

## 📝 License

MIT
