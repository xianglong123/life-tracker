"""
Life Tracker 配置管理
"""
import json
from pathlib import Path

DATA_DIR = Path.home() / "workspace" / "life-tracker" / "data"
DB_PATH = DATA_DIR / "life-tracker.db"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
CONFIG_PATH = DATA_DIR / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "track_interval": 5,           # 监控轮询间隔（秒）
    "screenshot_interval": 300,    # 截图间隔（秒），默认5分钟
    "screenshot_quality": 60,      # JPEG压缩质量（1-100）
    "screenshot_retention_days": 30,  # 截图保留天数
    "idle_threshold": 120,         # 闲置判定阈值（秒）
    "deepseek_model": "deepseek-chat",
    "deepseek_base_url": "https://api.deepseek.com/v1",
    "privacy_filter_apps": [       # 隐私过滤（这些应用不记录窗口标题）
        "com.apple.Safari",
        "com.google.Chrome",
        "com.microsoft.edgemac",
        "org.mozilla.firefox"
    ],
    "auto_summary_time": "23:00",  # 自动生成日报时间
    "dashboard_port": 5001,        # Web后台端口
    "dashboard_host": "127.0.0.1", # Web后台监听地址
}


def load_config():
    """加载配置，不存在则创建默认配置"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        # 合并默认值（新增配置项自动补全）
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    else:
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)


def save_config(config):
    """保存配置"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_api_key():
    """从 ~/.hermes/.env 读取 DeepSeek API key"""
    env_file = Path.home() / ".hermes" / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1]
    return ""
