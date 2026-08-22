#!/usr/bin/env python3
"""agent-guardrails — a PreToolUse hook that mechanically enforces your hard rules.

Wire it on Bash|Write|Edit|MultiEdit|Read. It reads the hook payload on stdin, matches
the *proposed* action against rules.json, and blocks or escalates before the tool runs.

Why this exists
---------------
A PostToolUse hook warns AFTER a write. That is useful for code smells and useless for
`rm -rf`. The alternative — writing your rules into a CLAUDE.md or a memory file — means
enforcement depends on a model *remembering* to check, every time, forever. It will not.
Context gets compacted. Attention drifts. A new session starts cold.

This converts rules into machinery: they hold even when the model is wrong, distracted,
or has forgotten the instruction entirely.

Decisions
---------
  deny → hard block. The agent sees the reason and must find another way. Reserve this
         for irreversible or externally-consequential actions.
  ask  → routed to the human. For risky-but-legitimate actions.

deny wins over ask: every rule is evaluated and the strongest verdict is kept, rather
than stopping at the first match.

FAIL-OPEN BY DESIGN
-------------------
Any internal error — bad JSON, missing rules file, bad regex — exits 0 with no output,
so a bug here can never wedge every tool call in every session.

That trade-off is deliberate, and it was learned the hard way. See docs/LESSONS.md #1:
a guard that blocks all work when it breaks gets deleted within a day, and then it
protects nothing. Failures are appended to the log so they are never silent — trusting
silence is its own failure mode.

Quick test:
    echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}' | ./guard.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Rules live beside this script by default so they cannot be removed by a branch
# checkout (LESSONS.md #2). Override with GUARDRAILS_RULES.
RULES_FILE = Path(os.environ.get("GUARDRAILS_RULES", Path(__file__).resolve().parent / "rules.json"))
LOG_FILE = Path(os.environ.get("GUARDRAILS_LOG", Path.home() / ".agent-guardrails" / "guard.log"))

# Optional: where your rule-rationale documents live, surfaced in the block message so
# the agent (and you) can see WHY a rule exists, not just that it fired.
DOCS_DIR = os.environ.get("GUARDRAILS_DOCS", "")

# Shadow mode: evaluate rules and LOG what they would have done, but never block.
#
# This exists because the central claim of this project — that false positives are the
# primary risk — is useless if you can only discover a false positive by being blocked by
# it. Shadow mode lets you measure a rule's real-world hit rate against your own working
# habits *before* it can cost you anything.
#
# Two scopes, because they answer different questions:
#   GUARDRAILS_SHADOW=1        → everything observes. "What would this ruleset do to me?"
#   "shadow": true on a rule   → that rule alone observes. "Is my NEW rule too broad?"
#
# The second is the one you will use most: it lets a new, unproven rule run alongside
# established enforcing ones, which is how a rule should earn its way into blocking.
SHADOW_ALL = os.environ.get("GUARDRAILS_SHADOW", "").strip() not in ("", "0", "false", "no")


def _log(msg: str) -> None:
    """Record guard failures and every block. Must never raise."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        import datetime

        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with LOG_FILE.open("a") as fh:
            fh.write(f"[{stamp}] {msg}\n")
    except Exception as exc:
        # The logger must never raise — a crash here would wedge the very tool call it is
        # only meant to observe. But it must not vanish either: stderr from a hook
        # surfaces in the transcript, so a broken log path stays visible.
        try:
            print(f"guardrails: log write failed ({exc}): {msg}", file=sys.stderr)
        except Exception:
            # DELIBERATE last-resort swallow, and the only one in this file.
            # We are already in the failure path of the failure path: the log write
            # failed AND stderr is unavailable. Raising here would propagate out of a
            # hook and turn an unwritable log file into a blocked tool call — the exact
            # outcome fail-open exists to prevent. There is nowhere left to report to.
            # Do NOT copy this pattern anywhere that has a reporting channel left.
            pass


