# Time-log sessions

This file applies only when a tracker is configured (`gzp_tracker` is `zoho` or `windshift`). With `gzp_tracker: none` there are no time-log sessions and nothing here runs.

A *session* brackets one segment of work on one tracker task: it starts when the work starts and stops when the segment ends. `open_time_logs` in `session-state` is keyed by task id, not a single slot. The primary task and an in-flight issue-task (`references/issue-report.md`) can each have a session open at once, so always pass the exact `task_id` you're acting on.

**Never compute or type in a duration yourself.** Both trackers derive it from the start and end times.

A task can have several sessions over its life (planning, implementation, post-review follow-up, a subagent dispatch). Always start a fresh session when work resumes rather than reusing or extending a closed one. If `open-time-log` for a task id fails because one is already open, that's a dangling session from an interrupted run. Stop it first, with a best-effort end time and the note "recovered after interruption", before opening the new one.

## Zoho Projects

Zoho's time-log tools have no live timer: `add_time_log` only accepts a *finished* entry (`hours`, or a `start_time` **and** `end_time` together). A session is simulated with two calls bracketing the work.

**Start.** The moment work begins on a task: get the wall-clock time (`date +"%I:%M %p"`). Call `add_time_log` for the task with:
- `date` = today;
- `start_time` = that time, and `end_time` = that same time (a zero-length placeholder);
- `bill_status` = `gzp_default_bill_status`, unless the task clearly calls for something else;
- a note like "Session started."

Record the returned time-log `id`:

```
uv run scripts/session_state.py open-time-log --path {project-root}/_bmad/memory/gzp-pipeline/session-state.json --task-id <task-id> --time-log-id <returned-id> --started-at "<time>"
```

**Stop.** When the segment ends: get the wall-clock time again and call `update_single_time_log` on that same `timelog_id`, setting `end_time` to the new time. Append a one-line summary of what was actually done to `notes`/`extra_data.notes`, never leaving it blank. Then close the session:

```
uv run scripts/session_state.py close-time-log --path {project-root}/_bmad/memory/gzp-pipeline/session-state.json --task-id <task-id>
```

## Windshift

Windshift's MCP server has no tool for editing a worklog after it's created, and its timer (`start_timer`/`stop_timer`) allows only one running timer per user. That can't carry two concurrent sessions, and it collides with a timer you start yourself in the Windshift UI. So the pipeline doesn't use the timer. It records the start in `session-state` and books one finished worklog with `log_time` when the session stops. Nothing appears in Windshift while a session is open. `session-state` is the record until then.

**Start.** The moment work begins on a task: call `get_temporal_context` and take `local_now` (as `HH:MM`) and `local_date`. These are the authoritative wall-clock values in your Windshift timezone, so don't use the shell's clock here. Record them, with no time-log id yet:

```
uv run scripts/session_state.py open-time-log --path {project-root}/_bmad/memory/gzp-pipeline/session-state.json --task-id <item-key> --started-at "<HH:MM>" --started-on "<YYYY-MM-DD>"
```

**Stop.** When the segment ends, call `get_temporal_context` again for the end time. Then call `log_time` with:
- `project_id` = `resolved.windshift_time_project_id`;
- `item_key` = the task's item key;
- `date` = the session's `started_on`;
- `start_time` = `started_at`, and `end_time` = the new `HH:MM`;
- `description` = a one-line summary of what was actually done, never blank.

Pass the times exactly as returned. Never convert them or add a timezone offset. Then close the session, and mention the returned worklog `id` in your report:

```
uv run scripts/session_state.py close-time-log --path {project-root}/_bmad/memory/gzp-pipeline/session-state.json --task-id <item-key>
```

Edge cases:
- **The session crossed midnight:** book two worklogs, from `started_at` to `23:59` on `started_on`, and from `00:00` to the end time on the new date. Use the same description, marked "(continued)" on the second.
- **The session lasted under a minute** (start and end are the same `HH:MM`): don't book a zero-length worklog. Close the session and say it was too short to book.
- **`log_time` fails** (time project inactive, no permission): leave the session open in `session-state`, so the time isn't lost. Report the exact error and ask how to proceed. In an unattended run, report it as a blocker.
