# Lessons

Every one of these came from something going wrong in production use, not from design.
They are ordered by how much pain they caused.

---

## 1. Fail open, always

A guard that blocks work when it breaks gets deleted within a day — and then it protects
nothing. Zero enforcement beats negative enforcement, because negative enforcement gets
the whole idea thrown out.

Bad JSON, a missing rules file, a malformed regex, an unreadable payload: all exit 0
silently. Every failure is logged, because trusting silence is its own failure mode.

There is exactly one `except: pass` in the codebase — in the failure path of the *logger*,
where there is genuinely nowhere left to report to. It is commented as such. Everywhere
else, failures are recorded.

## 2. Never let the guard live somewhere it can be deleted

The original version lived inside a working repository. Checking out a branch that
predated it deleted the hook script mid-session. A hook that cannot start is treated as a
denial, so **every** tool call was refused — including the ones needed to restore the
file. There was no route back from inside the session.

The guard, its rules, and its tests must live outside any tree you check out, branch, or
`git clean`. Add a launcher that exits 0 if the script or interpreter is missing, so a
vanished guard degrades to no-enforcement instead of total-lockout.

## 3. Pick the right match target — this is the #1 source of false positives

For a shell tool, the *entire script text* is the command string. So a rule that scans
everything will fire on a script that merely **contains** a protected string as data.

The very first day this shipped, a rule meant to stop us touching a protected directory
blocked a documentation file that *described* the rule.

Targets:

| target | matches | use for |
|---|---|---|
| `command` | the shell command | destructive-command rules |
| `path` | the target file path | protected-location rules |
| `content` | text being written | rules genuinely about written text (a license check) |
| `action` | command + path, **not content** | protected-*resource* rules |
| `any` | everything | almost never |

If a rule protects a *resource*, use `action`. Writing docs about a thing must not trip
the rule that stops you touching it.

## 4. Test fixtures must live outside the test file

Because the whole script is the command, a test file containing protected strings as
literals trips the guard it is testing. Keep fixtures in a separate JSON file.

## 5. Every deny rule needs an allow-case — this is the big one

This is the lesson that cost the most and is easiest to skip.

A rule with only deny-tests is *guaranteed* to be over-broad, and you will not find out
until it blocks something you needed. Our exfiltration rule shipped with deny-cases only.
It matched its trigger words **anywhere** in the command text, with no command-position
anchor. Consequences:

- It blocked a heredoc that merely *documented* an incident.
- Worse: it matched `rsync` next to a protected path **regardless of destination** — so it
  blocked copying that data to a *locally attached backup drive*. **The guard was blocking
  the remedy**, not the risk.

Nobody noticed for weeks, because there was no test asserting anything should be allowed.

The fix was a command-position anchor plus an explicit local-destination exemption:

```
(^|[;|&("'\n])[ \t]*((sudo|time|nohup|env|xargs)[ \t]+|VAR=[^ \t]*[ \t]+)*(curl|wget|scp|rsync|…)(?![^|;&\n]*/Volumes/)[^|;&\n]*(PROTECTED_NAME)
```

Note what the anchor buys: it still catches `time …`, `FOO=1 …`, `sudo …`, `… && …`,
`… | …`, `bash -c "…"`, `(…)`, and a later line of a multi-line script. Those wrapped
forms are bypasses the unanchored version caught only by accident.

**Rule of thumb: you have not finished a deny rule until you have written the allow-case
that proves it is not over-broad.**

## 6. Watch out for misplaced negative lookaheads

Found while writing this repo's allow-cases:

```
BROKEN:  \bgit\s+push\b[^|;&\n]*(--force\b|-f\b)(?!orce-with-lease)
FIXED:   \bgit\s+push\b[^|;&\n]*(--force(?!-with-lease)|-f\b)
```

`--force\b` matches *inside* `--force-with-lease` — the hyphen is a word boundary — so the
trailing lookahead was evaluated at the wrong position. The result: `--force-with-lease`,
the **safe** form, prompted every time.

That is not a harmless bug. Prompting on safe operations trains the human to click
through prompts, which destroys the value of the ones that matter.

This bug had been live for months. An allow-case caught it in the first test run.

## 7. Keep one canonical copy of the rules

We had two copies of the rules file: the one the hook read, and the one the test suite
read. They were byte-identical, so nothing broke — until a fix applied to one would have
gone **green against the stale other**. A false all-clear on security machinery is worse
than a red test.

Symlink them, or resolve both from a single path.

## 8. Grow the ruleset from real mistakes

Rules invented in the abstract are noisy; rules extracted from something that actually
went wrong are precise, and you can write the reason line with conviction. Attach each
rule to a document explaining *why* it exists — the agent surfaces it in the block
message, which makes the block persuasive rather than mysterious.

## 9. `deny` and `ask` are different tools

- `deny` — irreversible or externally-consequential. The agent must find another way.
- `ask` — risky but often legitimate. Routed to a human.

Over-using `deny` produces an agent that cannot work. Over-using `ask` produces prompt
fatigue and reflexive approval. Both end with the guard switched off.
