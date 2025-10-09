testjson='''
[
  {
    "activeName": "苏州家长邀好友，英语试听免费领",
    activeDesc: 结合地域‘苏州’场景，针对家长群体‘关注本地教育、传播意愿高’的特点，以‘邀请好友注册并完成学习活动’为社交切入点，突出专属英语试听课产品，既撬动老用户拉新，又通过‘免费领取’激励确保新用户完成学习活动，贴合用户拉新核心目标。,
    activeType: 教育行业用户拉新裂变活动,
    fissionInfo: 核心裂变目标：用户拉新；活动规则：现有用户（激励对象）邀请新用户注册并完成一次学习活动（如观看一节视频），每邀请1人可获得一个专属英语试听课；领取限制：单用户最多额外邀请5人，额外获得5次试听课。,
    assistInfo: 活动推送载体：通过企业微信或APP基于地域标签推送‘苏州家长裂变’，强调本地名师资源，便于追踪转化,
    repeatAssistInfo: 分层用户匹配：有地域标签用户偏好免费试听课（如K12辅导资源），且传播意愿高（易分享本地教育机会），专属试听课玩法可直接满足其需求,
    endAssistInfo: 成本控制：总奖金上限关联incentive_cost_cap设置为60元；单次激励固定为试听课（价值约1元等效）；限制每人最多5次以控制总成本。；目标支撑：支持30天新增5000注册用户目标，确保70%有效用户率，且成本可控,
    activeRedPacketInfo: {
      totalBonus: 60.0,
      virtualBonus: 100.0,
      everyInvitation: 1,
      minBonus: 1.0,
      maxBonus: 1.0,
      maxTimes: 5,
      unlimitedBonus: false
    },
    customerIds: [1, 4, 5]
  },
  {
    activeName: 知识分享赢惊喜，红包资料随机送,
    activeDesc: 针对无地域标签用户‘偏好实用学习资源或小惊喜’的特点，以‘分享知识’为社交切入点，通过‘随机红包或学习资料包’激励邀请新用户注册并完成测验，突出教育行业通用产品，既实现拉新，又确保学习活动完成，贴合用户拉新核心目标。,
    activeType: 教育行业用户拉新裂变活动,
    fissionInfo: 核心裂变目标：用户拉新；活动规则：现有用户（激励对象）邀请新用户注册并完成一次学习活动（如完成一次测验），每邀请1人可获得随机金额红包（0.5元至2.0元）或通用学习资料包；领取限制：单用户最多额外邀请4人，额外领取4次奖励。,
    assistInfo: 活动推送载体：通过APP推送‘知识分享裂变’活动，突出通用资源，适应未知地域特征,
    repeatAssistInfo: 分层用户匹配：无地域标签用户偏好学习资料包或小礼品，且传播意愿中等（需更强随机激励），随机红包玩法能提供不确定性奖励以提升参与度,
    endAssistInfo: 成本控制：总奖金上限关联incentive_cost_cap设置为40元；单次激励金额范围控制在0.5-2.0元以内；限制每人最多4次以控制总成本。；目标支撑：支持新增5000注册用户目标，确保70%有效用户率，同时控制成本,
    activeRedPacketInfo: {
      totalBonus: 40.0,
      virtualBonus: 100.0,
      everyInvitation: 1,
      minBonus: 0.5,
      maxBonus: 2.0,
      maxTimes: 4,
      unlimitedBonus: false
    },
    customerIds: [2, 3, 6]
  }
]

'''

import json5
testjson=json5.loads(testjson)
print(testjson)