"""
Life Tracker — 命令行入口
"""
import sys
import os
import signal
import subprocess
from pathlib import Path

# 确保能导入同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_tracker():
    """启动后台监控"""
    from tracker import run_tracker
    run_tracker()


def cmd_summary():
    """生成日报"""
    from summarizer import generate_daily_summary
    result = generate_daily_summary()
    if result:
        print("\n" + "=" * 50)
        print(result)
        print("=" * 50)


def cmd_batch():
    """批量生成最近N天日报"""
    from summarizer import batch_summarize_recent
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    batch_summarize_recent(days)


def cmd_dashboard():
    """启动 Web 后台"""
    from web import run_dashboard
    run_dashboard()


def cmd_status():
    """查看状态"""
    from datetime import date, datetime
    from database import get_activities, get_app_stats, get_daily_summary

    today = date.today().isoformat()
    activities = get_activities(today)
    stats = get_app_stats(today)
    summary = get_daily_summary(today)

    print(f"📊 Life Tracker - {today}")
    print(f"   今日活动记录: {len(activities)} 条")
    print(f"   今日应用: {len(stats)} 个")
    if stats:
        for s in stats[:5]:
            print(f"     {s['app_name']}: {s['total_minutes']}分钟")
    if summary:
        print(f"\n📝 今日摘要:")
        print(f"   {summary['summary'][:200]}...")
    else:
        print("\n⚠️  今日日报未生成，运行: python main.py summary")


def cmd_config():
    """查看/编辑配置"""
    from config import load_config, save_config
    import json

    config = load_config()
    if len(sys.argv) > 2 and "=" in sys.argv[2]:
        # 修改配置: python main.py config key=value
        key, value = sys.argv[2].split("=", 1)
        if value.isdigit():
            value = int(value)
        config[key] = value
        save_config(config)
        print(f"✅ 配置已更新: {key} = {value}")
    else:
        print(json.dumps(config, indent=2, ensure_ascii=False))


def cmd_help():
    print("""
Life Tracker — 你的电脑活动记录助手

用法:
  python main.py tracker    启动后台监控（窗口追踪 + 截图）
  python main.py dashboard  启动 Web 管理后台
  python main.py summary    生成今日日报
  python main.py batch [N]  批量生成最近 N 天日报
  python main.py status     查看今日状态
  python main.py config     查看配置
  python main.py config key=value  修改配置

快捷键:
  Ctrl+C 停止后台监控
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)

    command = sys.argv[1]
    commands = {
        "tracker": cmd_tracker,
        "dashboard": cmd_dashboard,
        "summary": cmd_summary,
        "batch": cmd_batch,
        "status": cmd_status,
        "config": cmd_config,
        "help": cmd_help,
        "--help": cmd_help,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"未知命令: {command}")
        cmd_help()
