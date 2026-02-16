# Strategy: Closing the Loop with The Factory

This document defines the strategy for integrating **Spark Swarm** (Ralph) with **The Factory** (Foreman) to achieve a closed-loop autonomous engineering workflow.

## 1. The Concept

The goal is to move from "Open Loop" (Code -> Commit) to "Closed Loop" (Code -> Validate -> Commit/Retry).

- **Builder:** Spark Swarm (Ralph) writes code.
- **Validator:** The Factory (Foreman) runs simulated scenarios against that code.
- **Gatekeeper:** Ralph's new `--validator` hook prevents code from being committed unless it passes the simulation.

## 2. Implementation: The Validator Hook

We are adding a `--validator <command>` flag to `ralph start`.

```bash
ralph start prd.json --validator "foreman run --scenario network_storm.json"
```

### Flow
1.  **Agent Phase:** Agent writes code for Item X.
2.  **Test Phase:** Ralph runs unit tests (existing behavior).
3.  **Validation Phase:** Ralph runs the validator command.
    *   **Pass (Exit 0):** Commit, Checkpoint, Proceed.
    *   **Fail (Exit != 0):**
        *   Capture `stdout/stderr` from validator.
        *   **DO NOT** commit.
        *   Feed failure output back to Agent as feedback.
        *   Agent retries (decrementing retry counter).

## 3. Testing Strategy (The "Toy World")

Since The Factory is complex, we will validate this workflow using a **Mock Validator** script first.

### 3.1 Components
1.  **`mock_foreman.py`**: A simple script that simulates The Factory.
    *   Accepts `--scenario <name>`.
    *   Checks for specific files/strings in the codebase.
    *   Returns 0 (Pass) or 1 (Fail) with a reason.
    *   *Scenario:* "Check if `magic_token.txt` exists and contains '42'".

2.  **`test_loop.json`** (PRD):
    *   **Item 1:** Create `magic_token.txt` with value '0'. (Should FAIL validation).
    *   **Item 2:** Update `magic_token.txt` with value '42'. (Should PASS validation).

### 3.2 The Test Run
We will run Ralph against this PRD with the mock validator:

```bash
ralph start test_loop.json --validator "python3 mock_foreman.py"
```

### 3.3 Expected Outcome
1.  Agent writes "0".
2.  Validator runs: `python3 mock_foreman.py`. Fails ("Expected 42, got 0").
3.  Ralph captures error: "Validator failed: Expected 42, got 0".
4.  Ralph prompts Agent: "Verification failed. Output: ... Fix it."
5.  Agent writes "42".
6.  Validator runs. Passes.
7.  Ralph commits and moves on.

## 4. Next Steps (Post-Merge)

Once this `feat/validator-hook` is merged:
1.  Deploy updated Ralph to the VPS.
2.  Configure The Factory's `Foreman` to accept CLI runs from Ralph.
3.  Run the first real closed-loop mission: **"The Network Storm"**.
