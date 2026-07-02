# NGT-AI · 多智能体协作决策系统

> 把社会学的「名义小组技术」(Nominal Group Technique) 搬进多 LLM 协作——
> 用**强制异构的模型** + **结构化的 6 阶段流程**,从机制上对抗单模型偏见。

开源 · MIT · Python 3.10+

## 这是什么 / 为什么这样设计

复杂决策里,单个 LLM 常「自信地偏」:给出看似合理、却漏掉关键反方视角的答案,被追问还会用更精致的论证维护原观点。这不是某个模型的缺陷,是**单模型只有一个世界观**的结构性问题。

市面多数「多 Agent」其实是**同一模型扮演不同角色**——底层一致,多元只是修辞,4 个 GPT 角色不会比 1 个多出多少真视角。

NGT-AI 的核心主张:**真正的多元需要异构的物理基础。** 它借用 Delbecq(1968)提出的名义小组技术(一种规避群体决策「从众/权威效应」的结构化方法),强制让**来自不同厂商的模型**(GPT / Gemini / DeepSeek / Qwen,Claude 任裁判)各自独立产出,再经结构化流程交叉评审、表态、裁定。

## 6 阶段流程

1. **独立观点产出** — 4 个 Discussant 各自独立思考,互不接收输出
2. **互不可见的方案** — 各自给完整方案,系统隔离(防止先发者锚定后发者)
3. **交叉评分** — 每个给其他三个打分,不能自评
4. **看到评分** — 评分公开
5. **立场表态(REVISED / DEFENDED)** — 强制二选一,不允许模糊中间态
6. **Referee 综合** — 独立裁判模型基于完整过程做最终裁定

## 快速开始(无需任何 API Key,Mock 模式即可跑通)

```bash
git clone https://github.com/xhnmakegreatai/NGT-AI.git
cd NGT-AI
python ngt_ai_mvp.py --question "我们公司应该如何制定远程办公政策?"
```

Mock 模式仅用 Python 标准库,克隆后即可直接运行,立刻看到一份完整决策报告。

接入真实模型:安装依赖并在 `config.yaml` 配置各 provider 的 key,即可让 4 个异构模型真实参与。

```bash
pip install -r requirements-minimal.txt
python ngt_ai_mvp.py --real-api --question "你的决策问题"
```

## 两种使用方式

- **CLI**(`ngt_ai_mvp.py`)— 核心引擎,稳定可用,Mock 模式零依赖
- **Web 全栈**(`backend/` FastAPI + `frontend/` React+Vite)— 任务管理 / 决策可视化脚手架

## 作为 A2A 智能体接入(Agent2Agent)

NGT-AI 可以暴露成一个符合 **[A2A 协议](https://a2a-protocol.org)** 的智能体,让别的系统/智能体用统一标准调用它做决策,而无需了解内部 6 阶段与异构模型细节。见 `a2a_server.py`。

```bash
pip install fastapi "uvicorn[standard]"          # 核心引擎 Mock 模式仍零依赖
uvicorn a2a_server:app --host 0.0.0.0 --port 4340
# 用真实多模型(需在 config.yaml 配 key):  NGT_A2A_REAL=1 uvicorn a2a_server:app --port 4340
```

- **Agent Card(发现)**:`GET /.well-known/agent.json`
- **A2A 端点(JSON-RPC 2.0)**:`POST /a2a`,方法 `message/send`

发一个决策问题,拿回一个 Task,artifact 里是决策报告:

```bash
curl -s -X POST http://localhost:4340/a2a -H 'content-type: application/json' -d '{
  "jsonrpc":"2.0","id":"1","method":"message/send",
  "params":{"message":{"role":"user","messageId":"m1",
    "parts":[{"kind":"text","text":"公司该用强制返岗还是永久远程?"}]}}}'
```

> 定位:**MCP = 智能体↔工具;A2A = 智能体↔智能体**。这一层让 NGT 成为可被编排的决策节点。

## 现状与局限(诚实说明)

- ✅ **CLI 引擎可用**:6 阶段全实现、异步并发、Mock 零依赖;克隆即可跑通。
- 🚧 **Web 全栈是脚手架**:后端路由 / 模型 / 认证完整,但实时进度的 WebSocket 推送尚未接线、前后端联调未全验证(代码中以 `TODO` 标注)。部署前请改掉默认 JWT secret。

> 把局限写清楚,是这个项目的一部分:决策系统最该诚实的,正是「它什么时候还不够好」。

## 方法论出处

Delbecq & Van de Ven (1971), *A Group Process Model for Problem Identification and Program Planning* —— 名义小组技术(NGT)。

## License

MIT
