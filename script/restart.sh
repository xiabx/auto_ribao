#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "正在重启服务..."

# 调用停止脚本
bash "$SCRIPT_DIR/stop.sh"

# 等待一小会儿确保端口释放
sleep 2

# 调用启动脚本
bash "$SCRIPT_DIR/start.sh"
