#!/bin/bash
# 运行测试脚本

echo "Excel Reader 测试脚本"
echo "===================="
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python"
    exit 1
fi

# 运行测试
echo "运行测试..."
python3 test_example.py "$@"

