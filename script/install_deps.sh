#!/bin/bash

# 获取脚本所在目录的上一级目录作为项目根目录
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)

# 检测 python 命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

echo "正在安装 Playwright 浏览器及系统依赖..."
echo "注意：此步骤可能需要 sudo 权限，请输入密码（如果需要）"

# 安装浏览器内核
$PYTHON_CMD -m playwright install chromium

# 安装系统依赖 (需要 sudo)
if command -v sudo &> /dev/null; then
    sudo $PYTHON_CMD -m playwright install-deps chromium
else
    echo "未找到 sudo 命令，尝试直接运行..."
    $PYTHON_CMD -m playwright install-deps chromium
fi

echo "安装完成。"
