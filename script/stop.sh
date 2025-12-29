#!/bin/bash

# 获取脚本所在目录的上一级目录作为项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
PID_FILE="$PROJECT_ROOT/app.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "未找到 PID 文件，服务可能未运行"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p $PID > /dev/null; then
    echo "正在停止服务 (PID: $PID)..."
    kill $PID
    
    # 等待进程结束
    count=0
    while ps -p $PID > /dev/null; do
        sleep 1
        count=$((count+1))
        if [ $count -gt 10 ]; then
            echo "服务未响应，强制停止..."
            kill -9 $PID
            break
        fi
    done
    
    echo "服务已停止"
    rm "$PID_FILE"
else
    echo "进程 $PID 不存在，清理 PID 文件"
    rm "$PID_FILE"
fi
