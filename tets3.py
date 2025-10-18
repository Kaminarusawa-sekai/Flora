import json
import csv

# 原始数据（你提供的 JSON 数组）
data = [
  {
    "code": "rules_system_create_active",
    "strength": 1,
    "name": "规则与系统构建-新增活动",
    "capability": "活动创建流程配置、活动基础规则定义、活动生命周期管理",
    "capability_desc": "负责营销活动中从创建到上线的全流程规则配置，包括活动基本信息、时间范围、状态控制及基础业务规则的设定。",
    "datascope": "activity_id, activity_name, activity_type, start_time, end_time, status, rule_config, creator_id",
    "datascope_desc": "管理活动的唯一标识、名称、类型、起止时间、当前状态、规则配置（如参与条件）以及创建人ID等核心字段。"
  },
  {
    "code": "rules_system_create_active_center",
    "strength": 1,
    "name": "规则与系统构建-新增活动中心",
    "capability": "多活动统一管理平台构建、活动模板库维护、活动审批流配置",
    "capability_desc": "构建集中化的活动管理中心，支持批量活动管理、标准化模板复用及跨部门审批流程的配置与执行。",
    "datascope": "center_id, template_id, template_name, approval_flow, operator_id, activity_list, create_time",
    "datascope_desc": "管理活动中心ID、所用模板ID与名称、审批流程定义、操作人ID、关联的活动列表及创建时间等元数据。"
  },
  {
    "code": "private_domain",
    "strength": 0.8,
    "name": "私域营销",
    "capability": "企业微信/社群/小程序等私域渠道用户运营、私域流量转化策略",
    "capability_desc": "通过企业微信、微信群、小程序等私域触点进行用户精细化运营，设计并执行用户留存与转化策略。",
    "datascope": "user_id, wechat_id, group_id, tag_list, last_contact_time, conversion_status, channel_source",
    "datascope_desc": "管理用户唯一ID、企微ID、所属社群ID、用户标签集合、最近互动时间、当前转化状态（如未触达/意向/成交）及来源渠道。"
  },
  {
    "code": "fission_activity",
    "strength": 0.8,
    "name": "裂变活动策划*",
    "capability": "裂变类营销活动整体方案设计、目标人群定位、传播路径规划",
    "capability_desc": "从0到1策划裂变营销活动，明确目标用户、传播机制、预期效果及资源投入，输出完整活动方案。",
    "datascope": "campaign_id, target_audience, referral_path, expected_uv, kpi_goal, budget, planner_id",
    "datascope_desc": "管理活动方案ID、目标人群描述、推荐/邀请路径设计、预期独立访客数、核心KPI目标、预算金额及策划人ID。"
  },
  {
    "code": "fission_implement",
    "strength": 0.8,
    "name": "裂变实施",
    "capability": "裂变活动上线执行、渠道投放、用户参与引导、异常监控",
    "capability_desc": "负责裂变活动的实际落地执行，包括上线部署、多渠道投放、用户引导及实时监控异常情况。",
    "datascope": "execution_log_id, channel_id, participant_count, share_count, error_log, operator_id, real_time_metrics",
    "datascope_desc": "记录执行日志ID、投放渠道ID、参与人数、分享次数、错误日志、操作人ID及实时指标（如转化率、跳出率）。"
  },
  {
    "code": "fission_mech_design",
    "strength": 0.8,
    "name": "裂变机制设计*",
    "capability": "邀请奖励规则、层级关系判定、裂变链路逻辑设计",
    "capability_desc": "设计裂变的核心激励与传播逻辑，包括谁邀请谁、奖励如何发放、层级如何计算等规则体系。",
    "datascope": "mechanism_id, reward_rule, invitee_level, inviter_id, reward_type, threshold, validity_period",
    "datascope_desc": "管理机制ID、奖励规则（如邀请1人得5元）、被邀请人层级、邀请人ID、奖励类型（现金/券/积分）、触发门槛及有效期。"
  },
  {
    "code": "user_strat_fission",
    "strength": 0.8,
    "name": "用户分层裂变设计",
    "capability": "基于用户价值/行为的分层裂变策略制定（如高净值用户专属裂变）",
    "capability_desc": "针对不同价值或行为特征的用户群体，设计差异化的裂变策略，提升高潜力用户的传播效率。",
    "datascope": "user_segment, segment_id, fission_strategy, expected_roi, conversion_rate_by_segment",
    "datascope_desc": "管理用户分群名称、分群ID、对应裂变策略描述、预期投资回报率及该群体的历史转化率。"
  },
  {
    "code": "activity_creative",
    "strength": 0.8,
    "name": "活动创意与立项",
    "capability": "营销活动创意构思、主题包装、立项文档撰写与评审",
    "capability_desc": "负责活动的创意发想、主题命名、视觉调性建议，并输出立项文档供跨部门评审。",
    "datascope": "creative_id, theme, slogan, visual_direction, proposal_doc_url, approver_id, 立项时间",
    "datascope_desc": "管理创意方案ID、活动主题、宣传口号、视觉风格指引、立项文档链接、审批人ID及立项时间（建议统一为英文字段如 proposal_time）。"
  },
  {
    "code": "def_planning",
    "strength": 0.8,
    "name": "定义与规划",
    "capability": "营销目标拆解、资源需求评估、项目时间线规划",
    "capability_desc": "将高层目标拆解为可执行的营销任务，评估所需人力、预算、技术资源，并制定详细项目计划。",
    "datascope": "project_id, objective, timeline, resource_plan, stakeholder_list, milestone_dates",
    "datascope_desc": "管理项目ID、核心目标描述、整体时间线、资源分配计划、相关干系人列表及关键里程碑日期。"
  },
  {
    "code": "fission_user_portrait",
    "strength": 0.8,
    "name": "裂变用户分层与画像定义",
    "capability": "构建裂变场景下的用户标签体系与分层画像模型",
    "capability_desc": "围绕裂变行为（如是否愿意分享、是否有社交影响力）构建专用用户画像和标签体系。",
    "datascope": "user_id, tags, behavior_score, referral_potential, ltv, activity_preference, portrait_version",
    "datascope_desc": "管理用户ID、裂变相关标签（如‘爱分享’‘高影响力’）、行为评分、推荐潜力值、用户生命周期价值、偏好活动类型及画像版本号。"
  },
  {
    "code": "mech_game_design",
    "strength": 0.8,
    "name": "机制与玩法设计",
    "capability": "互动玩法（如抽奖、拼团、助力）规则与激励机制设计",
    "capability_desc": "设计具体互动游戏的参与规则、胜负判定、奖励发放逻辑，确保玩法有趣且可执行。",
    "datascope": "game_id, game_type, participation_rule, win_probability, reward_pool, cooldown_time",
    "datascope_desc": "管理游戏ID、玩法类型（如砍价/抽奖）、参与条件、中奖概率、奖池配置及用户冷却时间（防刷）。"
  },
  {
    "code": "rules_system",
    "strength": 0.8,
    "name": "规则与系统构建",
    "capability": "营销活动通用规则引擎搭建、风控策略配置、系统对接规范",
    "capability_desc": "搭建可复用的营销规则引擎，支持活动规则灵活配置，并集成风控与外部系统对接能力。",
    "datascope": "rule_engine_id, rule_type, condition_expr, action, system_api_list, risk_control_flag",
    "datascope_desc": "管理规则引擎ID、规则类型（如资格校验/奖励触发）、条件表达式、执行动作、对接的外部API列表及是否启用风控标识。"
  },
  {
    "code": "strat_fission_strat",
    "strength": 0.8,
    "name": "分层裂变策略设计",
    "capability": "针对不同用户群体制定差异化裂变路径与激励策略",
    "capability_desc": "为不同用户层级（如新客、活跃用户、KOC）设计专属的裂变路径和激励组合，提升整体传播效率。",
    "datascope": "strategy_id, user_tier, incentive_plan, channel_mapping, expected_share_rate",
    "datascope_desc": "管理策略ID、用户层级（如T1/T2/T3）、激励方案详情、匹配的触达渠道及预期分享率。"
  },
  {
    "code": "comm_scripts",
    "strength": 0.8,
    "name": "定制沟通话术与素材",
    "capability": "私域/客服/推送场景下的个性化话术与视觉素材制作",
    "capability_desc": "根据用户分层和场景，制作精准的沟通话术（如欢迎语、催促话术）及配套图片/视频素材。",
    "datascope": "script_id, scene_type, user_segment, message_template, image_url, voice_url, a/b_test_group",
    "datascope_desc": "管理话术ID、使用场景（如入群/流失召回）、目标用户分群、消息模板、配图/语音链接及A/B测试分组。"
  },
  {
    "code": "copy_planning",
    "strength": 0.8,
    "name": "文案策划",
    "capability": "活动主文案、传播文案、落地页文案等内容策划",
    "capability_desc": "撰写各类营销文案，包括活动主标题、社交媒体传播语、落地页正文等，传递核心价值点。",
    "datascope": "copy_id, copy_type, headline, body_text, call_to_action, brand_tone, review_status",
    "datascope_desc": "管理文案ID、文案类型（如主KV/朋友圈文案）、标题、正文内容、行动号召语、品牌语调要求及审核状态。"
  },
  {
    "code": "fission_game_match",
    "strength": 0.8,
    "name": "匹配裂变玩法",
    "capability": "根据用户特征与业务目标匹配最优裂变游戏机制（如砍价 vs 邀请）",
    "capability_desc": "基于用户画像和活动目标，智能推荐最适合的裂变玩法，提升参与意愿和传播效果。",
    "datascope": "match_id, user_profile, recommended_game, confidence_score, historical_performance",
    "datascope_desc": "管理匹配记录ID、用户画像摘要、推荐的玩法名称、推荐置信度及该玩法历史表现数据。"
  },
  {
    "code": "gameplay_mode",
    "strength": 0.8,
    "name": "玩法模式选择",
    "capability": "从预设玩法库中选择适合当前活动的互动模式",
    "capability_desc": "从标准化玩法库（如助力、拼团、打卡）中挑选与活动目标最匹配的互动形式。",
    "datascope": "mode_id, mode_name, suitability_score, required_resources, tech_dependency",
    "datascope_desc": "管理玩法模式ID、名称、适配评分、所需资源（如奖品库存）、技术依赖（如是否需对接支付）。"
  },
  {
    "code": "goal_setting",
    "strength": 0.8,
    "name": "目标设定",
    "capability": "设定裂变活动的核心KPI（如新增用户数、分享率、转化率）",
    "capability_desc": "明确活动要达成的关键结果指标，并设定可衡量的目标值和考核周期。",
    "datascope": "goal_id, metric_name, target_value, baseline, time_window, owner_id",
    "datascope_desc": "管理目标ID、指标名称（如‘邀请人数’）、目标值、历史基线值、统计时间窗口及负责人ID。"
  },
  {
    "code": "incentive_system",
    "strength": 0.8,
    "name": "激励体系设计",
    "capability": "设计统一的奖励体系（现金、积分、权益等）及发放规则",
    "capability_desc": "构建标准化的激励框架，定义奖励类型、发放条件、额度控制及发放方式，确保公平与合规。",
    "datascope": "incentive_id, reward_type, amount, condition, validity, distribution_channel",
    "datascope_desc": "管理激励方案ID、奖励类型（如优惠券/现金红包）、金额或数量、触发条件、有效期及发放渠道（如微信卡包/账户余额）。"
  },
  {
    "code": "strat_incentives",
    "strength": 0.8,
    "name": "设计分层激励",
    "capability": "针对不同用户层级（如新客/老客/KOC）设计差异化激励方案",
    "capability_desc": "为不同价值用户设计阶梯式或定制化激励，例如KOC获得更高佣金，新客获得首单礼包。",
    "datascope": "tier_id, user_tier, incentive_config, max_reward, frequency_limit",
    "datascope_desc": "管理层级ID、用户层级名称（如‘KOC’）、激励配置详情、单用户最高奖励上限及单位时间参与次数限制。"
  },
  {
    "code": "strat_portraits",
    "strength": 0.8,
    "name": "绘制分层画像",
    "capability": "基于行为、属性、价值等维度构建用户分层画像",
    "capability_desc": "综合用户基础属性、行为数据和商业价值，划分用户群体并输出结构化画像，用于精准营销。",
    "datascope": "portrait_id, segment_name, user_count, avg_ltv, engagement_score, key_behaviors",
    "datascope_desc": "管理画像ID、分群名称（如‘高价值沉默用户’）、群体人数、平均生命周期价值、互动活跃度评分及关键行为特征（如‘常浏览未下单’）。"
  }
]

# 定义 CSV 的列顺序（字段名）
fieldnames = [
    "code",
    "strength",
    "name",
    "capability",
    "capability_desc",
    "datascope",
    "datascope_desc"
]

# 写入 CSV 文件
output_file = "output.csv"
with open(output_file, mode='w', encoding='utf-8-sig', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

print(f"数据已成功导出到 {output_file}")