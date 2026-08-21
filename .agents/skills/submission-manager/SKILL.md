---
name: submission-manager
description: >-
  Prepare and verify a source-code submission at every stage deadline: confirm the project is runnable
  from the committed state, confirm the latest verified work is included, exclude secrets and generated
  dependency/build artifacts, keep lock files and required config, follow the organizers' stated format,
  optionally produce a clean archive, and output a checklist of exactly what was verified. Use before
  every submission and for the final one.
---

# Submission Manager

Read `AGENTS.md`. This skill ships what exists; it does not add features. Once this skill starts, the code is frozen except for submission-blocking fixes.

Budget: **10–15 minutes**. Start it before you feel ready — the goal is that a stage is never missed because someone was still coding.

**Submit the best verified state, not the most ambitious one.** A green project missing one feature scores; a broken project with everything does not.

---

## Step 1 — Confirm the organizers' requirements

Check what was actually asked for, and follow it exactly: naming convention, file format (repo link, zip, specific portal), required documents, whether dependencies must be included, per-stage vs cumulative submission, deadline and timezone. If the format is unknown or ambiguous, ask the user rather than guessing (P7) — a wrongly formatted submission can score zero regardless of the code.

Where organizer instructions conflict with the defaults below, organizer instructions win.

## Step 2 — Confirm what state you are shipping

```
git status
git log --oneline -5
git diff --stat HEAD
```

- Are there **uncommitted or untracked** changes that belong in this submission? If they are verified, commit them; if they are unverified or broken, exclude them and say so.
- Is the newest verified work actually committed? The classic failure is submitting an older snapshot while the good work sits uncommitted or on another branch.
- Is HEAD on the branch you intend to ship?
- Confirm the current state's status label (P8). If YELLOW, name what is degraded. If RED → `emergency-recovery` immediately; if the deadline will not wait, ship the last green checkpoint and state that clearly.

## Step 3 — Verify runnability from the committed state

This is the step most often skipped and most often fatal. Do not trust your warm dev environment.

- Confirm every file the project needs to run is tracked (`git ls-files`), especially recently added source, assets, schemas, and config.
- Confirm build/compile passes and the app starts, from the committed state.
- Confirm the run instructions in `README.md` / `BUILD.md` §4 match the commands that actually work, including setup and any required env variables.
- If time allows and it is affordable, do the strongest check: clone or copy the repo to a temp directory, install from the lock file, and run it. This catches missing files, missing dependency declarations, and hardcoded local paths.
- Exercise the `BUILD.md` §8 core flow once in that state.

## Step 4 — Hygiene: what must not ship, and what must

**Exclude** (verify they are ignored and not tracked):
- Secrets: env files, credential files, key files, tokens, service-account JSON, private certs.
- Dependency directories and virtual environments.
- Build output, compiled artifacts, and caches — unless the organizers explicitly want a build.
- Local databases, logs, temp/scratch files, editor and OS metadata, large media not needed to run.

If a secret was ever committed, say so plainly to the user and treat the key as compromised — rotate it. Do not attempt history rewriting under time pressure without explicit approval.

**Include:**
- All source files, assets, schemas, migrations, and config needed to run.
- Lock/pin files — they make the submission reproducible.
- Dependency manifest, and an example env file with placeholder values documenting every required variable.
- `README.md` with setup, run, and core-flow verification steps.
- `BUILD.md` and `AGENTS.md` (they demonstrate process and are cheap to include).
- Any organizer-required documents.

Quick sanity check: scan the staged/tracked file list for anything that looks like a secret, and for unexpectedly large files.

## Step 5 — Package (only if the organizers require an archive)

- Commit and, if useful, tag the submission point: e.g. `stage-<N>-submission`.
- Build the archive from a **clean copy of the committed state** (a fresh clone or export), not from the working directory — this is what guarantees ignored files stay out.
- Name it as the organizers specified; if unspecified, `AGENTX24_stage<N>.zip`.
- Verify the archive: check its size is plausible, list its contents, and confirm no dependency directories, no caches, and no secrets are inside.
- If a repository link is what is required, confirm the intended branch is pushed and the link resolves to the intended commit.

## Step 6 — Output the verification checklist

Report exactly this, filled in with real observed results:

```
SUBMISSION — Stage <N>            STATUS: GREEN | YELLOW
Commit:      <hash> <message>
Branch/Tag:  <branch> / <tag>

VERIFIED
[ ] Organizer format/naming requirements followed
[ ] Latest verified work committed; nothing needed left uncommitted
[ ] Build/compile passes from committed state — <command>
[ ] App starts / entry point runs — <command>
[ ] Core flow observed working — <what was observed>
[ ] Stage <N> feature working — <what was observed>
[ ] Run instructions match reality
[ ] All required files tracked (clean-copy run: yes/no)
[ ] Lock/manifest/config included
[ ] No secrets, no dependency dirs, no caches, no build junk
[ ] Archive/link verified — <name or URL>

EXCLUDED ON PURPOSE
- <unverified or broken work left out>

KNOWN LIMITATIONS
- <carried from BUILD.md §12>
```

Any unchecked box must be stated as unchecked, with the reason.

---

## Anti-patterns

- Adding features, refactoring, or polishing during the submission window.
- Submitting an older commit while newer verified work sits uncommitted, unpushed, or on another branch.
- Claiming runnable without running it from the committed state.
- Shipping secrets, or committing an env file "just so it runs".
- Shipping dependency directories or caches when they were not requested, bloating the archive.
- Stripping lock files, manifests, or config to "clean up" the submission.
- Building the archive from a dirty working directory.
- Ignoring organizer naming/format rules in favour of your own convention.
- Missing the deadline while trying to finish one more feature.
- Hiding a degraded state instead of reporting it.

## Definition of done

- [ ] Organizer requirements confirmed and followed.
- [ ] Shipping commit identified; latest verified work included.
- [ ] Runnability verified from the committed state; core flow and stage feature observed working.
- [ ] Secrets and generated artifacts excluded; required files and lock files present.
- [ ] Archive or repo link created and inspected, if required.
- [ ] Checklist reported with honest status and known limitations.

## Handoff

→ Wait for the next requirement, then `feature-integrator`. Before the final demo, `demo-polisher` (only if green), then this skill once more for the final submission.
