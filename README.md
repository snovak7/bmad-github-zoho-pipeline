# bmad-github-zoho-pipeline

**Pipeline Forge** — a configurable task pipeline that tracks work in Zoho Projects or Windshift and drives it through GitHub Flow on GitHub or Forgejo repos, packaged as a [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) module and Claude Code plugin.

It acts as the operator of your repo's delivery pipeline: it plans work into a phase list on your tracker (a Zoho Projects task list, or a parent work item in a Windshift workspace), drives every code-touching task through GitHub Flow (optional tracking issue → branch → GPG-signed commits → PR → review → merge → close), and brackets every segment of work with time-log sessions on the tracker. The forge is a setup choice — GitHub or Forgejo (Codeberg or self-hosted) — and so is the tool that drives it: an MCP server, or the forge's CLI (`gh` / `fj`). Each leg is a setup toggle: the tracker (or none), GPG enforcement, issue-first flow, and PR auto-merge can each be turned on or off per project — everything on is the default; everything off leaves a plain GitHub Flow driver. State is tracked in `session-state.json`, so work can be resumed correctly across sessions, days, or a context reset — no skipped steps, no time-log session left open, no forge issue mistaken for a work item.

## What it does

- **Plans phases.** Breaks a chunk of work into a phase list on the tracker (Zoho task list or Windshift parent item) under a logged Planning task, and mirrors the breakdown into a local todo list for in-session visibility.
- **Drives tasks end to end.** Each task moves through In Progress → PR opened → In Review → merge-verified → Closed. Optionally issue-first: an issue is opened on the forge for each code-change task before branching, referenced by the branch and PR, and auto-closed by the merge (`gzp_issue_first`). Branch names are deterministic — `{type}/{task-key}-{forge}{issue}-{slug}`, e.g. `feat/ecm-t101-gh5-generic-toggles` on GitHub or `feat/ecm-t101-fj5-generic-toggles` on Forgejo — with the conventional-commit type (which sets the semver bump) leading and the tracker/issue segments dropping out when those toggles are off.
- **Self-assigns everything.** Every tracker task it creates and every PR (and tracking issue) it opens is assigned to you automatically, with an appropriate label attached when one fits.
- **Time-logs every segment.** On Zoho, a paired start/stop pattern against the time-log API (Zoho has no live timer). On Windshift, the start is recorded locally and one finished worklog is booked against the workspace's time project when the segment ends (Windshift's MCP server can't edit a worklog afterwards, and allows only one running timer per user).
- **Handles ad hoc requests and issues.** Small unplanned work and one-off "report an issue" flows are supported without forcing them into a task list.
- **Resumes safely.** On activation it reads `session-state.json` first — never re-derives position from conversation history — and reports/resumes any task or time-log session left mid-flight.
- **Never fabricates verification.** Status changes, merges, GPG signatures, and time-log entries must correspond to something actually checked or called.
- **Can run itself invisibly inside `bmad-build`.** Optionally hooks into `bmad-build`'s activation and completion steps at install time, so build work gets tracked without ever saying "gzp-pipeline." See [Auto-tracking bmad-build](#auto-tracking-bmad-build). The unattended loop (`bmad-build-auto`) can be hooked the same way, with rules that never wait on a human — see [Auto-tracking the unattended loop](#auto-tracking-the-unattended-loop).

See [`skills/gzp-pipeline/SKILL.md`](skills/gzp-pipeline/SKILL.md) for the full activation flow, invariants, and capability map.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- A tracker MCP server connected in your Claude Code session, unless the tracker is off (`gzp_tracker: none`):
  - **Zoho Projects** (the default): a Zoho Projects MCP server exposing time-log tools (e.g. `add_time_log` / `update_single_time_log`).
  - **Windshift:** your instance's built-in MCP server (the `/mcp` endpoint, enabled with `--mcp` or `MCP_ENABLED=true`), with the `mcp:access` permission for your user. The workspace needs a linked time project, or you name one in `gzp_windshift_time_project`.
