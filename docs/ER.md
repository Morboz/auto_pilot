下面给你 **完整的数据库 ER 图（Agent / Tool / Task / Logs）**，这是为“自主任务执行 Agent 框架”设计的最合理、可扩展的数据库结构，适用于 PostgreSQL / MySQL / SQLite。

图中包含：

* **Agent 配置**
* **Tool 注册表**
* **Agent–Tool 绑定（多对多）**
* **Task 任务实例**
* **Task Logs（ReAct 风格 step logs）**
* **Tool Execution Logs（单独跟踪每次工具调用）**

### 重要更新
**agent_tools 表新增 `permissions` 字段**：支持 per-agent-per-tool 的精细化权限配置，与 AutoPilot Tool System 架构完全对齐。

下面给你 **ASCII 风格 ER 图 + 每个表的详细字段解释**。

---

# 🧩 **数据库 ER 图（核心模块）**

```
┌────────────────────┐          ┌────────────────────┐
│      agents        │ 1       *│    agent_tools     │*       1 ┌───────────────────┐
│────────────────────│----------│────────────────────│----------│       tools       │
│ id (PK)            │          │ id (PK)            │          │───────────────────│
│ name               │          │ agent_id (FK)      │          │ id (PK)           │
│ model              │          │ tool_id  (FK)      │          │ name              │
│ system_prompt      │          └────────────────────┘          │ type              │
│ created_at         │                                          │ description       │
│ updated_at         │                                          │ schema (JSON)     │
└────────────────────┘                                          │ created_at        │
                                                                │ updated_at        │
                                                                └───────────────────┘

          1 ┌────────────────────┐  *
agents ─────────── tasks ────────────────────┐
            │ id (PK)            │           │
            │ agent_id (FK)      │           │
            │ input_text         │           │
            │ status             │           │
            │ result_text        │           │
            │ meta (JSON)        │           │
            │ created_at         │           │
            │ updated_at         │           │
            └────────────────────┘           │
                                             │
                                   1         │       *
                                 ┌───────────────────────────┐
                                 │        task_logs          │
                                 │───────────────────────────│
                                 │ id (PK)                   │
                                 │ task_id (FK)              │
                                 │ step_number               │
                                 │ type (thought/action/obs) │
                                 │ content (TEXT/JSON)       │
                                 │ created_at                │
                                 └───────────────────────────┘


                         1             ┌──────────────────────────┐             *
tasks ──────────────────┼──────────────│   tool_execution_logs    │
                                       │──────────────────────────│
                                       │ id (PK)                 │
                                       │ task_id (FK)            │
                                       │ tool_id (FK)            │
                                       │ input_params (JSON)     │
                                       │ output (JSON)           │
                                       │ error_message           │
                                       │ created_at              │
                                       └──────────────────────────┘
```

---

# 🟥 **表 1：agents（自定义 Agent 配置）**

### 用途

存储每个用户创建的 Agent（类似 Claude Projects 或 Claude Code 的 Agent Profile）。

### 字段定义

| 字段            | 类型       | 说明                |
| ------------- | -------- | ----------------- |
| id            | PK, UUID | Agent ID          |
| name          | string   | 可读名称              |
| model         | string   | 使用模型名称（如 gpt-5-1） |
| system_prompt | text     | Agent 的人格与指令      |
| created_at    | datetime | 创建时间              |
| updated_at    | datetime | 更新时间              |

---

# 🟦 **表 2：tools（工具注册表）**

### 用途

存储开发者注册的 Tool。

### 字段定义

| 字段          | 类型                            | 说明                       |
| ----------- | ----------------------------- | ------------------------ |
| id          | PK, UUID                      | Tool ID                  |
| name        | string                        | 工具名字（如 HTTP GET）         |
| type        | enum(http/sql/web3/js/custom) | 工具类型                     |
| description | text                          | 工具说明                     |
| schema      | JSON                          | 工具参数 schema（JSON Schema） |
| created_at  | datetime                      | 创建时间                     |
| updated_at  | datetime                      | 更新时间                     |

---

# 🟩 **表 3：agent_tools（多对多关联 + 权限配置）**

### 用途

一个 Agent 可以绑定多个 Tools。
一个 Tool 也可以被多个 Agent 共享。

**核心功能**：为每个 Agent 配置独立的 Tool 权限（JSON 格式），实现精细化权限控制。

### 字段定义

| 字段          | 类型             | 说明                              |
| ----------- | -------------- | --------------------------------- |
| id          | PK, UUID       | 记录 ID                           |
| agent_id    | FK → agents.id | 关联的 agent                      |
| tool_id     | FK → tools.id  | 关联的 tool                       |
| permissions | JSON           | Tool 权限配置（可选，为 null 时使用默认权限） |
| created_at  | datetime       | 创建时间                           |
| updated_at  | datetime       | 更新时间                           |

### permissions JSON 结构

```json
{
  "filesystem": {
    "allowed_paths": ["/tmp", "/workspace"],
    "denied_paths": ["/etc", "/home", "/root"],
    "operations": ["read", "write"],
    "recursive_access": true
  },
  "network": {
    "enabled": false,
    "allowed_hosts": ["*.api.openai.com", "localhost"],
    "allowed_ports": [80, 443],
    "denied_hosts": ["*"],
    "max_connections": 10
  },
  "resources": {
    "max_cpu_percent": 50.0,
    "max_memory_mb": 256,
    "max_disk_space_mb": 512,
    "max_execution_time_seconds": 10.0,
    "max_processes": 5,
    "max_file_size_mb": 100
  },
  "security": {
    "enable_sandbox": true,
    "enable_output_sanitization": true,
    "enable_audit_logging": true,
    "allowed_imports": ["os", "json"],
    "blocked_imports": ["subprocess", "socket"]
  },
  "custom_permissions": {}
}
```

