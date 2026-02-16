# Spark Swarm (formerly Sisyphus)

> Autonomous AI coding agent orchestrator with branch isolation, checkpoints, and PR workflow.

Spark Swarm (powered by the `ralph` CLI) orchestrates AI coding agents (Claude Code, Codex, Gemini) to work through a Product Requirements Document (PRD) systematically. Each run creates an isolated git branch, auto-commits after each item, and can generate pull requests automatically.

Named for "Spark" - the energy that drives the swarm.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/spark-swarm.git
cd spark-swarm

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install ralph
pip install -e .
```

## Quick Start

1. **Create a PRD file** (JSON format):

```json
{
  "project": "My Feature",
  "goal": "Implement user authentication",
  "items": [
    {
      "id": 1,
      "category": "setup",
      "title": "Add auth dependencies",
      "description": "Install and configure auth libraries",
      "priority": 1,
      "verification": "pip list shows auth packages",
      "steps": ["Add to requirements.txt", "Run pip install"]
    }
  ]
}
```

2. **Start Ralph**:

```bash
ralph start my-feature-prd.json
```

3. **Monitor progress**:

```bash
ralph status
```

4. **Create PR when done**:

```bash
ralph pr
```

## Commands

### `ralph start <prd.json>`

Start a new Ralph run from a PRD file.

```bash
ralph start feature.json                    # Use default agent (Claude)
ralph start feature.json -a codex           # Use Codex CLI
ralph start feature.json --push             # Auto-push after each checkpoint
ralph start feature.json --force            # Skip dirty directory check
```

### `ralph status`

Show current Ralph run status.

```bash
ralph status
```

Output includes:
- Current branch
- Progress (N/M items)
- Time elapsed
- Next item to work on

### `ralph resume`

Resume an interrupted run from where it left off.

```bash
ralph resume
```

### `ralph rollback [N]`

Undo the last N completed items.

```bash
ralph rollback        # Roll back 1 item
ralph rollback 3      # Roll back 3 items
ralph rollback --hard # Use git reset instead of revert
```

### `ralph diff`

Show summary of all changes since branch creation.

```bash
ralph diff
```

### `ralph dry-run [prd.json]`

Preview what Ralph would do without executing.

```bash
ralph dry-run feature.json
```

### `ralph pr`

Create a pull request with auto-generated description.

```bash
ralph pr           # Requires all items complete
ralph pr --force   # Allow partial completion
```

## PRD Format

```json
{
  "project": "Project Name",
  "goal": "What this PRD accomplishes",
  "tech_stack": {
    "language": "Python 3.11+",
    "framework": "FastAPI"
  },
  "context": {
    "target_user": "Developers",
    "constraints": "Must maintain backwards compatibility"
  },
  "hooks": {
    "pre_commit": ["ruff check", "mypy"],
    "post_item": ["echo 'Item complete!'"]
  },
  "items": [
    {
      "id": 1,
      "category": "setup",
      "title": "Item title",
      "description": "What needs to be done",
      "priority": 1,
      "passes": false,
      "verification": "How to verify completion",
      "steps": ["Step 1", "Step 2"],
      "notes": "Additional notes"
    }
  ]
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `project` | Yes | Project name (used for branch naming) |
| `goal` | Yes | Overall goal of the PRD |
| `tech_stack` | No | Technology stack info |
| `context` | No | Additional context for the agent |
| `hooks` | No | Validation hooks (see below) |
| `items` | Yes | List of items to implement |

### Item Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique item ID |
| `category` | Yes | Category (e.g., setup, core, polish) |
| `title` | Yes | Short title |
| `description` | Yes | Full description |
| `priority` | Yes | Priority (1 = highest) |
| `passes` | No | Whether item is complete |
| `verification` | No | How to verify completion |
| `steps` | No | Step-by-step instructions |
| `notes` | No | Additional notes |

## Hooks

Ralph supports validation hooks that run after each item:

```json
{
  "hooks": {
    "pre_commit": ["ruff check .", "mypy ."],
    "post_item": ["./scripts/validate.sh"]
  }
}
```

- **pre_commit**: Run before creating the checkpoint commit. If any fail, Ralph pauses.
- **post_item**: Run after the checkpoint. Failures are logged but don't stop progress.

## Supported Agents

| Agent | Command | Description |
|-------|---------|-------------|
| `claude` | `claude --dangerously-skip-permissions -p` | Claude Code (default) |
| `codex` | `codex exec --yolo -p` | Codex CLI |
| `gemini` | `gemini -p` | Gemini CLI |

Select agent with `-a/--agent`:

```bash
ralph start prd.json -a codex
```

## State Management

Ralph stores state in `.ralph/state.json` (added to `.gitignore`):

```json
{
  "branch": "ralph/my-project-20240101-1200",
  "prd_path": "/path/to/prd.json",
  "current_item": 3,
  "completed_items": [1, 2],
  "started_at": "2024-01-01T12:00:00",
  "checkpoints": [
    {
      "item_id": 1,
      "commit_sha": "abc123...",
      "timestamp": "2024-01-01T12:05:00",
      "files_changed": ["src/main.py"],
      "tests_passed": true
    }
  ]
}
```

## Migration from sisyphus.sh

Ralph replaces `sisyphus.sh` with these improvements:

| Feature | sisyphus.sh | Ralph |
|---------|-------------|-------|
| Branch isolation | ❌ | ✅ Automatic branch per PRD |
| Checkpoints | ❌ | ✅ Auto-commit after each item |
| Resume support | ❌ | ✅ `ralph resume` |
| Rollback | ❌ | ✅ `ralph rollback` |
| PR generation | ❌ | ✅ `ralph pr` |
| Multiple agents | Limited | ✅ claude, codex, gemini |
| State persistence | ❌ | ✅ `.ralph/state.json` |
| Validation hooks | ❌ | ✅ pre_commit, post_item |

### Migration Steps

1. Install Ralph: `pip install -e .`
2. Convert your task list to PRD JSON format
3. Run `ralph start your-prd.json`

## Using with The Companion (Swarm Controller)

You can run Ralph with the [Claude Code Controller (The Companion)](https://github.com/The-Vibe-Company/claude-code-controller) for a rich web UI, parallel session management, and full visibility.

### Quick Start (Swarm Harness)

Use the included harness script to launch The Companion and Ralph together:

```bash
# Ensure you have 'bun' installed
./swarm.py start my-feature-prd.json
```

This will:
1. Start The Companion server on port 3456 (if not running).
2. Generate a unique session ID for this run.
3. Launch Ralph, configured to stream all agent activity to the UI.
4. Print the session URL for you to open.

### Manual Usage

If you prefer to run manually:

```bash
export RALPH_COMPANION_URL="ws://localhost:3456/ws/cli/my-custom-session-id"
ralph start my-feature-prd.json
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Type checking
mypy src/ralph

# Linting
ruff check src/ralph
```

## License

MIT
