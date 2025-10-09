# context_builder.py
import sqlite3
import json
from config import DB_PATH

class ContextBuilder:
    def __init__(self):
        pass

    def get_recent_history(self, task_id: str, limit: int = 5) -> list:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, status, metrics, feedback
            FROM execution_history
            WHERE task_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (task_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def build_state(self, current_result: dict) -> dict:
        history = self.get_recent_history(current_result["task_id"], 5)
        trend = self._analyze_trend(history)

        return {
            "task_id": current_result["task_id"],
            "current": {
                "status": current_result["status"],
                "metrics": current_result["metrics"],
                "feedback": current_result.get("feedback", {}),
                "logs": current_result.get("logs", [])
            },
            "history": history,
            "trend": trend
        }

    def _analyze_trend(self, history: list) -> dict:
        if not history:
            return {}
        durations = [json.loads(h["metrics"]).get("duration_sec", 0) for h in history]
        trend_duration = "stable"
        if len(durations) >= 2:
            if durations[0] > durations[1] * 1.2:
                trend_duration = "increasing"
            elif durations[0] < durations[1] * 0.8:
                trend_duration = "decreasing"
        return {"duration_trend": trend_duration}