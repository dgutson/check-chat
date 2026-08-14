---
name: Base rate from another corpus
about: Paste `checkchat --sweep` output, so thresholds stop being fitted to one person's sessions
title: 'base rate: '
labels: base-rate
---

Every threshold in this repo was measured against one corpus belonging to one experienced
engineer, and that corpus is a *negative control*: it measures sycophancy at zero and
re-asking at nearly zero. Those are the right answers for him and they establish nothing
about the people the junior-auditor checks were built for. ROADMAP.md item 9 forbids
tuning against it. What unblocks that item is a number from a corpus nobody here can see.

**Run this and paste the output.** Read it first — the `--text` form takes ten seconds to
scan, and you should not paste anything you have not looked at.

```bash
checkchat --sweep --text     # read this
checkchat --sweep            # paste this
```

<!-- paste between the fences -->
```json

```

**What kind of work is this corpus?** One or two lines. Roughly how many people, roughly
what they were doing, and anything that would make the numbers read wrong without it —
mostly one long-running project, or many short ones; mostly writing code, or mostly
asking questions. This is the part the numbers cannot carry and the part that makes them
mean something.



---

Before you post:

- [ ] I ran `--sweep --text` and read it.
- [ ] The corpus is more than one session. A one-session sweep is *contentless*, not
      anonymous — every distribution in it is that session's own value.

The aggregate carries numbers plus the check names, labels, dimensions and tiers that
`checkchat --catalog` already publishes: no path, filename, command, prompt, reply,
session id, timestamp or project name. Two tests enforce that rather than a promise.
**Please do not attach transcripts** — they are not needed and will not be read.

**And do not attach a `--calibrate` file here.** That one is the opposite by design: it
carries your paths, commands and project names so the findings in it can be judged, and it
goes privately to whoever asked you to run it. This issue is for the anonymous aggregate.
