# Spec: Ralph OpenClaw Backend

This document defines the architecture for replacing Ralph's fragile `pexpect`-based CLI wrapper with a robust **OpenClaw Sub-Agent** backend.

## 1. Motivation

Current Ralph uses `pexpect` to drive `claude` CLI.
*   **Problem:** PTY parsing is flaky (colors, spinners, prompts).
*   **Problem:** Single-threaded (one CLI session at a time).
*   **Problem:** Host context leakage (running directly on host shell).

New Ralph will use OpenClaw `sessions spawn`.
*   **Benefit:** Structured JSON IO.
*   **Benefit:** Parallel execution (spawn N sub-agents).
*   **Benefit:** Sandboxed sessions (isolated history).

## 2. Architecture

### 2.1 The Agent Interface

We introduce an abstract base class `AgentBackend`:

```python
class AgentBackend(Protocol):
    def run(self, task: str, model: str | None = None) -> AgentResult:
        ...

@dataclass
class AgentResult:
    exit_code: int  # 0 = success, 1 = failure
    output: str     # Full transcript
    files_changed: list[str] # Detected file modifications
```

### 2.2 OpenClaw Implementation

The `OpenClawBackend` uses the `openclaw` CLI (or API via IPC) to spawn sessions.

**Command:**
```bash
openclaw sessions spawn --agent <agent_id> --task "<prompt>" --json
```

**Workflow:**
1.  **Spawn:** Ralph calls `openclaw sessions spawn`.
2.  **Wait:** OpenClaw manages the conversation loop.
3.  **Result:** OpenClaw returns a JSON result:
    ```json
    {
      "sessionId": "sess_123",
      "status": "completed",
      "result": "I have updated the files...",
      "tool_calls": [
        {"tool": "write", "args": {"file_path": "src/main.py"}}
      ]
    }
    ```
4.  **Parse:** Ralph parses the result.
    *   `exit_code`: 0 if status "completed", 1 if "failed".
    *   `files_changed`: Extracted from `tool_calls` history (specifically `write`/`edit`).

### 2.3 Configuration

Add to `ralph/config.py`:

```python
class Config:
    backend: Literal["cli", "openclaw"] = "cli"
    openclaw_agent_id: str = "coding-agent"  # The ID of the sub-agent profile to use
```

## 3. Implementation Plan

### Phase 1: The Wrapper
Create `src/ralph/backends/openclaw.py`.
Implement `run()` to subprocess call `openclaw sessions spawn`.

### Phase 2: The Switch
Update `ralph start` to accept `--backend openclaw`.

```bash
ralph start prd.json --backend openclaw
```

### Phase 3: Parallelism (Future)
Since `sessions spawn` is non-blocking (if we use the API), Ralph can eventually spawn multiple items at once:
`ralph start prd.json --parallel 3`

## 4. Risks & Mitigations

*   **Risk:** Context Window. Sub-agents start fresh. They don't know previous items.
    *   *Mitigation:* Ralph must include relevant context (file summaries, PRD status) in the `task` prompt for every item.
*   **Risk:** Tool Access. Sub-agents need write access to the repo.
    *   *Mitigation:* Ensure the `coding-agent` profile has `fs` permissions for the project root.

## 5. Next Steps

1.  Create `AgentBackend` interface (refactor existing code).
2.  Implement `OpenClawBackend`.
3.  Test with a simple PRD.
