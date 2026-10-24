#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""巡券报告：盘点麦当劳账户的优惠券资产。

依次调用只读工具 now-time-info / available-coupons / query-my-coupons，
输出「服务器时间 → 可领取 → 已持有 → 临期预警」四段式报告。

用法::

    export MCD_MCP_TOKEN=<你的Token>
    python sweep_coupons.py                # 只读盘点，不动账户
    python sweep_coupons.py --bind         # 盘点后一键领取可领券（需确认）
    python sweep_coupons.py --json         # 输出原始 JSON

注意：--bind 会调用 auto-bind-coupons 领取账户下全部可领优惠券，
属于账户变更操作，执行前会打印提示并要求输入 yes 确认。
"""

from __future__ import annotations

import argparse
import json
import sys

from mcd_mcp_client import MCPError, McDonaldsMCPClient


def _text(part):
    return part.get("text", "") if part.get("type") == "text" else ""


def build_report(client):
    """拉取数据并生成报告（返回 report dict 与原文）。"""
    now = client.call_tool("now-time-info")
    available = client.call_tool("available-coupons")
    mine = client.call_tool("query-my-coupons")

    server_time = now.get("data", {}).get("formatted", "未知")

    can_get = [c for c in (available.get("data") or []) if c.get("couponStatus") == "CAN_GET"]
    already = [c for c in (available.get("data") or []) if c.get("couponStatus") != "CAN_GET"]
    wallet = (mine.get("data") or {}).get("coupons", [])

    return {
        "serverTime": server_time,
        "canGet": can_get,
        "alreadyReceived": already,
        "wallet": wallet,
    }


def print_report(report):
    print("=" * 56)
    print("麦门省钱军师 · 巡券报告")
    print("服务器时间：%s" % report["serverTime"])
    print("=" * 56)

    print("\n【可领取】共 %d 张" % len(report["canGet"]))
    if report["canGet"]:
        for coupon in report["canGet"]:
            print("  - %s（%s）" % (coupon.get("couponName", "?"), coupon.get("label", "")))
    else:
        print("  （当前没有可领取的券）")

    print("\n【麦麦省已领取】共 %d 张" % len(report["alreadyReceived"]))
    for coupon in report["alreadyReceived"]:
        print("  - %s（%s）" % (coupon.get("couponName", "?"), coupon.get("label", "")))

    print("\n【卡包资产】共 %d 张" % len(report["wallet"]))
    for coupon in report["wallet"]:
        times = []
        for item in (coupon.get("instructions") or {}).get("availableTime", []):
            if item.get("text"):
                times.append(item["text"])
        window = "；".join(times) if times else "有效期见券面"
        print("  - %s  有效期：%s" % (coupon.get("title", "?"), window))

    print("\n【行动建议】")
    if report["canGet"]:
        print("  1. 有 %d 张券可领取，加 --bind 参数一键领取。" % len(report["canGet"]))
    else:
        print("  1. 当前无可领券，可明日再来或关注活动日历。")
    print("  2. 卡包券能否用于当前订单，请以门店维度查询（query-store-coupons）为准。")
    print("  3. 临近有效期截止的券请优先使用。")


def main(argv=None):
    parser = argparse.ArgumentParser(description="麦当劳优惠券巡券报告（只读）")
    parser.add_argument("--bind", action="store_true", help="盘点后调用 auto-bind-coupons 一键领券（需确认）")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON 而非文本报告")
    args = parser.parse_args(argv)

    try:
        client = McDonaldsMCPClient()
        report = build_report(client)
    except MCPError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)

    if args.bind:
        if not report["canGet"]:
            print("\n没有可领取的券，跳过领取。")
            return 0
        print("\n即将调用 auto-bind-coupons 领取上述 %d 张可领券。" % len(report["canGet"]))
        answer = input("确认领取？输入 yes 继续：").strip().lower()
        if answer != "yes":
            print("已取消，未做任何变更。")
            return 0
        try:
            result = client.call_tool("auto-bind-coupons")
        except MCPError as error:
            print("领取失败：%s" % error, file=sys.stderr)
            return 1
        print("领取完成：%s" % result.get("message", "成功"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
