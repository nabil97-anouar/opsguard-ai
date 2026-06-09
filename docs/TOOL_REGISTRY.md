# TOOL_REGISTRY.md — OpsGuard AI MCP-Style Tool Registry

## Design Principles

1. **No arbitrary shell execution.** No tool executes raw shell commands.
2. **Allowlist enforcement.** Only tools in the allowlist can be called by the agent.
3. **Typed inputs and outputs.** Every tool call validated against Pydantic schemas before execution and after response.
4. **Audit every call.** Every tool call is logged to the `tool_calls` table atomically.
5. **Untrusted outputs.** All tool outputs are tagged `untrusted` until schema-validated. Tool output content (free-text fields) is injection-scanned before passing to the LLM.
6. **Sandboxed.** In demo/dev mode, all tools return mock data. In production, tools call read-only monitoring APIs with no write access.
7. **Dangerous actions are never in the executable allowlist.** They appear only as human-approval recommendations.

---

## Tool Allowlist (Executable)

```python
TOOL_ALLOWLIST = [
    "search_logs",
    "get_node_metrics",
    "get_running_jobs",
    "check_network_connections",
    "query_past_incidents",
    "retrieve_runbook",
    "create_ticket_draft",
]
```

---

## Executable Tools

---

### Tool: `search_logs`

**Purpose:** Search recent log entries for a specific node, service, or time window. Returns structured log entries.

**Trust level:** Untrusted (log content can contain injection vectors)

**Allowed use:**
- Searching for specific error patterns, kernel messages, NVML errors, job failures
- Time-bounded queries on a single node or service

**Blocked use:**
- Bulk export of all logs
- Search queries containing shell metacharacters
- Free-form log analysis beyond pattern matching

**Input schema:**
```python
class SearchLogsInput(BaseModel):
    node_id: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9\-_\.]+$")
    query_terms: list[str] = Field(..., max_items=10)
    time_window_minutes: int = Field(default=60, ge=1, le=1440)
    max_results: int = Field(default=50, ge=1, le=200)
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None
```

**Output schema:**
```python
class LogEntry(BaseModel):
    timestamp: str
    level: str
    source: str
    message: str            # injection-scanned before passing to LLM

class SearchLogsOutput(BaseModel):
    node_id: str
    total_found: int
    entries: list[LogEntry]
    query_duration_ms: int
    truncated: bool
```

**Example call:**
```json
{
  "tool_name": "search_logs",
  "args": {
    "node_id": "gpu-node-04",
    "query_terms": ["ECC", "NVML error", "memory overflow"],
    "time_window_minutes": 120,
    "max_results": 50
  }
}
```

**Example response:**
```json
{
  "node_id": "gpu-node-04",
  "total_found": 3,
  "entries": [
    {
      "timestamp": "2024-11-15T08:14:32Z",
      "level": "ERROR",
      "source": "kernel",
      "message": "NVIDIA NVML error on GPU 3: ECC memory error — uncorrected"
    }
  ],
  "query_duration_ms": 23,
  "truncated": false
}
```

**Audit log fields:** `tool_name`, `node_id`, `query_terms`, `time_window_minutes`, `total_found`, `agent_run_id`, `step_id`, `timestamp`

**Security risks:**
- Log content can contain injected instructions
- Over-broad queries could return sensitive data

**Mitigation:**
- Each log entry's `message` field is injection-scanned before LLM context inclusion
- Query terms validated: no shell metacharacters, no `; & | > < $`
- `node_id` pattern-validated

---

### Tool: `get_node_metrics`

**Purpose:** Retrieve current resource utilization metrics for a specific node: CPU, memory, GPU, disk, temperature.

**Trust level:** Untrusted (free-text fields in response scanned)

**Allowed use:**
- Single node metric retrieval for incident analysis

**Blocked use:**
- Bulk metrics export for all nodes
- Continuous metric streaming

**Input schema:**
```python
class GetNodeMetricsInput(BaseModel):
    node_id: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9\-_\.]+$")
    metrics: list[Literal["cpu", "memory", "gpu", "disk", "temperature", "network"]] = Field(
        default=["cpu", "memory", "gpu"]
    )
```

