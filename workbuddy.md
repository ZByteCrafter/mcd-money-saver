# workbuddy.md — 使用 WorkBuddy 开发的对话上下文

> 本文件记录「麦门省钱军师」在 WorkBuddy 中的开发过程，用于大赛 WorkBuddy 专项奖励核验。
> 开发时间：2026-10-24 23:45 – 2026-10-25（北京时间），全程在 WorkBuddy Agent 模式中完成。

## 一、项目背景

- 赛事：麦当劳程序员创意开发大赛（麦当劳 × WorkBuddy 联合发起，活动周期 2026-10-09 10:30 – 10-25 23:59）。
- 要求：基于麦当劳 MCP 能力，开发有创意或实用价值的 Skill；参赛项目须包含 README.md、CONTEST_DECLARATION.md、MCP_INTEGRATION.md、mcp-config.example.json、源代码，参加 WorkBuddy 专项奖励须提交本文件。
- 开发者前置条件：已申请麦当劳中国 MCP Token 并在 WorkBuddy 中完成连接器配置。

## 二、开发过程（WorkBuddy 协作时间线）

| 阶段 | 时间 | 在 WorkBuddy 中完成的工作 |
|---|---|---|
| 1. 规则研读 | 23:45 | 克隆官方仓库 `M-China/mcd-developer-innovation-challenge` 到本地，通读 README、activityGuidelines 与 CONTEST_DECLARATION，整理出参赛文件清单、报名条件与排名规则 |
| 2. 能力调研 | 23:46–23:48 | 通过官方文档与本地 MCP 配置确认接入方式；对 `https://mcp.mcd.cn` 发起 `initialize`、`tools/list` 实测，确认服务在线（mcd-mcp v1.0.0，协议 2025-03-26），拿到 35 个工具的完整结构快照 |
| 3. 方案设计 | 23:49–23:50 | 基于实测工具清单确定 Skill 形态：WorkBuddy Skill（SKILL.md + references + scripts），核心差异点为「以 calculate-price 为唯一价格裁判的凑单比价」与「变更类工具强制人工确认」 |
| 4. 编码实现 | 23:50–23:54 | 编写 SKILL.md、references/mcp-tools.md、三个零依赖 Python 脚本（mcd_mcp_client / sweep_coupons / combo_optimizer）及全部赛事文档 |
| 5. 实测验证 | 23:51–23:55 | 在 WorkBuddy 中逐工具真实调用：now-time-info、available-coupons、query-my-coupons、query-nearby-stores、campaign-calendar、query-meals、query-meal-detail、calculate-price；运行两个 CLI 脚本验证输出；记录「预约场景菜单查询」「卡券日期校验基于实时时间」等实测结论 |
| 6. 文档与交付 | 23:55 起 | 编写 README、MCP_INTEGRATION、演示脚本（全部使用真实调用输出）与本文件 |

## 三、关键技术决策（WorkBuddy 协作中形成）

1. **Skill 形态选 WorkBuddy Skill 而非独立应用**：赛事鼓励「使用 WorkBuddy 开发 Skill」；Skill 形态零安装成本、可被 AI 直接编排，且附带 CLI 脚本保证可验证性。
2. **价格结论只信 calculate-price**：杜绝 AI 估算误差，比价结果可复现——这也是本项目与「罗列接口」型参赛作品的核心差异。
3. **只读优先 + 变更类工具强制确认**：7 个有副作用的工具（领券/下单/取消订单/新增地址/抽奖/积分兑换/主题活动下单）必须复述后果并取得用户明确确认，防止 AI 误操作账户。
4. **零依赖脚本**：MCP 客户端仅用 Python 标准库实现 Streamable HTTP + JSON-RPC，任何 Python 3.8+ 环境可直接运行，与「配置仅环境变量占位符」的信息安全声明一致。
5. **references 而非把细节塞进 SKILL.md**：遵循 Skill 的渐进式披露原则，SKILL.md 只放工作流与安全红线，35 个工具的地图与参数结构放 references。

## 四、实测验证记录（摘要）

| 调用 | 结果 |
|---|---|
| initialize / tools/list | 成功，35 个工具（含官方文档未收录的 query-survey-coupon、query-promotions） |
| now-time-info / available-coupons / query-my-coupons / campaign-calendar | 成功，真实数据已用于演示文档 |
| query-nearby-stores（city=上海） | 成功，返回附近门店 |
| query-meals（营业中门店，无预约） | 拒绝 600057「门店可能已关闭或不在营业时间」→ 传 reservationDate 后成功 |
| calculate-price（龙焰鸡腿堡） | 成功，原价 ¥24.00 → 到手 ¥15.90 |
| calculate-price + 卡券（10.26 起效） | 拒绝 600012「此卡券不在使用日期内」→ 确认卡券校验基于实时时间，脚本按设计降级 |
| scripts/sweep_coupons.py | 通过，输出真实巡券报告 |
| scripts/combo_optimizer.py | 通过，基准 ¥39.00 → 应付 ¥26.90 |

## 五、开发环境

- WorkBuddy（Agent 模式），工作区 `D:/Codes/buddy/麦当劳`
- 麦当劳 MCP 连接器 `mcd-mcp`（streamablehttp，Token 由开发者在控制台申请，未写入仓库）
- Python 3（标准库），Git（PortableGit）

## 六、产物清单

- Skill 主文件：`SKILL.md`
- 参考文档：`references/mcp-tools.md`、`references/mcp-tools.schema.json`（实测快照）
- 可执行代码：`scripts/mcd_mcp_client.py`、`scripts/sweep_coupons.py`、`scripts/combo_optimizer.py`
- 赛事文档：`README.md`、`CONTEST_DECLARATION.md`（官方原文）、`MCP_INTEGRATION.md`、`mcp-config.example.json`
- 演示：`examples/demo.md`（真实调用输出）
