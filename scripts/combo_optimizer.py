#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""凑单比价器：用权威计价接口找出最省的用券组合。

对给定门店与商品清单，先算无券基准价，再逐券试算、高价值券两两叠加，
全部通过 calculate-price 得出，不自行估算任何金额。

用法::

    export MCD_MCP_TOKEN=<你的Token>
    python combo_optimizer.py --store 1450724 --be-type 1 --order-type 1 \
        --items 521952:1,521986:1 \
        --coupons B34E5EC6710BEEECEC8B25C742D3F119:MCD60SU2906A51AG02031

    # 预约场景加 --reserve "2026-10-27 11:30"；外送场景 --be-type 2 --be-code <beCode>

说明：
  - 券通过 items[].couponId / couponCode 挂在商品项上；本脚本默认挂在第一个商品上，
    适用于整单券。单品券请把 --items 只保留对应商品。
  - 受服务限流约束（每 Token 每分钟 600 次），--max-calls 控制单轮最多试算次数，
    两次调用之间按 --interval 秒休眠。
  - 价格为接口返回的「分」，脚本统一换算成元展示。
"""

from __future__ import annotations

import argparse
import sys
import time

from mcd_mcp_client import MCPError, McDonaldsMCPClient


def parse_items(text):
    """解析 'code:qty,code:qty' 为 calculate-price 的 items 结构。"""
    items = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            code, quantity = chunk.rsplit(":", 1)
            items.append({"productCode": code.strip(), "quantity": int(quantity)})
        else:
            items.append({"productCode": chunk, "quantity": 1})
    if not items:
        raise ValueError("--items 不能为空")
    return items


def parse_coupons(text):
    """解析 'id:code,id:code' 为 [(couponId, couponCode), ...]。"""
    coupons = []
    for chunk in (text or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            coupon_id, coupon_code = chunk.split(":", 1)
            coupons.append((coupon_id.strip(), coupon_code.strip()))
        else:
            coupons.append((chunk, ""))
    return coupons


def price_of(result):
    """从计价结果提取（原价, 应付, 优惠）分。"""
    data = result.get("data") or {}
    return (
        int(data.get("originalPrice", 0)),
        int(data.get("price", 0)),
        int(data.get("discount", 0)),
    )


def fen_to_yuan(fen):
    return "¥%.2f" % (fen / 100.0)


def main(argv=None):
    parser = argparse.ArgumentParser(description="麦当劳凑单比价器（基于 calculate-price）")
    parser.add_argument("--store", required=True, help="门店编码 storeCode")
    parser.add_argument("--be-type", type=int, required=True, choices=[1, 2, 5, 6],
                        help="1 到店自取 / 2 麦乐送 / 5 得来速 / 6 企业团餐")
    parser.add_argument("--order-type", type=int, required=True, choices=[1, 2],
                        help="1 到店 / 2 外送")
    parser.add_argument("--be-code", default="", help="外送/得来速场景必填")
    parser.add_argument("--reserve", default="", help="预约时间，格式 'yyyy-MM-dd HH:mm'")
    parser.add_argument("--items", required=True, help="商品清单 '编码:数量,编码:数量'")
    parser.add_argument("--coupons", default="", help="候选券 '券Id:券Code,...'")
    parser.add_argument("--max-calls", type=int, default=15, help="单轮最多试算次数（默认 15）")
    parser.add_argument("--interval", type=float, default=0.6, help="调用间隔秒数（默认 0.6）")
    args = parser.parse_args(argv)

    try:
        items = parse_items(args.items)
    except ValueError as error:
        print("参数错误：%s" % error, file=sys.stderr)
        return 2
    coupons = parse_coupons(args.coupons)

    base_arguments = {
        "storeCode": args.store,
        "orderType": args.order_type,
        "beType": args.be_type,
        "items": items,
    }
    if args.be_code:
        base_arguments["beCode"] = args.be_code
    if args.reserve:
        base_arguments["reservationDate"] = args.reserve

    try:
        client = McDonaldsMCPClient()
    except MCPError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1

    def call_price(label, extra_items=None):
        arguments = dict(base_arguments)
        if extra_items is not None:
            arguments["items"] = extra_items
        try:
            result = client.call_tool("calculate-price", arguments)
        except MCPError as error:
            print("  [跳过] %s：%s" % (label, error), file=sys.stderr)
            return None
        if not result.get("success"):
            print("  [跳过] %s：%s" % (label, result.get("message")), file=sys.stderr)
            return None
        return price_of(result)

    rows = []
    calls = 0

    # 1. 无券基准
    baseline = call_price("无券基准")
    if baseline is None:
        print("基准计价失败，无法比价。请检查门店、商品编码与营业时间。", file=sys.stderr)
        return 1
    calls += 1
    rows.append(("无券基准", baseline))

    # 2. 逐券试算（券挂在第一个商品上）
    for index, (coupon_id, coupon_code) in enumerate(coupons):
        if calls >= args.max_calls:
            print("已达 --max-calls 上限，剩余券未试算。", file=sys.stderr)
            break
        coupon_items = [dict(item) for item in items]
        coupon_items[0]["couponId"] = coupon_id
        if coupon_code:
            coupon_items[0]["couponCode"] = coupon_code
        time.sleep(args.interval)
        result = call_price("券 %s" % coupon_id[:8], coupon_items)
        calls += 1
        if result:
            rows.append(("券 %s" % coupon_id[:8], result))

    # 3. 高价值券两两叠加（按单券应付升序取前 4 名）
    single_results = [(label, result) for label, result in rows[1:]]
    single_results.sort(key=lambda pair: pair[1][1])
    for i in range(min(4, len(single_results))):
        for j in range(i + 1, min(4, len(single_results))):
            if calls >= args.max_calls:
                break
            id_a = coupons[[r[0] for r in rows].index(single_results[i][0])][0]
            id_b = coupons[[r[0] for r in rows].index(single_results[j][0])][0]
            code_a = coupons[[r[0] for r in rows].index(single_results[i][0])][1]
            code_b = coupons[[r[0] for r in rows].index(single_results[j][0])][1]
            coupon_items = [dict(item) for item in items]
            coupon_items[0]["couponId"] = id_a
            if code_a:
                coupon_items[0]["couponCode"] = code_a
            time.sleep(args.interval)
            # 第二张券挂在第二个商品上（若只有一个商品则放弃叠加）
            if len(coupon_items) < 2:
                break
            coupon_items[1]["couponId"] = id_b
            if code_b:
                coupon_items[1]["couponCode"] = code_b
            result = call_price("叠加 %s+%s" % (id_a[:6], id_b[:6]), coupon_items)
            calls += 1
            if result:
                rows.append(("叠加 %s+%s" % (id_a[:6], id_b[:6]), result))

    # 4. 输出比价表
    print("=" * 64)
    print("凑单比价结果（共 %d 次计价调用）" % calls)
    print("=" * 64)
    print("%-22s %10s %10s %10s" % ("组合", "原价", "优惠", "应付"))
    for label, (original, payable, discount) in sorted(rows, key=lambda pair: pair[1][1]):
        saved = baseline[1] - payable
        print("%-22s %10s %10s %10s   较基准省 %s"
              % (label, fen_to_yuan(original), fen_to_yuan(discount), fen_to_yuan(payable),
                 fen_to_yuan(saved) if saved > 0 else "¥0.00"))
    best_label, best = min(rows, key=lambda pair: pair[1][1])
    print("\n结论：%s 最省，应付 %s（较无券基准省 %s）。"
          % (best_label, fen_to_yuan(best[1]), fen_to_yuan(baseline[1] - best[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