- [`uv`](https://docs.astral.sh/uv/) (used by the module's setup/config scripts)
- A git repository with `commit.gpgsign` enabled, if GPG enforcement is on (`gzp_gpg_signing`, the default)
- One forge tool for issues, PRs, and merges, picked at setup (`gzp_forge` + `gzp_forge_tool`):
  - **GitHub:** a GitHub MCP server connected in your session, or the [`gh` CLI](https://cli.github.com/) installed and authenticated.
  - **Forgejo:** a Forgejo MCP server connected in your session, or the [`fj` CLI (forgejo-cli)](https://codeberg.org/forgejo-contrib/forgejo-cli) installed and logged in to your instance (`fj -H <host> auth login`).

  The choice is strict: if the configured tool isn't available, the pipeline stops before the first forge step and says what's missing. It doesn't silently switch tools.

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
| `gzp_tracker` | Which tracker holds work items, statuses, and time logs: `zoho` (default), `windshift`, or `none` (a pure GitHub Flow driver; pairing with `gzp_issue_first` is then recommended so each task still has a durable record). Configs from before 1.6.0 with `gzp_zoho_workflow: false` are migrated to `none` |
| `gzp_zoho_mcp_name` | Which Zoho Projects MCP server to use for tasks and time-logging (asked only when the tracker is `zoho`; configs from before 1.3.0 that still say `gzp_mcp_name` are migrated on first activation) |
| `gzp_zoho_project_name` | The Zoho Projects project this repo's work is tracked against (asked only when the tracker is `zoho`) |
| `gzp_default_bill_status` | Default bill status for time-log entries (defaults to "Non Billable"; asked only when the tracker is `zoho`) |
| `gzp_windshift_mcp_name` | Which Windshift MCP server to use for work items and time logs (personal setting; asked only when the tracker is `windshift`) |
| `gzp_windshift_workspace_name` | The Windshift workspace this repo's work is tracked in (asked only when the tracker is `windshift`) |
| `gzp_windshift_time_project` | The Windshift time project to book against; leave empty to use the workspace's linked time project (asked only when the tracker is `windshift`) |
| `gzp_forge` | Which forge hosts the repo: `github` (default) or `forgejo` |
| `gzp_forge_tool` | How the forge is driven: `mcp` (default) or `cli` (`gh` for GitHub, `fj` for Forgejo). Personal setting; configs from before 1.5.0 keep the old MCP-then-`gh` fallback until reconfigured |
| `gzp_forge_mcp_name` | Which MCP server to use for the forge (asked only when `gzp_forge_tool` is `mcp`; a pre-1.5.0 `gzp_github_mcp_name` is migrated automatically) |
| `gzp_gpg_signing` | Whether GPG-signed commits are enforced as a hard checkpoint via `git log --show-signature` (defaults to yes; when off, commits use the repo's git config as-is) |
| `gzp_auto_merge_pr` | Whether the pipeline merges its own PRs (explicit-method `gh pr merge` / `fj pr merge`, or the MCP's merge tool) instead of waiting for your manual review and merge (defaults to no; blocked merges fall back to waiting, never forced) |
| `gzp_issue_first` | Whether each code-change task opens a tracking issue before branching — linked from the branch and PR, auto-closed by the merge (defaults to yes at setup; projects configured before this option existed behave as "no" until reconfigured) |
| `gzp_autotrack_bmad_build` | Whether to auto-hook `bmad-build` (defaults to yes) — see [Auto-tracking bmad-build](#auto-tracking-bmad-build) |
| `gzp_autotrack_bmad_loop` | Whether to auto-hook the unattended development loop, `bmad-build-auto` (defaults to yes at setup; projects configured before this option existed leave the loop untracked until reconfigured) — see [Auto-tracking the unattended loop](#auto-tracking-the-unattended-loop) |
| `gzp_loop_auto_merge_pr` | Whether the pipeline merges its own PRs inside the unattended loop (defaults to yes; asked only when the loop hook is on; independent of `gzp_auto_merge_pr`) |

Settings that belong to an option you didn't select are neither asked nor written: the Zoho settings exist only while the tracker is `zoho`, the Windshift settings only while it's `windshift`, and `gzp_forge_mcp_name` only while the forge tool is `mcp`. Switching an option in `configure` removes the other option's settings from both config files.

Setup writes shared config to `_bmad/config.yaml`, personal settings to `_bmad/config.user.yaml` (gitignore this), and registers the module in `_bmad/module-help.csv`.

## Auto-tracking bmad-build

If you use [`bmad-build`](https://github.com/bmad-code-org/BMAD-METHOD) to implement work and answer yes to `gzp_autotrack_bmad_build` during setup, Pipeline Forge writes a hook into `_bmad/custom/bmad-build.toml`:

- **Before Build starts** (`activation_steps_prepend`) — hands off to gzp-pipeline to resume or start tracker task status + time-log tracking.
- **After Build completes** (`on_complete`) — hands off to gzp-pipeline to drive the change through GitHub Flow (branch, commit, push, self-assigned PR with a label), update the tracker task's status, and close the time-log session.

This means `bmad-build` runs get tracked automatically, without ever typing "gzp-pipeline." A few things to know:

- **The hook is installed on first use of the skill, not by the BMAD installer.** The installer only writes config files (including your `gzp_autotrack_bmad_build` answer) — it never runs hooks. `_bmad/custom/bmad-build.toml` is written the first time the gzp-pipeline skill activates in the project (which auto-runs setup for an unregistered module), or whenever you say `setup`/`configure`. So a missing hook right after the installer finishes is expected — just use the skill once.
- **It self-heals.** On every activation, if auto-tracking is enabled, `bmad-build` is installed, and the hook entry is missing, the skill re-installs it — so installing `bmad-build` *after* this module still gets you the hooks without re-running anything by hand.
- **It's skipped, not forced.** If `bmad-build` isn't installed in the project yet, the write is a no-op — re-run `configure` after installing it, or the next `configure` run picks it up.
- **It won't clobber your own customizations.** If `_bmad/custom/bmad-build.toml` already has a different `on_complete` override, that field is left alone and setup reports a conflict for you to resolve by hand (the `activation_steps_prepend` entry is additive, so it's written either way).
- **Answering no later removes it cleanly.** Re-running `configure` and switching the answer to no strips only the entries this module added — anything else in that file is untouched.
- **Prefer it off, or want it elsewhere?** Answer no during setup, or edit `_bmad/custom/bmad-build.toml` directly — see the [How to Customize BMad guide](https://docs.bmad-method.org/how-to/customize-bmad/).

### Auto-tracking the unattended loop

`bmad-build-auto` runs one iteration of an unattended development loop, and it reads its **own** override file (`_bmad/custom/bmad-build-auto.toml`) — so the `bmad-build` hook above never reaches it, and without a hook of its own the loop skips the pipeline entirely. Answer yes to `gzp_autotrack_bmad_loop` and Pipeline Forge writes the same two hooks there, in an unattended variant:

- **It never asks and never waits.** Anything that would need an answer — unresolved required config, an unusable forge tool, ambiguous resume state — is reported as a blocker, and the loop halts with status `blocked` instead of hanging on a prompt nobody will see.
- **The loop accepts its own PRs.** `gzp_loop_auto_merge_pr` (default yes) governs unattended runs, separately from `gzp_auto_merge_pr`, which governs interactive ones — so you can keep a human merge when you're at the keyboard and still let the loop flow on its own. The pipeline merges only the PR it opened for the current task, only once its checks are green, and never with `--admin` or any force-style override.
- **A blocked merge halts the loop instead of hanging it.** If checks are pending or failing, a review is required, or there's a conflict — or you turned loop auto-merge off — the iteration ends with its PR open. The next iteration re-checks that PR first: it merges and continues if it can, otherwise halts as `blocked: PR #<n> awaiting merge — <exact blocker>`. One task in flight holds in the loop too.
- **It doesn't depend on the loop runner's decision support.** `blocked` with a precise condition is the only thing the pipeline ever hands back; a runner that can surface decisions may present it as one, and one that can't simply stops.
- **Everything else is unchanged.** Tracking, time logs, GPG checks, the tracking issue, and branch naming all apply exactly as in an interactive run.

The install, self-heal, `skipped`, conflict, and "answer no to remove it" behaviors described above apply to this hook the same way, and the two hooks are independent — either can be on without the other.

## Usage

Once installed and configured, just talk to it:

- **"Start a new phase"** — plan and break down a new chunk of work into a tracked phase list on the tracker.
- **"Work the next task"** / **"continue"** — pick up the next task, or resume one already in progress.
- **"Report an issue"** — file a standalone issue on the forge outside the task pipeline.
- **"Configure"** — re-run setup to change project/config values.

Say `configure` at any time to reconfigure, or edit `_bmad/config.yaml` / `_bmad/config.user.yaml` directly.

## License

MIT © Simon Novak
