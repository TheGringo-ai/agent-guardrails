# agent-guardrails

**Stop telling your AI coding agent what not to do. Make it structurally unable to.**

A small `PreToolUse` hook that matches an agent's *proposed* tool call against a rules
file and blocks or escalates **before** the call runs.

Your rules become a file you can review, version, test, and check into a repo — and every
block leaves an audit line. If your team is letting coding agents touch real
infrastructure, this is the smallest thing that turns "we told it not to" into something
you can actually point at.

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
python3 tests/test_guard.py                              # 41/41
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

## Start in shadow mode — you don't have any rules yet

The advice everywhere below is *grow rules from real mistakes, not imagined ones*. On day
one you have no logged mistakes, so that advice is useless to you. Shadow mode is the
answer: rules observe and log, and block nothing.

```bash
GUARDRAILS_SHADOW=1        # in your shell profile, or the hook's env
# ...work normally for a week...
python3 guardrails/shadow_report.py
```

```
  rm-recursive-force  (5 hits, would ask)
      Bash: rm -rf /tmp/build
      Bash: rm -rf node_modules
      Bash: rm -rf dist
      -> moderate. Check for false positives before promoting.
```

That output is doing real work. Three of those five are routine build cleanup — so
enforcing that rule as written would nag you constantly, and a rule that nags gets
switched off. Now you know that *before* it costs you anything, instead of finding out by
being interrupted.

Two scopes, answering different questions:

| | question it answers |
|---|---|
| `GUARDRAILS_SHADOW=1` | "What would this whole ruleset do to me?" |
| `"shadow": true` on one rule | "Is my **new** rule too broad?" |

The second is the one you'll use most: a new, unproven rule observes while your
established rules keep enforcing. That's how a rule earns its way into blocking.

Shadow rules never influence the live verdict — a rule you're still evaluating can't
accidentally suppress a real block.

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
| `shadow` | optional; `true` = observe and log only, never block |

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
41/41 passed
```

Includes deny-cases, matching allow-cases, wrapped-command bypasses
(`time …`, `FOO=1 …`, `sudo …`, `… && …`, `bash -c "…"`, subshells, later lines), and
fail-open guarantees for garbage payloads and a missing rules file, plus shadow-mode
behaviour (a shadowed rule must not block, and must not suppress an enforcing one).

## For teams

A rules file is org policy for agents, in a form you can actually enforce and review:

- **Check `rules.json` into the repo.** Policy travels with the codebase and changes go
  through code review like anything else.
- **Point `doc` at your rationale.** The agent surfaces it in the block message, so a
  block explains itself instead of just refusing. New joiners read the same document.
- **The log is the audit trail.** Every block and every shadow hit is a timestamped line:
  what was attempted, which rule caught it, when.
- **Roll out in shadow first.** Ship a policy to the team observing-only, collect a week
  of `shadow_report.py` output across everyone, and promote the rules that proved
  themselves. Enforcing an untested ruleset across a team is how you get it disabled
  team-wide on day two.

The honest limit: this is a **regex matcher on tool input**, not a sandbox. It stops
mistakes, not a determined adversary — anyone who wants to get around a pattern can. Treat
it as the guardrail on the stairs, not the lock on the vault. If you need real containment,
you need actual isolation, and this sits alongside that rather than replacing it.

## Author

By **Fred Taylor** — [thegringo.ai](https://thegringo.ai). This runs on my own machine
every day, against a real 27-repo working tree. It is new; the mistake log behind it is not.

A decade on plant floors in food manufacturing before I wrote production code, which is
where the bias in this project comes from: a safety interlock that trips constantly gets
bypassed, and an interlock everyone bypasses is worse than none — because it still looks
like protection. That is the same failure mode as a noisy guardrail, and it is why this
project treats false positives as the primary risk rather than an annoyance.

## License

MIT — see [LICENSE](LICENSE).
