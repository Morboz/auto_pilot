# LLM Adapter 设计规范

> **更新日期：2025-11-20**
>
> **✨ 新增功能：Claude Adapter 现已支持 Anthropic 兼容供应商（如 MiniMax）**
> 📖 [查看详情](./claude-compatible-providers.md)

---

下面我给你一个 **明确、可落地、行业最佳实践的「LLM Adapter 设计规范」**，专门适配你正在做的「自主任务执行 Agent 框架」。
会回答：

* LLM Adapter **需要哪些能力？**
* **要不要支持多轮对话？**
* **要不要支持工具调用？**
* Claude / OpenAI 的差异如何统一？

这是你框架中最关键的抽象层，一定要设计好，否则未来扩展多个模型（GPT、Claude、Gemini、Ollama、自建 LLM）都会很痛苦。

---

# 🧩 **什么是 LLM Adapter？**

它是你的系统中：

**Agent Runtime → LLM API（OpenAI/Claude/自建模型）**
之间的“统一接口层”。

Adapter 的目标是：
👉 **无论底层接的是 GPT、Claude、或其他模型，上层 Agent 代码永远保持不变。**

---

# 🟥 **LLM Adapter 应具备的能力（必须项）**

你最终会有 7 个 Required 能力 + 3 个可选能力。

下面是完整列表。

---

# 1️⃣ **generate()：基础文本生成能力（必选）**

```ts
adapter.generate({
  model: "gpt-5",
  messages: [...],
  temperature: 0.3
})
```

返回：

```json
{
  "content": "思考结果…"
}
```

> 所有模型，包括自建 LLM 都一定能提供这个能力。

---

# 2️⃣ **structured_generate()：结构化输出（必选）**

很多 Agent 步骤需要 **JSON/特定 Schema 输出**。

所以 Adapter 必须提供强制结构化的接口：

```ts
adapter.structuredGenerate({
  model: "gpt-5",
  messages: [...],
  response_format: {
    type: "json_schema",
    schema: {
      type: "object",
      properties: {
        thought: { type: "string" },
        action: { type: "string", nullable: true },
        actionInput: { type: "object" }
      }
    }
  }
});
```

> Claude 有 Anthropic “structured output”，OpenAI 有 `response_format: json_schema`。
> 需要统一抽象。

---

# 3️⃣ **支持 Tool Call / Function Call（必选）**

你的 Agent 框架本质是「Claude Code」风格 → **所以必须支持工具调用**。

Adapter 提供：

```ts
adapter.runWithTools({
  model: "gpt-5",
  messages: [...],
  tools: [
    {
      name: "web3_getBalance",
      description: "...",
      parameters: { ... JSON schema ... }
    }
  ]
})
```

并返回：

```json
{
  "type": "tool_call",
  "name": "web3_getBalance",
  "arguments": { "address": "0x123..." }
}
```

> Claude 使用 `tool_use` / `tool_result`
> OpenAI 使用 `function_call`
> 必须统一。（下面给你统一规范）

---

# 4️⃣ **流式输出 streaming（必选）**

前端 UI（类似 Claude Code）**一定要实时显示模型思考流**。

Adapter 需要能：

```ts
adapter.stream({
  messages: [...],
  onDelta: (chunk) => { ... }
});
```

并实现内部对 OpenAI / Claude 的 chunk 转换。

---

# 5️⃣ **工具调用流式输出（必选）**

Claude Code 的行为：

* “思考中…”（token 流）
* 返回 tool_use action
* tool result
* 思考…
* 再次执行工具…

你口中的 Agent Runtime 也要做到这一点。

所以 Adapter 要支持：

**流式：文本 + 工具调用 + 工具结果插入到上下文**

统一格式如下：

```ts
{
  "type": "text",
  "content": "我先检查价格…"
}
{
  "type": "tool_call",
  "name": "http_get",
  "arguments": { "url": "..." }
}
{
  "type": "tool_result",
  "output": { "price": 2480.12 }
}
```

---

# 6️⃣ **Token 计费（必选）**

LLM 调用成本不可忽略，必须透明化。

LLM Adapter 应该返回：

```json
{
  "usage": {
    "input_tokens": 123,
    "output_tokens": 55
  }
}
```

所有模型都归一化。

---

# 7️⃣ **模型能力描述（必选）**

你的框架需要知道“这个模型是否支持工具调用？是否支持 JSON Schema？”

所以适配器应该提供：

```ts
adapter.capabilities("gpt-5")
```

返回：

```json
{
  "supportsTools": true,
  "supportsStreaming": true,
  "supportsJsonSchema": true,
  "supportsImages": false
}
```

---

# 🟦 **要不要支持多轮对话？——答案：必须支持（但不是 Chat 形式）**

你做的是：

**自主任务执行 Agent**

这种 Agent 是 *多步骤* 的：

* thought
* action
* observation
* thought
* action
* observation
* ...

所以 **必须具备多轮上下文（memory of previous messages）**。

但是不是普通 Chat：

* 用户不会介入
* 这是一组 runtime messages（类似 ReAct）

### ✔ 所以 Adapter 要支持：

```ts
messages = [
  { role: "system", content: "..." },
  { role: "user", content: "Analyze ..." },
  { role: "assistant", type: "thought", content: "" },
  { role: "assistant", type: "tool_use", ... },
  { role: "tool", content: ... }
]
```

Adapter 要把这种格式转为：

* OpenAI 的 structure
* Claude 的 structure

---

# 🟩 **总结：Adapter “必须支持”工具调用、多轮对话、流式、结构化输出**

最终结论：

| 能力          | 要支持吗？                  | 说明 |
| ----------- | ---------------------- | -- |
| 文本生成        | ✔ 必须                   |    |
| 结构化输出       | ✔ 必须                   |    |
| 工具调用        | ✔ 必须（你要做 ReAct Agent）  |    |
| 流式输出        | ✔ 必须                   |    |
| 多轮对话（上下文记忆） | ✔ 必须（ReAct dependency） |    |
| 调用成本统计      | ✔ 必须                   |    |
| 图像、多模态      | 可选                     |    |

---

# 🔥 统一工具调用格式（极重要）

建议定义内部统一格式（你系统内部）：

```ts
interface ToolCall {
  type: "tool_call";
  name: string;
  arguments: Record<string, any>;
}

interface ToolResult {
  type: "tool_result";
  name: string;
  result: any;
}
```

然后让 Adapter 去负责：

* 将这个格式转为 OpenAI function_call
* 或 Anthropic tool_use

这样你的 Agent Runtime 永远不需要知道底层模型是谁。
