"""
NGT-AI · A2A(Agent2Agent)服务器
=================================

把 NGT-AI 决策引擎暴露成一个符合 **A2A 协议**的智能体,让别的系统/智能体用
统一标准就能调用它做多模型协同决策(而不必知道内部 6 阶段/异构模型细节)。

暴露两个东西:
- **Agent Card**:`GET /.well-known/agent.json` —— 名片(身份/能力/端点/技能),用于发现。
- **A2A 端点(JSON-RPC 2.0)**:`POST /a2a` —— 方法 `message/send`(兼容旧名 `tasks/send`)。
  发一个决策问题的 message,拿回一个 Task,artifact 里是 NGT 决策报告。

运行:
    pip install fastapi "uvicorn[standard]"        # 核心引擎 Mock 模式零依赖
    uvicorn a2a_server:app --host 0.0.0.0 --port 4340
    # 想用真实多模型(需在 config.yaml 配 key):  NGT_A2A_REAL=1 uvicorn a2a_server:app ...

调用示例(标准 A2A 客户端亦可):
    curl -s http://localhost:4340/.well-known/agent.json
    curl -s -X POST http://localhost:4340/a2a -H 'content-type: application/json' -d '{
      "jsonrpc":"2.0","id":"1","method":"message/send",
      "params":{"message":{"role":"user","messageId":"m1",
        "parts":[{"kind":"text","text":"公司该用强制返岗还是永久远程?"}]}}}'
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# 复用现有决策引擎(Mock 模式零依赖;真实模式读 config.yaml 的 key)
from ngt_ai_mvp import NGTDecisionApp

# —— A2A 协议版本(对齐 a2a-protocol.org v0.2.x 的字段约定)——
PROTOCOL_VERSION = "0.2.5"
AGENT_VERSION = "1.0.0"
# 对外可访问的基地址(部署到公网时改成真实域名,Agent Card 的 url 要用绝对地址)
PUBLIC_BASE_URL = os.environ.get("A2A_PUBLIC_URL", "http://localhost:4340")

app = FastAPI(title="NGT-AI A2A Agent", version=AGENT_VERSION)

# 决策引擎单例(首次调用时创建;真假模式由 NGT_A2A_REAL 控制)
_engine: NGTDecisionApp | None = None
_engine_lock = asyncio.Lock()


async def _get_engine() -> NGTDecisionApp:
    global _engine
    if _engine is None:
        async with _engine_lock:
            if _engine is None:
                use_real = os.environ.get("NGT_A2A_REAL", "").lower() in ("1", "true", "yes")
                _engine = NGTDecisionApp(use_real_apis=use_real)
    return _engine


# ---------------------------------------------------------------- Agent Card
AGENT_CARD = {
    "protocolVersion": PROTOCOL_VERSION,
    "name": "ngt-ai-decision-agent",
    "description": (
        "基于名义小组技术(NGT)的多智能体协同决策智能体:强制异构模型(GPT/Gemini/"
        "DeepSeek/Qwen)独立产出 → 交叉评分 → 立场表态 → 裁判综合,从机制上对抗单模型偏见。"
        "输入一个决策问题,返回结构化的多视角决策报告。"
    ),
    "url": f"{PUBLIC_BASE_URL}/a2a",
    "version": AGENT_VERSION,
    "provider": {"organization": "xhnmakegreatai", "url": "https://github.com/xhnmakegreatai/NGT-AI"},
    "documentationUrl": "https://github.com/xhnmakegreatai/NGT-AI",
    "capabilities": {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/markdown", "text/plain"],
    "skills": [
        {
            "id": "ngt-decision",
            "name": "多智能体协同决策",
            "description": "对一个复杂决策问题,用 NGT 6 阶段流程组织多个异构 LLM 协同研判,产出综合决策建议与风险分析。",
            "tags": ["decision", "multi-agent", "NGT", "deliberation"],
            "examples": [
                "公司应该如何制定远程办公政策?",
                "初创公司早期该优先做核心产品还是扩展生态?",
                "是否应该进入某个新市场?",
            ],
        }
    ],
}


@app.get("/.well-known/agent.json")
async def agent_card():
    """A2A 发现入口:返回 Agent Card。"""
    return JSONResponse(AGENT_CARD)


@app.get("/")
async def root():
    return {"agent": AGENT_CARD["name"], "card": "/.well-known/agent.json", "endpoint": "/a2a"}


# ---------------------------------------------------------------- JSON-RPC 工具
def _rpc_error(req_id, code: int, message: str, status: int = 200):
    return JSONResponse(
        {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}},
        status_code=status,
    )


def _extract_text(message: dict) -> str:
    """从 A2A message 的 parts 里取出文本(兼容 kind/type 两种写法)。"""
    parts = (message or {}).get("parts") or []
    chunks = []
    for p in parts:
        if not isinstance(p, dict):
            continue
        kind = p.get("kind") or p.get("type")
        if kind == "text" and p.get("text"):
            chunks.append(str(p["text"]))
    return "\n".join(chunks).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- A2A 端点
@app.post("/a2a")
async def a2a_endpoint(request: Request):
    """A2A JSON-RPC 2.0 端点。支持 message/send(及旧名 tasks/send)。"""
    try:
        body = await request.json()
    except Exception:
        return _rpc_error(None, -32700, "Parse error: invalid JSON")

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}

    if method not in ("message/send", "tasks/send"):
        return _rpc_error(req_id, -32601, f"Method not found: {method}")

    message = params.get("message") or {}
    question = _extract_text(message)
    if not question:
        return _rpc_error(req_id, -32602, "Invalid params: 缺少决策问题文本(message.parts[].text)")

    task_id = str(uuid.uuid4())
    context_id = message.get("contextId") or str(uuid.uuid4())

    try:
        engine = await _get_engine()
        report_md = await engine.process_decision(question)  # → markdown 决策报告
        task = {
            "id": task_id,
            "contextId": context_id,
            "kind": "task",
            "status": {"state": "completed", "timestamp": _now()},
            "artifacts": [
                {
                    "artifactId": str(uuid.uuid4()),
                    "name": "ngt-decision-report",
                    "description": "NGT 多智能体协同决策报告(Markdown)",
                    "parts": [{"kind": "text", "text": report_md}],
                }
            ],
        }
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": task})
    except Exception as exc:  # 引擎失败 → 返回 failed 状态的 Task,而非 500
        task = {
            "id": task_id,
            "contextId": context_id,
            "kind": "task",
            "status": {
                "state": "failed",
                "timestamp": _now(),
                "message": {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": f"决策执行失败: {exc}"}],
                },
            },
            "artifacts": [],
        }
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": task})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "4340")))
