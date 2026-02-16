# The Factory Manual: Autonomous Engineering Loop

> "We are software gods building the future." — Jon McBee

## 1. The Philosophy
We are moving from **Open Loop** (Human writes code, hopes it works) to **Closed Loop** (Agent writes code, Simulation proves it works).

*   **Builder:** `Spark Swarm` (Ralph). The chaotic creative force.
*   **Validator:** `The Factory` (Foreman). The cold, hard reality check.
*   **State:** `CXDB`. The single source of truth.

## 2. The Components

### 2.1 Spark Swarm (Ralph)
**Role:** The General / Builder.
**Repo:** `zoidbergclawd/sisyphus`
**Command:** `ralph start prd.json`

Ralph reads a PRD (Product Requirements Document) and orchestrates AI agents to implement it item-by-item.

**Key Features:**
*   **Checkpoints:** Auto-commits after every item.
*   **Hooks:** Runs tests and validators before committing.
*   **Backends:**
    *   `cli` (Legacy): Wraps `claude` CLI via pexpect.
    *   `openclaw` (Modern): Spawns isolated OpenClaw sub-agents.

### 2.2 The Factory (Foreman)
**Role:** The Validator / Simulation.
**Repo:** `zoidbergclawd/the-factory`
**Command:** `foreman run --scenario <file>`

Foreman spins up "Twins" (simulated hardware/software) and runs them through a deterministic "Scenario".

**Key Features:**
*   **Twins:** Digital replicas of systems (e.g., `MockOhmX`, `MockGithub`).
*   **Scenarios:** A timeline of events (e.g., "Network Storm at t=5s").
*   **Adversarial:** Actively tries to break the code.

## 3. The Workflow

### Step 1: The Plan (PRD)
Create a `prd.json` defining what to build. Add a `validator` hook.

```json
{
  "project": "Risk Radar",
  "items": [...],
  "hooks": {
    "validator": "foreman run --scenario stress_test.json"
  }
}
```

### Step 2: The Build (Ralph)
Run Ralph with the OpenClaw backend.

```bash
ralph start prd.json --backend openclaw --validator "foreman run ..."
```

**The Loop:**
1.  **Agent:** Writes code for Item 1.
2.  **Ralph:** Runs unit tests (`pytest`).
3.  **Ralph:** Runs Validator (`foreman`).
    *   **PASS:** Ralph commits code, updates state, moves to Item 2.
    *   **FAIL:** Ralph captures the failure log, feeds it back to the Agent, and says "Fix it." (Retries).

### Step 3: The Reality (Deploy)
Once all items pass The Factory, the code is merging-ready.

## 4. Economic Strategy
Using API keys (OpenClaw) costs money per token.
*   **Fail Fast:** The Factory prevents agents from "drifting" into expensive hallucinations.
*   **Checkpoint:** Resume from the last known good state. Never rebuild from zero.
*   **Model Tiering:** Use cheaper models for drafting, expensive models for architecture.

## 5. Quick Reference

**Start a Run:**
```bash
ralph start my-feature.json --backend openclaw
```

**Resume a Run:**
```bash
ralph resume
```

**Create a PR:**
```bash
ralph pr
```

**Run a Simulation:**
```bash
cd ~/Projects/the-factory
python3 foreman/foreman.py run --scenario scenarios/network_storm.json
```
