#!/usr/bin/env python3
import os
import sys
import subprocess

project_root = os.path.abspath(os.path.dirname(__file__))
os.environ["PYTHONPATH"] = project_root

print("🚀 启动 Trigger Service")
print(f"工作目录: {project_root}")
subprocess.run([sys.executable, 
                "trigger/main.py"
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"], cwd=project_root)