**Output schema:**
```python
class GPUMetrics(BaseModel):
    gpu_id: int
    utilization_pct: float
    memory_used_gb: float
    memory_total_gb: float
    temperature_c: float
    ecc_errors_volatile: int
    ecc_errors_aggregate: int

class NodeMetricsOutput(BaseModel):
    node_id: str
    timestamp: str
    cpu_utilization_pct: float
    memory_used_gb: float
    memory_total_gb: float
    disk_used_gb: Optional[float]
    disk_total_gb: Optional[float]
    gpu_metrics: Optional[list[GPUMetrics]]
    network_rx_mbps: Optional[float]
    network_tx_mbps: Optional[float]
    status: Literal["online", "degraded", "offline"]
    alerts_active: list[str]    # injection-scanned
```

**Example call:**
```json
{
  "tool_name": "get_node_metrics",
  "args": {
    "node_id": "gpu-node-04",
    "metrics": ["gpu", "memory", "temperature"]
  }
}
```

**Example response:**
```json
{
  "node_id": "gpu-node-04",
  "timestamp": "2024-11-15T10:30:00Z",
  "cpu_utilization_pct": 45.2,
  "memory_used_gb": 120.4,
  "memory_total_gb": 256,
  "gpu_metrics": [
    {
      "gpu_id": 3,
      "utilization_pct": 99.7,
      "memory_used_gb": 79.8,
      "memory_total_gb": 80,
      "temperature_c": 84.0,
      "ecc_errors_volatile": 12,
      "ecc_errors_aggregate": 47
    }
  ],
  "status": "degraded",
  "alerts_active": ["GPU_MEM_OVERFLOW_GPU3"]
}
```

**Security risks:** Debug/status fields can carry injection vectors
**Mitigation:** All string list fields scanned; structured numeric fields safe by type

---

### Tool: `get_running_jobs`

**Purpose:** Retrieve current running jobs on a node or in the cluster (Slurm-style).

**Trust level:** Untrusted (job names and user names can contain adversarial content)

**Input schema:**
```python
class GetRunningJobsInput(BaseModel):
    node_id: Optional[str] = Field(default=None, max_length=100)
    user_filter: Optional[str] = Field(default=None, max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    max_results: int = Field(default=20, ge=1, le=100)
    include_completed: bool = False
```

**Output schema:**
```python
class JobRecord(BaseModel):
    job_id: str
    user: str
    node: str
    partition: str
    state: Literal["RUNNING", "PENDING", "COMPLETING", "FAILED", "CANCELLED"]
    start_time: str
    elapsed_seconds: int
    gpu_ids_used: list[int]
    memory_requested_gb: float
    name: str   # injection-scanned

class GetRunningJobsOutput(BaseModel):
    total_running: int
    jobs: list[JobRecord]
    query_node: Optional[str]
    timestamp: str
```

**Example response:**
```json
{
  "total_running": 2,
  "jobs": [
    {
      "job_id": "12345",
      "user": "researcher1",
      "node": "gpu-node-04",
      "partition": "gpu",
      "state": "RUNNING",
      "start_time": "2024-11-15T04:00:00Z",
      "elapsed_seconds": 23400,
      "gpu_ids_used": [3],
      "memory_requested_gb": 64,
      "name": "llm-training-run-42"
    }
  ]
}
```

---

### Tool: `check_network_connections`

**Purpose:** Check active network connections and open ports for a specific node. Read-only. Does not perform port scanning.

**Trust level:** Untrusted

**Blocked use:**
- Active port scanning
- External IP resolution
- DNS queries to external hosts

**Input schema:**
```python
class CheckNetworkConnectionsInput(BaseModel):
    node_id: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9\-_\.]+$")
    include_external: bool = Field(default=False)
    suspicious_only: bool = Field(default=False)
```

**Output schema:**
```python
class NetworkConnection(BaseModel):
    local_address: str
    remote_address: str
    state: str
    process: str    # injection-scanned
    is_suspicious: bool
    suspicion_reason: Optional[str]

class CheckNetworkConnectionsOutput(BaseModel):
    node_id: str
    total_connections: int
    suspicious_count: int
    connections: list[NetworkConnection]
    timestamp: str
```

---

### Tool: `query_past_incidents`

**Purpose:** Query the PostgreSQL incidents table for past similar incidents. Used for pattern matching and resolution history.

**Trust level:** Trusted (internal database)

**Input schema:**
```python
class QueryPastIncidentsInput(BaseModel):
    keywords: list[str] = Field(..., max_items=10)
    infrastructure_type: Optional[str] = None
    severity_filter: Optional[str] = None
    days_back: int = Field(default=90, ge=1, le=365)
    max_results: int = Field(default=10, ge=1, le=50)
```

