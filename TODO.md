# Ralph CLI Roadmap

## Future Features

- [ ] **Hung Prompt Watchdog** 🐕
  - Monitor agent execution for inactivity (e.g., >10 mins without output).
  - Auto-escalate: take screenshot (if UI), dump stack, or alert user.
  - Option to auto-kill and retry (`--watchdog-retry`).
  - Prevents "zombie ralphs" spinning on hidden prompts.

- [ ] **Cage Match Mode**
  - Run same item with multiple agents (Claude vs Codex) and pick the winner.

- [ ] **Granular Status & Live Tail**
  - `ralph status` should show the active sub-step (e.g., "Running tests...", "Generating code...").
  - Option to tail logs directly via `ralph log`.

- [ ] **ETA & Metrics**
  - Calculate average time per item and project completion time.
  - Show estimated finish time in `ralph status`.
