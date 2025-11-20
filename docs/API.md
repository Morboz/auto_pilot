下面给你提供 **完整的接口设计（REST API + WebSocket）**，覆盖你的 Agent 框架的所有核心模块，包括：

* 用户会用到的交互接口（任务执行 / Chat UI）
* 系统内部模块（Tool Registry / Agent Config / 运行时控制）
* WebSocket（任务流日志推送）
* 适合 MVP 版本即可上线

接口风格：**REST + WebSocket（SSE 可替代）**
数据格式：JSON（工具参数使用 JSON schema）

> 这个设计可以直接交给前端/后端工程师实现。

---

# 🧩 **总览：模块 → 接口清单**

```
User / Dev UI
   ├── Agent Config API     (CRUD)
   ├── Tool Registry API    (CRUD + Test)
   ├── Task API             (submit task)
   ├── Log API              (fetch logs)
   └── WS: Task Stream      (push agent steps)

Agent Runtime
   ├── Planner API          (internal)
   ├── Executor API         (internal)
   └── Sandbox API          (internal)

Authentication (optional)
```

---

# 🟥 **1. Agent Config API（管理 Agent 配置）**

## **1.1 列出所有 Agents**

```
GET /api/agents
```

**Response**

```json
[
  {
    "id": "agent_trader_01",
    "name": "Web3 Trading Agent",
    "model": "gpt-5",
    "tools": ["tool_http", "tool_web3_rpc"],
    "created_at": "2025-01-01T10:00:00Z"
  }
]
```

---

## **1.2 创建 Agent**

```
POST /api/agents
```

**Body**

```json
{
  "name": "My Agent",
  "model": "gpt-5",
  "system_prompt": "You are a trading assistant...",
  "tools": ["tool_web3_rpc", "tool_sql"]
}
```

**Response**

```json
{ "id": "agent_12345" }
```

---

## **1.3 更新 Agent**

```
PATCH /api/agents/{agentId}
```

---

## **1.4 删除 Agent**

```
DELETE /api/agents/{agentId}
```

---

# 🟦 **2. Tool Registry API（工具管理）**

---

## **2.1 获取所有工具**

```
GET /api/tools
```

**Response**

```json
[
  {
    "id": "tool_web3_rpc",
    "name": "Web3 RPC",
    "type": "http",
    "description": "Call web3 JSON-RPC endpoints",
    "schema": {
      "rpc_url": "string",
      "method": "string",
      "params": "array"
    }
  }
]
```

---

## **2.2 创建 Tool**

```
POST /api/tools
```

**Body**

```json
{
  "name": "HTTP GET",
  "type": "http",
  "description": "Perform GET request",
  "schema": {
    "url": "string",
    "headers": "object?"
  }
}
```

---

## **2.3 更新 Tool**

```
PATCH /api/tools/{toolId}
```

---

## **2.4 删除 Tool**

```
DELETE /api/tools/{toolId}
```

---

## **2.5 测试 Tool**

开发者可在 UI 里输入参数点击 "Test Tool"

```
POST /api/tools/{toolId}/test
```

**Body**

```json
{ "params": { "url": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT" } }
```

**Response**

```json
{
  "success": true,
  "output": { "symbol": "ETHUSDT", "price": "2486.27" }
}
```

---

# 🟩 **3. Task API（提交任务 / 执行 Agent）**

---

## **3.1 向 Agent 提交任务**

```
POST /api/agents/{agentId}/tasks
```

**Body**

```json
{
  "input": "帮我分析 ETH 价格走势并决定是否买入",
  "meta": { "riskLevel": "low" }
}
```

**Response**

```json
{
  "taskId": "task_8899",
  "status": "running"
}
```

---

## **3.2 获取任务状态**

```
GET /api/tasks/{taskId}
```

**Response**

```json
{
  "taskId": "task_8899",
  "status": "running",
  "agent": "agent_trader_01",
  "created_at": "...",
  "completed_at": null
}
```

