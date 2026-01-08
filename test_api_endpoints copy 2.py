import uuid
import json
import requests
from datetime import datetime

# API 基础 URL
BASE_URL = "http://localhost:8004"  # 请根据实际情况修改
API_V1_PREFIX = f"{BASE_URL}/api/v1"

# 测试用的 request_id
REQUEST_ID = "71242311-9be7-4dfd-8134-873b33a7a261"

# 生成 trace_id
TRACE_ID = f"test-trace-{str(uuid.uuid4())[:8]}"

# 测试数据
TEST_USER_ID = "test-user-123"

# 辅助函数：发送 POST 请求
def send_post_request(endpoint, data):
    url = f"{API_V1_PREFIX}{endpoint}"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"\nPOST {endpoint}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response

# 辅助函数：发送 GET 请求
def send_get_request(endpoint):
    url = f"{API_V1_PREFIX}{endpoint}"
    response = requests.get(url)
    print(f"\nGET {endpoint}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response

# 测试 1：启动 trace (创建根节点)
def test_start_trace():
    print("=== 测试 1: 启动 Trace ===")
    data = {
        "request_id": REQUEST_ID,
        "trace_id": TRACE_ID,
        "input_params": {"test_param": "test_value"},
        "user_id": TEST_USER_ID
    }
    response = send_post_request("/traces/start", data)
    return response.json().get("trace_id")

# 测试 2：分裂任务 (测试 split_task)
def test_split_task(trace_id, parent_id):
    print("\n=== 测试 2: 分裂任务 ===")
    subtasks_meta = [
        {
            "id": f"subtask-{str(uuid.uuid4())[:8]}",
            "name": "Subtask 1",
            "params": {"subtask_param": "value1"},
            "actor_type": "AGENT"
        },
        {
            "id": f"subtask-{str(uuid.uuid4())[:8]}",
            "name": "Subtask 2",
            "params": {"subtask_param": "value2"},
            "actor_type": "AGENT"
        }
    ]
    
    data = {
        "parent_id": parent_id,
        "trace_id": trace_id,
        "subtasks_meta": subtasks_meta,
        "reasoning_snapshot": {"reason": "Test split task"}
    }
    
    response = send_post_request(f"/traces/{trace_id}/split", data)
    return response.json().get("new_child_ids", [])

# 测试 3：上报任务状态 (测试 report_execution_event)
def test_report_execution_event(task_id, event_type="STARTED", extra_data=None, agent_id=None):
    print(f"\n=== 测试 3: 上报任务状态 - {event_type} ===")
    base_data = {
        "task_id": task_id,
        "trace_id": TRACE_ID,
        "event_type": event_type,
        "enriched_context_snapshot": {
            "lifecycle": event_type.lower(),
            "timestamp": datetime.now().isoformat()
        },
        "agent_id": agent_id,
        "worker_id": "test-worker-456",
        "realtime_info": {"step": 1},
    }

    if event_type == "COMPLETED":
        base_data["data"] = extra_data or {"result": "success"}
    elif event_type == "FAILED":
        base_data["error"] = "simulated error"

    response = send_post_request("/traces/events", base_data)
    return response.json()

# 测试 4：查询 trace 状态
def test_get_trace_status():
    print("\n=== 测试 4: 查询 Trace 状态 ===")
    response = send_get_request(f"/traces/{TRACE_ID}/status")
    return response.json()

# 主测试函数
def main(strategy_mode="full"):
    """
    strategy_mode 可选值:
      - "quick"   : 快速启动型（仅机制）
      - "user"    : 用户精细化型（分层+策略）
      - "full"    : 全链路完整型（默认）
    """
    print(f"开始测试 API 端点，使用 request_id: {REQUEST_ID}")
    print(f"Generated trace_id: {TRACE_ID}")
    print(f"▶ 执行策略模式: {strategy_mode}")

    AGENT_CODE_TO_NAME = {
        "rules_system_create_active": "规则与系统构建-新增活动",
        "rules_system_create_active_center": "规则与系统构建-新增活动中心",
        "private_domain": "私域营销",
        "fission_activity": "裂变活动策划",
        "fission_implement": "裂变实施",
        "fission_mech_design": "裂变机制设计",
        "user_strat_fission": "用户分层裂变设计",
        "activity_creative": "活动创意与立项",
        "def_planning": "定义与规划",
        "fission_user_portrait": "裂变用户分层与画像定义",
        "mech_game_design": "机制与玩法设计",
        "rules_system": "规则与系统构建",
        "strat_fission_strat": "分层裂变策略设计",
        "comm_scripts": "定制沟通话术与素材",
        "copy_planning": "文案策划",
        "fission_game_match": "匹配裂变玩法",
        "gameplay_mode": "玩法模式选择",
        "goal_setting": "目标设定",
        "incentive_system": "激励体系设计",
        "strat_incentives": "设计分层激励",
        "strat_portraits": "绘制分层画像",
    }


    # ====== 从你提供的节点自动生成任务树 ======

    RAW_NODES = [
        {"name": " 规则与系统构建-新增活动中心", "id": "rules_system_create_active_center", "parent_id": None},
        {"name": " 私域营销", "id": "private_domain", "parent_id": None},
        {"name": " 裂变机制设计", "id": "fission_mech_design", "parent_id": None},
        {"name": " 用户分层裂变设计", "id": "user_strat_fission", "parent_id": None},
        {"name": " 分层裂变策略设计", "id": "strat_fission_strat", "parent_id": None},
        {"name": " 定制沟通话术与素材", "id": "comm_scripts", "parent_id": None},
        {"name": " 文案策划", "id": "copy_planning", "parent_id": None},
        {"name": " 匹配裂变玩法", "id": "fission_game_match", "parent_id": None},
        {"name": " 目标设定", "id": "goal_setting", "parent_id": None},
        {"name": " 设计分层激励", "id": "strat_incentives", "parent_id": None},
        {"name": " 绘制分层画像", "id": "strat_portraits", "parent_id": None},
        {"name": "客户运营*", "id": "customer_operations", "parent_id": "marketing"},
        {"name": "营销", "id": "marketing", "parent_id": None},
        {"name": "客户分层与标签化", "id": "customer_segmentation_and_tagging", "parent_id": "customer_operations"},
        {"name": "数据采集与整合", "id": "data_collection_and_integration", "parent_id": "customer_segmentation_and_tagging"},
        {"name": "标签体系设计", "id": "tagging_system_design", "parent_id": "customer_segmentation_and_tagging"},
        {"name": "定义标签维度", "id": "define_tag_dimensions", "parent_id": "tagging_system_design"},
        {"name": "制定标签规则", "id": "define_tag_rules", "parent_id": "tagging_system_design"},
        {"name": "自动化打标与分层", "id": "automated_tagging_and_segmentation", "parent_id": "customer_segmentation_and_tagging"},
        {"name": "*自动化培育流程设计", "id": "automated_nurturing_process_design", "parent_id": "customer_operations"},
        {"name": "多形式精准内容触达", "id": "multi_format_precise_content_delivery", "parent_id": "automated_nurturing_process_design"},
        {"name": "定义触发事件", "id": "define_trigger_events", "parent_id": "multi_format_precise_content_delivery"},
        {"name": "匹配内容与渠道", "id": "match_content_and_channels", "parent_id": "multi_format_precise_content_delivery"},
        {"name": "制定时机规则", "id": "define_timing_rules", "parent_id": "multi_format_precise_content_delivery"},
        {"name": "培育策略与路径设计流程", "id": "nurturing_strategy_and_path_design_process", "parent_id": "automated_nurturing_process_design"},
        {"name": "定义培育目标", "id": "define_nurturing_goals", "parent_id": "nurturing_strategy_and_path_design_process"},
        {"name": "绘制培育路径蓝图", "id": "draw_nurturing_path_blueprint", "parent_id": "nurturing_strategy_and_path_design_process"},
        {"name": "效能监控与路径优化流程", "id": "performance_monitoring_and_path_optimization_process", "parent_id": "automated_nurturing_process_design"},
        {"name": "MQL资格判定与流转", "id": "mql_qualification_assessment_and_handoff", "parent_id": "customer_operations"},
        {"name": "MQL判定标准制定", "id": "mql_qualification_criteria_definition", "parent_id": "mql_qualification_assessment_and_handoff"},
        {"name": "自动化判定", "id": "automated_assessment", "parent_id": "mql_qualification_assessment_and_handoff"},
        {"name": "自动化判定与触发流转流程", "id": "automated_assessment_and_triggered_handoff_process", "parent_id": "mql_qualification_assessment_and_handoff"},
        {"name": "销售反馈与闭环优化流程", "id": "sales_feedback_and_closed_loop_optimization_process", "parent_id": "mql_qualification_assessment_and_handoff"},
        {"name": "深化需求", "id": "needs_deepening", "parent_id": "customer_operations"},
        {"name": "需求洞察与机会识别流程", "id": "needs_insight_and_opportunity_identification_process", "parent_id": "needs_deepening"},
        {"name": "定义机会规则", "id": "define_opportunity_rules", "parent_id": "needs_insight_and_opportunity_identification_process"},
        {"name": "系统扫描", "id": "system_scanning", "parent_id": "needs_insight_and_opportunity_identification_process"},
        {"name": "个性化策略与触达执行流程", "id": "personalized_strategy_and_reach_execution_process", "parent_id": "needs_deepening"},
        {"name": "机会分配", "id": "opportunity_allocation", "parent_id": "personalized_strategy_and_reach_execution_process"},
        {"name": "制定沟通策略", "id": "define_communication_strategy", "parent_id": "personalized_strategy_and_reach_execution_process"},
        {"name": "多渠道触达", "id": "multi_channel_reach", "parent_id": "personalized_strategy_and_reach_execution_process"},
        {"name": "闭环管理与价值验证流程", "id": "closed_loop_management_and_value_validation_process", "parent_id": "needs_deepening"},
        {"name": "设计验证指标", "id": "design_validation_metrics", "parent_id": "closed_loop_management_and_value_validation_process"},
        {"name": "价值验证", "id": "value_validation", "parent_id": "closed_loop_management_and_value_validation_process"},
        {"name": "客户健康度监测", "id": "customer_health_monitoring", "parent_id": "customer_operations"},
        {"name": "健康度指标体系设计流程", "id": "health_metrics_system_design_process", "parent_id": "customer_health_monitoring"},
        {"name": "确定健康度维度", "id": "determine_health_dimensions", "parent_id": "health_metrics_system_design_process"},
        {"name": "定义指标与权重", "id": "define_metrics_and_weights", "parent_id": "health_metrics_system_design_process"},
        {"name": "设定阈值与等级", "id": "set_thresholds_and_levels", "parent_id": "health_metrics_system_design_process"},
        {"name": "自动化监控与预警触发流程", "id": "automated_monitoring_and_alert_trigger_process", "parent_id": "customer_health_monitoring"},
        {"name": "分级干预与反馈优化流程", "id": "tiered_intervention_and_feedback_optimization_process", "parent_id": "customer_health_monitoring"},
        {"name": "根因调查", "id": "root_cause_investigation", "parent_id": "tiered_intervention_and_feedback_optimization_process"},
        {"name": "执行分级干预措施", "id": "execute_tiered_interventions", "parent_id": "tiered_intervention_and_feedback_optimization_process"},
        {"name": "记录干预结果", "id": "record_intervention_results", "parent_id": "tiered_intervention_and_feedback_optimization_process"},
        {"name": "品牌建设", "id": "brand_building", "parent_id": "marketing"},
        {"name": "品牌定位", "id": "brand_positioning", "parent_id": "brand_building"},
        {"name": "品牌故事", "id": "brand_story", "parent_id": "brand_building"},
        {"name": "价值观输出", "id": "values_output", "parent_id": "brand_building"},
        {"name": "总体战略", "id": "overall_strategy", "parent_id": "marketing"},
        {"name": "市场洞察", "id": "market_insight", "parent_id": "overall_strategy"},
        {"name": "目标客户分析", "id": "target_customer_analysis", "parent_id": "overall_strategy"},
        {"name": "核心卖点提炼", "id": "core_selling_point_refinement", "parent_id": "overall_strategy"},
        {"name": "建议定价策略", "id": "pricing_strategy_recommendation", "parent_id": "overall_strategy"},
        {"name": "竞品分析*", "id": "competitor_analysis", "parent_id": "overall_strategy"},
        {"name": "差异化机会", "id": "differentiation_opportunities", "parent_id": "overall_strategy"}
    ]

    # 构建 code -> name 映射（去除前后空格）
    AGENT_CODE_TO_NAME = {
        node["id"]: node["name"].strip() for node in RAW_NODES
    }

    # 构建任务树：parent_id -> [child_ids]
    TASK_TREE = {}

    # 初始化所有节点（包括根节点）
    for node in RAW_NODES:
        agent_id = node["id"]
        parent_id = node["parent_id"]
        if parent_id is None:
            # 根节点：暂时不加入 TASK_TREE，由调用方指定入口
            continue
        if parent_id not in TASK_TREE:
            TASK_TREE[parent_id] = []
        TASK_TREE[parent_id].append(agent_id)

    # 补全叶子节点（无子任务的节点）
    all_ids = {node["id"] for node in RAW_NODES}
    for agent_id in all_ids:
        if agent_id not in TASK_TREE:
            TASK_TREE[agent_id] = []  # 叶子节点

    # 找出所有根节点（可用于不同入口）
    ROOT_NODES = [node["id"] for node in RAW_NODES if node["parent_id"] is None]

    print("✅ 已从输入数据构建任务树")
    print(f"根节点: {ROOT_NODES}")
    print(f"总任务数: {len(AGENT_CODE_TO_NAME)}")


    # 手动补充私域营销的子任务（根据你之前的逻辑）
    PRIVATE_DOMAIN_SUBTREE = {
        "private_domain": [
            "user_strat_fission",
            "fission_mech_design",
            "copy_planning",
            "comm_scripts"
        ],
        "user_strat_fission": ["strat_portraits", "strat_fission_strat"],
        "strat_fission_strat": ["fission_game_match", "strat_incentives"],
        "fission_mech_design": ["goal_setting"],
        # 其他已存在，无需重复
    }

    # 合并到 TASK_TREE
    for parent, children in PRIVATE_DOMAIN_SUBTREE.items():
        if parent in TASK_TREE:
            # 避免重复，用 set 合并
            existing = set(TASK_TREE[parent])
            TASK_TREE[parent] = list(existing | set(children))
        else:
            TASK_TREE[parent] = children

    # # 完整任务依赖树（不变）
    FULL_TASK_TREE = {
        "private_domain": [
            "user_strat_fission",
            "fission_mech_design",
            "copy_planning",
            "comm_scripts"
        ],
        "user_strat_fission": ["strat_portraits", "strat_fission_strat"],
        "strat_fission_strat": ["fission_game_match", "strat_incentives"],
        "fission_mech_design": ["goal_setting"],
        "strat_portraits": [],
        "fission_game_match": [],
        "strat_incentives": [],
        "goal_setting": [],
        "copy_planning": [],
        "comm_scripts": []
    }

    BRAND_BUILDING_PATH = [
        "marketing",
        "brand_building",
        "brand_positioning",
        "brand_story",
        "values_output"
    ]

    CUSTOMER_OPS_FULL_PATH = [
        "marketing",
        "customer_operations",
        "customer_segmentation_and_tagging",
        "data_collection_and_integration",
        "tagging_system_design",
        "define_tag_dimensions",
        "define_tag_rules",
        "automated_tagging_and_segmentation",
        "automated_nurturing_process_design",
        "multi_format_precise_content_delivery",
        "define_trigger_events",
        "match_content_and_channels",
        "define_timing_rules",
        "nurturing_strategy_and_path_design_process",
        "define_nurturing_goals",
        "draw_nurturing_path_blueprint",
        "performance_monitoring_and_path_optimization_process",
        "mql_qualification_assessment_and_handoff",
        "mql_qualification_criteria_definition",
        "automated_assessment",
        "automated_assessment_and_triggered_handoff_process",
        "sales_feedback_and_closed_loop_optimization_process",
        "needs_deepening",
        "needs_insight_and_opportunity_identification_process",
        "define_opportunity_rules",
        "system_scanning",
        "personalized_strategy_and_reach_execution_process",
        "opportunity_allocation",
        "define_communication_strategy",
        "multi_channel_reach",
        "closed_loop_management_and_value_validation_process",
        "design_validation_metrics",
        "value_validation",
        "customer_health_monitoring",
        "health_metrics_system_design_process",
        "determine_health_dimensions",
        "define_metrics_and_weights",
        "set_thresholds_and_levels",
        "automated_monitoring_and_alert_trigger_process",
        "tiered_intervention_and_feedback_optimization_process",
        "root_cause_investigation",
        "execute_tiered_interventions",
        "record_intervention_results"
    ]

    MARKET_INSIGHT_AND_COMPETITOR_ANALYSIS_PATH = [
        "marketing",
        "overall_strategy",
        "market_insight",
        "target_customer_analysis",
        "core_selling_point_refinement",
        "pricing_strategy_recommendation",
        "competitor_analysis",
        "differentiation_opportunities"
    ]

    LEAD_GEN_FOCUS_PATH = [
        "marketing",
        "customer_operations",
        "customer_segmentation_and_tagging",
        "tagging_system_design",
        "define_tag_rules",               # 快速打标
        "automated_tagging_and_segmentation",
        "mql_qualification_assessment_and_handoff",
        "mql_qualification_criteria_definition",
        "automated_assessment",
        "automated_assessment_and_triggered_handoff_process"
    ]

    HEALTH_RETENTION_PATH = [
        "marketing",
        "customer_operations",
        "customer_health_monitoring",
        "health_metrics_system_design_process",
        "determine_health_dimensions",
        "define_metrics_and_weights",
        "set_thresholds_and_levels",
        "automated_monitoring_and_alert_trigger_process",
        "tiered_intervention_and_feedback_optimization_process",
        "root_cause_investigation",
        "execute_tiered_interventions",
        "record_intervention_results",
        # 补充：触发个性化触达以挽回
        "needs_deepening",
        "personalized_strategy_and_reach_execution_process",
        "define_communication_strategy",
        "multi_channel_reach"
    ]

    MARKET_INSIGHT_LITE_PATH = [
        "marketing",
        "overall_strategy",
        "market_insight",
        "target_customer_analysis",
        "competitor_analysis",
        "differentiation_opportunities"
    ]

    # 根据策略模式，决定根任务分裂哪些子任务
    if strategy_mode == "quick":
        selected_level1 = ["fission_mech_design"]
    elif strategy_mode == "user":
        selected_level1 = ["user_strat_fission"]
    elif strategy_mode == "full":
        selected_level1 = FULL_TASK_TREE["private_domain"]
    elif strategy_mode == "lite":
        selected_level1 = MARKET_INSIGHT_LITE_PATH
    elif strategy_mode == "brand_building":
        selected_level1 = BRAND_BUILDING_PATH
    elif strategy_mode == "market_insight":
        selected_level1 = MARKET_INSIGHT_AND_COMPETITOR_ANALYSIS_PATH
    elif strategy_mode == "lead_gen":
        selected_level1 = LEAD_GEN_FOCUS_PATH
    elif strategy_mode == "health_retention":
        selected_level1 = HEALTH_RETENTION_PATH
    else:
        raise ValueError(f"未知策略模式: {strategy_mode}")

    agent_to_task_id = {}

    try:
        # === 启动根任务 ===
        root_agent_id = "private_domain"
        start_data = {
            "request_id": REQUEST_ID,
            "trace_id": TRACE_ID,
            "input_params": {
                "campaign": "春节裂变2026",
                "strategy_mode": strategy_mode  # 记录决策依据
            },
            "user_id": TEST_USER_ID
        }
        resp = send_post_request("/traces/start", start_data)
        root_task_id = resp.json().get("root_task_id") or TRACE_ID
        agent_to_task_id[root_agent_id] = root_task_id
        test_report_execution_event(root_task_id, "STARTED", agent_id=root_agent_id)

        # === 第一轮分裂：按策略选择子任务 ===
        level1_subtasks = []
        for aid in selected_level1:
            task_id = f"{aid}-{str(uuid.uuid4())[:6]}"
            level1_subtasks.append({
                "id": task_id,
                "name": AGENT_CODE_TO_NAME.get(aid, f"任务-{aid}"),
                "params": {"agent_id": aid},
                "actor_type": "Agent"
            })
            agent_to_task_id[aid] = task_id

        split1_data = {
            "parent_id": root_task_id,
            "trace_id": TRACE_ID,
            "subtasks_meta": level1_subtasks,
            "reasoning_snapshot": {
                "reason": f"根据 strategy_mode='{strategy_mode}' 选择执行路径",
                "selected_agents": selected_level1
            }
        }
        send_post_request(f"/traces/{TRACE_ID}/split", split1_data)

        # === 递归执行任务（深度优先）===
        def execute_task(agent_id, task_id):
            task_name = AGENT_CODE_TO_NAME.get(agent_id, agent_id)
            print(f"\n--- 执行任务: {task_name} ({agent_id}) ---")
            test_report_execution_event(task_id, "STARTED", agent_id=agent_id)

            children = FULL_TASK_TREE.get(agent_id, [])
            if children:
                test_report_execution_event(task_id, "COMPLETED", agent_id=agent_id)
                # 分裂子任务
                child_subtasks = []
                for caid in children:
                    ctask_id = f"{caid}-{str(uuid.uuid4())[:6]}"
                    child_subtasks.append({
                        "id": ctask_id,
                        "name": AGENT_CODE_TO_NAME.get(caid, f"任务-{caid}"),
                        "params": {"agent_id": caid},
                        "actor_type": "Agent"
                    })
                    agent_to_task_id[caid] = ctask_id

                split_data = {
                    "parent_id": task_id,
                    "trace_id": TRACE_ID,
                    "subtasks_meta": child_subtasks,
                    "reasoning_snapshot": {"reason": f"展开 {task_name} 的子任务"}
                }
                send_post_request(f"/traces/{TRACE_ID}/split", split_data)

                # 递归执行子任务
                for caid in children:
                    execute_task(caid, agent_to_task_id[caid])
            else:
                test_report_execution_event(task_id, "COMPLETED", agent_id=agent_id)

        # 执行所有选中的 Level 1 任务（及其子树）
        for aid in selected_level1:
            execute_task(aid, agent_to_task_id[aid])

        # 根任务完成
        test_report_execution_event(root_task_id, "COMPLETED", agent_id=root_agent_id)
        test_get_trace_status()

        print(f"\n✅ 策略模式 '{strategy_mode}' 执行完成！")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
