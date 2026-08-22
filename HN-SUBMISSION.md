# Hacker News submission kit

**Do not submit before the account is ready.** See the ramp below — this matters more than
the copy does.

---

## The problem to solve first: no account

A brand-new account submitting its own GitHub repo is the single most-flagged pattern on
HN. Not because self-promotion is banned — it isn't — but because that shape is what
spam looks like, and new ("green") accounts get more scrutiny automatically.

### Account ramp — start today, submit Tue–Thu

**Today (5 min).** Create the account at https://news.ycombinator.com/login
- Username: something you'll keep. `thegringo` or similar is fine; it doesn't need to be
  your real name, and the writeup carries your byline anyway.
- Set an email in settings — without one you cannot recover the account, ever.

**Days 1–4 (10 min/day).** Comment genuinely on threads you actually have something to say
about. You have an unfair advantage here that most HN commenters do not: **a decade on a
plant floor.** Threads where that is worth more than another web-dev opinion:
- anything about industrial automation, OT/IT convergence, SCADA, manufacturing
- AI agent tooling, coding assistants, developer workflow
- reliability, safety systems, incident postmortems

Do not mention your project. The point is a non-zero comment history and a few karma, so
the account is not green on submission day. Three or four substantive comments is enough.

**Submission day: Tuesday, Wednesday, or Thursday, 08:00–10:00 US Eastern.**
That is when HN traffic peaks and `/newest` moves fast enough to reach front-page voters.
Avoid Friday–Sunday entirely.

---

## The submission

**Type:** regular story, **not** "Show HN".

> "Show HN" frames it as a tool launch, competing with every other AI tool that week.
> The story frame competes on the idea, which is much stronger here.

**Title** (exactly this — 80 char limit, do not add a tagline):

```
The guardrail that blocked its own fix
```

**URL:**

```
https://github.com/TheGringo-ai/agent-guardrails/blob/main/WRITEUP.md
```

Why this title works: it is specific, slightly puzzling, and promises a story with a
reversal in it. It does not contain "AI", "LLM", or a product name — all of which trigger
scroll-past on HN right now.

---

## First comment (post immediately after submitting)

Self-submissions do better with a short, plain author comment. Keep it factual. No pitch,
no "excited to share".

```
Author here. Short version of what happened:

I had a guard rule that blocked uploading a protected directory anywhere off the
machine. It worked — it stopped a real upload during a genuine task.

Then I sat down to back that same directory up to a local encrypted drive, which was
the actual remedy for the risk, and the rule blocked that too. It matched "rsync next
to the protected path" with no concept of destination. The guard was blocking the fix
rather than the risk, and had been for a while, because every test I had written
asserted something should be BLOCKED. Not one asserted anything should be ALLOWED.

Writing those allow-cases afterwards immediately turned up a second bug: --force-with-
lease, the safe form, had been prompting every time because a negative lookahead sat in
the wrong position.

The tool itself is ~150 lines and not very clever. The part I think is worth arguing
about is that a false positive in a safety system isn't a minor bug — it's the
mechanism by which the system gets switched off. I spent a decade on plant floors
before I wrote production code, and that's the one lesson that transferred intact:
nobody decides to defeat an interlock, they defeat one nuisance trip, then another,
and the bypass becomes the procedure.
```

---

## Expect this objection, and concede it fast

> "This is just regex on a string, it's not real security."

**Correct, and say so.** The README already states it: a regex matcher on tool input, not
a sandbox — it stops mistakes, not adversaries. Agreeing immediately reads far better than
defending, and it is true. If you get this comment, the good reply is a one-liner agreeing
plus what it is actually for.

Second likely objection: *"Claude Code already has permissions in settings.json."* Also
fair. The honest answer: built-in permissions are coarse, carry no reason, aren't testable,
can't be shadow-run, and don't read as reviewable policy in a PR. That's an incremental
difference, not a revolutionary one — do not oversell it.

---

## Realistic expectations

Most submissions get very little attention. That is the normal outcome and not a verdict
on the work. If it does not take, do **not** resubmit the same URL — HN dedupes, and a
second attempt performs worse.

Better fallbacks if HN doesn't bite:
- r/ExperiencedDevs — same argument, more patient audience
- A technical LinkedIn post — smaller reach, but far closer to people who hire

**And keep the actual goal in view:** this is career evidence, not a product launch. One
person who could hire you reading it is worth more than 300 stars.
