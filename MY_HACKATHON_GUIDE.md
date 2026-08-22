# MY HACKATHON GUIDE — AGENTX24

My personal playbook. Not an AI instruction file. Nothing here changes the workflow — it just tells me what to do next.

Workspace: `D:\AGENTX24`
Prompts live in: `HACKATHON_PROMPTS.txt` (10 sections, copy between the `>>> COPY FROM HERE` / `<<< COPY TO HERE` markers)

---

## WHAT I DO TOMORROW

```
MAIN PROBLEM DROPS
   OpenCode   -> Prompts Section 1 -> BUILD1.md appears
   Antigravity-> Prompts Section 2 -> app gets built + tested + committed
   Antigravity-> Prompts Section 7 -> submit

NEW FEATURE DROPS (every 3 hours, repeat 7x)
   OpenCode   -> Prompts Section 3 -> BUILD[next].md appears
   Antigravity-> Prompts Section 4 -> feature built + tested + committed
   Either     -> Prompts Section 5 -> regression test
   Antigravity-> Prompts Section 7 -> submit

BROKEN AT ANY POINT
   Either     -> Prompts Section 6 -> diagnose, fix, verify, commit

LOST / JUST SAT DOWN
   Either     -> Prompts Section 10 -> tells me where I am and what to do next
```

Rule of thumb: **OpenCode thinks. Antigravity builds.**

---

## SECTION 1 — BEFORE THE HACKATHON

- Open `D:\AGENTX24`. This one folder is the whole project for all 24 hours.
- Have both tools ready and pointed at `D:\AGENTX24`: **OpenCode** and **Antigravity**.
- `HACKATHON_PROMPTS.txt` = all my prompts. `AGENTS.md` + `.agents/skills/` = the AI rules, already set up. I don't need to touch either.
- Git is **local only**. Nothing uploads anywhere unless I add a remote myself. Commits are just my undo points.
- Never delete, reset, or re-create the workspace. Never start a second project folder.
- Handy: `.gitignore` already blocks secrets, dependency folders, build output and caches.

Optional 30-second sanity check before Hour 0: open either tool, paste **Section 10 (Quick Project Status Check)**, confirm it reads the workspace fine.

---

## SECTION 2 — WHEN THE MAIN PROBLEM IS REVEALED

**STEP 1** — Open **OpenCode** in `D:\AGENTX24`.

**STEP 2** — Open `HACKATHON_PROMPTS.txt`.

**STEP 3** — Go to **SECTION 1 — HOUR 0: MAIN PROBLEM ANALYSIS** (TOOL: OPENCODE). Copy the whole block between the copy markers.

**STEP 4** — Paste the problem statement over the placeholder:
`[PASTE MAIN PROBLEM STATEMENT HERE]`
Then send it.

**STEP 5** — OpenCode reads the workspace and creates **`BUILD1.md`** — problem understanding, MUST/SHOULD/NICE/OUT, stack choice, MVP, architecture, risks, build order, what NOT to build yet.

**STEP 6** — OpenCode **plans only**. Zero application code at this step. If it starts writing app code, stop it.

**STEP 7** — Read the plan. Check two things: the MUST list looks right, and the "Not To Be Built Yet" list looks sane. Answer any blocking question it asks. Then **switch to Antigravity**.

**STEP 8** — In Antigravity, use **SECTION 2 — BUILD INITIAL MVP** (TOOL: ANTIGRAVITY). No placeholder to fill — just paste and send.

**STEP 9** — Antigravity reads `BUILD1.md` + the workspace, then builds the actual app **in the workspace root** (not a subfolder).

**STEP 10** — Antigravity runs the project and walks the Core Flow Test from `BUILD1.md`. It must report the commands it ran and what it observed. "I wrote the code" is not done — "I ran it and saw X" is done.

**STEP 11** — Antigravity **appends** to the `Stage Outcome` section at the bottom of `BUILD1.md` (what was actually built, real run commands, limitations) and creates/updates `README.md`. It does not rewrite the planning sections above.

**STEP 12** — Antigravity creates the local Git commit: `stage-0: working MVP — ...`. If it forgot, paste **Section 9 (Quick Git Checkpoint)**.