def _haystacks(tool: str, ti: dict) -> dict[str, str]:
    """Build the strings a rule can match against, per target type.

    Choosing the right target is the single most common way to get this wrong.
    See docs/LESSONS.md #3.
    """
    command = str(ti.get("command", "")) if tool == "Bash" else ""
    path = str(ti.get("file_path", "") or ti.get("path", "") or "")

    if "content" in ti:                       # Write
        content = str(ti["content"])
    elif "new_string" in ti:                  # Edit
        content = str(ti["new_string"])
    elif "edits" in ti:                       # MultiEdit
        content = "\n".join(str(e.get("new_string", "")) for e in ti.get("edits", []))
    else:
        content = ""

    return {
        "command": command,
        "path": path,
        "content": content,
        # "action" = what the call DOES (a shell command or a target file), EXCLUDING the
        # text being written. This is the right target for protected-resource rules:
        # writing documentation that merely mentions a protected resource must not trip a
        # rule meant to stop you from touching it.
        "action": "\n".join([command, path]),
        # "any" scans everything the call carries, including written content. Reserve it
        # for rules that are genuinely about written text (e.g. a license check).
        "any": "\n".join([command, path, content]),
    }


def _matches(rule: dict, tool: str, hay: dict[str, str]) -> bool:
    if tool not in rule.get("tools", []):
        return False

    target = rule.get("target", "any")
    text = hay.get(target, "")
    if not text:
        return False

    # path_scope narrows a rule to files under a subpath, so e.g. a license check fires
    # inside product repos without firing on scratch files.
    scope = rule.get("path_scope")
    if scope and scope not in hay.get("path", ""):
        return False

    try:
        return re.search(rule["pattern"], text) is not None
    except re.error as exc:
        _log(f"BAD REGEX in rule '{rule.get('id')}': {exc}")
        return False


def _emit(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                            # unreadable payload → stay out of the way

    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    if not tool or not isinstance(ti, dict):
        sys.exit(0)

    try:
        rules = json.loads(RULES_FILE.read_text()).get("rules", [])
    except Exception as exc:
        _log(f"RULES UNREADABLE ({RULES_FILE}): {exc} — failing open")
        sys.exit(0)

    hay = _haystacks(tool, ti)

    # deny wins over ask, so evaluate every rule and keep the strongest verdict rather
    # than stopping at the first match.
    hits = [r for r in rules if _matches(r, tool, hay)]
    if not hits:
        sys.exit(0)

    # Shadow rules must not influence the live verdict at all — otherwise a rule you are
    # still evaluating could suppress a real block by winning the "strongest verdict"
    # contest. Split them out before choosing.
    shadow_hits = [r for r in hits if SHADOW_ALL or r.get("shadow")]
    live_hits = [] if SHADOW_ALL else [r for r in hits if not r.get("shadow")]

    snippet = (hay["command"] or hay["path"])[:160].replace("\n", " ")

    for r in shadow_hits:
        would = "deny" if r.get("decision") == "deny" else "ask"
        _log(f"SHADOW would-{would} [{r.get('id')}] {tool}: {snippet}")

    if not live_hits:
        sys.exit(0)                            # only shadow rules matched → allow

    denies = [r for r in live_hits if r.get("decision") == "deny"]
    chosen = denies[0] if denies else live_hits[0]
    decision = "deny" if denies else "ask"

    reason = f"[{chosen.get('id')}] {chosen.get('reason', 'Blocked by guard rule.')}"
    if chosen.get("doc") and DOCS_DIR:
        reason += f"\n\nRule rationale: {DOCS_DIR}/{chosen['doc']}"
    if decision == "deny":
        reason += (
            "\n\nThis is a hard rule, not a preference. Do not retry a reworded version "
            "of the same action — explain the block to the user and ask how to proceed."
        )

    _log(f"{decision.upper()} [{chosen.get('id')}] {tool}: {snippet}")

    _emit(decision, reason)
    sys.exit(0)


if __name__ == "__main__":
    main()
