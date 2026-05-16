"""
Life Tracker — Flask Web 管理后台
"""
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, send_file
from config import load_config, save_config, DATA_DIR, SCREENSHOT_DIR
from database import (
    get_activities, get_app_stats, get_daily_summary,
    get_summary_list, get_daily_summaries
)

app = Flask(__name__)


def _today():
    return date.today().isoformat()


# ---- 页面路由 ----

@app.route("/")
def index():
    """首页 - 今日总览"""
    today = _today()
    activities = get_activities(today)
    stats = get_app_stats(today)
    summary = get_daily_summary(today)

    # 统计
    total_records = len(activities)
    total_minutes = sum(s["total_minutes"] for s in stats) if stats else 0
    app_count = len(stats)

    screenshots = _get_screenshots_for_date(today)

    return render_template("index.html",
        today=today,
        total_records=total_records,
        total_minutes=total_minutes,
        app_count=app_count,
        stats=stats[:10],
        summary=summary,
        screenshots=screenshots[:20]  # 最多20张
    )


@app.route("/timeline")
def timeline():
    """时间轴 - 按时间查看活动记录"""
    d = request.args.get("date", _today())
    activities = get_activities(d)

    # 按时间分组展示
    timeline_data = []
    for a in activities:
        if not a.get("is_idle"):
            timeline_data.append({
                "time": a["timestamp"][11:19],
                "app": a["app_name"],
                "title": a.get("window_title", ""),
                "duration": a.get("duration_seconds", 0),
                "screenshot": a.get("screenshot_path", ""),
            })

    return render_template("timeline.html",
        date=d,
        timeline=timeline_data,
        prev_date=(datetime.strptime(d, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d"),
        next_date=(datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
        is_today=(d == _today())
    )


@app.route("/summaries")
def summaries():
    """日报列表"""
    page = int(request.args.get("page", 1))
    summary_list, total = get_summary_list(page=page)
    return render_template("summaries.html",
        summaries=summary_list,
        page=page,
        total_pages=max(1, (total + 19) // 20)
    )


@app.route("/summary/<date_str>")
def summary_detail(date_str):
    """日报详情"""
    summary = get_daily_summary(date_str)
    stats = get_app_stats(date_str)
    screenshots = _get_screenshots_for_date(date_str)
    activities_count = len(get_activities(date_str))

    return render_template("summary_detail.html",
        date=date_str,
        summary=summary,
        stats=stats,
        screenshots=screenshots,
        activities_count=activities_count
    )


@app.route("/screenshots")
def screenshots():
    """截图浏览"""
    # 列出所有有截图的日期
    dates = []
    if SCREENSHOT_DIR.exists():
        for d in sorted(SCREENSHOT_DIR.iterdir(), reverse=True):
            if d.is_dir():
                count = len(list(d.glob("*.jpg")))
                dates.append({"date": d.name, "count": count})

    return render_template("screenshots.html", dates=dates)


@app.route("/screenshots/<date_str>")
def screenshots_date(date_str):
    """某天截图列表"""
    screenshots = _get_screenshots_for_date(date_str)
    return render_template("screenshots_day.html",
        date=date_str,
        screenshots=screenshots
    )


@app.route("/screenshot/<path:filepath>")
def serve_screenshot(filepath):
    """提供截图文件"""
    full_path = SCREENSHOT_DIR / filepath
    if full_path.exists():
        return send_file(str(full_path), mimetype="image/jpeg")
    return "Not found", 404


@app.route("/config", methods=["GET", "POST"])
def config_page():
    """配置页"""
    config = load_config()
    if request.method == "POST":
        for key in config:
            if key in request.form:
                val = request.form[key]
                if val.isdigit():
                    val = int(val)
                config[key] = val
        save_config(config)
        return render_template("config.html", config=config, saved=True)
    return render_template("config.html", config=config, saved=False)


# ---- API 接口 ----

@app.route("/api/generate_summary/<date_str>", methods=["POST"])
def api_generate_summary(date_str):
    """手动触发生成日报"""
    from summarizer import generate_daily_summary
    result = generate_daily_summary(date_str)
    return jsonify({
        "success": bool(result) and not result.startswith("❌"),
        "summary": result or "该天没有活动记录，无法生成日报"
    })


@app.route("/api/stats/<date_str>")
def api_stats(date_str):
    """获取某天统计数据"""
    stats = get_app_stats(date_str)
    return jsonify(stats)


# ---- 辅助函数 ----

def _get_screenshots_for_date(date_str):
    """获取某天的截图列表"""
    day_dir = SCREENSHOT_DIR / date_str
    if not day_dir.exists():
        return []
    screenshots = []
    for f in sorted(day_dir.glob("*.jpg")):
        screenshots.append({
            "path": str(f.relative_to(SCREENSHOT_DIR)),
            "name": f.stem,
            "size": f"{f.stat().st_size / 1024:.0f}KB",
        })
    return screenshots


def run_dashboard():
    """启动后台"""
    config = load_config()
    host = config.get("dashboard_host", "127.0.0.1")
    port = config.get("dashboard_port", 5001)
    print(f"🌐 Life Tracker 后台: http://{host}:{port}")
    print(f"   按 Ctrl+C 停止")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_dashboard()
