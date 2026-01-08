#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from typing import List, Dict, Any, Tuple
from neo4j import GraphDatabase, basic_auth


def load_updates(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("JSON root must be a list")

    seen_element_ids = set()
    rows = []

    for item in payload:
        node_data = item.get("n", {})
        element_id = node_data.get("elementId")
        if element_id is None:
            continue

        if element_id in seen_element_ids:
            continue
        seen_element_ids.add(element_id)

        props = node_data.get("properties", {})
        # 可选：只保留你需要更新的字段，避免意外覆盖
        # 如果要全量覆盖，直接用 props 即可
        # 例如：
        # update_props = {k: v for k, v in props.items() if k in {"id", "parent_id", "capability", "datascope", "name", "businessId"}}
        # 但通常直接传整个 props 更简单

        rows.append({
            "element_id": element_id,
            "props": props  # 👈 传递整个属性字典
        })

    return rows


def update_batch(
    driver,
    rows: List[Dict[str, Any]],
    report_missing: bool,
) -> Tuple[int, List[int]]:
    """使用 Neo4j 内部 ID (identity) 批量更新节点的 datascope。"""
    updated = 0
    missing_identities = []

    # 更新语句：通过 id(n) 匹配
    update_query = """
        UNWIND $rows AS row
        MATCH (n) WHERE elementId(n) = row.element_id
        SET n += row.props  // 👈 合并/覆盖属性
        RETURN count(n) AS updated
        """

    with driver.session() as session:
        result = session.run(update_query, {"rows": rows})
        record = result.single()
        updated = record["updated"] if record else 0

        if report_missing:
            # 查询哪些 identity 实际存在
            find_query = """
            UNWIND $identities AS iid
            MATCH (n) WHERE id(n) = iid
            RETURN id(n) AS identity
            """
            identities = [r["identity"] for r in rows]
            found_result = session.run(find_query, {"identities": identities})
            found_set = {record["identity"] for record in found_result}

            missing_identities = [
                r["identity"] for r in rows if r["identity"] not in found_set
            ]

    return updated, missing_identities


def main() -> int:
    # 直接定义参数值，无需控制台传入
    json_path = "records (1)(4).json"
    batch_size = 200
    report_missing = False
    
    # Neo4j 连接信息
    uri = "bolt://121.36.203.36:10008"
    user = "neo4j"
    password = "12345678"

    try:
        driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))
        # 验证连接
        driver.verify_connectivity()
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}", file=sys.stderr)
        return 2

    try:
        rows = load_updates(json_path)
        if not rows:
            print("No valid nodes with 'identity' found in JSON.")
            return 1

        total_updated = 0
        all_missing = []

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            updated, missing = update_batch(driver, batch, report_missing)
            total_updated += updated
            all_missing.extend(missing)

        print(f"✅ Updated nodes: {total_updated}/{len(rows)}")
        if report_missing and all_missing:
            print("⚠️ Missing node identities (not found in DB):")
            for iid in sorted(all_missing):
                print(iid)

        return 0

    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())