**Output schema:**
```python
class PastIncidentSummary(BaseModel):
    incident_id: str
    title: str
    severity: str
    root_cause: str
    resolution: str
    infrastructure_type: str
    resolved_at: str
    relevance_score: float

class QueryPastIncidentsOutput(BaseModel):
    total_found: int
    incidents: list[PastIncidentSummary]
```

---

### Tool: `retrieve_runbook`

**Purpose:** Retrieve a specific runbook by ID or by keyword match. Returns structured runbook content with section navigation.

**Trust level:** Trusted if `injection_scan_result = "clean"`, Untrusted otherwise

**Input schema:**
```python
class RetrieveRunbookInput(BaseModel):
    runbook_id: Optional[str] = None
    alert_type: Optional[str] = None
    infrastructure_type: Optional[str] = None
```

**Output schema:**
```python
class RunbookSection(BaseModel):
    heading: str
    content: str    # injection-scanned even for trusted docs
    step_number: Optional[int]

class RetrieveRunbookOutput(BaseModel):
    runbook_id: str
    title: str
    version: str
    trust_level: str
    injection_scan_result: str
    sections: list[RunbookSection]
    retrieved_at: str
```

---

### Tool: `create_ticket_draft`

**Purpose:** Create a structured draft incident ticket in the database. Does NOT call any external ticketing system.

**Trust level:** N/A (creates internal record)

**Blocked use:**
- Calling external Jira/ServiceNow/PagerDuty APIs directly (that requires human confirmation)

**Input schema:**
```python
class CreateTicketDraftInput(BaseModel):
    alert_id: str
    title: str = Field(..., max_length=500)
    severity: Literal["info", "warning", "error", "critical"]
    description: str = Field(..., max_length=5000)
    suggested_actions: list[str] = Field(..., max_items=10)
    evidence_citations: list[str] = Field(..., max_items=20)
    kill_chain_stage: Optional[str] = None
    assigned_team: str = Field(default="ops-team", max_length=100)
```

**Output schema:**
```python
class CreateTicketDraftOutput(BaseModel):
    ticket_draft_id: str
    status: str     # "created"
    title: str
    created_at: str
```

---

## Simulated Dangerous Actions (Recommendation Only)

These actions **NEVER execute directly**. They appear only as `requires_human_approval` entries in the recommendation object. The agent's `plan_tool_calls` node is explicitly blocked from placing these in `planned_tool_calls`.

| Action | Description | Risk | Human Approval Required |
|---|---|---|---|
| `cancel_job` | Cancel a running Slurm/batch job | Data loss, user disruption | Always |
| `drain_node` | Remove a node from cluster scheduling | Service disruption | Always |
| `block_user` | Revoke a user's cluster access | Access disruption, HR/legal | Always |
| `isolate_node` | Network-isolate a node | Service disruption, cascading failures | Always |
| `disable_service` | Stop a running service | Service outage | Always |

**How they appear in recommendations:**
```json
{
  "suggested_actions": [
    {
      "action_type": "requires_human_approval",
      "action": "drain_node",
      "target": "gpu-node-04",
      "rationale": "GPU 3 is experiencing uncorrected ECC errors indicating hardware failure. Node should be drained to prevent job failures and data corruption.",
      "supporting_evidence": ["EVIDENCE-1", "TOOL-1"],
      "tool_name": "drain_node",
      "severity": "high"
    }
  ]
}
```

These appear in the human approval panel with APPROVE / REJECT controls and full rationale. They are never passed to the tool executor.

---

## Tool Registry Implementation

```python
from typing import Callable
from pydantic import BaseModel

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    trust_level: str
    handler: Callable    # points to implementation or mock

TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "search_logs": ToolDefinition(
        name="search_logs",
        description="Search recent log entries for a node",
        input_schema=SearchLogsInput,
        output_schema=SearchLogsOutput,
        trust_level="untrusted",
        handler=search_logs_handler,
    ),
    # ... other tools
}

def execute_tool(tool_name: str, args: dict, agent_run_id: str, step_id: str) -> dict:
    if tool_name not in TOOL_ALLOWLIST:
        raise ToolNotAllowedError(f"Tool '{tool_name}' is not in allowlist")
    
    definition = TOOL_REGISTRY[tool_name]
    validated_input = definition.input_schema(**args)
    
    result = definition.handler(validated_input)
    
    validated_output = definition.output_schema(**result)
    
    # Audit log
    log_tool_call(
        tool_name=tool_name,
        input_args=validated_input.model_dump(),
        output=validated_output.model_dump(),
        trust_level=definition.trust_level,
        agent_run_id=agent_run_id,
        step_id=step_id,
    )
    
    return validated_output.model_dump()
```
