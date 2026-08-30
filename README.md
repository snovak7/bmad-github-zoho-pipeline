# bmad-github-zoho-pipeline

**Pipeline Forge** — a configurable Zoho Projects + GitHub Flow task pipeline, packaged as a [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) module and Claude Code plugin.

It acts as the operator of your repo's delivery pipeline: it plans work into a Zoho Projects task list, drives every code-touching task through GitHub Flow (branch → PR → review → GPG-verified merge → close), and brackets every segment of work with paired Zoho time-log sessions. State is tracked in `session-state.json`, so work can be resumed correctly across sessions, days, or a context reset — no skipped steps, no time-log session left open, no GitHub issue mistaken for a work item.

## What it does

- **Plans phases.** Breaks a chunk of work into a Zoho Projects task list under a logged Planning task.
- **Drives tasks end to end.** Each task moves through In Progress → PR opened → In Review → merge-verified → Closed.
- **Time-logs every segment.** Uses a paired start/stop pattern against Zoho's time-log API (Zoho has no live timer).
- **Handles ad hoc requests and issues.** Small unplanned work and one-off "report an issue" flows are supported without forcing them into a task list.
- **Resumes safely.** On activation it reads `session-state.json` first — never re-derives position from conversation history — and reports/resumes any task or time-log session left mid-flight.
- **Never fabricates verification.** Status changes, merges, GPG signatures, and time-log entries must correspond to something actually checked or called.

See [`gzp-pipeline/SKILL.md`](gzp-pipeline/SKILL.md) for the full activation flow, invariants, and capability map.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- A Zoho Projects MCP server connected in your Claude Code session, exposing time-log tools (e.g. `add_time_log` / `update_single_time_log`)
- [`uv`](https://docs.astral.sh/uv/) (used by the module's setup/config scripts)
- A git repository with `commit.gpgsign` enabled, if you want tasks driven through GitHub Flow

## Install

### As a Claude Code plugin (recommended)

Add this repo as a plugin marketplace, then install the `gzp` plugin:

```
/plugin marketplace add snovak7/bmad-github-zoho-pipeline
/plugin install gzp
```

This installs the `gzp-pipeline` skill, which Claude Code loads automatically whenever you say things like "start a new phase," "work the next task," or "report an issue."

### As a BMAD module

Clone or add this repo's `gzp-pipeline/` directory into your project's BMAD module path, then run the skill with `setup` (or just start using it — first-run activation detects an unregistered module and runs setup automatically):

```
setup
```

You'll be asked for:

| Setting | Purpose |
| --- | --- |
| `gzp_mcp_name` | Which Zoho Projects MCP server to use for time-logging |
| `gzp_zoho_project_name` | The Zoho Projects project this repo's work is tracked against |
| `gzp_default_bill_status` | Default bill status for time-log entries (defaults to "Non Billable") |

Setup writes shared config to `_bmad/config.yaml`, personal settings to `_bmad/config.user.yaml` (gitignore this), and registers the module in `_bmad/module-help.csv`.

## Usage

Once installed and configured, just talk to it:

- **"Start a new phase"** — plan and break down a new chunk of work into a tracked Zoho task list.
- **"Work the next task"** / **"continue"** — pick up the next task, or resume one already in progress.
- **"Report an issue"** — file a standalone GitHub issue outside the task pipeline.
- **"Configure"** — re-run setup to change project/config values.

Say `configure` at any time to reconfigure, or edit `_bmad/config.yaml` / `_bmad/config.user.yaml` directly.

## License

MIT © Simon Novak
