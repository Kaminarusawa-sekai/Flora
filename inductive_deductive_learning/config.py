# config.py
import os

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 从环境变量读取
DB_PATH = "optimization.db"