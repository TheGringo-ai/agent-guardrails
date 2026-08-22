#!/usr/bin/env python3
"""Summarise the shadow log so you can decide which rules have earned enforcement.

The point of shadow mode is that a rule should prove itself against your real working
habits before it is allowed to block anything. This turns the raw log into that decision.

Usage:
    python3 guardrails/shadow_report.py                 # default log location
    python3 guardrails/shadow_report.py --log path.log
    python3 guardrails/shadow_report.py --samples 5     # more examples per rule
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_LOG = Path(os.environ.get("GUARDRAILS_LOG", Path.home() / ".agent-guardrails" / "guard.log"))

# [2026-01-01T00:00:00] SHADOW would-deny [rule-id] Bash: snippet
SHADOW_RE = re.compile(r"^\[(?P<ts>[^\]]+)\] SHADOW would-(?P<verdict>deny|ask) \[(?P<rule>[^\]]+)\] (?P<tool>\w+): (?P<snip>.*)$")
LIVE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\] (?P<verdict>DENY|ASK) \[(?P<rule>[^\]]+)\] (?P<tool>\w+): (?P<snip>.*)$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--samples", type=int, default=3)
    args = ap.parse_args()

    path = Path(args.log)
    if not path.is_file():
        print(f"No log at {path}.\n"
              f"Run with GUARDRAILS_SHADOW=1 for a while, then come back.", file=sys.stderr)
        return 1

    shadow: dict[str, list] = defaultdict(list)
    live: dict[str, int] = defaultdict(int)
    for line in path.read_text(errors="replace").splitlines():
        if m := SHADOW_RE.match(line):
            shadow[m["rule"]].append((m["verdict"], m["tool"], m["snip"]))
        elif m := LIVE_RE.match(line):
            live[m["rule"]] += 1

    if not shadow and not live:
        print(f"{path} has no rule activity yet.")
        return 0

    if shadow:
        print("SHADOW — rules observing, blocking nothing\n" + "=" * 62)
        for rule, hits in sorted(shadow.items(), key=lambda kv: -len(kv[1])):
            verdict = hits[0][0]
            print(f"\n  {rule}  ({len(hits)} hit{'s' if len(hits) != 1 else ''}, would {verdict})")
            for _, tool, snip in hits[:args.samples]:
                print(f"      {tool}: {snip[:100]}")
            if len(hits) > args.samples:
                print(f"      … and {len(hits) - args.samples} more")

            # The whole point: turn a count into a decision.
            if len(hits) == 0:
                note = "never fired — is the pattern right?"
            elif len(hits) <= 3:
                note = "rare. Read the samples: if all are genuinely risky, promote it."
            elif len(hits) <= 15:
                note = "moderate. Check for false positives before promoting."
            else:
                note = ("NOISY. This would interrupt you constantly. Narrow it, or make it "
                        "'ask' rather than 'deny' — a rule this loud will get switched off.")
            print(f"      -> {note}")

        print("\nTo promote a rule: remove \"shadow\": true from it in rules.json,")
        print("and add an ALLOW-case to tests/cases.json proving it is not over-broad.")

    if live:
        print("\n\nENFORCING — rules that actually blocked something\n" + "=" * 62)
        for rule, n in sorted(live.items(), key=lambda kv: -kv[1]):
            print(f"  {rule:<44} {n}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
