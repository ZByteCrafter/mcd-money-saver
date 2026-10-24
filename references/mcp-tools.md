# 麦当劳 MCP 工具能力映射表（35 个）

> 依据 2026-10-24 对线上服务 `https://mcp.mcd.cn`（mcd-mcp v1.0.0）的 `tools/list` 实测结果整理。
> 官方 README 仅列出 33 个工具，本表包含实测新增的 2 个未收录工具（`query-survey-coupon`、`query-promotions`），已用 ★ 标注。
> 每个工具的完整参数结构见同目录 `mcp-tools.schema.json`。

## 工具分类总览

| 分类 | 数量 | 说明 |
|---|---|---|
| 只读查询 | 28 | 可自由调用 |
| 账户/订单变更 | 7 | 必须经用户明确确认后才能调用（见 SKILL.md 安全红线） |

## 变更类工具（调用前必须复述并取得确认）

| 工具 | 作用 | 副作用 |
|---|---|---|
| `auto-bind-coupons` | 麦麦省一键领券 | 领取账户下全部可领优惠券 |
| `create-order` | 创建点餐订单 | 生成待支付订单 |
| `cancel-order` | 取消订单 | 订单作废 |
| `delivery-create-address` | 新增配送地址 | 写入用户地址簿 |
| `draw-lottery` | 积分抽奖 | 消耗积分或次数 |
| `mall-create-order` | 积分兑换商品下单 | 扣减积分、发放券码 |
| `party-order-create` | 主题活动订单创建 | 生成待支付订单 |

## 只读工具明细

### 时间与活动

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `now-time-info` | 返回服务器当前时间（临期判断基准） | 无 |
| `campaign-calendar` | 当月营销活动日历（进行中/往期/未来，含订阅状态） | `specifiedDate`（可选，yyyy-MM-dd，锚定前后各一天共三天） |
| `query-lottery-info` | 积分抽奖活动信息、奖品列表、消耗规则 | 无 |
| `query-my-prizes` | 我的抽奖奖品记录（分页、按中奖时间倒序） | 分页参数 |

### 优惠券

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `available-coupons` | 麦麦省当前可领取的券列表 | 无 |
| `query-my-coupons` | 卡包已有券资产（**不做门店/渠道校验，不等于当前订单可用**） | `page`（≤5）、`pageSize`（≤200） |
| `query-store-coupons` | 指定门店 + 订单类型下真正可用的券 | `storeCode` 必填；`orderType`（1 到店/2 外送）；`beType`、`beCode`、`reservationDate` |
| `query-survey-coupon` ★ | 按订单号查询 CSAT 满意度答卷关联奖券的标题、核销时间与状态 | `orderId`（用户提供，禁止编造） |
| `query-promotions` ★ | 企业团餐场景（beType=6）当前门店满减/满折促销规则 | `storeCode` 必填；`beCode` 必传；`orderType=2` |

### 门店与菜单

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `query-nearby-stores` | 附近可用门店（到店自提/得来速） | `beType`（1 或 5）必填；`searchType`（1 收藏餐厅/2 按位置）；`city`、`keyword` |
| `delivery-query-addresses` | 已创建的配送地址列表 | 无 |
| `delivery-query-stores` | 收货地址附近可配送门店 | 地址上下文 |
| `query-meals` | 当前门店在售餐品（分类、餐品编码、标签） | `storeCode`、`orderType`、`beType`、`beCode` |
| `query-meal-detail` | 餐品详情：套餐组成与可替换选项 | 餐品编码 |
| `query-meal-assistance` | 企业团餐门店助餐服务 | 门店上下文 |

### 计价与订单查询

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `calculate-price` | 权威计价：商品额、优惠额、配送费、应付总额（含优惠券） | `storeCode`、`orderType`、`beType` 必填；`items[]`（`productCode`、`quantity` 必填，券挂 `couponId`/`couponCode`，套餐 `roundList`，特制 `modification`）；`beCode`、`reservationDate`、`withOrder`（随单购卡） |
| `query-order` | 订单状态、内容、配送信息 | 订单号 |
| `order-list` | 近期到店/外送历史订单 | 无 |

### 积分与商城

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `query-my-account` | 积分账户：可用/累计/冻结/即将过期 | 无 |
| `mall-points-products` | 麦麦商城可兑换或购买的商品列表 | `catRuleIds` 类目筛选（如 `2` 实物、`2>8` 周边、`1>6>20` 生日派对） |
| `mall-product-detail` | 商城商品详情（图片、积分、有效期） | 商品标识 |
| `mall-order-list` | 商城近一年订单列表 | 无 |
| `mall-order-detail` | 商城订单详情 | 订单标识 |

### 主题活动与营养

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `query-party-city` | 主题活动可参与城市列表 | 无 |
| `query-party-store` | 指定城市下主题活动可参与门店 | 城市标识 |
| `query-party-store-date` | 指定门店主题活动的可预约日期 | 门店标识 |
| `query-party-store-session` | 指定门店 + 日期的可预约场次 | 门店 + 日期 |
| `list-nutrition-foods` | 餐品营养成分：能量、蛋白质、脂肪、碳水化合物、钠、钙 | 无 |

## 关键业务规则（实测与文档结论）

1. **场景编码映射**：`beType` 1-到店取餐、2-麦乐送到家、5-得来速、6-企业团餐；`orderType` 1-到店（含得来速）、2-外送（含团餐）。`beCode` 需与 `storeCode` 配对，从 `query-nearby-stores` 或 `delivery-query-stores` 返回中获取；到店自取场景不传。
2. **限流**：每 Token 每分钟 600 次请求，超限返回 429；401 表示 Token 无效或过期。
3. **券的可用性分层**：`query-my-coupons` 是卡包资产视角；`query-store-coupons` 是当前门店 + 渠道视角。凑单比价只认后者。
4. **价格裁判**：`calculate-price` 是唯一权威计价入口，任何「能省多少」的结论都必须由它算出，禁止自行加减估算。
