# MCP 集成说明

本文档说明「麦门省钱军师」与麦当劳中国 MCP 服务的集成方式：使用了哪个 Server、哪些 Tool、调用流程与业务价值。

## 1. MCP Server

| 项目 | 内容 |
|---|---|
| 服务名称 | mcd-mcp（麦当劳中国 MCP Server） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 认证方式 | 请求头 `Authorization: Bearer <MCP Token>` |
| Token 申请 | [麦当劳 MCP 开放平台](https://open.mcd.cn/mcp) 控制台激活 |
| 协议版本 | 2025-03-26（实测握手返回） |
| 服务版本 | 1.0.0（实测握手返回） |
| 限流 | 每 Token 每分钟 600 次请求，超限返回 429；401 表示 Token 无效或过期 |
| 官方文档 | [M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server) |

配置示例见仓库根目录 `mcp-config.example.json`（仅环境变量占位符，不含任何真实凭证）。

## 2. 使用的 Tool

服务端当前共上线 **35 个工具**（2026-10-24 实测 `tools/list`，比官方 README 列出的 33 个多出 `query-survey-coupon` 与 `query-promotions` 两个未收录工具）。完整能力映射见 [`references/mcp-tools.md`](references/mcp-tools.md)，参数结构快照见 [`references/mcp-tools.schema.json`](references/mcp-tools.schema.json)。

本 Skill 按工作流实际使用的工具：

| 工作流 | 使用的工具 | 用途 |
|---|---|---|
| W1 巡券 | `now-time-info`、`available-coupons`、`query-my-coupons`、`auto-bind-coupons`（需确认） | 时间校准、可领券盘点、卡包资产、临期预警、一键领取 |
| W2 凑单比价 | `query-nearby-stores`、`delivery-query-addresses`、`delivery-query-stores`、`query-store-coupons`、`query-meals`、`query-meal-detail`、`calculate-price` | 门店定位、门店维度可用券、在售菜单、套餐组成、权威计价 |
| W3 活动雷达 | `campaign-calendar`、`query-my-account`、`mall-points-products`、`mall-product-detail` | 活动时间线、积分盘点、商城兑换建议 |
| W4 营养参谋 | `list-nutrition-foods`（搭配后回到 `calculate-price` 核价） | 营养成分接入搭配决策 |
| W5 点餐方案 | 汇总 W1–W4 结果，仅在用户明确确认后调用 `create-order` | 生成方案、复述确认、代下单 |

未纳入日常流程但已在 references 中建档的工具（如主题活动系列 `query-party-*`、积分抽奖系列 `query-lottery-info`/`draw-lottery`/`query-my-prizes`、商城订单系列、`cancel-order`、`query-order`/`order-list`、`query-survey-coupon`、`query-promotions`）可按需扩展。

## 3. 调用流程

以核心工作流 W2「凑单比价」为例：

```
1. beType 场景确认        用户选择 到店自取(1)/麦乐送(2)/得来速(5)/团餐(6)
2. query-nearby-stores    beType + searchType=2 + city/keyword → storeCode（及 beCode）
   delivery-query-stores  外送场景：先 delivery-query-addresses 取地址
3. query-store-coupons    storeCode + orderType + beType → 当前门店真正可用的券
4. query-meals            storeCode + orderType + beType → 在售餐品编码
   query-meal-detail      code → 套餐组成与替换选项（roundList/modification）
5. calculate-price        storeCode + orderType + beType 必填；
                          items[].productCode/quantity 必填，券挂 couponId/couponCode
                          → 无券基准价 → 逐券试算 → 高价值券两两叠加
6. 输出比价表             按应付升序，标注节省金额，给出主推 + 备选组合
```

关键业务规则（实测结论）：

1. **券的可用性分层**：`query-my-coupons` 是卡包资产视角，不做门店/渠道校验；`query-store-coupons` 是当前门店 + 订单类型视角。凑单比价只认后者。
2. **价格唯一裁判**：所有「能省多少」的结论必须由 `calculate-price` 算出，禁止自行加减估算。
3. **预约场景**：门店非营业时间时，菜单/计价类调用传 `reservationDate`（`yyyy-MM-dd HH:mm`）可按预约时段查询。
4. **卡券日期校验**：实测卡券有效期校验基于实时时间而非预约时间——预约 10.27 使用 10.26 起效的券，在 10.24 当天调用会被拒绝（错误码 600012「此卡券不在使用日期内」）。Skill 已按此现实设计降级路径：跳过该券，输出其余组合结论。

## 4. 业务价值

1. **把 35 个接口编织成决策**：单个工具只回答一个问题（有什么券/多少钱/有什么活动），本 Skill 回答用户真正的问题——「怎么点最省」，价值在编排而非封装。
2. **可信的省钱数字**：所有价格来自官方计价接口，杜绝 AI 估算误差；比价过程可复现（CLI 脚本输出即证据）。
3. **安全的下单边界**：AI 只负责决策到「方案」为止，支付前的最后一步永远留给用户确认，避免误下单与误领券。
4. **未文档化工具的实测补充**：发现并验证了官方 README 未收录的 `query-survey-coupon`（按订单号查满意度答卷关联奖券）与 `query-promotions`（团餐满减满折规则），已写入 references 供其他开发者参考。

## 5. 实测记录

| 时间 | 项目 | 结果 |
|---|---|---|
| 2026-10-24 23:46 | initialize 握手 | 成功，mcd-mcp v1.0.0，协议 2025-03-26 |
| 2026-10-24 23:46 | tools/list | 成功，35 个工具 |
| 2026-10-24 23:46 | now-time-info | 成功，返回服务器时间 |
| 2026-10-24 23:51 | available-coupons | 成功，返回可领/已领券列表 |
| 2026-10-24 23:51 | query-nearby-stores | 成功，返回附近门店（city=上海 + keyword） |
| 2026-10-24 23:51 | campaign-calendar | 成功，返回当月活动日历 |
| 2026-10-24 23:52 | query-my-coupons | 成功，返回卡包券（含有效期） |
| 2026-10-24 23:52 | query-meals（营业中门店） | 拒绝，600057「门店可能已关闭或不在营业时间」 |
| 2026-10-24 23:52 | query-meals + reservationDate | 成功，返回全部分类菜单 |
| 2026-10-24 23:52 | calculate-price | 成功，龙焰鸡腿堡原价 ¥24.00 → 到手 ¥15.90 |
| 2026-10-24 23:53 | calculate-price + 卡券 | 拒绝，600012「此卡券不在使用日期内」（10.26 起效） |
| 2026-10-24 23:54 | scripts/sweep_coupons.py | 通过，输出真实巡券报告 |
| 2026-10-24 23:55 | scripts/combo_optimizer.py | 通过，基准 ¥39.00 → 应付 ¥26.90，卡券按设计跳过 |
