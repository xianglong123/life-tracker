"""
Life Tracker — DeepSeek 日报总结引擎
"""
import json
import urllib.request
import urllib.error
import ssl
from datetime import date, timedelta

from config import load_config, get_api_key
from database import get_activities, get_app_stats, save_daily_summary

# macOS Python SSL 修复
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()


def call_deepseek(messages, temperature=0.7, max_tokens=2000):
    """调 DeepSeek API"""
    config = load_config()
    api_key = get_api_key()
    if not api_key:
        return "❌ 未配置 DeepSeek API Key"

    payload = json.dumps({
        "model": config.get("deepseek_model", "deepseek-chat"),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(
        url=f"{config.get('deepseek_base_url', 'https://api.deepseek.com/v1')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ API调用失败: {e}"


def generate_daily_summary(today=None):
    """为某天生成日报，存入数据库"""
    if today is None:
        today = date.today().isoformat()

    # 1. 获取当日活动
    activities = get_activities(today)
    if not activities:
        print(f"[日报] {today} 没有活动记录")
        return None

    # 2. 获取应用统计
    stats = get_app_stats(today, limit=10)

    # 3. 统计基础数据
    total_active_minutes = sum(s["total_minutes"] for s in stats)
    # 直接从文件系统统计截图数，比关联 activity_log 靠谱
    from config import SCREENSHOT_DIR
    day_dir = SCREENSHOT_DIR / today
    screenshot_count = len(list(day_dir.glob("*.jpg"))) if day_dir.exists() else 0

    # 4. 整理活动时间线（精简版）
    timeline = []
    last_app = None
    for a in activities:
        if a.get("is_idle"):
            continue
        app = a["app_name"]
        title = a.get("window_title", "")
        ts = a["timestamp"][11:16]  # HH:MM
        if app != last_app:
            timeline.append(f"  {ts} {app}" + (f" - {title}" if title else ""))
            last_app = app

    timeline_summary = "\n".join(timeline[:60])  # 最多60条，避免 token 超标
    top_apps_text = "\n".join(f"  {s['app_name']}: {s['total_minutes']}分钟" for s in stats[:5])

    # 5. 调用 DeepSeek 生成日报
    prompt = f"""你是一个个人生活记录助手。根据以下用户的电脑活动数据，生成一段友好的中文日报总结。

要求：
- 语气自然亲切，像朋友聊天
- 总结今天主要做了什么事
- 指出工作时间/效率情况
- 给出一个小建议
- 不少于150字，不超过300字

日期：{today}
总活跃时间：{total_active_minutes} 分钟
主要应用：
{top_apps_text}

活动时间线（简要）：
{timeline_summary}

请生成日报："""

    print(f"[日报] 正在生成 {today} 的日报...")
    summary = call_deepseek([
        {"role": "system", "content": "你是个人生活记录助手，根据电脑使用数据生成亲切的日报总结。"},
        {"role": "user", "content": prompt}
    ], temperature=0.7, max_tokens=1000)

    # 6. 存入数据库
    save_daily_summary(
        today=today,
        summary_text=summary,
        total_active_minutes=total_active_minutes,
        top_apps=[{"name": s["app_name"], "minutes": s["total_minutes"]} for s in stats[:5]],
        screenshots_count=screenshot_count
    )

    print(f"[日报] {today} 日报已生成")
    return summary


def batch_summarize_recent(days=7):
    """批量补生成最近N天的日报"""
    results = []
    for i in range(days):
        d = (date.today() - timedelta(days=i)).isoformat()
        summary = generate_daily_summary(d)
        if summary:
            results.append({"date": d, "summary": summary})
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        batch_summarize_recent(days)
    else:
        print(generate_daily_summary())
