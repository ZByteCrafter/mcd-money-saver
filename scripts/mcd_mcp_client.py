#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦当劳 MCP 零依赖客户端（仅使用 Python 标准库）。

通过 Streamable HTTP 与麦当劳中国 MCP 服务（默认 https://mcp.mcd.cn）通信，
封装 initialize / tools/list / tools/call 三个核心 MCP 方法。

作为模块使用::

    from mcd_mcp_client import McDonaldsMCPClient

    client = McDonaldsMCPClient()  # Token 从环境变量 MCD_MCP_TOKEN 读取
    tools = client.list_tools()
    result = client.call_tool("now-time-info")

命令行使用::

    python mcd_mcp_client.py list-tools
    python mcd_mcp_client.py call now-time-info
    python mcd_mcp_client.py call calculate-price '{"storeCode": "...", "orderType": 1, "beType": 1, "items": []}'

安全约定：Token 只从环境变量 MCD_MCP_TOKEN（或参数）读取，不写入任何文件。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-03-26"
USER_AGENT = "mcd-money-saver/1.0.0"


class MCPError(RuntimeError):
    """MCP 调用失败：网络错误、限流（429）、服务端业务错误等。"""


class McDonaldsMCPClient:
    """麦当劳 MCP 最小客户端。"""

    def __init__(self, url=None, token=None, timeout=30):
        self.url = (url or os.environ.get("MCD_MCP_URL") or DEFAULT_URL).rstrip("/")
        self.token = token or os.environ.get("MCD_MCP_TOKEN")
        if not self.token:
            raise MCPError("未找到 MCP Token：请设置环境变量 MCD_MCP_TOKEN")
        self.timeout = timeout
        self._next_id = 1
        self._initialized = False

    # ------------------------------------------------------------------ 底层
    def _send(self, method, params=None, auto_init=True):
        if auto_init and method != "initialize" and not self._initialized:
            self.initialize()
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        self._next_id += 1
        if params is not None:
            payload["params"] = params
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer " + self.token,
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise MCPError("HTTP %s：%s" % (exc.code, detail[:500])) from exc
        except urllib.error.URLError as exc:
            raise MCPError("网络错误：%s" % exc.reason) from exc
        return self._parse(body)

    @staticmethod
    def _parse(body):
        """解析 JSON-RPC 响应，兼容 SSE（data: 前缀）包裹。"""
        text = body.strip()
        if text.startswith("event:") or text.startswith("data:"):
            for line in text.splitlines():
                if line.startswith("data:"):
                    text = line[len("data:"):].strip()
                    break
        try:
            message = json.loads(text)
        except ValueError as exc:
            raise MCPError("响应不是合法 JSON：%s" % text[:200]) from exc
        if "error" in message:
            error = message["error"]
            raise MCPError("MCP 错误 %s：%s" % (error.get("code"), error.get("message")))
        return message.get("result", {})

    # -------------------------------------------------------------- MCP 方法
    def initialize(self):
        result = self._send(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": USER_AGENT, "version": "1.0.0"},
            },
            auto_init=False,
        )
        self._initialized = True
        return result

    def list_tools(self):
        """返回工具定义列表（含 name / description / inputSchema）。"""
        return self._send("tools/list", {}).get("tools", [])

    def call_tool(self, name, arguments=None):
        """调用工具，返回 structuredContent（缺失时返回原始 result）。"""
        result = self._send("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            texts = [part.get("text", "") for part in result.get("content", []) if part.get("type") == "text"]
            raise MCPError("工具 %s 执行失败：%s" % (name, " ".join(texts)[:500]))
        if "structuredContent" in result:
            return result["structuredContent"]
        texts = [part.get("text", "") for part in result.get("content", []) if part.get("type") == "text"]
        if len(texts) == 1:
            try:
                return json.loads(texts[0])
            except ValueError:
                return texts[0]
        return result


def _main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    command = argv[1]
    client = McDonaldsMCPClient()
    if command == "list-tools":
        tools = client.list_tools()
        print("共 %d 个工具：" % len(tools))
        for tool in tools:
            print("- %-28s %s" % (tool["name"], tool.get("description", "").splitlines()[0][:60]))
        return 0
    if command == "call":
        if len(argv) < 3:
            print("用法：python mcd_mcp_client.py call <工具名> [参数JSON]")
            return 2
        arguments = json.loads(argv[3]) if len(argv) > 3 else {}
        print(json.dumps(client.call_tool(argv[2], arguments), ensure_ascii=False, indent=2))
        return 0
    print("未知命令：%s（支持 list-tools / call）" % command)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(_main(sys.argv))
    except MCPError as error:
        print("错误：%s" % error, file=sys.stderr)
        sys.exit(1)
