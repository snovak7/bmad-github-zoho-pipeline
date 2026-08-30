---
name: gzp-pipeline
description: Configurable Zoho Projects + GitHub Flow task pipeline. Use when the user says "start a new phase", "work the next task", "report an issue", makes an ad hoc pipeline request, or references "gzp-pipeline"/"Pipeline Forge".
---

# gzp-pipeline

## Overview

Act as the expert operator who owns this repo's Zoho Projects + GitHub Flow pipeline — not a facilitator asking what to do next, but the one driving Zoho task lists, GitHub issues/PRs, and time-log sessions to a correct state at every step. The outcome is every piece of planned work (brainstorming, planning, implementing, testing, ad hoc fixes) landing as an accurately time-logged Zoho task, with every code-touching task also driven cleanly through GitHub Flow to a merged, GPG-verified, review-clean close. The consumer is the user returning across sessions and days — sometimes mid-task after a context reset — who needs to trust that no time-log session was left open, no step was skipped or reordered, and no GitHub issue was mistaken for a work item in its own right.

## Resolution rules

- Bare paths and `{skill-root}` (e.g. `references/task-loop.md`) resolve from this skill's installed directory.
- `{project-root}` → the project working directory.
- `gzp-pipeline` → the skill directory's basename.

## On Activation

1. **Run module setup when it's due.** Read and follow `assets/module-setup.md` before anything else when either trigger holds:
   - the user's request is itself a setup ask for this module (`setup`, `configure`, or `install` as the command/argument — not a mere substring of an unrelated task), or
   - `{project-root}/_bmad/config.yaml` has no `gzp` section — the fresh/unregistered-install signal, including a project where an external installer only wrote per-module config (e.g. `{project-root}/_bmad/gzp/config.yaml`).

   Setup registers the module and installs the optional bmad-build auto-track hooks (see module-setup.md § Auto-Track bmad-build). When activation happens mid-task with no room for a setup conversation (e.g. invoked from a hook), run setup headless: per-module installer config values as answers, defaults for the rest, asking only for required values that cannot be resolved — except `gzp_github_issue_first`, which headless setup writes as `false` unless an installer config already set it: enabling issue-first is an interactive choice, never a silent default. If the user declines setup, fall back to step 2 and proceed for this session. Resume the steps below once setup completes.
   - **Hook self-heal (runs even when setup isn't due):** if config has `gzp_autotrack_bmad_build: true`, `{project-root}/.claude/skills/bmad-build/customize.toml` exists, and `{project-root}/_bmad/custom/bmad-build.toml` lacks the gzp-pipeline `activation_steps_prepend` entry, run `uv run scripts/write-build-hook.py --target "{project-root}/_bmad/custom/bmad-build.toml" --bmad-build-customize-toml "{project-root}/.claude/skills/bmad-build/customize.toml" --action enable` — auto-tracking must survive bmad-build being installed after this module was set up.
2. **Load config.** Read `gzp_mcp_name`, `gzp_zoho_project_name`, `gzp_default_bill_status`, `gzp_github_issue_first` from `{project-root}/_bmad/config.yaml` (`gzp` section) and `{project-root}/_bmad/config.user.yaml`. If either of the first two is missing, ask for it directly (same question module setup would ask) and persist the answer where setup would have written it (`gzp_mcp_name` → `config.user.yaml`; `gzp_zoho_project_name` → the `gzp` section of `config.yaml`) so it isn't re-asked next session — don't block on full setup having been run. Default `gzp_default_bill_status` to "Non Billable" if unset. Default `gzp_github_issue_first` to `false` if unset (projects configured before the option existed keep the straight-to-branch flow until reconfigured).
3. **Resume session-state.** Run `uv run scripts/session_state.py init --path {project-root}/_bmad/memory/gzp-pipeline/session-state.json` (no-op if it exists), then `show` it. This is the single source of truth for where the pipeline stands — never re-derive position from conversation history.
   - If `resolved.*` fields are null, resolve them now and write them back with `set`: call `get_portals` (single portal → use it, else ask), `get_projects_list` matched against `gzp_zoho_project_name`, the task-status field's option ids via `get_options_list_for_a_field_in_module` (never hardcode status ids — they vary per portal), `owner/repo` from `git remote -v`, and the caller's own Zoho identity (`zuid`/`zpuid`/`name`) via `get_current_user_details` — needed to self-assign every Zoho task created (see Invariants).
   - If `open_time_logs` has any entries or `current_task.step` is mid-flight, report the exact state to the user (task, step, and every still-open session by task id) and resume automatically when it's unambiguous (e.g. "PR open — awaiting merge" → check the PR yourself); ask only when genuinely ambiguous (e.g. the PR check itself fails). When resuming a code-path task with issue-first enabled, consult `current_task.github_issue` before re-running the tracking-issue step — non-null means the issue exists; null means also search open issues for the task title before creating one (the prior session may have died between creating and recording it).

## Invariants

These hold across every capability below:

- **Sole Zoho-writer.** This skill is the only caller of Zoho Projects MCP tools. A dispatched subagent (research, implementation) reports a summary back rather than calling Zoho itself; fold that summary into the time-log session note you own. Each distinct subagent dispatch on a task gets its own time-log session pair.
- **GitHub issues are not work items — Zoho tasks are.** By default a task's GitHub Flow goes straight to a branch and PR, with no issue step. When `gzp_github_issue_first` is enabled, each code-change task additionally opens a *tracking issue* before branching (see `references/task-loop.md`) — but that issue mirrors the Zoho task, never replaces it: it's self-assigned, referenced by the branch and PR, auto-closed by the merge, and never separately planned or time-logged. An issue as its own standalone, separately-tracked artifact only exists via the "Report an issue" capability.
- **One task in flight at a time.** Finish (or explicitly park, updating `session-state`) the current task before starting another.
- **GPG signing is a hard checkpoint, never bypassed.** `git config commit.gpgsign` is expected already `true` locally — never override it, never pass `--no-gpg-sign`. If a commit can't be verified signed (`git log --show-signature -1`), stop and ask rather than guessing or skipping the check.
- **Non-code work skips GitHub Flow entirely.** Decide up front whether a task will touch code. If not, only Zoho status + time-log apply — no branch, issue, or PR.
- **Never fabricate verification.** A status change, a merge confirmation, a GPG-signature check, or a time-log entry must correspond to something actually called, checked, or measured. If a required tool isn't available or a call fails, say so exactly and ask how to proceed — never invent a result to keep the pipeline moving.
- **Self-assign everything.** Every Zoho task this skill creates (planned tasks, the Planning task, an issue's linked task) gets `owners_and_work.owners` set to the caller (`resolved.zoho_user`) at creation time. Every GitHub PR gets assigned to the caller too (already covered in `references/task-loop.md`).

## Capabilities

| Capability | When | Location |
| --- | --- | --- |
| Start a new phase | User describes a new chunk of work to plan/break down | `references/planning-phase.md` |
| Work a task | User names a task, says "next"/"continue", or work is already in progress per `session-state` | `references/task-loop.md` |
| Report an issue | Something goes wrong mid-task and needs standalone tracking | `references/issue-report.md` |
| Ad hoc request | A request too small/unplanned to belong to an open task list | `references/task-loop.md` (Ad Hoc Requests section) |

Every capability above brackets its work with time-log sessions using the paired start/stop pattern in `references/time-log-session.md` — read it before the first `add_time_log` call of a session, since Zoho has no live timer and the mechanics aren't guessable.
