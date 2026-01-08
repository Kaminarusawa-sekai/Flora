import json

def simplify_node(node):
    props = node.get("n", {}).get("properties", {})
    
    simplified = {
        "name": props.get("name"),
        "id": props.get("id"),
        "parent_id": props.get("parent_id")  # 如果原数据有 parent_id 就取，否则为 None
    }
    
    # 可选：如果希望 parent_id 不存在时显式设为 null（而不是跳过字段）
    # 如果你确定有些节点有 parent_id 而有些没有，这样写即可
    
    return simplified

def main():
    # 示例输入：你可以替换成从文件读取或 API 获取的数据
    input_data = [
  {
    "n": {
      "identity": 69,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_wecom.crm_active_center",
        "capability": "【用户场景】创建活动、管理活动、配置活动审批、使用活动模板、批量管理活动、活动参与率低的问题\n【核心能力】作为规则与系统构建的核心功能落地子模块，同时为裂变实施提供活动管理的关键工具支撑，聚焦搭建多活动统一管理平台、维护活动模板库、配置活动审批流三大核心任务，具体包括：承接规则与系统构建的底层框架要求，搭建集中化活动管理中心，重点支持批量活动管理（适配裂变实施中多场次活动的高效统筹需求）、标准化模板复用（降低裂变活动策划后的落地成本）及跨部门审批流程的配置与落地（确保裂变活动执行前的流程合规性），最终\n【关键词】活动中心、活动管理、活动模板、审批流程、批量管理、活动创建",
        "datascope": "管理活动中心ID、所用模板ID与名称、审批流程定义、操作人ID、关联的活动列表及创建时间等元数据。",
        "updated_at": "{\"year\":2025,\"month\":11,\"day\":30,\"hour\":9,\"minute\":33,\"second\":4,\"nanosecond\":27000000,\"timeZoneOffsetSeconds\":0}",
        "strength": 1.0,
        "dify": "app-aUm4ypKPSIWXnQJ3p0pkerJS",
        "businessId": 134.0,
        "name": " 规则与系统构建-新增活动中心",
        "id": "rules_system_create_active_center",
        "seq": "4"
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:69"
    }
  },
  {
    "n": {
      "identity": 70,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "",
        "capability": "【用户场景】私域运营、私域营销、企业微信营销、微信群运营、私域流量管理\n【核心能力】以企业微信、微信群、小程序等私域触点为核心载体，构建 “分层策略 - 机制设计 - 活动落地 - 全流程执行” 的私域裂变运营体系，作为用户分层裂变设计、裂变机制设计、裂变活动策划、裂变实施的核心场景与价值闭环。具体包括：整合私域触点开展用户精细化运营，依托用户分层裂变设计输出的差异化策略明确运营方向，通过裂变机制设计的规则体系保障裂变逻辑的可执行性，借助裂变活动策划的文案、玩法、素材将策略与机制\n【关键词】私域营销、私域运营、企微、微信群、小程序、私域流量",
        "datascope": "管理用户唯一ID、企微ID、所属社群ID、用户标签集合、最近互动时间、当前转化状态（如未触达/意向/成交）及来源渠道。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "",
        "name": " 私域营销",
        "businessId": 17,
        "id": "private_domain",
        "seq": 5
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:70"
    }
  },
  {
    "n": {
      "identity": 71,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "",
        "capability": "【用户场景】配置裂变规则、设计邀请奖励、设置裂变层级、解决裂变传播效果差、奖励发放问题\n【核心能力】作为私域营销体系中裂变运营的底层规则核心，向上承接私域营销的流量裂变目标，向下为两个 “机制与玩法设计” 模块提供统一的底层规则框架，具体包括：邀请奖励规则制定、层级关系判定、裂变链路逻辑设计，设计裂变的核心邀请奖励与链路传播逻辑，明确邀请主体与对象、奖励发放规则、层级计算方式等关键内容，形成完整规则体系，为后续玩法与激励的细化设计奠定基础。\n【关键词】裂变机制、裂变规则、邀请奖励、层级关系、裂变链路",
        "datascope": "管理机制ID、奖励规则（如邀请1人得5元）、被邀请人层级、邀请人ID、奖励类型（现金/券/积分）、触发门槛及有效期。",
        "updated_at": "{\"year\":2025,\"month\":11,\"day\":30,\"hour\":9,\"minute\":33,\"second\":4,\"nanosecond\":27000000,\"timeZoneOffsetSeconds\":0}",
        "strength": 0.8,
        "dify": "",
        "businessId": 37.0,
        "name": " 裂变机制设计",
        "id": "fission_mech_design",
        "seq": "1"
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:71"
    }
  },
  {
    "n": {
      "identity": 72,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "capability": "【用户场景】用户分层、设计裂变方案、做裂变活动、提高分享率、提高用户活跃度\n【核心能力】作为私域营销体系中精准裂变的核心策略源头，向上承接私域营销的流量运营与转化目标，向下为定制沟通话术与素材、匹配裂变玩法提供分层依据，具体包括：基于用户价值 / 行为特征制定分层裂变策略（如高净值用户专属裂变方案），针对不同价值、行为特征的用户群体，设计差异化裂变策略，重点提升高潜力用户的传播转化效率，为下游模块输出清晰的用户分层导向与策略方向。\n【关键词】用户分层、分层裂变、用户价值、差异化策略、裂变方案",
        "database": "",
        "datascope": "管理用户分群名称、分群ID、对应裂变策略描述、预期投资回报率及该群体的历史转化率。",
        "updated_at": "{\"year\":2025,\"month\":11,\"day\":30,\"hour\":9,\"minute\":33,\"second\":4,\"nanosecond\":27000000,\"timeZoneOffsetSeconds\":0}",
        "strength": 0.8,
        "dify": "",
        "businessId": 47.0,
        "name": " 用户分层裂变设计",
        "id": "user_strat_fission",
        "seq": "2"
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:72"
    }
  },
  {
    "n": {
      "identity": 74,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "capability": "【用户场景】设计裂变方案、设置用户等级、划分用户群体、实现病毒式传播、提高分享率\n【核心能力】针对新客、活跃用户、KOC 等不同层级用户群体，设计差异化裂变路径及配套激励方案，具体包括针对各层级用户规划适配的专属裂变路径与激励组合，进而提升整体裂变的传播效率与转化效果。\n【关键词】分层策略、裂变策略、用户等级、差异化路径、传播效率",
        "database": "",
        "datascope": "管理策略ID、用户层级（如T1/T2/T3）、激励方案详情、匹配的触达渠道及预期分享率。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "",
        "name": " 分层裂变策略设计",
        "businessId": 90,
        "id": "strat_fission_strat",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:74"
    }
  },
  {
    "n": {
      "identity": 75,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_agent.agent_global_key",
        "capability": "【用户场景】写营销话术、设计沟通话术、解决用户流失问题、定制客服话术\n【核心能力】作为用户分层裂变设计的场景化内容落地载体，承接其输出的用户分层特征与策略需求，具体包括：针对私域、客服、推送三大场景，定制个性化沟通话术与视觉素材，结合用户分层裂变设计的群体差异（如新客对福利敏感、高净值用户注重体验）与场景特点，产出精准适配的沟通话术（如欢迎语、催促语、售后安抚语）及配套视觉素材（含图片、短视频），确保内容与用户需求、场景氛围高度契合，强化分层裂变的沟通精准度。\n【关键词】话术设计、沟通话术、客服话术、营销话术、用户流失",
        "datascope": "管理话术ID、使用场景（如入群/流失召回）、目标用户分群、消息模板、配图/语音链接及A/B测试分组。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "app-IxAznVKxVZ8e0OrZgWrDDxfT",
        "name": " 定制沟通话术与素材",
        "businessId": 96,
        "id": "comm_scripts",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:75"
    }
  },
  {
    "n": {
      "identity": 76,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_agent.agent_global_key",
        "capability": "【用户场景】设计推广文案、写活动文案、降低获客成本、解决活动效果不好的问题\n【核心能力】聚焦活动主文案、传播文案、落地页文案等核心内容的策略性策划，具体包括撰写适配不同场景的营销文案 —— 活动主标题贴合主题调性，社交媒体传播语匹配平台氛围，落地页正文衔接用户转化路径，最终精准传递品牌或活动核心价值，助力营销目标落地。\n【关键词】文案策划、活动文案、传播文案、推广文案、获客成本",
        "datascope": "管理文案ID、文案类型（如主KV/朋友圈文案）、标题、正文内容、行动号召语、品牌语调要求及审核状态。",
        "updated_at": "{\"year\":2025,\"month\":11,\"day\":30,\"hour\":9,\"minute\":33,\"second\":4,\"nanosecond\":27000000,\"timeZoneOffsetSeconds\":0}",
        "strength": 0.8,
        "dify": "app-zH133VOxSTZqNTQwYGkvSfdb",
        "businessId": 99.0,
        "name": " 文案策划",
        "id": "copy_planning",
        "seq": "3"
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:76"
    }
  },
  {
    "n": {
      "identity": 77,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_agent.agent_global_key",
        "capability": "【用户场景】选择裂变玩法、做裂变活动、设计裂变方案、提高转化、增加用户数量\n【核心能力】作为用户分层裂变设计的玩法执行支撑模块，依托其输出的用户特征与策略方向，具体包括：结合用户分层裂变设计的用户群体属性（如行为偏好、价值层级）与业务目标，匹配最优裂变玩法机制（如砍价、邀请助力等），基于精准用户画像与明确活动目标，筛选并推荐最适配的裂变玩法类型，同步提升用户参与意愿、传播广度与最终转化效率，让分层裂变策略通过具象化玩法落地。\n【关键词】匹配玩法、裂变玩法、玩法推荐、转化效率",
        "datascope": "管理匹配记录ID、用户画像摘要、推荐的玩法名称、推荐置信度及该玩法历史表现数据。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "app-biWQJ47WcAcxiXouNOw68mwB",
        "name": " 匹配裂变玩法",
        "businessId": 105,
        "id": "fission_game_match",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:77"
    }
  },
  {
    "n": {
      "identity": 79,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_agent.agent_global_key",
        "capability": "【用户场景】设定KPI、配置活动目标、定义考核指标、关于目标的功能\n【核心能力】作为机制与玩法设计的目标导向模块，承接其玩法与规则设计需求，明确裂变活动的量化标准，具体包括：锚定裂变活动核心 KPI（如新增用户数、分享率、裂变转化率），先明确活动需达成的关键结果指标（匹配机制与玩法设计的互动目标），再为各指标设定可量化的目标值，同时确定清晰的考核周期，确保目标可落地、可追踪，为玩法与激励设计提供结果导向。\n【关键词】目标设定、KPI、活动目标、考核指标、量化目标",
        "datascope": "管理目标ID、指标名称（如‘邀请人数’）、目标值、历史基线值、统计时间窗口及负责人ID。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "app-onEo7S6WehdvW5OgwqfzB0zK",
        "name": " 目标设定",
        "businessId": 109,
        "id": "goal_setting",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:79"
    }
  },
  {
    "n": {
      "identity": 81,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_agent.agent_global_key",
        "capability": "【用户场景】用户分层激励、设置不同用户不同奖励、提高用户活跃度、设置用户等级\n【核心能力】针对新客、老客、KOC 等不同用户层级，设计差异化激励策略，具体包括为不同价值用户匹配阶梯式或定制化激励内容 —— 新客可获首单专属礼包，老客享裂变专属折扣券，KOC 得更高比例佣金，以此提升各层级用户的裂变参与度与价值贡献。\n【关键词】分层激励、差异化激励、用户层级、阶梯激励",
        "datascope": "管理层级ID、用户层级名称（如‘KOC’）、激励配置详情、单用户最高奖励上限及单位时间参与次数限制。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "app-RrquaFK7AUav58HDtMWcsNgG",
        "name": " 设计分层激励",
        "businessId": 126,
        "id": "strat_incentives",
        "seq": 4
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:81"
    }
  },
  {
    "n": {
      "identity": 82,
      "labels": [
        "Agent",
        "Agent_bak"
      ],
      "properties": {
        "database": "eqiai_wecom.crm_customer_info",
        "capability": "【用户场景】用户分层、分析用户特征、解决用户流失问题、增加用户数量\n【核心能力】基于行为、属性、价值等核心维度，构建多维度用户分层画像，具体包括综合用户基础属性（如年龄、地域）、关键行为数据（如浏览频次、消费记录）和商业价值（如客单价、复购率），划分差异化用户群体并输出结构化分层画像报告，为后续精准营销、分层运营提供数据支撑。\n【关键词】用户画像、用户分层、用户分析、用户特征、用户流失",
        "datascope": "管理画像ID、分群名称（如‘高价值沉默用户’）、群体人数、平均生命周期价值、互动活跃度评分及关键行为特征（如‘常浏览未下单’）。",
        "updated_at": "2025-11-30T09:33:04.027000000Z",
        "strength": 0.8,
        "dify": "app-y96fZH5kCbv6YEuQtMZangg0",
        "name": " 绘制分层画像",
        "businessId": 127,
        "id": "strat_portraits",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:82"
    }
  },
  {
    "n": {
      "identity": 189,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于客户运营*的整体框架设计与管理，覆盖客户分层与标签化、*自动化培育流程设计、MQL资格判定与流转、深化需求、客户健康度监测，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：客户分层与标签化（数据采集与整合、标签体系设计、自动化打标与分层）；自动化培育流程设计（多形式精准内容触达、培育策略与路径设计流程、效能监控与路径优化流程）；MQL资格判定与流转（MQL判定标准制定、自动化判定、自动化判定与触发流转流程、销售反馈与闭环优化流程）；深化需求（需求洞察与机会识别流程、个性化策略与触达执行流程、闭环管理与价值验证流程）；客户健康度监测（健康度指标体系设计流程、自动化监控与预警触发流程、分级干预与反馈优化流程）。",
        "strength": "",
        "parent_id": "marketing",
        "dify": "",
        "name": "客户运营*",
        "id": "customer_operations",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:189"
    }
  },
  {
    "n": {
      "identity": 190,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于营销的整体框架设计与管理，覆盖客户运营*、营销效能*、公域营销、私域营销、品牌建设、总体战略，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：客户运营（客户分层与标签化、自动化培育流程设计、MQL资格判定与流转、深化需求、客户健康度监测）；品牌建设（品牌定位、品牌故事、价值观输出）；总体战略（市场洞察、目标客户分析、核心卖点提炼、建议定价策略、竞品分析、差异化机会）。",
        "updated_at": "2026-01-04 11:05:33",
        "strength": "",
        "dify": "",
        "name": "营销",
        "id": "marketing",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:190"
    }
  },
  {
    "n": {
      "identity": 191,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于客户分层与标签化的整体框架设计与管理，覆盖数据采集与整合、标签体系设计、自动化打标与分层，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：数据采集与整合（管理数据源ID、数据源类型、采集字段清单、接入方式、数据质量评分及采集时间等元数据）；标签体系设计（定义标签维度、制定标签规则）；自动化打标与分层（管理打标作业ID、分群ID、标签列表、分层策略、运行时间及操作人等过程数据）。",
        "strength": "",
        "parent_id": "customer_operations",
        "dify": "",
        "name": "客户分层与标签化",
        "id": "customer_segmentation_and_tagging",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:191"
    }
  },
  {
    "n": {
      "identity": 192,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于数据采集与整合，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理数据源ID、数据源类型、采集字段清单、接入方式、数据质量评分及采集时间等元数据。",
        "strength": "",
        "parent_id": "customer_segmentation_and_tagging",
        "dify": "",
        "name": "数据采集与整合",
        "id": "data_collection_and_integration",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:192"
    }
  },
  {
    "n": {
      "identity": 193,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于标签体系设计的整体框架设计与管理，覆盖定义标签维度、制定标签规则，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：定义标签维度（管理标签维度ID、维度名称与定义、值类型、负责人及更新时间等元数据）；制定标签规则（管理标签规则ID、规则表达式与类型、目标维度、更新频率及负责人等元数据）。",
        "strength": "",
        "parent_id": "customer_segmentation_and_tagging",
        "dify": "",
        "name": "标签体系设计",
        "id": "tagging_system_design",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:193"
    }
  },
  {
    "n": {
      "identity": 194,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于定义标签维度，定义/维护标签并支撑分层运营。",
        "database": "",
        "datascope": "管理标签维度ID、维度名称与定义、值类型、负责人及更新时间等元数据。",
        "strength": "",
        "parent_id": "tagging_system_design",
        "dify": "",
        "name": "定义标签维度",
        "id": "define_tag_dimensions",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:194"
    }
  },
  {
    "n": {
      "identity": 195,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于制定标签规则，制定标准/策略/规则并形成文档。",
        "database": "",
        "datascope": "管理标签规则ID、规则表达式与类型、目标维度、更新频率及负责人等元数据。",
        "strength": "",
        "parent_id": "tagging_system_design",
        "dify": "",
        "name": "制定标签规则",
        "id": "define_tag_rules",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:195"
    }
  },
  {
    "n": {
      "identity": 196,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于自动化打标与分层，进行分层并制定差异化策略。",
        "database": "",
        "datascope": "管理打标作业ID、分群ID、标签列表、分层策略、运行时间及操作人等过程数据。",
        "strength": "",
        "parent_id": "customer_segmentation_and_tagging",
        "dify": "",
        "name": "自动化打标与分层",
        "id": "automated_tagging_and_segmentation",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:196"
    }
  },
  {
    "n": {
      "identity": 197,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于*自动化培育流程设计的整体框架设计与管理，覆盖多形式精准内容触达、培育策略与路径设计流程、效能监控与路径优化流程，支撑上层营销目标达成。",
        "datascope": "范围：多形式精准内容触达（定义触发事件、匹配内容与渠道、制定时机规则）；培育策略与路径设计流程（定义培育目标、绘制培育路径蓝图）；效能监控与路径优化流程（管理效能指标ID与名称、当前值与基线、预警规则及优化动作建议等监控数据）。",
        "strength": "",
        "parent_id": "customer_operations",
        "dify": "",
        "name": "*自动化培育流程设计",
        "id": "automated_nurturing_process_design",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:197"
    }
  },
  {
    "n": {
      "identity": 198,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于多形式精准内容触达的整体框架设计与管理，覆盖定义触发事件、匹配内容与渠道、制定时机规则，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：定义触发事件（管理触发事件ID、事件名称与条件、事件来源、触发阈值及负责人等元数据）；匹配内容与渠道（管理内容ID、渠道ID、目标人群、匹配规则、投放优先级及负责人等元数据）；制定时机规则（管理时机规则ID、触达时间窗口、频次限制、延迟策略、时区及负责人等元数据）。",
        "strength": "",
        "parent_id": "automated_nurturing_process_design",
        "dify": "",
        "name": "多形式精准内容触达",
        "id": "multi_format_precise_content_delivery",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:198"
    }
  },
  {
    "n": {
      "identity": 199,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于定义触发事件，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理触发事件ID、事件名称与条件、事件来源、触发阈值及负责人等元数据。",
        "strength": "",
        "parent_id": "multi_format_precise_content_delivery",
        "dify": "",
        "name": "定义触发事件",
        "id": "define_trigger_events",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:199"
    }
  },
  {
    "n": {
      "identity": 200,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于匹配内容与渠道，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理内容ID、渠道ID、目标人群、匹配规则、投放优先级及负责人等元数据。",
        "strength": "",
        "parent_id": "multi_format_precise_content_delivery",
        "dify": "",
        "name": "匹配内容与渠道",
        "id": "match_content_and_channels",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:200"
    }
  },
  {
    "n": {
      "identity": 201,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于制定时机规则，制定标准/策略/规则并形成文档。",
        "database": "",
        "datascope": "管理时机规则ID、触达时间窗口、频次限制、延迟策略、时区及负责人等元数据。",
        "strength": "",
        "parent_id": "multi_format_precise_content_delivery",
        "dify": "",
        "name": "制定时机规则",
        "id": "define_timing_rules",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:201"
    }
  },
  {
    "n": {
      "identity": 202,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于培育策略与路径设计流程的整体框架设计与管理，覆盖定义培育目标、绘制培育路径蓝图，支撑上层营销目标达成。",
        "datascope": "范围：定义培育目标（管理培育目标ID、目标描述、指标口径、目标值、时间窗口及负责人等元数据）；绘制培育路径蓝图（管理培育路径ID与名称、阶段清单、阶段转移规则、触达序列及负责人等元数据）。",
        "strength": "",
        "parent_id": "automated_nurturing_process_design",
        "dify": "",
        "name": "培育策略与路径设计流程",
        "id": "nurturing_strategy_and_path_design_process",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:202"
    }
  },
  {
    "n": {
      "identity": 203,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于定义培育目标，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理培育目标ID、目标描述、指标口径、目标值、时间窗口及负责人等元数据。",
        "strength": "",
        "parent_id": "nurturing_strategy_and_path_design_process",
        "dify": "",
        "name": "定义培育目标",
        "id": "define_nurturing_goals",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:203"
    }
  },
  {
    "n": {
      "identity": 204,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于绘制培育路径蓝图，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理培育路径ID与名称、阶段清单、阶段转移规则、触达序列及负责人等元数据。",
        "strength": "",
        "parent_id": "nurturing_strategy_and_path_design_process",
        "dify": "",
        "name": "绘制培育路径蓝图",
        "id": "draw_nurturing_path_blueprint",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:204"
    }
  },
  {
    "n": {
      "identity": 205,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于效能监控与路径优化流程，持续监控关键指标与状态，触发预警和干预。",
        "datascope": "管理效能指标ID与名称、当前值与基线、预警规则及优化动作建议等监控数据。",
        "strength": "",
        "parent_id": "automated_nurturing_process_design",
        "dify": "",
        "name": "效能监控与路径优化流程",
        "id": "performance_monitoring_and_path_optimization_process",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:205"
    }
  },
  {
    "n": {
      "identity": 206,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "MQL资格判定与流转主流程。用于MQL资格判定与流转的整体框架设计与管理，覆盖MQL判定标准制定、自动化判定与触发流转流程、销售反馈与闭环优化流程，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：MQL判定标准制定（管理产品ID、工作流任务ID、目标行业、企业规模/决策层级/地域标准、各类行为与互动权重、意向信号分层及MQL阈值等数据）；自动化判定（管理线索ID、工作流任务ID、属性/行为评分及明细、总分与衰减/阈值对比、MQL判定结果、优先级与培育标记、触发因素与推荐动作等数据）；自动化判定与触发流转流程（管理线索ID、工作流任务ID、触发条件与类型、路由规则及状态、SLA时效、任务/通知/培育触发状态、SDR分配信息与CRM更新结果等数据）；销售反馈与闭环优化流程（管理产品ID、工作流任务ID、合格/不合格线索数量与转化率、反馈周期、拒绝原因、响应与来源质量分析、季节性趋势、评分/阈值/路由优化建议及培育策略建议等数据）。",
        "updated_at": "2026-01-04 11:05:09",
        "strength": "",
        "parent_id": "customer_operations",
        "dify": "app-gmzo5KrxMVf7UGV0To60i7wt",
        "name": "MQL资格判定与流转",
        "id": "mql_qualification_assessment_and_handoff",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:206"
    }
  },
  {
    "n": {
      "identity": 207,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于MQL判定标准制定，按标准进行判定并完成流转。",
        "database": "",
        "datascope": "管理产品ID、工作流任务ID、目标行业、企业规模/决策层级/地域标准、各类行为与互动权重、意向信号分层及MQL阈值等数据。",
        "updated_at": "2026-01-04 11:05:06",
        "strength": "",
        "parent_id": "mql_qualification_assessment_and_handoff",
        "dify": "app-PwKh9zHvtcYoIQr0wI5wHup4",
        "name": "MQL判定标准制定",
        "id": "mql_qualification_criteria_definition",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:207"
    }
  },
  {
    "n": {
      "identity": 208,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于自动化判定，按标准进行判定并完成流转。",
        "datascope": "管理线索ID、工作流任务ID、属性/行为评分及明细、总分与衰减/阈值对比、MQL判定结果、优先级与培育标记、触发因素与推荐动作等数据。",
        "updated_at": "2026-01-04 11:05:04",
        "strength": "",
        "parent_id": "mql_qualification_assessment_and_handoff",
        "dify": "app-4CmZ6wFlfYDzy8DGtK6G9FNg",
        "name": "自动化判定",
        "id": "automated_assessment",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:208"
    }
  },
  {
    "n": {
      "identity": 209,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于自动化判定与触发流转流程，按标准进行判定并完成流转。",
        "datascope": "管理线索ID、工作流任务ID、触发条件与类型、路由规则及状态、SLA时效、任务/通知/培育触发状态、SDR分配信息与CRM更新结果等数据。",
        "updated_at": "2026-01-04 11:05:02",
        "strength": "",
        "parent_id": "mql_qualification_assessment_and_handoff",
        "dify": "app-2XPncw6RvgE3fQd1nLtzhYO7",
        "name": "自动化判定与触发流转流程",
        "id": "automated_assessment_and_triggered_handoff_process",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:209"
    }
  },
  {
    "n": {
      "identity": 210,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于销售反馈与闭环优化流程，基于反馈持续优化流程与策略。",
        "datascope": "管理产品ID、工作流任务ID、合格/不合格线索数量与转化率、反馈周期、拒绝原因、响应与来源质量分析、季节性趋势、评分/阈值/路由优化建议及培育策略建议等数据。",
        "updated_at": "2026-01-04 11:05:01",
        "strength": "",
        "parent_id": "mql_qualification_assessment_and_handoff",
        "dify": "app-2XPncw6RvgE3fQd1nLtzhYO7",
        "name": "销售反馈与闭环优化流程",
        "id": "sales_feedback_and_closed_loop_optimization_process",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:210"
    }
  },
  {
    "n": {
      "identity": 211,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于深化需求的整体框架设计与管理，覆盖需求洞察与机会识别流程、个性化策略与触达执行流程、闭环管理与价值验证流程，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：需求洞察与机会识别流程（定义机会规则、系统扫描）；个性化策略与触达执行流程（机会分配、制定沟通策略、多渠道触达）；闭环管理与价值验证流程（设计验证指标、价值验证）。",
        "strength": "",
        "parent_id": "customer_operations",
        "dify": "",
        "name": "深化需求",
        "id": "needs_deepening",
        "business_id": "",
        "seq": 4
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:211"
    }
  },
  {
    "n": {
      "identity": 212,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于需求洞察与机会识别流程的整体框架设计与管理，覆盖定义机会规则、系统扫描，支撑上层营销目标达成。",
        "datascope": "范围：定义机会规则（管理机会规则ID、判定条件、机会阶段、评分权重、负责人及更新时间等元数据）；系统扫描（管理系统扫描任务ID、扫描范围与频率、发现的机会清单、扫描状态及操作人等过程数据）。",
        "strength": "",
        "parent_id": "needs_deepening",
        "dify": "",
        "name": "需求洞察与机会识别流程",
        "id": "needs_insight_and_opportunity_identification_process",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:212"
    }
  },
  {
    "n": {
      "identity": 213,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于定义机会规则，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理机会规则ID、判定条件、机会阶段、评分权重、负责人及更新时间等元数据。",
        "strength": "",
        "parent_id": "needs_insight_and_opportunity_identification_process",
        "dify": "",
        "name": "定义机会规则",
        "id": "define_opportunity_rules",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:213"
    }
  },
  {
    "n": {
      "identity": 214,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于系统扫描，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理系统扫描任务ID、扫描范围与频率、发现的机会清单、扫描状态及操作人等过程数据。",
        "strength": "",
        "parent_id": "needs_insight_and_opportunity_identification_process",
        "dify": "",
        "name": "系统扫描",
        "id": "system_scanning",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:214"
    }
  },
  {
    "n": {
      "identity": 215,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于个性化策略与触达执行流程的整体框架设计与管理，覆盖机会分配、制定沟通策略、多渠道触达，支撑上层营销目标达成。",
        "datascope": "范围：机会分配（管理机会ID、分配对象、分配规则与时间、优先级及处理状态等过程数据）；制定沟通策略（管理沟通策略ID、目标人群、内容主题、渠道组合、触达节奏及负责人等元数据）；多渠道触达（管理触达任务ID、渠道列表、消息ID、目标人群、触达状态及发送时间等过程数据）。",
        "strength": "",
        "parent_id": "needs_deepening",
        "dify": "",
        "name": "个性化策略与触达执行流程",
        "id": "personalized_strategy_and_reach_execution_process",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:215"
    }
  },
  {
    "n": {
      "identity": 216,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于机会分配，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理机会ID、分配对象、分配规则与时间、优先级及处理状态等过程数据。",
        "strength": "",
        "parent_id": "personalized_strategy_and_reach_execution_process",
        "dify": "",
        "name": "机会分配",
        "id": "opportunity_allocation",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:216"
    }
  },
  {
    "n": {
      "identity": 217,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于制定沟通策略，制定标准/策略/规则并形成文档。",
        "database": "",
        "datascope": "管理沟通策略ID、目标人群、内容主题、渠道组合、触达节奏及负责人等元数据。",
        "strength": "",
        "parent_id": "personalized_strategy_and_reach_execution_process",
        "dify": "",
        "name": "制定沟通策略",
        "id": "define_communication_strategy",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:217"
    }
  },
  {
    "n": {
      "identity": 218,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于多渠道触达，规划触达内容与渠道并执行。",
        "database": "",
        "datascope": "管理触达任务ID、渠道列表、消息ID、目标人群、触达状态及发送时间等过程数据。",
        "strength": "",
        "parent_id": "personalized_strategy_and_reach_execution_process",
        "dify": "",
        "name": "多渠道触达",
        "id": "multi_channel_reach",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:218"
    }
  },
  {
    "n": {
      "identity": 219,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于闭环管理与价值验证流程的整体框架设计与管理，覆盖设计验证指标、价值验证，支撑上层营销目标达成。",
        "datascope": "范围：设计验证指标（管理验证指标ID与名称、计算公式、目标值、数据来源及负责人等元数据）；价值验证（管理价值验证ID、验证方法、指标清单、结果摘要、结论判定及负责人等数据）。",
        "strength": "",
        "parent_id": "needs_deepening",
        "dify": "",
        "name": "闭环管理与价值验证流程",
        "id": "closed_loop_management_and_value_validation_process",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:219"
    }
  },
  {
    "n": {
      "identity": 220,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于设计验证指标，设计流程/机制/规则，形成可落地的方案。",
        "database": "",
        "datascope": "管理验证指标ID与名称、计算公式、目标值、数据来源及负责人等元数据。",
        "strength": "",
        "parent_id": "closed_loop_management_and_value_validation_process",
        "dify": "",
        "name": "设计验证指标",
        "id": "design_validation_metrics",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:220"
    }
  },
  {
    "n": {
      "identity": 221,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于价值验证，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理价值验证ID、验证方法、指标清单、结果摘要、结论判定及负责人等数据。",
        "strength": "",
        "parent_id": "closed_loop_management_and_value_validation_process",
        "dify": "",
        "name": "价值验证",
        "id": "value_validation",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:221"
    }
  },
  {
    "n": {
      "identity": 222,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "客户健康度监测。用于客户健康度监测的整体框架设计与管理，覆盖健康度指标体系设计流程、自动化监控与预警触发流程、分级干预与反馈优化流程，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：健康度指标体系设计流程（确定健康度维度、定义指标与权重、设定阈值与等级）；自动化监控与预警触发流程（管理客户ID、工作流任务ID、使用/互动/商业数据与评分、健康度总分及变化、预警触发结果（类型/级别/原因/详情）、监控指标与阈值、通知对象与渠道、推荐响应与SLA等数据）；分级干预与反馈优化流程（根因调查、执行分级干预措施、记录干预结果）。",
        "updated_at": "2026-01-04 11:05:31",
        "strength": "",
        "parent_id": "customer_operations",
        "dify": "app-zpatNb2VFx4Zhp0zCn4qzAr4",
        "name": "客户健康度监测",
        "id": "customer_health_monitoring",
        "business_id": "",
        "seq": 5
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:222"
    }
  },
  {
    "n": {
      "identity": 223,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "健康度指标体系设计流程。用于健康度指标体系设计流程的整体框架设计与管理，覆盖确定健康度维度、定义指标与权重、设定阈值与等级，支撑上层营销目标达成。",
        "datascope": "范围：确定健康度维度（管理健康度维度ID、维度名称与定义、权重、负责人及更新时间等元数据）；定义指标与权重（管理指标ID与名称、指标定义、权重、计算公式及负责人等元数据）；设定阈值与等级（管理阈值ID、指标ID、等级名称、阈值标准、比较规则及负责人等元数据）。",
        "updated_at": "2026-01-04 11:05:29",
        "strength": "",
        "parent_id": "customer_health_monitoring",
        "dify": "app-Yxr0FQw30RY909J50WZaTdtU",
        "name": "健康度指标体系设计流程",
        "id": "health_metrics_system_design_process",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:223"
    }
  },
  {
    "n": {
      "identity": 224,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于确定健康度维度，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理健康度维度ID、维度名称与定义、权重、负责人及更新时间等元数据。",
        "strength": "",
        "parent_id": "health_metrics_system_design_process",
        "dify": "",
        "name": "确定健康度维度",
        "id": "determine_health_dimensions",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:224"
    }
  },
  {
    "n": {
      "identity": 225,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于定义指标与权重，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理指标ID与名称、指标定义、权重、计算公式及负责人等元数据。",
        "strength": "",
        "parent_id": "health_metrics_system_design_process",
        "dify": "",
        "name": "定义指标与权重",
        "id": "define_metrics_and_weights",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:225"
    }
  },
  {
    "n": {
      "identity": 226,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于设定阈值与等级，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理阈值ID、指标ID、等级名称、阈值标准、比较规则及负责人等元数据。",
        "strength": "",
        "parent_id": "health_metrics_system_design_process",
        "dify": "",
        "name": "设定阈值与等级",
        "id": "set_thresholds_and_levels",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:226"
    }
  },
  {
    "n": {
      "identity": 227,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于自动化监控与预警触发流程，持续监控关键指标与状态，触发预警和干预。",
        "datascope": "管理客户ID、工作流任务ID、使用/互动/商业数据与评分、健康度总分及变化、预警触发结果（类型/级别/原因/详情）、监控指标与阈值、通知对象与渠道、推荐响应与SLA等数据。",
        "updated_at": "2026-01-04 11:05:27",
        "strength": "",
        "parent_id": "customer_health_monitoring",
        "dify": "app-B6gDWdEo7DXM2DSfwe0a8a0y",
        "name": "自动化监控与预警触发流程",
        "id": "automated_monitoring_and_alert_trigger_process",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:227"
    }
  },
  {
    "n": {
      "identity": 228,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "分级干预与反馈优化流程。用于分级干预与反馈优化流程的整体框架设计与管理，覆盖根因调查、执行分级干预措施、记录干预结果，支撑上层营销目标达成。",
        "datascope": "范围：根因调查（管理调查ID、问题ID、根因结论、证据清单、调查人及调查时间等过程数据）；执行分级干预措施（管理干预ID、干预等级、干预方案、目标客户、执行人及执行时间等过程数据）；记录干预结果（管理结果ID、关联干预ID、结果结论、影响指标、后续动作及记录时间等数据）。",
        "updated_at": "2026-01-04 11:05:25",
        "strength": "",
        "parent_id": "customer_health_monitoring",
        "dify": "app-69McfaDL1pxX5X9sjEpP2hED",
        "name": "分级干预与反馈优化流程",
        "id": "tiered_intervention_and_feedback_optimization_process",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:228"
    }
  },
  {
    "n": {
      "identity": 229,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于根因调查，完成相关工作的执行与交付。",
        "database": "",
        "datascope": "管理调查ID、问题ID、根因结论、证据清单、调查人及调查时间等过程数据。",
        "strength": "",
        "parent_id": "tiered_intervention_and_feedback_optimization_process",
        "dify": "",
        "name": "根因调查",
        "id": "root_cause_investigation",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:229"
    }
  },
  {
    "n": {
      "identity": 230,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于执行分级干预措施，按流程执行并记录结果。",
        "database": "",
        "datascope": "管理干预ID、干预等级、干预方案、目标客户、执行人及执行时间等过程数据。",
        "strength": "",
        "parent_id": "tiered_intervention_and_feedback_optimization_process",
        "dify": "",
        "name": "执行分级干预措施",
        "id": "execute_tiered_interventions",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:230"
    }
  },
  {
    "n": {
      "identity": 231,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于记录干预结果，记录关键过程与结果数据。",
        "database": "",
        "datascope": "管理结果ID、关联干预ID、结果结论、影响指标、后续动作及记录时间等数据。",
        "strength": "",
        "parent_id": "tiered_intervention_and_feedback_optimization_process",
        "dify": "",
        "name": "记录干预结果",
        "id": "record_intervention_results",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:231"
    }
  },
  {
    "n": {
      "identity": 232,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "品牌建设主流程。用于品牌建设的整体框架设计与管理，覆盖品牌定位、品牌故事、价值观输出，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：品牌定位（管理品牌ID、工作流任务ID、市场分析（规模/增长/空白）、目标客户画像与动机痛点、品牌定位策略/定位语、差异化优势、USP、品牌个性与口号建议等数据）；品牌故事（管理品牌ID、工作流任务ID、品牌故事完整版/简版/一句话版本、故事要素（起源/主角/冲突/旅程/使命/情感/价值等）等数据）；价值观输出（管理品牌ID、工作流任务ID、核心价值观及内涵、行为准则、品牌承诺、使命/愿景陈述、内外部表达与输出结果等数据）。",
        "updated_at": "2026-01-04 11:04:58",
        "strength": "",
        "parent_id": "marketing",
        "dify": "app-fJ7R60Ud6COVVoawUcXzvyIl",
        "name": "品牌建设",
        "id": "brand_building",
        "business_id": "",
        "seq": 5
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:232"
    }
  },
  {
    "n": {
      "identity": 233,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于品牌定位，完成相关工作的执行与交付。",
        "datascope": "管理品牌ID、工作流任务ID、市场分析（规模/增长/空白）、目标客户画像与动机痛点、品牌定位策略/定位语、差异化优势、USP、品牌个性与口号建议等数据。",
        "updated_at": "2026-01-04 11:04:56",
        "strength": "",
        "parent_id": "brand_building",
        "dify": "app-ZqdSkYjtTzElWVgFiGog7XMf",
        "name": "品牌定位",
        "id": "brand_positioning",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:233"
    }
  },
  {
    "n": {
      "identity": 234,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于品牌故事，完成相关工作的执行与交付。",
        "datascope": "管理品牌ID、工作流任务ID、品牌故事完整版/简版/一句话版本、故事要素（起源/主角/冲突/旅程/使命/情感/价值等）等数据。",
        "updated_at": "2026-01-04 11:04:54",
        "strength": "",
        "parent_id": "brand_building",
        "dify": "app-TU8lRpwsvVphWslPtRKw3Ki3",
        "name": "品牌故事",
        "id": "brand_story",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:234"
    }
  },
  {
    "n": {
      "identity": 235,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于价值观输出，输出内容或价值表达成果。",
        "datascope": "管理品牌ID、工作流任务ID、核心价值观及内涵、行为准则、品牌承诺、使命/愿景陈述、内外部表达与输出结果等数据。",
        "updated_at": "2026-01-04 11:04:50",
        "strength": "",
        "parent_id": "brand_building",
        "dify": "app-Q93Qfi8AVn1eKy7AHclxAVzv",
        "name": "价值观输出",
        "id": "values_output",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:235"
    }
  },
  {
    "n": {
      "identity": 236,
      "labels": [
        "Agent"
      ],
      "properties": {
        "capability": "用于总体战略的整体框架设计与管理，覆盖市场洞察、目标客户分析、核心卖点提炼、建议定价策略、竞品分析*、差异化机会，支撑上层营销目标达成。",
        "database": "",
        "datascope": "范围：市场洞察（管理市场规模与增长趋势、行业分析、五力分析（买方/竞争/供应商/进入/替代威胁）及SWOT洞察等数据）；目标客户分析（管理产品ID、工作流任务ID、目标市场与客户分群、客户画像特征与需求、获客渠道、竞争优势与定位描述、市场需求匹配分析等数据）；核心卖点提炼（管理产品ID、工作流任务ID、用户痛点、核心功能与卖点、客户价值收益、价值描述与量化指标等数据）；建议定价策略（管理产品ID、工作流任务ID、定价模型与影响因素、竞品价格与支付能力分析、价值定价与支付意愿、建议价格区间（最高/最低/最优）等数据）；竞品分析（管理产品ID、工作流任务ID、竞品清单及其特性/价格/市场位置/优劣势、功能与价格对比、市场表现、SWOT与机会威胁、竞争策略建议等数据）；差异化机会（管理产品ID、工作流任务ID、差异化机会清单（机会/可行性/影响）、核心优势与客户价值、独特价值主张、目标人群与问题解决、定位表述等数据）。",
        "updated_at": "2026-01-04 11:05:33",
        "strength": "",
        "parent_id": "marketing",
        "dify": "",
        "name": "总体战略",
        "id": "overall_strategy",
        "business_id": "",
        "seq": 6
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:236"
    }
  },
  {
    "n": {
      "identity": 237,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "总体战略-市场洞察。用于市场洞察，从数据与市场信息中提炼洞察，输出结论与建议。",
        "datascope": "管理市场规模与增长趋势、行业分析、五力分析（买方/竞争/供应商/进入/替代威胁）及SWOT洞察等数据。",
        "updated_at": "2026-01-04 11:05:45",
        "strength": "",
        "parent_id": "overall_strategy",
        "dify": "app-TWQDBxfnuoZy2EOClzeb8ivX",
        "name": "市场洞察",
        "id": "market_insight",
        "business_id": "",
        "seq": 1
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:237"
    }
  },
  {
    "n": {
      "identity": 238,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于目标客户分析，对相关对象进行分析，输出结论与建议。",
        "datascope": "管理产品ID、工作流任务ID、目标市场与客户分群、客户画像特征与需求、获客渠道、竞争优势与定位描述、市场需求匹配分析等数据。",
        "updated_at": "2026-01-04 11:05:43",
        "strength": "",
        "parent_id": "overall_strategy",
        "dify": "app-mMozp7KV40rYJI73Pn4jcgWc",
        "name": "目标客户分析",
        "id": "target_customer_analysis",
        "business_id": "",
        "seq": 2
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:238"
    }
  },
  {
    "n": {
      "identity": 239,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "核心卖点提炼。用于核心卖点提炼，完成相关工作的执行与交付。",
        "datascope": "管理产品ID、工作流任务ID、用户痛点、核心功能与卖点、客户价值收益、价值描述与量化指标等数据。",
        "updated_at": "2026-01-04 11:05:42",
        "strength": "",
        "parent_id": "overall_strategy",
        "dify": "app-8bAHWtGgZHYnLkdsQtsxrbUE",
        "name": "核心卖点提炼",
        "id": "core_selling_point_refinement",
        "business_id": "",
        "seq": 3
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:239"
    }
  },
  {
    "n": {
      "identity": 240,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于建议定价策略，制定策略并输出行动方案。",
        "datascope": "管理产品ID、工作流任务ID、定价模型与影响因素、竞品价格与支付能力分析、价值定价与支付意愿、建议价格区间（最高/最低/最优）等数据。",
        "updated_at": "2026-01-04 11:05:40",
        "strength": "",
        "parent_id": "overall_strategy",
        "dify": "app-dGoDNVyQwDKvFVdodRxYfdIa",
        "name": "建议定价策略",
        "id": "pricing_strategy_recommendation",
        "business_id": "",
        "seq": 4
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:240"
    }
  },
  {
    "n": {
      "identity": 241,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "竞品分析。用于竞品分析*，对相关对象进行分析，输出结论与建议。",
        "datascope": "管理产品ID、工作流任务ID、竞品清单及其特性/价格/市场位置/优劣势、功能与价格对比、市场表现、SWOT与机会威胁、竞争策略建议等数据。",
        "updated_at": "2026-01-04 11:05:35",
        "strength": "",
        "parent_id": "overall_strategy",
        "dify": "app-dexTVPqGzpJmmbL7lAd4lmkm",
        "name": "竞品分析*",
        "id": "competitor_analysis",
        "business_id": "",
        "seq": 5
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:241"
    }
  },
  {
    "n": {
      "identity": 242,
      "labels": [
        "Agent"
      ],
      "properties": {
        "database": "",
        "capability": "用于差异化机会，完成相关工作的执行与交付。",
        "datascope": "管理产品ID、工作流任务ID、差异化机会清单（机会/可行性/影响）、核心优势与客户价值、独特价值主张、目标人群与问题解决、定位表述等数据。",
        "updated_at": "2026-01-04 11:05:33",
        "strength": "",
        "parent_id": "overall_strategy",
        "dify": "app-9SWqEnBMVYbArI9Qnz9h3a75",
        "name": "差异化机会",
        "id": "differentiation_opportunities",
        "business_id": "",
        "seq": 6
      },
      "elementId": "4:574fcd92-4cde-4c56-bb43-6fbc72fa28fd:242"
    }
  }
]


    # 处理所有节点
    output = [simplify_node(item) for item in input_data]

    # 打印结果（或写入文件）
    print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()