# Start a new phase

Every phase gets its own Zoho task list — never reuse a prior phase's list or drop tasks into the project's default/general list.

1. Agree the phase's name and rough scope with the user — a short natural-language check is fine unless there's a genuine fork in how to split it, in which case use `AskUserQuestion`.
2. **Create the task list** (`create_task_list`, named after the phase, e.g. "Phase 3: Webhook delivery retries"). Write its id/name to `session-state.current_task_list`.
3. **Create a standing Planning task** inside the new list — not one of the worked items — that the breakdown and any cross-task planning gets logged against.
4. **Start a time-log session** on the Planning task (`references/time-log-session.md`).
5. **Decide, per planned item, whether it touches code.** Break the phase into individual tasks (`create_a_task`) — one task = one logical, independently reviewable unit. Prefer more, smaller tasks. A task that's pure brainstorming/planning/testing-only is still a task; it just won't enter the code branch of `references/task-loop.md` later.
6. Surface the resulting list as a short numbered summary and confirm which task to start on (or take the first one if the user said "just go").
7. **Stop the Planning session** with a note summarizing the breakdown (e.g. "Split into N tasks, starting with X").
8. **Close the Planning task.** It's a standing task for the evaluation work, and that work is finished the moment the tasks below it exist — don't leave it open indefinitely.

If the phase's scope needs re-evaluation later (a task grows, a new task surfaces), start a fresh Planning session (a new start/stop pair) for that re-evaluation rather than leaving it untimed, and close the Planning task again afterward.

Once the breakdown is confirmed, hand off to `references/task-loop.md` for the first task.
