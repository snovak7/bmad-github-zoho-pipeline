#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Tests for merge-config.py's conditional-variable handling.

Run: uv run scripts/tests/test-merge-config.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "merge-config.py"
MODULE_YAML = Path(__file__).resolve().parent.parent.parent / "assets" / "module.yaml"


def run_merge(tmp: Path, module_answers: dict, config: dict | None = None, user: dict | None = None):
    config_path = tmp / "config.yaml"
    user_path = tmp / "config.user.yaml"
    answers_path = tmp / "answers.json"
    if config is not None:
        config_path.write_text(yaml.safe_dump(config))
    if user is not None:
        user_path.write_text(yaml.safe_dump(user))
    answers_path.write_text(json.dumps({"module": module_answers}))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--config-path", str(config_path), "--user-config-path", str(user_path),
         "--module-yaml", str(MODULE_YAML), "--answers", str(answers_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    cfg = yaml.safe_load(config_path.read_text()) or {}
    usr = yaml.safe_load(user_path.read_text()) if user_path.exists() else {}
    return out, cfg.get("gzp", {}), usr or {}


ZOHO_ANSWERS = {
    "gzp_tracker": "zoho",
    "gzp_zoho_mcp_name": "Zoho MCP",
    "gzp_zoho_project_name": "NE-4",
    "gzp_default_bill_status": "Non Billable",
    "gzp_windshift_mcp_name": "",
    "gzp_windshift_workspace_name": "",
    "gzp_windshift_time_project": "",
    "gzp_forge": "github",
    "gzp_forge_tool": "mcp",
    "gzp_forge_mcp_name": "GitHub MCP",
}


def test_windshift_selected_drops_zoho_keys(tmp: Path):
    answers = dict(ZOHO_ANSWERS, gzp_tracker="windshift", gzp_windshift_mcp_name="WS MCP",
                   gzp_windshift_workspace_name="Platform")
    out, section, user = run_merge(tmp, answers, user={"user_name": "Simon", "gzp_zoho_mcp_name": "Zoho MCP"})
    for key in ("gzp_zoho_mcp_name", "gzp_zoho_project_name", "gzp_default_bill_status"):
        assert key not in section, (key, section)
        assert key not in user, (key, user)
    assert section["gzp_windshift_workspace_name"] == "Platform"
    assert user["gzp_windshift_mcp_name"] == "WS MCP"
    assert "gzp_zoho_mcp_name" in out["user_keys_removed"]
    assert user["user_name"] == "Simon"


def test_zoho_selected_drops_windshift_keys(tmp: Path):
    out, section, user = run_merge(
        tmp, ZOHO_ANSWERS,
        config={"gzp": {"gzp_windshift_workspace_name": "Old"}},
        user={"gzp_windshift_mcp_name": "WS MCP"},
    )
    for key in ("gzp_windshift_mcp_name", "gzp_windshift_workspace_name", "gzp_windshift_time_project"):
        assert key not in section, (key, section)
        assert key not in user, (key, user)
    assert section["gzp_zoho_project_name"] == "NE-4"
    assert user["gzp_zoho_mcp_name"] == "Zoho MCP"


def test_tracker_none_drops_both(tmp: Path):
    _, section, user = run_merge(tmp, dict(ZOHO_ANSWERS, gzp_tracker="none"),
                                 user={"gzp_zoho_mcp_name": "Zoho MCP", "gzp_windshift_mcp_name": "WS"})
    assert not any(k.startswith(("gzp_zoho_", "gzp_windshift_")) for k in section), section
    assert not any(k.startswith(("gzp_zoho_", "gzp_windshift_")) for k in user), user
    assert "gzp_default_bill_status" not in section


def test_user_settings_never_land_in_shared_section(tmp: Path):
    _, section, user = run_merge(tmp, ZOHO_ANSWERS)
    for key in ("gzp_zoho_mcp_name", "gzp_forge_tool", "gzp_forge_mcp_name"):
        assert key not in section, (key, section)
        assert key in user, (key, user)


def test_forge_cli_drops_forge_mcp_name(tmp: Path):
    _, section, user = run_merge(tmp, dict(ZOHO_ANSWERS, gzp_forge_tool="cli"),
                                 user={"gzp_forge_mcp_name": "GitHub MCP"})
    assert "gzp_forge_mcp_name" not in user, user
    assert user["gzp_forge_tool"] == "cli"


def test_gate_from_existing_config_when_not_answered(tmp: Path):
    answers = {k: v for k, v in ZOHO_ANSWERS.items() if k != "gzp_tracker"}
    _, section, _ = run_merge(tmp, answers, config={"gzp": {"gzp_tracker": "windshift"}})
    assert "gzp_zoho_project_name" not in section, section


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
