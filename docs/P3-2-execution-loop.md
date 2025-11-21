下面我会从 **“路线选择建议” → “详细设计”** 两部分来回答，帮助你决定先做 3.1、3.2 还是 3.3，以及给你下一个模块的完整设计文档级别内容。

---

# ✅ 一、下一步应该先做哪个模块？

你已经完成了 **3.4 LLM Adapter（计划/工具调用/多轮能力）**，此时 Agent 的“核心大脑”已经齐了，现在三个模块之间的依赖关系如下：

### **依赖顺序图**

```
LLM Adapter  ←  Execution Loop  ←  Controller
                 ↑
             State Manager
```

### ✨ 最推荐的开发顺序：

## **第一优先：3.2 Execution Loop（执行循环）**

理由：

* 你已经有 LLM Adapter，但没有 Execution Loop，LLM 现在没有地方“跑起来”。
* Execution Loop 是真正让 Agent 自主执行任务的核心，“Plan → Act → Observe” 就在这里实现。
* 先做 Execution Loop 才能快速验证你的 LLM Adapter 是否真的可用，也能更早跑出一个 Demo。

> 📌 **这一步做完，你的 Agent 就能自主执行任务（尽管还不能 Pause/Resume）。非常关键。**

---

## **第二优先：3.3 State Manager（状态管理）**

理由：

* Execution Loop 需要读写 Agent 的执行状态（halt/crashed/running）。
* State Manager 抽象状态存储，让未来可以从数据库恢复任务。
* 在真正实现 Pause / Resume、Checkpoint 之前，State Manager 必须存在。

---

## **第三优先：3.1 Controller（启动/停止/恢复接口）**

理由：

* Controller 依赖 Execution Loop 和 State Manager。
* 没有它 Agent 还是能跑，只是没有“交互式控制开关”。

---

# 🎯 结论（你应该现在做的）

> **先实现：3.2 Execution Loop**
> 其次：3.3 State Manager
> 最后：3.1 Controller（UI 控制台/API）

---

---

# ✅ 二、接下来给你：

## **Execution Loop（3.2）+ State Manager（3.3）+ Controller（3.1）三个模块的完整详细设计**

你现在应该先做 3.2，但我一次性把三个模块的详细设计都给你，方便你完整规划。

---

# -----------------------------------

# 🧠 3.2 Execution Loop —— 详细设计

# -----------------------------------

## ✔ 设计目标

实现 Claude Code 的核心行为：

```
Plan  →  Execute Tool  →  Observe  →  Re-plan
```

支持：

* 自动调用工具
* 任务状态更新
* 错误处理 / 超时 / 重试
* 多轮思考
* 任务最终产出

---

## ✔ 核心流程图（Execution Loop）

```
┌─────────────┐
│ Load Task    │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│ while task not finished: │
│   state = StateManager   │
│                           │
│   step = LLM.plan(state)  │
│                           │
│   if step.tool_call:      │
│       result = Tool.run() │
│   else:                   │
│       result = step.text  │
│                           │
│   StateManager.append(...)│
│                           │
│   if step.final: break    │
└───────────────────────────┘
```

---

## ✔ Execution Loop API 规格

### **模块类名**

`AgentExecutor`

### **主要方法**

```python
class AgentExecutor:
    def run(task_id: str):
    def step():
    def handle_tool_call(call):
    def handle_error(e):
```

---

## ✔ 事件回调（可推给 WebSocket）

* on_step_start
* on_tool_executed
* on_llm_response
* on_error
* on_finished

---

## ✔ 错误处理策略

| 错误类型     | 行为                        |
| -------- | ------------------------- |
| 工具调用失败   | 重试 N 次 → 记录错误 → 返回 LLM 处理 |
| LLM 回复无效 | 自动修正提示，重新询问               |
| 死循环      | 每个任务步骤上限（如 50 steps）      |
| 超时       | 任务暂停并可恢复                  |

---

# -----------------------------------

# 🧠 3.3 State Manager —— 详细设计

# -----------------------------------

## ✔ 设计目标

* 持久化 Agent 的所有运行状态
* 支持暂停 / 恢复 / 回放
* 抽象状态读写，Execution Loop 不需要考虑 DB 实现细节

---

## ✔ 状态类型

| 状态              | 描述                                            |
| --------------- | --------------------------------------------- |
| execution_state | running / paused / stopped / finished / error |
| memory_state    | LLM 可见的对话上下文                                  |
| tool_history    | 工具调用历史                                        |
| final_output    | 最终结果                                          |

---

## ✔ State Manager 类设计

```python
class StateManager:
    def load_state(task_id): → AgentState
    def save_state(task_id, state: AgentState)
    def append_step(task_id, step_data)
    def update_execution_status(task_id, status)
```

---

## ✔ 数据结构（可映射数据库）

```python
class AgentState:
    task_id: str
    messages: List[Message]
    tool_calls: List[ToolCallRecord]
    execution_status: str
    current_step: int
    final_output: Optional[str]
```

---

## ✔ 数据库表链接（你已有 ER 图，可以直接映射）

* tasks
* agent_states
* agent_logs
* tool_invocations

---

# -----------------------------------

# 🧰 3.1 Controller（REST + WebSocket）

# -----------------------------------

## ✔ 职责

负责“外部控制”，而不是执行逻辑：

* Start Task
* Pause Task
* Resume Task
* Stop Task
* Get Task State
* Stream Task Logs (WebSocket)

---

## ✔ REST API 设计

### **POST /agents/{agent_id}/tasks**

启动任务

```json
{
  "input": "帮我自动化检查钱包余额并决定是否 rebalance"
}
```

返回 `task_id`

---

### **POST /tasks/{task_id}/pause**

暂停执行

### **POST /tasks/{task_id}/resume**

恢复执行

### **POST /tasks/{task_id}/stop**

强制停止

---

### **GET /tasks/{task_id}**

获取当前状态（包含 LLM memory、步骤、工具调用历史等）

---

## ✔ WebSocket 接口

### `ws://.../tasks/{task_id}/stream`

推送事件：

```json
{ "event": "step_started", "step": 5 }
{ "event": "llm_response", "content": "我的计划是..." }
{ "event": "tool_result", "tool": "CheckBalance", "result": { ... } }
{ "event": "finished", "output": "最终结果" }
```

这可以实现 Claude Code 那种实时日志 UI。

---

# 🎯 三、你应该现在做什么？（强烈建议）

你现在已经有：

### ✔ LLM Adapter

你应该现在做：

---

# ✔ 第一步（立即进行）

# **实现模块 3.2 Execution Loop（AgentExecutor）**

因为：

* 没有它你的 Agent 仍然不会动
* 它是整个系统的心脏
* 实现它能验证 Tools + LLM Adapter 的设计是否正确
* UI、控制器、状态恢复…统统依赖它

我已经给你了完整的设计图，你只要照着写就能跑。