**STEP 13** — Antigravity: **SECTION 7 — PRE-SUBMISSION CHECK**. Paste organizer rules into `[PASTE ORGANIZER SUBMISSION REQUIREMENTS HERE, IF ANY]` if I have them. Submit.

---

## SECTION 3 — EVERY TIME A NEW 3-HOUR FEATURE IS ANNOUNCED

Same loop every single time:

```
NEW FEATURE ANNOUNCED
        |
        v
OPENCODE  --  Prompts Section 3 (NEW FEATURE ANALYSIS)
        |     paste requirement into [PASTE NEW FEATURE REQUIREMENT HERE]
        v
It reads old BUILD files + THE ACTUAL CURRENT CODE
        |
        v
It creates the NEXT BUILD number  (planning only, no code)
        |
        v
I copy its implementation plan
        |
        v
ANTIGRAVITY  --  Prompts Section 4 (IMPLEMENT NEW FEATURE)
        |     paste plan into [PASTE OPENCODE IMPLEMENTATION PLAN HERE]
        v
Feature implemented
        |
        v
Test NEW feature + OLD features  (Section 4 does this; Section 5 if I want a deeper sweep)
        |
        v
Stage Outcome appended to this stage's BUILD file
        |
        v
GIT COMMIT  (stage-N: ...)
        |
        v
Prompts Section 7  ->  SUBMIT
```

**The BUILD number always goes up.**

```
Already exists: BUILD1.md, BUILD2.md      ->  next stage creates BUILD3.md
Already exists: BUILD1..BUILD5.md         ->  next stage creates BUILD6.md
```

Never overwrite an old BUILD file. Never rename one. Never delete one. If a tool tries to, stop it.

**My timing per 3-hour block** (mirrors the budget in the prompts file):

| Time into the block | What's happening |
|---|---|
| 0:00–0:15 | OpenCode planning, BUILD file created |
| 0:15–1:45 | Antigravity implementing |
| 1:45–2:10 | Regression testing |
| 2:10–2:25 | Polish — only if everything is green |
| 2:25–2:40 | Submission check + submit |
| 2:40–3:00 | Buffer. **No new features in the last 20 minutes** — fixes and submission only |

---

## SECTION 4 — WHICH TOOL DOES WHAT

| TASK | TOOL |
|---|---|
| Main problem analysis | OpenCode |
| Architecture | OpenCode |
| Choosing the implementation approach | OpenCode |
| Creating the next `BUILD[number].md` | OpenCode |
| Actual coding | Antigravity |
| Creating / modifying application files | Antigravity |
| Running the project | Antigravity |
| Testing | Antigravity |
| Fixing implementation issues | Antigravity |
| Git checkpoint (when the prompt says so) | Antigravity |

> **OPENCODE = THINK AND PLAN**
> **ANTIGRAVITY = BUILD AND MODIFY CODE**

Either tool is fine for: Section 5 (regression), Section 6 (emergency), Section 9 (git), Section 10 (status). Use whichever window is already open.

---

## SECTION 5 — WHICH MODEL TO USE IN OPENCODE

**Claude Opus 5** — for:
- Main problem analysis at Hour 0
- Difficult architecture decisions
- Confusing or ambiguous requirements
- Any change that could affect the whole project
- Complex debugging analysis

**GPT-5.6** — for:
- Normal feature planning
- Faster analysis
- Straightforward requirements
- A quick second opinion

Default: GPT-5.6 for speed, Opus 5 when it actually matters or when GPT-5.6's plan feels thin.
(Model list comes from the `opencode.json` I launch OpenCode with — worth confirming both models show up before Hour 0.)

---

## SECTION 6 — BUILD FILE CHEAT SHEET

| File | What it is |
|---|---|
| `BUILD1.md` | Original problem understanding, architecture, MVP plan + its Stage Outcome |
| `BUILD2.md` | First new requirement: plan + its Stage Outcome |
| `BUILD3.md` | Second new requirement: plan + its Stage Outcome |
| `BUILD4.md`… | …and so on, one per requirement |
| `BUILD-LAST.md` | Final summary map. **Only near the very end**, never during a normal stage |

