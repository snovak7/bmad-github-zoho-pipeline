# bmad-github-zoho-pipeline

**Pipeline Forge** — a configurable Zoho Projects + GitHub Flow task pipeline, packaged as a [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) module and Claude Code plugin.

It acts as the operator of your repo's delivery pipeline: it plans work into a Zoho Projects task list, drives every code-touching task through GitHub Flow (branch → PR → review → GPG-verified merge → close), and brackets every segment of work with paired Zoho time-log sessions. State is tracked in `session-state.json`, so work can be resumed correctly across sessions, days, or a context reset — no skipped steps, no time-log session left open, no GitHub issue mistaken for a work item.

## What it does

- **Plans phases.** Breaks a chunk of work into a Zoho Projects task list under a logged Planning task, and mirrors the breakdown into a local todo list for in-session visibility.
- **Drives tasks end to end.** Each task moves through In Progress → PR opened → In Review → merge-verified → Closed.
- **Self-assigns everything.** Every Zoho task it creates and every GitHub PR it opens is assigned to you automatically, with an appropriate label attached to the PR when one fits.
- **Time-logs every segment.** Uses a paired start/stop pattern against Zoho's time-log API (Zoho has no live timer).
- **Handles ad hoc requests and issues.** Small unplanned work and one-off "report an issue" flows are supported without forcing them into a task list.
- **Resumes safely.** On activation it reads `session-state.json` first — never re-derives position from conversation history — and reports/resumes any task or time-log session left mid-flight.
- **Never fabricates verification.** Status changes, merges, GPG signatures, and time-log entries must correspond to something actually checked or called.
- **Can run itself invisibly inside `bmad-build`.** Optionally hooks into `bmad-build`'s activation and completion steps at install time, so build work gets tracked without ever saying "gzp-pipeline." See [Auto-tracking bmad-build](#auto-tracking-bmad-build).

See [`skills/gzp-pipeline/SKILL.md`](skills/gzp-pipeline/SKILL.md) for the full activation flow, invariants, and capability map.

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

Clone or add this repo's `skills/gzp-pipeline/` directory into your project's BMAD module path, or install it with the BMAD installer, then run the skill with `setup` (or just start using it — first-run activation detects an unregistered module and runs setup automatically):

```
setup
```

You'll be asked for:

| Setting | Purpose |
| --- | --- |
| `gzp_mcp_name` | Which Zoho Projects MCP server to use for time-logging |
| `gzp_zoho_project_name` | The Zoho Projects project this repo's work is tracked against |
| `gzp_default_bill_status` | Default bill status for time-log entries (defaults to "Non Billable") |
| `gzp_autotrack_bmad_build` | Whether to auto-hook `bmad-build` (defaults to yes) — see [Auto-tracking bmad-build](#auto-tracking-bmad-build) |

Setup writes shared config to `_bmad/config.yaml`, personal settings to `_bmad/config.user.yaml` (gitignore this), and registers the module in `_bmad/module-help.csv`.

## Auto-tracking bmad-build

If you use [`bmad-build`](https://github.com/bmad-code-org/BMAD-METHOD) to implement work and answer yes to `gzp_autotrack_bmad_build` during setup, Pipeline Forge writes a hook into `_bmad/custom/bmad-build.toml`:

- **Before Build starts** (`activation_steps_prepend`) — hands off to gzp-pipeline to resume or start Zoho task status + time-log tracking.
- **After Build completes** (`on_complete`) — hands off to gzp-pipeline to drive the change through GitHub Flow (branch, commit, push, self-assigned PR with a label), update the Zoho task's status, and close the time-log session.

This means `bmad-build` runs get tracked automatically, without ever typing "gzp-pipeline." A few things to know:

- **The hook is installed on first use of the skill, not by the BMAD installer.** The installer only writes config files (including your `gzp_autotrack_bmad_build` answer) — it never runs hooks. `_bmad/custom/bmad-build.toml` is written the first time the gzp-pipeline skill activates in the project (which auto-runs setup for an unregistered module), or whenever you say `setup`/`configure`. So a missing hook right after the installer finishes is expected — just use the skill once.
- **It self-heals.** On every activation, if auto-tracking is enabled, `bmad-build` is installed, and the hook entry is missing, the skill re-installs it — so installing `bmad-build` *after* this module still gets you the hooks without re-running anything by hand.
- **It's skipped, not forced.** If `bmad-build` isn't installed in the project yet, the write is a no-op — re-run `configure` after installing it, or the next `configure` run picks it up.
- **It won't clobber your own customizations.** If `_bmad/custom/bmad-build.toml` already has a different `on_complete` override, that field is left alone and setup reports a conflict for you to resolve by hand (the `activation_steps_prepend` entry is additive, so it's written either way).
- **Answering no later removes it cleanly.** Re-running `configure` and switching the answer to no strips only the entries this module added — anything else in that file is untouched.
- **Prefer it off, or want it elsewhere?** Answer no during setup, or edit `_bmad/custom/bmad-build.toml` directly — see the [How to Customize BMad guide](https://docs.bmad-method.org/how-to/customize-bmad/).

## Usage

Once installed and configured, just talk to it:

- **"Start a new phase"** — plan and break down a new chunk of work into a tracked Zoho task list.
- **"Work the next task"** / **"continue"** — pick up the next task, or resume one already in progress.
- **"Report an issue"** — file a standalone GitHub issue outside the task pipeline.
- **"Configure"** — re-run setup to change project/config values.

Say `configure` at any time to reconfigure, or edit `_bmad/config.yaml` / `_bmad/config.user.yaml` directly.

## License

MIT © Simon Novak
