#!/usr/bin/env python3
import os
import sys
import subprocess

project_root = os.path.abspath(os.path.dirname(__file__))
os.environ["PYTHONPATH"] = project_root

print("🚀 启动 Interaction Service")
print(f"工作目录: {project_root}")
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "interaction.main:app",   # 模块路径：interaction/main.py 中的 app
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
], cwd=project_root)