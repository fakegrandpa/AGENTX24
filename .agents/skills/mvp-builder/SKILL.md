---
name: mvp-builder
description: >-
  Implement the approved MVP directly inside the existing AGENTX24 root as one working end-to-end
  vertical slice: scaffold, core logic, minimal interface, real run, fixes, verified core flow, and a
  green Git checkpoint. Use once BUILD.md exists and nothing is built yet (Stage 0). Do not use for
  later feature requirements.
---

# MVP Builder

Read `AGENTS.md`, then `BUILD.md` (scope, stack, run commands, build order, core flow test). Inspect the workspace before scaffolding (P1) — an earlier partial setup may already exist.

Goal: **a demoable end-to-end flow as early as possible**, built in the project root, not in a subproject.

Time box: aim for a first running slice within **60 minutes**, fully verified and committed well before the Stage 0 deadline. Reserve the last 20 minutes for verification and submission (P6 freeze rule).

---

## Step 1 — Ground yourself (5 min)

- Read `BUILD.md` §2, §3, §4, §8, §9.
- List the workspace root. Identify anything already present that must be preserved (`AGENTS.md`, `.agents/`, `BUILD.md`, config files, any prior scaffold).
- Confirm required toolchain versions are actually available by running the version commands. If the chosen stack is not installable here, stop and report (P7) — do not silently substitute a different stack from `BUILD.md`.

## Step 2 — Scaffold minimally (10 min)

- Use the stack's standard generator or a minimal hand-written entry point. Standard generators win when they are fast and produce known-good config.
- Scaffold **into the existing root**. If a generator insists on creating its own directory, generate elsewhere and move the contents in, keeping existing root files intact.
- Add or extend `.gitignore` before the first commit: dependency directories, virtual environments, build output, caches, local databases, env files, editor/OS junk (P5).
- Add a `.env.example`-style file with placeholder keys if the project needs configuration.
- Delete generator boilerplate you will not use (sample pages, demo assets, dead comments). Do not spend more than a couple of minutes on this.
- **Verify the empty shell runs before writing any feature code.** A green scaffold is the first checkpoint.

## Step 3 — Build the vertical slice (bulk of the time)

Implement in this order, and get each layer minimally working before moving on:

1. **Data shape** — the one or two structures the flow needs, in one place.
2. **Core operation** — the logic that creates the project's actual value, callable independently of any UI or trigger.
3. **Trigger/entry point** — the route, command, handler, or event that invokes the core operation.
4. **Output** — the visible result: rendered view, response, file, log, or console output.
5. **Wire the seam** — connect trigger → core → output and run the whole path once.

Rules while building:
- **One flow, complete.** A finished narrow path beats four half-built components. If the clock runs out, a working slice is a demo; disconnected pieces are nothing.
- **Required / nice / unnecessary:** implement only `BUILD.md` MUST items now. Note SHOULD/NICE items in `BUILD.md` §2 and move on. Anything not in the plan is unnecessary work — do not add it.
- Use reliable libraries for solved problems; do not hand-roll.
- Hardcoded seed or sample data is acceptable and often correct at this stage, as long as it is clearly labelled and not passed off as computed output.
- Handle the failure paths the demo will realistically hit (empty input, missing config, failed external call) with a clear message instead of a crash. Skip exhaustive validation.
- Keep files small and honestly named; that is the only "architecture" required now.

## Step 4 — Run it for real, then fix (P3)

- Start the app / execute the entry point. Fix errors until it starts clean.
- Walk the `BUILD.md` §8 core flow test yourself and observe the expected output.
- Re-run the build/compile/typecheck path so the committed state is not only dev-server-valid.
- Fix what you found. Prefer targeted fixes; if a fix keeps failing twice, re-diagnose rather than retry variants (P7).
- Note anything degraded but working as a limitation rather than silently leaving it.

## Step 5 — Document and checkpoint

- Update `BUILD.md`: correct §4 run commands to what you actually ran, fill §5 architecture map, adjust §6 data shapes, add the Stage 0 line to §11, record limitations in §12.
- Create a short `README.md`: one-line description, setup, run command, how to see the core flow work.
- Green checkpoint (P4): `stage-0: working MVP — <core flow in a few words>`.

---

## Anti-patterns

- Creating a nested project folder instead of building in the root.
- Building infrastructure (auth, admin, settings, logging framework, tests-for-everything, CI) before the core flow works.
- Polishing visuals before the flow is verified — that is `demo-polisher`, later, and only when green.
- Adding features not in `BUILD.md` because they seemed easy.
- Placeholder UI wired to nothing, presented as progress.
- Committing before the flow was observed working.
- Rewriting the scaffold because you prefer a different structure.
- Reporting "MVP complete" based on written code rather than a run.

## Definition of done

- [ ] Project scaffolded in the root; pre-existing files preserved.
- [ ] `.gitignore` covers dependencies, build output, caches, and env files.
- [ ] One complete trigger → core → output flow implemented.
- [ ] Build/compile/typecheck passes; app starts clean.
- [ ] `BUILD.md` §8 core flow observed producing the expected result, with commands reported.
- [ ] `BUILD.md` §4, §5, §11, §12 updated; `README.md` created.
- [ ] Green checkpoint committed.
- [ ] Status reported as GREEN/YELLOW with known limitations named (P8).

## Handoff

→ `regression-guardian` if anything felt fragile, otherwise `submission-manager` for the Stage 0 submission, then wait for the next requirement and use `feature-integrator`.
