# agent-guardrails

**Stop telling your AI coding agent what not to do. Make it structurally unable to.**

A ~150-line `PreToolUse` hook that matches an agent's *proposed* tool call against a rules
file and blocks or escalates **before** the call runs.

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/x"}}' | guardrails/guard.py
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask",
 "permissionDecisionReason":"[rm-recursive-force] Recursive force-delete. Confirm the exact target..."}}
```

## Why not just put it in CLAUDE.md?

Because that makes enforcement depend on a model *remembering* to check — every time,
forever. It will not. Context gets compacted, attention drifts, a new session starts cold,
and the one time it forgets is the time that matters.

Instructions are a preference. A hook is machinery. It holds when the model is wrong,
distracted, or has never seen your instruction at all.

And a PostToolUse hook doesn't help: warning *after* a write is useful for code smells and
useless for `rm -rf`.

## Install

```bash
git clone https://github.com/TheGringo-ai/agent-guardrails
cd agent-guardrails
cp guardrails/rules.example.json guardrails/rules.json   # then edit
python3 tests/test_guard.py                              # 37/37
```

Put the directory somewhere **outside any repo you check out or clean** — see
[LESSONS.md #2](docs/LESSONS.md) for the incident that taught us this. Then wire it in
`~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash|Write|Edit|MultiEdit|Read",
      "hooks": [{ "type": "command", "command": "/path/to/guardrails/guard.py" }]
    }]
  }
}
```

## Writing a rule

```json
{
  "id": "git-force-push",
  "tools": ["Bash"],
  "target": "command",
  "pattern": "\\bgit\\s+push\\b[^|;&\\n]*(--force(?!-with-lease)|-f\\b)",
  "decision": "ask",
  "reason": "Force-push rewrites published history. Confirm the branch.",
  "doc": "history-rewrites.md"
}
```

| field | meaning |
|---|---|
| `tools` | which tools this rule applies to |
| `target` | `command` · `path` · `content` · `action` (command+path, **not** content) · `any` |
| `pattern` | Python regex |
| `decision` | `deny` (hard block) or `ask` (route to human) |
| `reason` | shown to the agent — write it to persuade, not just to refuse |
| `doc` | optional rationale file surfaced with the block |
| `path_scope` | optional; narrows the rule to files under a subpath |

`deny` beats `ask`: all rules are evaluated and the strongest verdict wins.

## The one rule about writing rules

**A deny rule is not finished until you have written the allow-case that proves it isn't
over-broad.**

Our own exfiltration rule shipped with deny-tests only. It turned out to match its trigger
words *anywhere* in the command text — so it blocked documentation that merely described
it, and, far worse, it blocked copying the protected data to a **local backup drive**. The
guard was blocking the remedy rather than the risk. Nothing caught it because no test
asserted that anything should be *allowed*.

Writing the allow-cases for this repo also surfaced a bug where
`git push --force-with-lease` — the *safe* form — prompted every time, because a negative
lookahead sat in the wrong position. Prompting on safe operations is not harmless: it
trains you to click through prompts, which destroys the value of the ones that matter.

## Design commitments

- **Fails open.** Any internal error exits 0. A guard that blocks all work when it breaks
  gets deleted within a day, and then protects nothing. Every failure is logged.
- **High signal over high coverage.** A false deny costs more trust than a missed catch.
- **Rules grow from real mistakes**, not imagined ones.

Full write-up — three years of mistake-logging, one week of turning it into machinery:
[docs/LESSONS.md](docs/LESSONS.md) · [WRITEUP.md](WRITEUP.md)

## Tests

```
$ python3 tests/test_guard.py
...
37/37 passed
```

Includes deny-cases, matching allow-cases, wrapped-command bypasses
(`time …`, `FOO=1 …`, `sudo …`, `… && …`, `bash -c "…"`, subshells, later lines), and
fail-open guarantees for garbage payloads and a missing rules file.

## Author

By **Fred Taylor** — [thegringo.ai](https://thegringo.ai). This runs on my own machine
every day, against a real 27-repo working tree. It is new; the mistake log behind it is not.

<!-- FRED: fill in your actual years/role before publishing. The analogy below is the
     strongest thing you have and it is worth stating precisely — but state it truthfully. -->
Years on plant floors in food manufacturing before I wrote production code, which is where
the bias in this project comes from: a safety interlock that trips constantly gets
bypassed, and an interlock everyone bypasses is worse than none — because it still looks
like protection. That is the same failure mode as a noisy guardrail, and it is why this
project treats false positives as the primary risk rather than an annoyance.

## License

MIT — see [LICENSE](LICENSE).
