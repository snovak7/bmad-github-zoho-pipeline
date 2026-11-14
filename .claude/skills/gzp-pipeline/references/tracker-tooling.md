# Tracker tooling

The tracker is where work items, statuses, and time logs live. `gzp_tracker` picks it: `zoho` (Zoho Projects), `windshift` ([Windshift](https://windshift.sh), through its built-in MCP server), or `none`. The other reference files use generic words, and this file maps them to each tracker:

| Generic term | Zoho Projects | Windshift |
| --- | --- | --- |
| project | the project named by `gzp_zoho_project_name` | the workspace named by `gzp_windshift_workspace_name` |
| phase list | a task list | a parent work item for the phase; its tasks are child items |
| tracker task | a task (its id, plus a prefix like `ECM-T101`) | a work item (numeric id, plus a key like `PROJ-42`) |
| task key (used in branch names) | the task prefix, lowercased (`ecm-t101`) | the item key, lowercased (`proj-42`) |
| status change | the task-status field set to an option id | `transition_item` (workflow rules apply) |
| time log | a Zoho time-log entry on the task | a worklog on the workspace's time project, linked to the item |

With `gzp_tracker: none`, no tracker tools are called at all (see the tracker invariant in `SKILL.md`).

The tracker's MCP server is the only way in: neither tracker has a CLI path in this pipeline. Use the tool names from the connected server's own tool list. The names below are what each server exposes today.

## Resolve at activation

Write each value to `session-state.resolved` with `uv run scripts/session_state.py set`, and set `resolved.tracker` to the configured tracker. Re-resolve when the fields are null or `resolved.tracker` differs from config.

### Zoho Projects

The MCP server is `gzp_zoho_mcp_name`. Resolve:
- `portal_id`: `get_portals` (single portal → use it, else ask);
- `zoho_project_id`/`zoho_project_name`: `get_projects_list` matched against `gzp_zoho_project_name`;
- `status_option_ids`: the task-status field's option ids from `get_options_list_for_a_field_in_module`. Never hardcode status ids, since they vary per portal;
- `zoho_user` (`zuid`/`zpuid`/`name`): `get_current_user_details`, needed to self-assign every task.

### Windshift

The MCP server is `gzp_windshift_mcp_name`. It is the instance's `/mcp` endpoint, which the admin enables with `--mcp` or `MCP_ENABLED=true`. Your user needs the `mcp:access` permission. Resolve:
- `windshift_workspace_id`/`windshift_workspace_key`: `list_workspaces` matched by name against `gzp_windshift_workspace_name`. Several matches, or none → ask.
- `windshift_time_project_id`: when `gzp_windshift_time_project` is set, match it by name in `list_time_projects` (status `Active`). Otherwise use the workspace's own `time_project_id` (from `get_workspace`). If that's empty too, ask which time project to book against, and save the answer as `gzp_windshift_time_project` in the `gzp` section of `config.yaml`. In an unattended run, report it as a blocker instead.
- `status_option_ids`: `list_statuses` for the workspace, matched by name to the three roles the pipeline uses, "In Progress", "In Review" and "Closed". Store them as `{"In Progress": <id>, "In Review": <id>, "Closed": <id>}`. If a role has no status of that name, use the closest one: for "Closed", a status with `is_completed: true`. When the match is a guess, ask once and save the answer here. In an unattended run, report it as a blocker.
- `windshift_user_id`: Windshift has no "who am I" tool. Call `find_users` with the `user_name` from `config.user.yaml`, restricted to the workspace. A single match is you. Several matches, or none → ask.
- `windshift_timezone`: `get_temporal_context`. Windshift takes times as local wall-clock values in this zone.

## Operation map

| Operation | Zoho Projects | Windshift |
| --- | --- | --- |
| Create phase list | `create_task_list` named after the phase | `create_item` in the workspace, titled after the phase, with `assignee_id` = `windshift_user_id`. Use an item type above the default task type if `list_item_types` shows one (e.g. an Epic); otherwise use the default type |
| Create tracker task (self-assigned) | `create_a_task` in the list, `owners_and_work.owners` = `resolved.zoho_user` | `create_item` with `parent_id` = the phase item's id and `assignee_id` = `windshift_user_id` |
| Set status | the task-status field → `status_option_ids[<role>]` | `transition_item` with the item key and `to_status_id` = `status_option_ids[<role>]` |
| Task comment / final note | the task's comment tool | `add_comment` on the item key |
| Find a task again | `get_task_details` | `get_item` with the key |
| Time logs | `references/time-log-session.md`, Zoho section | `references/time-log-session.md`, Windshift section |

Record the phase list in `session-state.current_task_list` (Windshift: the parent item's key as `id`, its title as `name`). Record tracker tasks by their id (Zoho) or key (Windshift) in `current_task.id`.

A `transition_item` that the workflow rejects (no transition from the current status, or a condition fails) is a failed call. Report the exact error. Don't report the status as changed, and never fall back to `update_item`, which can't change status.
