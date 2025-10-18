import csv
import os
from neo4j import GraphDatabase
from tqdm import tqdm  # 可选：显示进度条，若不需要可删掉相关代码

# === 配置区 ===


NEO4J_URI = "bolt://121.36.203.36:10008"  # 注意：通常 Neo4j 使用 7687 端口（bolt 协议）
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678"

CSV_FILE = "market_code.csv"         # CSV 文件路径（需在当前目录或指定绝对路径）
BATCH_SIZE = 1000                        # 每批处理多少行

# === 主程序 ===
def main():
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV 文件不存在: {CSV_FILE}")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 获取总行数（用于进度条）
    with open(CSV_FILE, 'r', encoding='gbk') as f:
        total_rows = sum(1 for _ in f) - 1  # 减去 header

    print(f"📊 共 {total_rows} 行数据待处理...")

    batch = []
    processed = 0
    updated_count = 0

    with open(CSV_FILE, 'r', encoding='gbk') as f:
        reader = csv.DictReader(f)
        for row in tqdm(reader, total=total_rows, desc="🔄 更新节点"):
            code = row.get('code')
            capability = row.get('capability')
            datascope = row.get('datascope')
            database= row.get('database')

            if not code:
                continue  # 跳过无 code 的行
            print(f"Processing row: code={repr(code)}, cap={repr(capability)}, scope={repr(datascope)}")
            batch.append((code, capability, datascope,database))

            if len(batch) >= BATCH_SIZE:
                updated = update_batch(driver, batch)
                updated_count += updated
                processed += len(batch)
                print(f"✅ 已处理 {processed}/{total_rows} 行，成功更新 {updated_count} 个节点")
                batch = []

        # 处理剩余批次
        if batch:
            
            updated = update_batch(driver, batch)
            updated_count += updated
            print(f"✅ 最终批次完成，总计更新 {updated_count} 个节点")

    driver.close()
    print("🎉 所有数据更新完毕！")


def update_batch(driver, batch):
    """执行一个批次的更新"""
    query = """
    UNWIND $batch AS row
    MATCH (n {code: row.code})
    SET n.capability = row.capability,
        n.datascope = row.datascope,
        n.database=row.database
    RETURN count(n) AS updated
    """
    params = {
        "batch": [
            {"code": code, "capability": cap, "datascope": scope,"database":db}
            for code, cap, scope ,db in batch
        ]
    }
    with driver.session() as session:
        result = session.run(query, params)
        record = result.single()
        updated_count = record["updated"] if record else 0
        print(f"  → 本批次实际更新节点数: {updated_count}")
        return updated_count


if __name__ == "__main__":
    main()