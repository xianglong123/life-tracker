"""
Life Tracker — macOS 活动监控器
追踪：当前应用、窗口标题、闲置时间 + 周期截图
"""
import subprocess
import time
import os
import shutil
from datetime import datetime, date
from pathlib import Path

from config import load_config, DATA_DIR
from database import record_activity, update_app_stats


def get_active_window():
    """获取 macOS 当前活跃窗口的应用名和标题（两步走，避免后台进程弹窗）"""
    # 系统进程黑名单（这些 app 不查窗口标题，跳过 tell application）
    _SYSTEM_PROCS = {
        "app_model_loader", "app_mode_loader", "appstoreagent",
        "storeagent", "bird", "cloudd", "nsurlsessiond",
        "trustd", "secinitd", "securityd", "syspolicyd",
        "mobileassetd", "amfid", "loginwindow", "WindowServer",
        "CoreBrightness", "CoreServicesUIAgent",
    }

    script = '''
    tell application "System Events"
        set frontProc to first application process whose frontmost is true
        set frontApp to name of frontProc
        set frontAppId to bundle identifier of frontProc
    end tell
    return frontApp & "|||" & frontAppId
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {"app_name": "Unknown", "app_id": "", "window_title": ""}

        parts = result.stdout.strip().split("|||")
        app_name = parts[0] if len(parts) > 0 else "Unknown"
        app_id = parts[1] if len(parts) > 1 else ""

        # 只对前台用户应用获取窗口标题（避免后台进程弹窗）
        window_title = ""
        if app_name not in _SYSTEM_PROCS:
            try:
                title_result = subprocess.run(
                    ["osascript", "-e",
                     f'tell application "{app_name}" to get name of front window'],
                    capture_output=True, text=True, timeout=3
                )
                if title_result.returncode == 0:
                    window_title = title_result.stdout.strip()
            except Exception:
                pass

        return {"app_name": app_name, "app_id": app_id, "window_title": window_title}
    except Exception as e:
        pass
    return {"app_name": "Unknown", "app_id": "", "window_title": ""}


def get_idle_time():
    """获取闲置时间（秒）"""
    try:
        result = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem", "-r", "-d", "1"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "HIDIdleTime" in line:
                try:
                    # 值是以纳秒为单位的
                    ns = int(line.split("=")[-1].strip())
                    return int(ns / 1_000_000_000)
                except:
                    return 0
    except:
        pass
    return 0


def take_screenshot(output_path):
    """截屏（静音模式）"""
    try:
        output_path = str(output_path)
        subprocess.run(
            ["screencapture", "-x", "-t", "jpg", output_path],
            capture_output=True, timeout=10
        )
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"[截图失败] {e}")
        return False


def compress_jpeg(path, quality=60):
    """用 sips 压缩 JPEG（macOS 内置工具）"""
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality),
             str(path), "--out", str(path)],
            capture_output=True, timeout=10
        )
    except:
        pass


def clean_old_screenshots(retention_days=30):
    """清理过期截图"""
    screenshot_dir = DATA_DIR / "screenshots"
    if not screenshot_dir.exists():
        return
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=retention_days)
    for day_dir in screenshot_dir.iterdir():
        if day_dir.is_dir():
            try:
                dir_date = datetime.strptime(day_dir.name, "%Y-%m-%d").date()
                if dir_date < cutoff:
                    shutil.rmtree(day_dir)
                    print(f"[清理] 删除过期截图目录: {day_dir.name}")
            except:
                pass


def run_tracker():
    """主监控循环"""
    config = load_config()
    track_interval = config.get("track_interval", 5)
    screenshot_interval = config.get("screenshot_interval", 300)
    quality = config.get("screenshot_quality", 60)
    retention = config.get("screenshot_retention_days", 30)
    idle_threshold = config.get("idle_threshold", 120)

    print("=" * 50)
    print("📊 Life Tracker 已启动")
    print(f"   监控间隔: {track_interval}秒")
    print(f"   截图间隔: {screenshot_interval}秒")
    print(f"   截图质量: {quality}%")
    print(f"   闲置阈值: {idle_threshold}秒")
    print("=" * 50)

    last_app = ""
    last_window = ""
    last_active_time = time.time()
    activity_minutes = {}  # app -> seconds
    last_flush_time = time.time()
    last_record_time = time.time()
    activity_buffer = {}  # app_name -> accumulated seconds (for between-flush)

    # 系统后台进程黑名单（过滤掉干扰项）
    SYSTEM_PROCESSES = {
        "app_model_loader", "app_mode_loader", "appstoreagent",
        "storeagent", "bird", "cloudd", "nsurlsessiond",
        "trustd", "secinitd", "securityd", "syspolicyd",
        "mobileassetd", "amfid", "loginwindow", "WindowServer",
        "CoreBrightness",
    }

    # 跳过系统进程时的备选应用
    last_valid_app = None
    last_valid_window = ""

    screenshot_counter = 0
    last_screenshot_time = 0
    today_str = date.today().isoformat()

    while True:
        try:
            now = time.time()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            today_str_new = date.today().isoformat()

            # 跨天处理
            if today_str_new != today_str:
                _flush_app_stats(activity_minutes, today_str)
                activity_minutes = {}
                today_str = today_str_new
                clean_old_screenshots(retention)

            # 获取当前活跃窗口
            win = get_active_window()
            app_name = win.get("app_name", "Unknown")
            window_title = win.get("window_title", "")
            idle_seconds = get_idle_time()
            is_idle = idle_seconds > idle_threshold

            # 过滤系统后台进程 —— 跳过并复用上一个有效应用
            if app_name in SYSTEM_PROCESSES:
                if last_valid_app:
                    app_name = last_valid_app
                    window_title = last_valid_window
                else:
                    # 没有之前有效的应用记录，跳过这轮
                    time.sleep(track_interval)
                    continue

            # 记录最近一次真实的应用
            if app_name not in SYSTEM_PROCESSES:
                last_valid_app = app_name
                last_valid_window = window_title

            # 检测窗口切换
            app_changed = (app_name != last_app or window_title != last_window)

            if app_changed and last_app:
                # 记录切换前应用的持续时长
                elapsed = now - last_active_time
                key = f"{today_str}|{last_app}"
                activity_minutes[key] = activity_minutes.get(key, 0) + elapsed
                activity_buffer[key] = activity_buffer.get(key, 0) + elapsed

                record_activity(
                    timestamp=current_time,
                    app_name=last_app,
                    window_title=last_window,
                    duration=int(elapsed),
                    is_idle=False
                )

                last_active_time = now

            last_app = app_name
            last_window = window_title

            # 每 60 秒强制记录一次（即使应用没切换）
            if now - last_record_time >= 60:
                elapsed = now - last_active_time
                key = f"{today_str}|{app_name}"
                activity_minutes[key] = activity_minutes.get(key, 0) + elapsed
                activity_buffer[key] = activity_buffer.get(key, 0) + elapsed

                record_activity(
                    timestamp=current_time,
                    app_name=app_name,
                    window_title=window_title,
                    duration=int(elapsed),
                    is_idle=is_idle
                )
                last_record_time = now
                last_active_time = now

            # 每 60 秒刷新一次 app 统计数据到数据库
            if now - last_flush_time >= 60:
                _flush_app_stats(activity_buffer, today_str)
                activity_buffer = {}
                last_flush_time = now

            # 截图计时
            if not is_idle and (now - last_screenshot_time) >= screenshot_interval:
                _do_screenshot(current_time, quality)
                last_screenshot_time = now
                screenshot_counter += 1

            time.sleep(track_interval)

        except KeyboardInterrupt:
            print("\n⏹  Life Tracker 已停止")
            _flush_app_stats(activity_minutes, today_str)
            break
        except Exception as e:
            print(f"[错误] {e}")
            time.sleep(track_interval)


def _do_screenshot(timestamp, quality):
    """执行一次截图"""
    try:
        today = date.today()
        day_dir = DATA_DIR / "screenshots" / today.isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)

        time_str = timestamp.replace(":", "-").replace(" ", "_")
        filename = f"{time_str}.jpg"
        filepath = day_dir / filename

        if take_screenshot(filepath):
            compress_jpeg(filepath, quality)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"[截图] {timestamp} ({size_kb:.0f}KB)")
            from database import save_screenshot_path
            save_screenshot_path(timestamp, str(filepath))
            return str(filepath)
    except Exception as e:
        print(f"[截图失败] {e}")
    return None


def _flush_app_stats(activity_minutes, today_str):
    """将缓存的app时长写入数据库"""
    from database import update_app_stats
    for key, seconds in activity_minutes.items():
        parts = key.split("|")
        if len(parts) == 2 and parts[0] == today_str:
            minutes = max(1, int(seconds / 60))
            update_app_stats(today_str, parts[1], minutes)


if __name__ == "__main__":
    run_tracker()
