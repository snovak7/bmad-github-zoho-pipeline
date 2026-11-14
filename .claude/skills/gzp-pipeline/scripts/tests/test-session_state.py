#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Unit tests for session_state.py. Run: uv run scripts/tests/test-session_state.py"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "session_state.py"


def run(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )
    return result


def parse_stdout(result):
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_init_creates_default_schema(tmp_path):
    state_file = tmp_path / "session-state.json"
    result = run("init", "--path", str(state_file))
    assert result.returncode == 0, result.stderr
    payload = parse_stdout(result)
    assert payload["ok"] is True
    assert payload["created"] is True
    data = json.loads(state_file.read_text())
    assert data["current_task"] == {"id": None, "title": None, "step": None, "issue_number": None, "branch": None, "pr_number": None}
    assert data["issue_tasks"] == []


def test_init_is_idempotent(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    result = run("init", "--path", str(state_file))
    payload = parse_stdout(result)
    assert payload["created"] is False


def test_set_and_get_dotted_path(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    result = run("set", "--path", str(state_file), "current_task.id", '"T-1"')
    assert result.returncode == 0, result.stderr
    result = run("get", "--path", str(state_file), "current_task.id")
    payload = parse_stdout(result)
    assert payload["value"] == "T-1"


def test_set_unknown_top_level_field_fails(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    result = run("set", "--path", str(state_file), "bogus.field", '"x"')
    assert result.returncode == 1
    payload = json.loads(result.stderr.strip())
    assert payload["ok"] is False
    assert "bogus" in payload["error"]


def test_add_and_close_issue_task(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    result = run(
        "add-issue-task",
        "--path", str(state_file),
        "--issue-number", "7",
        "--task-id", "T-99",
        "--time-log-id", "TL-1",
    )
    assert result.returncode == 0, result.stderr
    result = run("add-issue-task", "--path", str(state_file), "--issue-number", "7", "--task-id", "T-99")
    assert result.returncode == 1

    result = run("close-issue-task", "--path", str(state_file), "--issue-number", "7")
    payload = parse_stdout(result)
    assert payload["entry"]["status"] == "closed"

    result = run("close-issue-task", "--path", str(state_file), "--issue-number", "999")
    assert result.returncode == 1


def test_clear_current_task_resets_current_task_only(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    run("set", "--path", str(state_file), "current_task.id", '"T-1"')
    run("open-time-log", "--path", str(state_file), "--task-id", "T-99", "--time-log-id", "TL-1", "--started-at", "9:00 AM")
    result = run("clear-current-task", "--path", str(state_file))
    payload = parse_stdout(result)
    assert payload["current_task"]["id"] is None
    data = json.loads(state_file.read_text())
    assert "T-99" in data["open_time_logs"]


def test_open_and_close_time_log_keyed_by_task(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    result = run("open-time-log", "--path", str(state_file), "--task-id", "T-1", "--time-log-id", "TL-1", "--started-at", "9:00 AM")
    assert result.returncode == 0, result.stderr

    # A second, unrelated task can have its own concurrent open session.
    result = run("open-time-log", "--path", str(state_file), "--task-id", "T-2", "--time-log-id", "TL-2", "--started-at", "9:05 AM")
    assert result.returncode == 0, result.stderr

    # Opening a second session on the same task fails rather than silently overwriting.
    result = run("open-time-log", "--path", str(state_file), "--task-id", "T-1", "--time-log-id", "TL-3", "--started-at", "9:10 AM")
    assert result.returncode == 1

    result = run("close-time-log", "--path", str(state_file), "--task-id", "T-1")
    assert result.returncode == 0, result.stderr
    data = json.loads(state_file.read_text())
    assert "T-1" not in data["open_time_logs"]
    assert "T-2" in data["open_time_logs"]  # closing T-1's session must not touch T-2's

    result = run("close-time-log", "--path", str(state_file), "--task-id", "T-1")
    assert result.returncode == 1


def test_init_migrates_legacy_github_keys(tmp_path):
    state_file = tmp_path / "session-state.json"
    legacy = {
        "resolved": {"zoho_mcp_name": "z", "github_tool": "gh", "repo_owner": "o", "repo_name": "r"},
        "current_task_list": {"id": None, "name": None},
        "current_task": {"id": "T-1", "title": "t", "step": "in_progress", "github_issue": 7},
        "open_time_logs": {},
        "issue_tasks": [],
    }
    state_file.write_text(json.dumps(legacy))
    result = run("init", "--path", str(state_file))
    assert result.returncode == 0, result.stderr
    payload = parse_stdout(result)
    assert payload["created"] is False
    assert payload["migrated"], payload
    data = json.loads(state_file.read_text())
    assert "github_tool" not in data["resolved"]
    assert data["resolved"]["forge"] == "github"
    assert data["resolved"]["forge_tool"] == "cli"
    assert data["resolved"]["forge_cli"] == "gh"
    assert data["resolved"]["repo_host"] is None
    assert "github_issue" not in data["current_task"]
    assert data["current_task"]["issue_number"] == 7
    assert data["current_task"]["pr_number"] is None
    again = parse_stdout(run("init", "--path", str(state_file)))
    assert again["migrated"] == []


def test_load_migrates_legacy_mcp_tool_in_memory(tmp_path):
    state_file = tmp_path / "session-state.json"
    state_file.write_text(json.dumps({"resolved": {"github_tool": "mcp"}, "current_task": {}}))
    payload = parse_stdout(run("get", "--path", str(state_file), "resolved.forge_tool"))
    assert payload["value"] == "mcp"


def test_open_time_log_without_id_for_windshift(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    result = run("open-time-log", "--path", str(state_file), "--task-id", "PROJ-42",
                 "--started-at", "09:10", "--started-on", "2026-11-14")
    assert result.returncode == 0, result.stderr
    data = json.loads(state_file.read_text())
    assert data["open_time_logs"]["PROJ-42"] == {"time_log_id": None, "started_at": "09:10", "started_on": "2026-11-14"}
    closed = parse_stdout(run("close-time-log", "--path", str(state_file), "--task-id", "PROJ-42"))
    assert closed["closed_entry"]["started_on"] == "2026-11-14"


def test_init_adds_windshift_fields_to_existing_state(tmp_path):
    state_file = tmp_path / "session-state.json"
    run("init", "--path", str(state_file))
    data = json.loads(state_file.read_text())
    del data["resolved"]["windshift_workspace_id"]
    del data["resolved"]["tracker"]
    state_file.write_text(json.dumps(data))
    payload = parse_stdout(run("init", "--path", str(state_file)))
    assert "added resolved.tracker" in payload["migrated"], payload
    data = json.loads(state_file.read_text())
    assert data["resolved"]["windshift_workspace_id"] is None


def main():
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                test(Path(tmp))
                print(f"PASS {test.__name__}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {test.__name__}: {exc}")
    if failures:
        print(f"{failures} failure(s)")
        return 1
    print("All tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
