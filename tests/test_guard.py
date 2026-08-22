#!/usr/bin/env python3
"""Regression suite for guard.py.

Fixtures live in cases.json rather than inline, because for the Bash tool the ENTIRE
script text is tool_input.command — so a test file containing protected strings as
literals would trip the very guard it is testing. (LESSONS.md #4.)

Run:  python3 tests/test_guard.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "guardrails" / "guard.py"
CASES = Path(__file__).parent / "cases.json"
# Test against the shipped example rules, not the user's private rules.json.
RULES = ROOT / "guardrails" / "rules.example.json"


def decide(tool: str, ti: dict) -> str:
    env = {**os.environ, "GUARDRAILS_RULES": str(RULES)}
    p = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps({"tool_name": tool, "tool_input": ti}),
        capture_output=True,
        text=True,
        env=env,
    )
    if p.returncode != 0:
        return f"CRASH(rc={p.returncode})"
    out = p.stdout.strip()
    if not out:
        return "allow"
    try:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return f"UNPARSEABLE({out[:60]})"


def main() -> int:
    cases = json.loads(CASES.read_text())
    passed = failed = 0

    for label, tool, ti, expected in cases:
        got = decide(tool, ti)
        ok = got == expected
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        print(f"{'PASS' if ok else 'FAIL'}  {label:<38} expected={expected:<6} got={got}")

    # Fail-open guarantees: a broken payload must never block a tool call.
    for label, payload in [
        ("fail-open:garbage", "not json at all"),
        ("fail-open:empty", ""),
        ("fail-open:no tool", json.dumps({"tool_input": {}})),
    ]:
        p = subprocess.run([sys.executable, str(GUARD)], input=payload,
                           capture_output=True, text=True)
        ok = p.returncode == 0 and not p.stdout.strip()
        passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
        print(f"{'PASS' if ok else 'FAIL'}  {label:<38} rc={p.returncode}")

    # A missing rules file must also fail open, not block everything.
    env = {**os.environ, "GUARDRAILS_RULES": "/nonexistent/rules.json"}
    p = subprocess.run([sys.executable, str(GUARD)],
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}),
                       capture_output=True, text=True, env=env)
    ok = p.returncode == 0 and not p.stdout.strip()
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    print(f"{'PASS' if ok else 'FAIL'}  {'fail-open:missing rules':<38} rc={p.returncode}")

    print(f"\n{passed}/{passed + failed} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
