# The guardrail that blocked its own fix

*What three years of AI-assisted development, 114 logged mistakes, and one very stubborn
regex taught me about constraining coding agents.*

---

I have been building with AI coding assistants since well before it was a normal thing to
do. Somewhere in year two I stopped counting features and started counting mistakes. The
count is currently 114 — each one written down, with what happened, how it was caught, and
what would have prevented it.

That log is the most valuable artifact I own. Not because the mistakes are interesting
individually — most are mundane — but because writing them down forced a conclusion I
resisted for a long time:

**You cannot fix a class of mistake by telling the model not to make it.**

## Instructions are a preference; hooks are machinery

Every AI coding tool now has a project-instructions file. Mine was excellent. It said
things like *never run `git add -A` in a live repo* and *never delete this directory*.
Those instructions were correct, well-written, and prominently placed.

They were also violated, because instructions depend on a model *remembering* to check —
every time, forever. Context gets compacted. Attention drifts. A new session starts cold
and has never seen your rule at all. The one time it forgets is, reliably, the time that
matters.

So I moved the rules out of prose and into a hook that runs **before** the tool call:

```python
hits = [r for r in rules if _matches(r, tool, hay)]
denies = [r for r in hits if r.get("decision") == "deny"]
decision = "deny" if denies else "ask"
```

About 150 lines. It reads the proposed tool call, matches it against a rules file, and
either blocks it outright or routes it to me. It holds when the model is wrong, when it is
distracted, and when it has no idea the rule exists.

A note on why it must run *before*: a PostToolUse hook warns after the write. That is fine
for code smells and worthless for `rm -rf`.

## Fail open, or watch it get deleted

The first hard lesson arrived when the guard lived inside a working repository.

I checked out a branch that predated the hook. Git deleted the script mid-session. A hook
that cannot start is treated as a **denial** — so every tool call was refused. Including
the ones needed to restore the file. There was no route back from inside the session.

Two changes came out of that:

1. The guard, its rules, and its tests live outside any tree that gets checked out.
2. **Any internal error exits 0.** Bad JSON, missing rules, malformed regex: the guard
   stands down and logs it.

That second one is counterintuitive for something billed as a safety control, and it is
the single most important design decision in the project. A guard that blocks all work
when it breaks gets deleted within a day — and then it protects nothing. **Zero
enforcement beats negative enforcement**, because negative enforcement gets the whole idea
thrown out.

Failures are logged, always. Trusting silence is its own failure mode.

## The mistake that made this worth writing about

Here is the one that changed how I think about the whole problem.

I had a rule protecting a sensitive directory — data that, for policy reasons, must never
leave the machine. The rule denied any upload command touching that path:

```
(curl|wget|scp|rsync|gsutil|gcloud\s+storage|aws\s+s3)[^|;&\n]*(PROTECTED_NAME)
```

It worked. It blocked a real upload attempt during a genuine task. I was pleased with it.

Then two things happened on the same afternoon.

**First**, it blocked me from writing a *document about the incident*. For a shell tool,
the entire script text is the command string — so a heredoc that merely narrated
"the guard blocked `gcloud storage rsync` of `~/PROTECTED`" contained both trigger tokens
on one line and tripped the rule. Annoying, not dangerous.

**Second — and this is the part worth reading —** I sat down to set up a proper backup for
that same directory. To a local, encrypted, physically-attached drive. The correct,
recommended, policy-compliant remedy.

```
rsync -a ~/PROTECTED/ /Volumes/BackupSSD/PROTECTED/     →  DENIED
```

The rule matched `rsync` next to the protected path **regardless of destination**. It had
no concept of local versus remote.

The guard was blocking the fix, not the risk. The one directory I most needed a second
copy of was the one directory my own safety system prevented me from backing up.

It had been that way for weeks and nothing caught it — because every test I had written
asserted that something should be **blocked**. Not one asserted that anything should be
**allowed**.

## The rule about rules

> **A deny rule is not finished until you have written the allow-case that proves it
> isn't over-broad.**

Deny-tests confirm your rule fires. They tell you nothing about what else it hits. A rule
with only deny-tests is *guaranteed* to be over-broad; you simply have not found out yet.

The fix was to anchor the match to an actual command position and exempt local
destinations:

```
(^|[;|&("'\n])[ \t]*((sudo|time|nohup|env|xargs)[ \t]+|VAR=[^ \t]*[ \t]+)*
(curl|wget|scp|rsync|gsutil|…)(?![^|;&\n]*/Volumes/)[^|;&\n]*(PROTECTED_NAME)
```

Note what the anchor buys, beyond fixing the false positives. It still catches
`time …`, `FOO=1 …`, `sudo …`, `… && …`, `… | …`, `bash -c "…"`, `( … )`, and a command on
a later line of a multi-line script. Several of those wrapped forms the original pattern
caught only by accident. **The narrower rule is also the more thorough one.**

Before: 2 wrong out of 14 real-world cases. After: 0.

## The bug the allow-cases found on their first run

While extracting this into a public repo, I wrote allow-cases for every existing rule.
The very first run failed on one I had considered settled:

```
BROKEN:  \bgit\s+push\b[^|;&\n]*(--force\b|-f\b)(?!orce-with-lease)
FIXED:   \bgit\s+push\b[^|;&\n]*(--force(?!-with-lease)|-f\b)
```

`--force\b` matches *inside* `--force-with-lease` — the hyphen is a word boundary — so the
trailing lookahead was evaluated at the wrong position entirely. Result:
`--force-with-lease`, the **safe** form, prompted every single time. For months.

That is not cosmetic. Prompting on safe operations trains you to click through prompts.
Prompt fatigue doesn't weaken your guardrails gradually — it converts every one of them
into a rubber stamp at once.

**A false positive is not a small bug in a safety system. It is the mechanism by which
safety systems get switched off.**

## What I would tell someone starting

1. **Fail open.** Non-negotiable. Log everything.
2. **Put it where a branch checkout cannot delete it.**
3. **Match on the right target.** For a shell tool the whole script is the command, so a
   rule that scans everything fires on scripts that merely *contain* a protected string as
   data. Protect *resources* by matching the command and path, never the written content.
4. **Write the allow-case.** Every time. It is where the bugs are.
5. **Grow rules from real mistakes.** Rules invented in the abstract are noisy. Rules
   extracted from something that actually went wrong are precise — and you can write the
   reason line with conviction, which matters, because the agent reads it.
6. **`deny` and `ask` are different tools.** Over-use `deny` and the agent cannot work.
   Over-use `ask` and you get prompt fatigue. Both end the same way: guard switched off.

## The uncomfortable part

The most interesting thing in this whole system is not the code. It is the 114-entry
mistake log it grew out of.

Everyone building with these tools is accumulating that log. Almost nobody is writing it
down. It is the difference between three years of experience and one year of experience
repeated three times — and it is the only input that produces rules precise enough to
survive contact with daily use.

The code is ~150 lines and it is on GitHub. The log is the part you have to build
yourself.

---

*Code: [agent-guardrails](https://github.com/YOURNAME/agent-guardrails) — MIT.
Full lessons: [docs/LESSONS.md](docs/LESSONS.md).*
