@echo off
chcp 65001 >nul

echo === 家教助手部署脚本 ===

echo 1. 检查 Python 版本...
python --version

echo 2. 创建虚拟环境...
python -m venv venv

echo 3. 激活虚拟环境...
call venv\Scripts\activate.bat

echo 4. 安装依赖...
pip install -r requirements.txt

echo 5. 运行测试...
pytest tests\ -v

echo === 部署完成 ===
echo 运行命令: venv\Scripts\activate.bat ^&^& python main.py
pause