**权限获取优先级**：
1. agent_tools.permissions (JSON) - 最高优先级
2. 代码中通过 `PermissionManager.set_tool_permissions()` 设置的权限
3. `PermissionManager._default_permissions` - 默认权限

> 也可用联合主键 `(agent_id, tool_id)`，但 UUID 更灵活。

---

# 🟧 **表 4：tasks（任务）**

### 用途

存储每次用户触发的任务执行（类似一次 Claude 调用）。

### 字段定义

| 字段          | 类型                                   | 说明                       |
| ----------- | ------------------------------------ | ------------------------ |
| id          | PK, UUID                             | Task ID                  |
| agent_id    | FK → agents.id                       | 使用的 agent                |
| input_text  | text                                 | 用户输入（如“请分析 ETH 价格”）      |
| status      | enum(pending/running/failed/success) |                          |
| result_text | text or JSON                         | 最终结果                     |
| meta        | JSON                                 | 任务额外信息（如 riskLevel=high） |
| created_at  | datetime                             |                          |
| updated_at  | datetime                             |                          |

---

# 🟨 **表 5：task_logs（ReAct 步骤日志）**

### 用途

存储 Agent 的 **thought / action / observation** 思考过程。

前端 UI 用这个展示「执行过程」。

### 字段定义

| 字段          | 类型                                 | 说明   |
| ----------- | ---------------------------------- | ---- |
| id          | PK, UUID                           |      |
| task_id     | FK → tasks.id                      |      |
| step_number | int                                | 递增步数 |
| type        | enum(thought, action, observation) |      |
| content     | TEXT/JSON                          | 具体内容 |
| created_at  | datetime                           |      |

**示例内容：**

**thought**

```json
"我需要查询当前 ETH 价格"
```

**action**

```json
{
  "tool": "tool_http",
  "input": {"url": "..."}
}
```

**observation**

```json
{"price": 2486.27}
```

---

# 🟫 **表 6：tool_execution_logs（每次工具实际执行的审计表）**

### 用途

每次工具调用都记录一条 Log，用于：

* 安全审计
* 事后回放
* 工具异常分析

### 字段定义

| 字段            | 类型            | 说明        |
| ------------- | ------------- | --------- |
| id            | PK, UUID      |           |
| task_id       | FK → tasks.id | 属于哪个 Task |
| tool_id       | FK → tools.id | 调用的 Tool  |
| input_params  | JSON          | 调用参数      |
| output        | JSON          | 工具返回      |
| error_message | string?       | 异常信息（如失败） |
| created_at    | datetime      |           |

---

# 🔐 **表 7：agent_tools.permissions 的设计优点**

### ✔ 支持 per-agent-per-tool 的精细化权限控制

通过 `agent_tools.permissions` 字段，可以实现：

**场景 1：不同 Agent 对同一工具有不同权限**
```
Agent: "debug-agent"
Tool: "file_operations"
Permissions: { filesystem: { allowed_paths: ["*"] } }
# 调试 Agent 可以访问所有文件

Agent: "public-agent"
Tool: "file_operations"
Permissions: { filesystem: { allowed_paths: ["/tmp", "/public"] } }
# 公开 Agent 只能访问受限目录
```

**场景 2：权限动态配置，无需修改代码**
- 通过 Web UI 修改 Agent 的工具权限
- 实时生效，无需重启服务
- 适合多租户场景

### ✔ 权限配置的灵活性

**三级权限回退机制**：
1. **数据库配置**（最高优先级）- agent_tools.permissions
2. **代码配置** - PermissionManager.set_tool_permissions()
3. **默认配置** - PermissionManager._default_permissions

**这样设计的好处**：
- 既有数据库的动态性
- 又保留了代码配置的版本控制能力
- 适合不同场景：开发环境用代码，生产环境用数据库

### ✔ 支持 Tool Permission 的版本化

```sql
-- 查看 Agent 的工具权限变更历史
SELECT
    agent_id,
    tool_id,
    permissions,
    updated_at
FROM agent_tools
WHERE agent_id = 'agent_123' AND tool_id = 'tool_456'
ORDER BY updated_at DESC;
```

### ✔ 与 AutoPilot Tool System 架构完全一致

- `arch-spec.md` 中 Tool System 包含 4 个核心组件
- `TOOL_SYSTEM.md` 详细描述了 Permission Manager
- ER 图现在完整映射了架构设计

### ✔ 数据库设计保持简洁

- 使用 JSON 字段存储复杂的权限结构
- 避免创建多个细粒度的权限表（如 filesystem_permissions, network_permissions）
- 与 Pydantic 的 ToolPermissions 模型完美对应

---

# 🧠 ER 图设计的整体优点

### ✔ 自动化 Agent 的所有数据都可追踪

### ✔ 工具调用能独立审计（最重要）

### ✔ 与 Claude API 或 OpenAI ReAct 执行模型 100% 对齐

### ✔ 可扩展到「多 Agent 互相调用」「Workflow DAG」

### ✔ UI 可实时展示任务执行每一步

### ✔ 支持精细化权限控制（新增）
