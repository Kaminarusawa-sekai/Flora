#!/usr/bin/env python3
import os
import sys
import subprocess

project_root = os.path.abspath(os.path.dirname(__file__))
os.environ["PYTHONPATH"] = project_root



# ✅ 直接运行 tasks/main.py，不再通过 uvicorn 加载 ASGI app
subprocess.run([
    sys.executable, "-u","tasks/main.py",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--rabbitmq",          # 如果需要 RabbitMQ
    "--debug",           # 如需开启 debug 模式（非热重载）
    
], cwd=project_root)