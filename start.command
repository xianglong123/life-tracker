#!/bin/bash
cd /Users/xianglong/workspace/life-tracker
echo "🚀 Life Tracker 正在启动..."
echo ""

# 检查 Flask
pip3 show flask > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⏳ 正在安装依赖..."
    pip3 install flask --quiet
fi

echo "📊 启动后台监控..."
python3 main.py tracker &
TRACKER_PID=$!
echo "   PID: $TRACKER_PID"

echo "🌐 启动 Web 后台..."
python3 main.py dashboard &
DASHBOARD_PID=$!
echo "   PID: $DASHBOARD_PID"

echo ""
echo "📋 访问 http://127.0.0.1:5001 查看"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $TRACKER_PID $DASHBOARD_PID 2>/dev/null; echo '已停止'; exit" SIGINT SIGTERM
wait
