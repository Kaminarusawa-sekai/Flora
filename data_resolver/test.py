# main.py
import thespian.actors as actors
from data_actor import DataActor

if __name__ == "__main__":
    system = actors.ActorSystem("simpleSystemBase")

    handler = system.createActor(DataActor)

    # 模拟查询
    msg = {
        "type": "query",
        "business_id": "biz_001",
        "database": "eqiai_wecom",
        "table_name": "crm_channel_active_info",
        "question": "线上广告活码1的id"
    }
    # 实际使用中需指定回复目标 Actor
     # ✅ 使用 ask() 等待回复（超时 10 秒）
    result = system.ask(handler, msg, timeout=1000)
    print("Final Result:", result)

    system.shutdown()