**What to trust, in order:**

```
1. THE CURRENT CODE   = the actual truth about what exists
2. README.md          = current setup and how to run it right now
3. BUILD[number].md   = history, decisions, stage context (what was INTENDED)
4. Git                = safe checkpoints and rollback history
```

Old BUILD files are **history, not homework**. They are never overwritten. Each one is frozen once its stage ends — only the current stage's file gets its `Stage Outcome` appended at the bottom.

So if `BUILD1.md` says "run it with command X" and the app now actually runs with command Y — the code and `README.md` are right, `BUILD1.md` is just old. That's expected, not a bug.

---

## SECTION 7 — IF SOMETHING BREAKS

```
PROJECT BREAKS
      |
      v
STOP RANDOM EDITING          <- most important step
      |
      v
Prompts SECTION 6 — EMERGENCY RECOVERY
      |
      v
Paste the ACTUAL error text (full message, not my summary of it)
      |
      v
It inspects Git state + the current code
      |
      v
Finds the root cause  ("X fails because Y, introduced by Z")
      |
      v
Applies the SMALLEST safe fix
      |
      v
Runs the project again
      |
      v
Commit only when it's green
```

**Do not:**
- run `git reset --hard`, `git clean -f`, or force push on impulse
- delete the project or any files to "start again"
- wipe and re-scaffold because it feels faster (it isn't)
- let a tool bundle five speculative fixes at once

If a fix fails twice, that's my signal: stop patching, ask for the root cause, or roll back to the last green commit. **Losing 40 minutes of work beats being broken at a deadline.**

---

## SECTION 8 — BEFORE EVERY SUBMISSION

```
[ ] Project runs
[ ] New feature works (I saw it work, not "the AI said so")
[ ] Previous important features still work
[ ] No secrets / API keys / .env files included
[ ] README.md is current
[ ] Git status checked, newest verified work committed
[ ] Required files are included
[ ] Organizer submission rules checked
```

Then use **SECTION 7 — PRE-SUBMISSION CHECK** in Antigravity, pasting the organizer rules into `[PASTE ORGANIZER SUBMISSION REQUIREMENTS HERE, IF ANY]`.

It gives me back a PASS/FAIL checklist. **Anything marked FAIL, I read before submitting.** It will not delete files or push anything online — if it wants something removed, it asks me first.

Start this 15 minutes before the deadline, not at the deadline.

---

## SECTION 9 — FINAL HOURS

Only when the project is stable and **GREEN**:

1. Run a full regression check — **Section 5**, and let it do the Tier 3 items including the clean-copy install.
2. Then **Section 8 — DEMO POLISH** in Antigravity.
3. Improve first-impression clarity: obvious title, obvious main action, consistent look.
4. Add loading / empty / error states wherever the demo can hit them.
5. Prepare seed/demo data so the flow can be shown in seconds. Labelled as sample data — **never fake output presented as real**.
6. Create `BUILD-LAST.md` only now, only at the final stage, if I actually want the summary. It never replaces the numbered BUILD files.
7. Run **Section 7** one last time for the final submission.
8. **No risky rewrites near the deadline.** If it works, leave it alone.

Also: rehearse the demo out loud once. Section 8 writes a Demo Script (setup, path, talk track, what to avoid, fallback) — read it before presenting.

If the project is NOT green in the final hours: skip polish entirely. Fix, verify, submit.

---

## SECTION 10 — 30-SECOND CHEAT SHEET

```
MAIN PROBLEM:
OpenCode (S1) -> BUILD1.md -> Antigravity (S2) -> Test -> Commit -> Submit (S7)

NEW FEATURE:
OpenCode (S3) -> BUILD[next].md -> Antigravity (S4) -> Test old + new
             -> Commit -> Submit (S7)

PROJECT BROKEN:
Emergency Recovery (S6) -> Fix -> Test -> Commit

FINAL:
Regression (S5) -> Demo Polish (S8) -> Final Verification (S7) -> Submit

LOST:
Status Check (S10)
```

**Three things I will not forget:**
1. One project, one folder, always runnable.
2. BUILD numbers only go up. Nothing gets overwritten.
3. Nothing is "working" until I have seen it run.
