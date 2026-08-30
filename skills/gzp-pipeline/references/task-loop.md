# Work a task

Set `session-state.current_task` to the task being worked (id, title) before doing anything else, so an interruption mid-task is always recoverable. `STATE` below stands for `{project-root}/_bmad/memory/gzp-pipeline/session-state.json`; `<task-id>` is `current_task.id`. If a `TodoWrite` list from `references/planning-phase.md` is active for this phase, mark this task's item `in_progress` now too — and `completed` when the task closes at the end of either path below.

## Decide the branch first

Does this task produce a code change? If no — pure brainstorming, planning, or testing-only work — skip straight to **Non-code path** below. Otherwise use **Code path**. This decision is made once per task, up front; don't re-litigate it mid-task.

## Code path

1. **Set status "In Progress"** on the Zoho task (using `session-state.resolved.status_option_ids`), and `uv run scripts/session_state.py set --path STATE current_task.step '"in_progress"'`.
2. **Start a time-log session** on `<task-id>` (`references/time-log-session.md`) covering the implementation segment.
3. **Implement the task's scope.** Create a branch named after the Zoho task id/title (e.g. `feature/<task-id>-<short-slug>`), fetching and updating from the base branch first. Don't stash or discard unrelated uncommitted changes already in the tree — scope your own staging carefully.
   - **Always work from a local git clone**, even for a repo other than the current working directory (resolve via `session-state.resolved.repo_owner`/`repo_name`, or an explicit override when the user names a different repo for this task). Clone it locally rather than editing via GitHub API file-write tools (`create_or_update_file`, `push_files`) — those bypass local git entirely and the resulting commit won't carry the user's own GPG signature.
4. **Verify before staging.** Build/test the affected code. Stage explicitly by path (never a blind `git add -A`) and diff what's staged before committing.
5. **Commit, push, open the PR.** Conventional commit message. PR body: summary bullets and a Test plan checklist — only check `[x]` what actually ran.
   - `git config commit.gpgsign` is expected already `true` locally — never override it, never pass `--no-gpg-sign`. After committing, spot-check `git log --show-signature -1` shows a good signature from the user's key, not just GitHub's own web-verification. If it doesn't, stop and ask rather than guessing or skipping the check.
   - Assign the PR to the user (resolve their GitHub identity via `get_me` once per session if not already known).
   - Attach labels that actually fit the repo's existing label set — don't invent new ones speculatively.
6. **Set status "In Review"** on the Zoho task, and `set current_task.step '"pr_open_awaiting_merge"'`.
7. **Stop the time-log session** from step 2, with a note summarizing what was implemented and the PR number.
8. **Wait. Do not proceed until the PR is confirmed merged.** When the user's message implies merge status ("continue", "next", "merged") or is otherwise ambiguous, verify yourself via `pull_request_read` rather than asking them to restate it. Only ask when the check itself is inconclusive (closed-not-merged, or the call fails).
9. **Check for open feedback before treating the merge as done.** Read the PR's description-level comments and review comments. If there's actionable feedback not already addressed pre-merge:
   - Keep the task's status at "In Review"/"In Progress" — don't close it yet. Set `current_task.step` to `"addressing_review_feedback"`.
   - Start a new time-log session on `<task-id>` (a fresh pair — never reopen or extend the one from step 2/7).
   - Address the feedback, then stop that session with a note on what was addressed. Set `current_task.step` back to `"pr_open_awaiting_merge"`.
   - Repeat until there's no more open feedback.
   - Bot reviews (Sourcery, CodeRabbit, etc.) don't need a reply comment — verify the finding against the actual diff (bots produce false positives), record what was found/done in the time-log note, and only reply on the PR if the user explicitly asks.
10. **Close out.** Add a final note (task comment and/or the last session's note) summarizing the work across all sessions and linking the merged PR(s). **Set status "Closed."**

## Non-code path

1. **Set status "In Progress"** and `set current_task.step '"in_progress"'`.
2. **Start a time-log session** on `<task-id>` covering the work (brainstorming, planning, testing, research — whatever the task actually is).
3. Do the work.
4. **Stop the session** with a note on what was produced/decided.
5. **Set status "Closed."** No branch, no issue, no PR — nothing GitHub-side happens for this task.

## After either path

Clear the current task: `uv run scripts/session_state.py clear-current-task --path STATE`. Then wait for new instructions — if more tasks are already broken out in the phase's list, either the user names the next one or you take the next open one and confirm. Only re-enter `references/planning-phase.md` when the user starts a genuinely new phase.

## Ad Hoc Requests

Not everything arrives as "start the next task from the list." A mid-session ask that doesn't fit an open task list — "merge these PRs", "fix Y real quick" — still needs a task and a time-log session *before* work starts, not skipped because it feels too small and not batched up as a retroactive log afterward. This is the exact failure mode the pipeline exists to prevent.

1. If an existing open task list is genuinely the right home for it, add the task there. Otherwise create a small task list for it (e.g. "Repo maintenance: <short description>") rather than skipping list creation because it's "just one thing."
2. Create the task (self-assigned, same as any other — see Invariants in `SKILL.md`), start a time-log session on it, *then* start the work. Add it to the active `TodoWrite` mirror if one exists for this phase; otherwise a single-item list is fine.
3. Run it through the normal lifecycle above (code or non-code path, whichever fits).

If a session catches itself having skipped this, don't just apologize and move on — create the missed task(s) now, reconstruct the time as accurately as possible (commit timestamps, prior task's close time as an anchor), and note in the log that it's a retroactive entry.
