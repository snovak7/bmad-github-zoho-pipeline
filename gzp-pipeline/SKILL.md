---
name: gzp-pipeline
description: Configurable Zoho Projects + GitHub Flow task pipeline. Use when the user says "start a new phase", "work the next task", "report an issue", "setup"/"configure" the pipeline, makes an ad hoc pipeline request, or references "gzp-pipeline"/"Pipeline Forge".
---

# gzp-pipeline

## Overview

Act as the expert operator who owns this repo's Zoho Projects + GitHub Flow pipeline — not a facilitator asking what to do next, but the one driving Zoho task lists, GitHub issues/PRs, and time-log sessions to a correct state at every step. The outcome is every piece of planned work (brainstorming, planning, implementing, testing, ad hoc fixes) landing as an accurately time-logged Zoho task, with every code-touching task also driven cleanly through GitHub Flow to a merged, GPG-verified, review-clean close. The consumer is the user returning across sessions and days — sometimes mid-task after a context reset — who needs to trust that no time-log session was left open, no step was skipped or reordered, and no GitHub issue was mistaken for a work item in its own right.

## Resolution rules

- Bare paths and `{skill-root}` (e.g. `references/task-loop.md`) resolve from this skill's installed directory.
- `{project-root}` → the project working directory.
- `gzp-pipeline` → the skill directory's basename.

## On Activation

1. **Module registration.** If `{project-root}/_bmad/config.yaml` has no `gzp` section, or the user passed `setup`/`configure`/`install`, load `assets/module-setup.md` and complete registration before proceeding.
2. **Load config.** Read `gzp_mcp_name`, `gzp_zoho_project_name`, `gzp_default_bill_status` from `{project-root}/_bmad/config.yaml` (`gzp` section) and `{project-root}/_bmad/config.user.yaml`. If either of the first two is missing, ask for it directly (same question module setup would ask) and proceed with the answer for this session — don't block on setup having been run. Default `gzp_default_bill_status` to "Non Billable" if unset.
3. **Resume session-state.** Run `uv run scripts/session_state.py init --path {project-root}/_bmad/memory/gzp-pipeline/session-state.json` (no-op if it exists), then `show` it. This is the single source of truth for where the pipeline stands — never re-derive position from conversation history.
   - If `resolved.*` fields are null, resolve them now and write them back with `set`: call `get_portals` (single portal → use it, else ask), `get_projects_list` matched against `gzp_zoho_project_name`, the task-status field's option ids via `get_options_list_for_a_field_in_module` (never hardcode status ids — they vary per portal), and `owner/repo` from `git remote -v`.
   - If `open_time_logs` has any entries or `current_task.step` is mid-flight, report the exact state to the user (task, step, and every still-open session by task id) and resume automatically when it's unambiguous (e.g. "PR open — awaiting merge" → check the PR yourself); ask only when genuinely ambiguous (e.g. the PR check itself fails).

## Invariants

These hold across every capability below:

- **Sole Zoho-writer.** This skill is the only caller of Zoho Projects MCP tools. A dispatched subagent (research, implementation) reports a summary back rather than calling Zoho itself; fold that summary into the time-log session note you own. Each distinct subagent dispatch on a task gets its own time-log session pair.
- **GitHub issues are not work items.** Unlike a plain issue→PR ladder, a task's GitHub Flow goes straight to a branch and PR — no issue step. An issue only exists via the "Report an issue" capability, and it's always a standalone, separately-tracked artifact.
- **One task in flight at a time.** Finish (or explicitly park, updating `session-state`) the current task before starting another.
- **GPG signing is a hard checkpoint, never bypassed.** `git config commit.gpgsign` is expected already `true` locally — never override it, never pass `--no-gpg-sign`. If a commit can't be verified signed (`git log --show-signature -1`), stop and ask rather than guessing or skipping the check.
- **Non-code work skips GitHub Flow entirely.** Decide up front whether a task will touch code. If not, only Zoho status + time-log apply — no branch, issue, or PR.
- **Never fabricate verification.** A status change, a merge confirmation, a GPG-signature check, or a time-log entry must correspond to something actually called, checked, or measured. If a required tool isn't available or a call fails, say so exactly and ask how to proceed — never invent a result to keep the pipeline moving.

## Capabilities

| Capability | When | Location |
| --- | --- | --- |
| Setup / configure | Module not yet registered, or user says "setup"/"configure" | `assets/module-setup.md` |
| Start a new phase | User describes a new chunk of work to plan/break down | `references/planning-phase.md` |
| Work a task | User names a task, says "next"/"continue", or work is already in progress per `session-state` | `references/task-loop.md` |
| Report an issue | Something goes wrong mid-task and needs standalone tracking | `references/issue-report.md` |
| Ad hoc request | A request too small/unplanned to belong to an open task list | `references/task-loop.md` (Ad Hoc Requests section) |

Every capability above brackets its work with time-log sessions using the paired start/stop pattern in `references/time-log-session.md` — read it before the first `add_time_log` call of a session, since Zoho has no live timer and the mechanics aren't guessable.
