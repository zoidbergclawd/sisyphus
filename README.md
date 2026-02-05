# Sisyphus

> *"One must imagine Sisyphus happy."* — Albert Camus

An autonomous coding loop that processes PRD items one at a time, using AI coding agents. Named for the mythological figure who found meaning in the eternal push.

## Philosophy

The universe is indifferent. The code will eventually be deprecated. The servers will shut down.

And yet—we build anyway.

Sisyphus is a tool for those who find joy in the push itself. You define what needs to be built (the PRD), and Sisyphus pushes the boulder up the hill one item at a time: read task, write tests, implement, verify, commit, repeat.

The boulder reaches the top. Then we start another project.

## Features

- **Multi-agent support**: Works with Claude Code, OpenAI Codex, and Google Gemini CLI
- **PRD-driven**: Structured JSON defines what to build, with verification criteria
- **TDD by default**: Tests first, always
- **Auto-commit**: Structured git commits after each completed item
- **Auto-push**: Optional push to remote after each commit
- **Progress tracking**: Living log of what was done and why

## Quick Start

```bash
# Clone sisyphus into your project (or copy the files)
git clone https://github.com/zoidbergclawd/sisyphus.git
cd your-project
cp ../sisyphus/sisyphus.sh .
cp ../sisyphus/prd-template.json prd.json
cp ../sisyphus/AGENTS.md .

# Edit prd.json with your items
vim prd.json

# Initialize progress tracking
echo "# Progress Log" > progress.txt

# Run with Claude (default)
./sisyphus.sh 10

# Run with Codex
./sisyphus.sh -a codex 10

# Run with Gemini
./sisyphus.sh -a gemini 10

# Push after each commit
./sisyphus.sh -a claude --push 10
```

## Requirements

At least one of these AI coding agents installed:

| Agent | Install | Docs |
|-------|---------|------|
| **Claude Code** | `brew install claude` or npm | [docs](https://docs.anthropic.com/claude-code) |
| **Codex CLI** | `npm install -g @openai/codex` | [docs](https://developers.openai.com/codex/cli/) |
| **Gemini CLI** | `npm install -g @google/gemini-cli` | [docs](https://geminicli.com/) |

## PRD Structure

The PRD (`prd.json`) defines your project:

```json
{
  "project": "My Awesome Project",
  "goal": "What we're building and why",
  "tech_stack": {
    "language": "Python 3.11+",
    "framework": "FastAPI",
    "testing": "pytest"
  },
  "items": [
    {
      "id": 1,
      "title": "Project scaffolding",
      "description": "Set up project structure with dependencies",
      "priority": 1,
      "passes": false,
      "verification": "pip install -e . && myproject --help shows usage"
    },
    {
      "id": 2,
      "title": "Core feature X",
      "description": "Implement the main feature",
      "priority": 1,
      "passes": false,
      "verification": "pytest tests/test_feature_x.py passes"
    }
  ]
}
```

### Item Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier, used in commit messages |
| `title` | Yes | Short description for commits |
| `description` | Yes | Full description of what to implement |
| `priority` | Yes | Lower = higher priority (1 is highest) |
| `passes` | Yes | Set to `true` by agent when complete |
| `verification` | Yes | How to verify the item is done |
| `steps` | No | Detailed implementation steps |
| `notes` | No | Additional context or constraints |

## Commit Format

Sisyphus uses structured commits for clean history:

```
[ITEM-3] User authentication (Route C)

Implemented OAuth2 login flow with JWT tokens.

- src/auth/oauth.py: Added OAuth2 provider integration
- src/auth/jwt.py: JWT token generation and validation
- tests/test_auth.py: 12 new tests for auth flow

Tests: 12 passing
```

The route indicates complexity:
- **Route A**: Simple (direct implementation)
- **Route B**: Medium (exploration needed)
- **Route C**: Complex (planning + exploration)

## Progress Tracking

`progress.txt` becomes a living log:

```markdown
# Progress Log

## Session Start: 2025-02-04 22:30:00

---

## Item 1: Project scaffolding ✅

**Route:** A (Simple)
**Time:** 2 minutes

**Files created:**
- pyproject.toml
- src/myproject/__init__.py
- src/myproject/cli.py

**Decisions:**
- Used hatchling as build backend
- Typer for CLI framework

**Verification:** ✓ myproject --help shows usage

---

## Item 2: Core feature X ✅

**Route:** B (Medium)
**Time:** 5 minutes

...
```

## Agent Comparison

| Feature | Claude Code | Codex CLI | Gemini CLI |
|---------|-------------|-----------|------------|
| **Non-interactive flag** | `--dangerously-skip-permissions -p` | `exec --yolo` | `-p` |
| **File access** | Full | Sandboxed (configurable) | Full |
| **Shell commands** | Yes | Yes | Yes |
| **Free tier** | No | No | 1000 req/day |
| **Best for** | Complex reasoning | Fast iteration | Long context |

## Cage Match Mode (Coming Soon)

Run the same PRD with multiple agents in parallel on separate branches:

```bash
./sisyphus.sh --cage-match prd.json
# Creates: branch claude-attempt, codex-attempt, gemini-attempt
# Runs all three in parallel
# Reports: time, commits, test coverage
# You pick the winner to merge
```

## Tips

1. **Start small**: First PRD item should be scaffolding/setup
2. **Verifiable items**: Each item needs clear pass/fail criteria
3. **TDD requirement**: Include test verification in each item
4. **Priority ordering**: Use priority field to control sequence
5. **One thing at a time**: Each item should be a single, focused change

## Why "Sisyphus"?

In Greek mythology, Sisyphus was condemned to roll a boulder up a hill for eternity—each time it reached the top, it would roll back down.

Camus saw this as a metaphor for human existence: repetitive, seemingly meaningless, yet potentially joyful. The act of pushing the boulder *is* the meaning.

Autonomous coding loops are similar: read task, implement, test, commit, repeat. Forever, or until the PRD is done. The joy is in the push.

## License

MIT - Push freely.

## Credits

Built by [Zoidberg](https://github.com/zoidbergclawd) in a dumpster, with love.

Inspired by:
- [Claude Code](https://docs.anthropic.com/)
- [do-work](https://github.com/bladnman/do-work) by bladnman
- The eternal boulder
