#!/bin/bash

# 获取脚本所在目录的上一级目录作为项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
# 进入 src 目录运行
cd "$PROJECT_ROOT/src"

PID_FILE="$PROJECT_ROOT/app.pid"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "服务已经在运行中 (PID: $PID)"
        exit 1
    else
        echo "PID 文件存在但进程不存在，清理 PID 文件..."
        rm "$PID_FILE"
    fi
fi

# 确保日志目录存在
mkdir -p "$PROJECT_ROOT/log"

# 检测 python 命令，优先使用 python3
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

# 启动服务
echo "正在启动服务 (使用 $PYTHON_CMD)..."
nohup $PYTHON_CMD app.py > /dev/null 2>&1 &

# 获取并保存 PID
NEW_PID=$!
echo $NEW_PID > "$PID_FILE"
echo "服务已启动 (PID: $NEW_PID)"
