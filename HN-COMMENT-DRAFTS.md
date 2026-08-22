# Comment drafts — read, edit, post yourself

I wrote these; **you have to own them.** Two reasons that aren't lecturing:

1. If someone replies with a follow-up question, you need to be able to answer it. You
   can only do that if the comment is actually your view.
2. HN is currently hunting for AI-generated comments — I read a thread today where users
   were asking dang to de-activate accounts posting them. Getting caught would burn the
   account *and* the writeup it's meant to support.

So: change anything that doesn't sound like you. Cut anything that isn't true. If a draft
feels like it's claiming more than you'd claim out loud, it is — trim it.

---

## Draft 1 — the strongest. Post this one first.

**Thread:** https://news.ycombinator.com/item?id=49357530
**Reply to:** the comment by `Incipient` asking "does it matter? Do we need to know that
detail any more? I genuinely don't know the answer to that..."

> I'm a data point for your question, from the far end of it.
>
> I've shipped a large amount of production code with AI assistance over about three
> years. I could not sit down and write most of it unaided at the same level today. The
> homework/exam split in this study maps almost exactly onto shipping vs. debugging — my
> output never dropped. What degraded is the thing I need when the model is confidently
> wrong.
>
> What I'd flag is how long it took me to notice. The metric that would have warned me —
> does it work, does it ship — is exactly the one AI keeps healthy. I only found out when
> I hit something the assistant kept getting subtly wrong and realised I'd lost the
> fluency to hold the whole problem in my head at once.
>
> On whether it matters: I don't know either. It clearly matters for debugging. For your
> fastapi middleware example I suspect knowing what it does and why really is enough. The
> uncomfortable part is that the line between those two cases is invisible until you're
> already on the wrong side of it.

**Check before posting:** "about three years" — adjust to your real number. "A large
amount of production code" is deliberately unquantified; if you'd rather give the real
figure, do, but then be ready to be asked about it.

**Why this works:** it answers a question someone actually asked, it's first-person where
the thread is all theory, and it admits something unflattering. HN rewards all three.

---

## Draft 2 — only if it's genuinely true for you

**Thread:** https://news.ycombinator.com/item?id=49398158 (Z80)

All 41 comments are hobby retrocomputing — ZX Spectrum, CP/M, RC2014 kits, transistor
counts. The article says the Z80 went into industrial embedded systems and is still in
ASICs today. Nobody has touched that.

⚠️ **I don't know whether you've personally worked on plant equipment running these
chips.** The `[ ]` blanks are things only you can fill. If you can't fill them honestly,
skip this thread entirely — a fabricated technical detail here gets caught by exactly the
people you want to impress.

> Most of this thread is treating the Z80 as a hobby platform, but a lot of them are still
> load-bearing. [ WHAT YOU ACTUALLY SAW — e.g. a controller on a line, a machine still
> running because the replacement quote was more than the machine earned in a year ].
>
> The thing that doesn't come across from the outside is that "still alive" isn't
> nostalgia, it's economics. [ YOUR ACTUAL EXPERIENCE of what replacing it costs —
> downtime, requalification, retraining, whatever was true where you worked ].
>
> Every few years someone proposes ripping it out and the number comes back worse than
> living with it.

If you have not stood in front of that equipment, don't post this. Post Draft 1 and
Draft 3 instead — two good comments beat three where one is hollow.

---

## Draft 3 — small thread, easy visibility

**Thread:** https://news.ycombinator.com/item?id=49397947 (Embedded AI, 9 comments)

Small enough that a comment gets read rather than buried — good for a new account.

Angle, if you agree with it: most "embedded AI" discussion assumes the constraint is
compute. In a plant the binding constraints are usually different — you can't depend on a
network link, you often can't send process data off-site at all, and anything in the
control path has to fail predictably rather than degrade gracefully.

Write it in your own words, three or four sentences. If you don't have a real view here,
skip it.

---

## Order and pacing

1. **Today:** Draft 1.
2. **Spread the rest over 2–3 days.** Four comments in one hour from an 8-minute-old
   account looks like exactly what it would be.
3. Reply to *specific people*, not top-level — top-level comments on a 300-comment thread
   are invisible.
4. If someone pushes back well, say so and update your view. That single move earns more
   standing on HN than winning would.

Then submit the writeup Tue–Thu 08:00–10:00 ET. See HN-SUBMISSION.md.