---

## **3.3 获取任务最终结果**

```
GET /api/tasks/{taskId}/result
```

**Response**

```json
{
  "result": "当前 ETH 呈现上涨趋势，但成交量不足 … 建议观望"
}
```

---

# 🟧 **4. 任务执行日志 API**

---

## **4.1 拉取所有步骤（类似 OpenAI ReAct logs）**

```
GET /api/tasks/{taskId}/logs
```

**Response**

```json
[
  {
    "step": 1,
    "thought": "我需要先获取 ETH 当前价格",
    "action": "tool_web3_rpc",
    "input": { "method": "eth_getPrice" },
    "observation": { "price": "2486.27" }
  },
  {
    "step": 2,
    "thought": "价格上升，应进一步查看深度…",
    "action": null,
    "observation": null
  }
]
```

---

# 🟨 **5. WebSocket 实时推送（关键）**

浏览器订阅：

```
WS /ws/tasks/{taskId}
```

服务器推送实时事件：

### **5.1 Agent 思考**

```json
{
  "type": "thought",
  "content": "I need to fetch the latest ETH price..."
}
```

### **5.2 Agent 调用工具**

```json
{
  "type": "action",
  "tool": "tool_web3_rpc",
  "input": { "method": "eth_getBalance", "params": ["0x..."] }
}
```

### **5.3 工具返回**

```json
{
  "type": "observation",
  "tool": "tool_web3_rpc",
  "output": { "result": "0.082 ETH" }
}
```

### **5.4 最终答案**

```json
{
  "type": "final",
  "result": "建议仓位保持不变。"
}
```

---

# 🟫 **6. 沙箱 / 安全控制 API（可选于MVP）**

---

## **6.1 预审 Tool 输入**

Agent 调用工具前，后端可查询：

```
POST /api/sandbox/validate
```

**Body**

```json
{
  "toolId": "tool_sql",
  "params": { "query": "DROP TABLE users;" },
  "agentId": "agent_trader_01"
}
```

**Response**

```json
{
  "allowed": false,
  "reason": "Query contains forbidden keywords"
}
```

---

# 🟪 **7. 内部模块 API（若你做微服务）**

可选，若你把 Planner / Executor 拆成独立服务。

---

## **7.1 任务规划（Planner）**

```
POST /internal/planner
```

**Body**

```json
{ "task": "分析 ETH 趋势并评估风险" }
```

---

## **7.2 工具执行（Executor）**

```
POST /internal/tools/execute
```

**Body**

```json
{
  "toolId": "tool_http",
  "params": { "url": "..." }
}
```

---

# 🔥 **最后给你一个完整 Task 日志流例子**

WebSocket 会推送：

```
[thought] → [action] → [observation] → [thought] → [action] → … → [final]
```

例如：

```json
{"type": "thought", "content": "First, I should check ETH price."}
{"type": "action", "tool": "tool_http", "input": {"url": "..."}}
{"type": "observation", "output": {"price": 2490.12}}
{"type": "thought", "content": "Price is rising. Now I check market depth."}
...
{"type": "final", "result": "结论：ETH 处于上涨趋势，可小仓试探买入。"}
```

---

# 🎯 这个接口设计的特点

### ✔ 与 OpenAI ReAct / Claude Tool Use 完全一致

### ✔ 纯 Web UI 就能驱动（无需命令行）

### ✔ 解耦（前端/后端/模型/工具都自由组合）

### ✔ 工具灵活（HTTP / Web3 / SQL / Playwright / Arbitrary Function）

### ✔ 支持多 Agent、多任务、可观察性完整

---

# 下一步

我可以继续为你生成：

1. **数据库 ER 图（Agent/Tool/Task/Logs）** ✔
2. **完整前端架构（页面 + 组件）**
3. **后端项目模板代码（FastAPI / NodeJS / Bun / Go）**
4. **Agent Runtime 的 ReAct Prompt 设计**

你想继续哪一块？
