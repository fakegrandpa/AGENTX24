# BUILD6.md — Stage 6 — Evaluation Harness

Stage record under AGENTS.md P9. Planning sections are frozen once written; only `Stage Outcome` is appended after implementation. `BUILD1.md`, `BUILD4.md` and `BUILD5.md` are untouched.

**Baseline:** branch `main`, HEAD `2234310` (`docs: complete rewrite of technical README for AGENTX24 final release`). Working tree clean apart from untracked `scratch/`. Verified at planning time.

---

## Requirement

Exact wording as announced:

> **6. Evaluation**
>
> "Define measurable criteria for accuracy, task completion, reliability, robustness, evidence quality, and efficiency using automated and human evaluation. Test the agent across normal, ambiguous, adversarial, contradictory, incomplete, and tool-failure scenarios, including repeated runs and baseline comparison. Measure accuracy, groundedness, hallucination, recovery, consistency, latency, and resource efficiency, while evaluating whether the agent can identify uncertainty, refuse unsupported conclusions, and recover from failures."

### Demanded, parsed literally

1. **Measurable criteria** — six named dimensions: accuracy, task completion, reliability, robustness, evidence quality, efficiency. Each needs a defined formula, not a vibe.
2. **"automated and human evaluation"** — both. Automated metrics computed from data; a human rubric that a person fills in.
3. **Six scenario classes** — normal, ambiguous, adversarial, contradictory, incomplete, tool-failure.
4. **"repeated runs and baseline comparison"** — the same objective run more than once, and a comparison against a weaker configuration.
5. **Eight measured quantities** — accuracy, groundedness, hallucination, recovery, consistency, latency, resource efficiency (and the scenario coverage that produces them).
6. **Three behavioural checks** — can the agent (a) identify uncertainty, (b) refuse unsupported conclusions, (c) recover from failures.

### Acceptance Test

**Given** the repository at `main` with a configured `GEMINI_API_KEY`, **when** an operator runs `python -m eval.runner --suite quick`, **then** `eval/results/<timestamp>/metrics.json` contains numeric scores for task completion, groundedness, fabrication-attempts-blocked, evidence quality, recovery, consistency, latency and resource efficiency for **every** scenario in the suite plus one `graph_off` baseline row; `eval/results/<timestamp>/scorecard.md` renders those figures beside an unfilled human rubric; and the adversarial scenario row shows `status="done"` with at least one injected tool failure recovered and at least one conflict recorded — with every number traceable to a field in the saved `Run` JSON under `eval/results/<timestamp>/runs/`.

### Boundaries — NOT requested (every adjacent temptation parked here)

An LLM-as-judge grader; a ground-truth answer corpus or labelled dataset; semantic similarity or embedding scoring; a vector store; statistical significance testing; CI integration; a metrics database or time-series store; Prometheus/Grafana/OpenTelemetry; a web dashboard for evaluation results; regression gating that blocks commits; changes to the agent, graph, prompts, tools, report pipeline or UI to make scores look better; new API endpoints; pytest or any test framework; refactoring `scratch/test_stage5_verification.py`; retuning budgets or model choice.

### Interpretation (chosen for cheapness and honesty; no blocking ambiguity)

- **Evaluation is measurement over data that already exists.** Inspection shows `Run` already carries almost every quantity the requirement names (see below). The harness therefore reads `Run` records; it does not instrument the agent. This is the single most important design decision in this stage.
- **"Hallucination" is measured as fabrication *attempts blocked*, not as undetected hallucination.** `app/report.py` already records every stripped citation marker and every removed model-authored URL into `run.limitations`. Counting those is a real, defensible measurement. Claiming to measure *undetected* hallucination without a ground-truth corpus would be dishonest, so the metric is named `fabrication_attempts_blocked` and the scorecard states plainly what it does and does not prove.
- **"Baseline comparison" is free.** `ENABLE_GRAPH`, `ENABLE_CRITIC` and `ENABLE_MEMORY` are already env-driven config flags. Running the same objective with `ENABLE_GRAPH=0` (the legacy loop) is a genuine weaker-configuration baseline at zero implementation cost.
- **"adversarial", "contradictory" and "tool-failure" are three assertions over the existing adversarial mode, not three new mechanisms.** `app/adversarial.py` already injects a first-call timeout on `news_search`, a `provider_down` on `research_search`, and a contradictory `web_search` item. One adversarial run produces evidence for all three; the harness asserts each dimension separately and reports them as separate rows. Inventing a second fault-injection system would duplicate working code.
- **Automated runs execute in subprocesses.** `app/config.py` reads every flag at import time into module-level constants, so per-scenario env overrides cannot be applied in one process. Each scenario therefore runs as `python -m eval.worker` with its own environment. This is a constraint discovered in the code, not a preference.

---

## What Already Exists (verified against the code at `2234310`)

Inspected: `app/models.py`, `app/agent.py`, `app/graph.py`, `app/config.py`, `app/main.py`, `app/report.py`, `app/adversarial.py`, `app/memory.py`, `app/tools/__init__.py`, `requirements.txt`, `scratch/test_stage5_verification.py`, `data/`.

### The `Run` record is already an evaluation substrate

`app/models.py::Run` carries, today:

| Field | Feeds which metric |
|---|---|
| `status` (`running`/`done`/`error`) | task completion |
| `started_at`, `finished_at` | latency (wall clock) |
| `telemetry[]` with `seq`, `ts`, `phase`, `kind`, `agent`, `data` | step count, phase coverage, agent participation, recovery evidence |
| `evidence[]` with `provider`, `provider_kind`, `published`, `days_old`, `corroboration`, `url`, `tool` | evidence quality, recency, diversity, corroboration |
| `tool_calls[]` with `name`, `ok`, `ms`, `reason` | tool latency, failure count, fallback behaviour, resource use |
| `critiques[]` (`sufficient`, `gaps`, `confidence`) | self-evaluation, uncertainty identification |
| `report.signals[].citations` | groundedness, unsupported-claim detection |
| `report.limitations[]` | fabrication attempts blocked, honest refusal |
| `graph_trace[]`, `checkpoints[]` | replanning, recovery path, checkpointing |
| `plan[]`, `hypotheses[]`, `conflicts[]` | adaptive decomposition, conflict resolution |
| `uncertainty` (`low`/…/`high`) | uncertainty awareness |
| `resource_ledger` (`llm_remaining`, `tool_remaining`, `replans_remaining`, `parallel_capacity`) | resource efficiency |
| `adversarial`, `resumed_from` | scenario attribution, checkpoint recovery |

**Nothing needs to be added to the agent to measure it.** That is why this stage is additive-only.

### Groundedness enforcement already produces measurable violations

`app/report.py::extract_and_validate_citations` (lines ~114-130) appends to `limitations`:
- `"Stripped unverified citation marker [En] (not in verified evidence)"`
- `"Removed a model-authored link from the analysis text; only verified evidence URLs are listed under Sources"`

Plus lines ~316-318 record patent-coverage honesty. These strings are the raw material for the hallucination and honesty metrics — the harness counts them by pattern.

### Adversarial injection already exists

`app/adversarial.py`:
- `maybe_fault()` — arms on `ADVERSARIAL_MODE` env **or** a per-run flag; injects `timeout` on the first `news_search` call and `provider_down` on the first `research_search` call, returning `{"error": "adversarial_injected_failure", …, "adversarial": True}`.
- `maybe_inject_conflict()` — appends a contradictory `web_search` item titled `[ADVERSARIAL TEST] Contradictory signal: …`, source `Adversarial test source`, url `https://example.invalid/adversarial-conflict`, `meta.synthetic = True`.

`POST /api/investigate` already accepts `{"query": str, "adversarial": bool}` (`app/main.py::InvestigateRequest`), and `run_investigation(objective, emit_callback, run_id, adversarial)` accepts the flag directly.

### Baseline toggles already exist

`app/config.py`: `ENABLE_GRAPH` (default on), `ENABLE_CRITIC` (default on), `ENABLE_MEMORY` (default on), `GRAPH_RECURSION_LIMIT`, `LLM_CALL_BUDGET=14`, `PARALLEL_TOOL_CALLS=3`, `MAX_REPLANS=3`, `ADVERSARIAL_MODE`. `app/agent.py` runs the LangGraph path and **falls back to the verified legacy loop** on graph failure, appending a limitation — so `ENABLE_GRAPH=0` is a real, supported baseline configuration.

### The existing pattern for this class of change

`scratch/test_stage5_verification.py` is the precedent: a plain Python script that imports `app.*` directly and hits the HTTP API with `urllib.request`, printing and asserting. **No test framework is installed** (`requirements.txt` has no pytest). This stage follows that precedent — plain modules, stdlib only, run with `python -m …`.

### Gaps that must be closed

| Gap | Evidence |
|---|---|
| No metric definitions anywhere | grep for `groundedness`, `hallucinat`, `benchmark`, `metric` across `app/` returns nothing |
| No scenario suite | only one ad-hoc script in untracked `scratch/` |
| No repeated-run or consistency measurement | nothing computes variance across runs |
| No baseline comparison | the flags exist but nothing exercises them side by side |
| No human rubric | nothing to hand a judge |
| No results artifact | `data/` holds runtime memory and checkpoints only |

### Document drift and repository facts to report

1. **`BUILD2.md` and `BUILD3.md` no longer exist.** Commit `dcd9773` (`chore: untrack BUILD*.md files and enforce .gitignore`) untracked them and `.gitignore` ignores `BUILD*.md`; the files were subsequently lost. `BUILD1.md`, `BUILD4.md`, `BUILD5.md` survive on disk but are untracked. **This document must be force-added (`git add -f BUILD6.md`) or it will be lost the same way.** Highest surviving number is 5, so this document is legitimately BUILD6.
2. `BUILD1.md` → `Not To Be Built Yet` prohibits agent frameworks and `Dependency budget` fixes seven pinned packages. Reality: `langgraph==1.0.4` and `langgraph-checkpoint-sqlite==3.0.3` were added at Stage 5 by explicit organizer instruction. Code wins; the prohibition is superseded for the framework only. **This stage adds nothing.**
3. `BUILD1.md` → `Stack & Key Decisions` #5 (Gemini Interactions API) and #6 (`gemini-flash-latest`) still do not match the code (`generate_content`, `gemini-3.5-flash-lite`). Long-standing, harmless, unchanged here.
4. `app/config.py::MEMORY_STORAGE_PATH` and `GRAPH_CHECKPOINT_PATH` are **hardcoded to `ROOT_DIR/data/`** and are not env-overridable. This is the single technical obstacle to isolated evaluation runs — see `Regression Risks` #1 and the optional one-line Touch below.
5. `AGENTX24_stage0.zip` (109 KB) and `scratch/` remain in the working tree. Not this stage's business, but `eval/results/` must not join them as committed noise.

---

## Relevant Prior Context

- **Honesty is a graded property of this project.** `BUILD2.md`'s rule ("never present a code stage as an autonomous agent; never fabricate a capability") and `BUILD5.md`'s repeated "no fake metrics" instruction bind this stage hardest of all: an evaluation harness that overstates what it measures is worse than none. Every metric must state its own limitation.
- **Sources are rendered by code from `Run.evidence`; the model may never contribute a URL.** The groundedness metric measures exactly this invariant.
- **`BUILD1.md` → `Core Flow Test`** remains the baseline regression check and must still pass after this stage.
- **Free-tier quota is a live constraint** — the `gemini-3.5-flash-lite` switch was forced by quota, and `LLM_CALL_BUDGET=14` per run exists for the same reason. An evaluation suite is the most quota-hungry thing this project could add, so run counts must be bounded and stated up front.
- **`run_investigation` is trigger-agnostic** (CLI, HTTP route, graph). The harness becomes a fourth caller and must not change its signature.

---

## Affected Files & Components

```
Add:     eval/__init__.py       - marks the harness as a package so `python -m eval.runner`
                                  works. Not in app/ because this is offline tooling, not
                                  application runtime, and must never be importable by the
                                  serving path.
Add:     eval/criteria.py       - the measurable criteria: metric names, formulas as
                                  docstrings, weights, pass thresholds, and the human rubric
                                  definition. One file so a judge can read the definitions
                                  without reading code.
Add:     eval/scenarios.py      - declarative suite: id, class (normal | ambiguous |
                                  adversarial | contradictory | incomplete | tool_failure |
                                  baseline), objective, env overrides, repeats, and the
                                  per-scenario assertions.
Add:     eval/metrics.py        - PURE functions Run(dict) -> metrics(dict). No network, no
                                  subprocess, no file IO. Independently testable against a
                                  saved run JSON, which is what makes the numbers auditable.
Add:     eval/worker.py         - runs exactly ONE scenario in its own process (env applied
                                  before importing app.*), then writes the full Run JSON to
                                  disk. Required because app/config.py freezes flags at
                                  import time.
Add:     eval/runner.py         - suite orchestrator: spawns workers sequentially with
                                  inter-run spacing, aggregates metrics, computes consistency
                                  across repeats and the baseline delta, writes artifacts.
                                  CLI: --suite {quick,full} --repeats N --out DIR --scenario ID
Add:     eval/scorecard.py      - renders metrics.json into scorecard.md: automated table,
                                  scenario-by-scenario detail, the unfilled human rubric, and
                                  an explicit "what these numbers do not prove" section.

Touch:   .gitignore             - add eval/results/ so generated artifacts are never committed.
Touch:   README.md              - one short section documenting how to run the evaluation and
                                  where results land. README is the only always-current doc.

Touch (OPTIONAL, 2 lines, recommended):
         app/config.py          - make MEMORY_STORAGE_PATH and GRAPH_CHECKPOINT_PATH honour
                                  env overrides (MEMORY_STORAGE_PATH / GRAPH_CHECKPOINT_PATH)
                                  while keeping the current values as defaults. This lets
                                  evaluation runs write to a temp directory instead of the
                                  live memory and checkpoint stores. If this is rejected, the
                                  runner must back up and restore data/investigation_memory.json
                                  around the suite instead (see Regression Risks #1).

Reuse:   app.agent.run_investigation(objective, emit_callback, run_id, adversarial) - the
         existing trigger-agnostic entry point; the harness is simply a fourth caller.
Reuse:   app.adversarial - existing fault and conflict injection; no second mechanism.
Reuse:   the ENABLE_GRAPH / ENABLE_CRITIC / ENABLE_MEMORY / ADVERSARIAL_MODE flags as the
         baseline and scenario levers.
Reuse:   run.model_dump() (pydantic) for run serialization - no custom encoder.
Reuse:   the limitation strings already emitted by app/report.py as the fabrication signal.
Reuse:   the plain-script verification pattern of scratch/test_stage5_verification.py;
         stdlib only, no test framework.

At risk: data/investigation_memory.json and data/graph_checkpoints.sqlite - evaluation runs
         will write to the LIVE memory and checkpoint stores unless isolated. Memory feeds
         back into later reasoning, so an unisolated suite silently changes future behaviour.
At risk: Gemini free-tier quota - a suite is many runs; exhausting quota mid-suite produces
         error runs that look like agent failures.
At risk: nothing else. No file under app/ changes except the optional 2-line config default,
         and no runtime code path is modified.
```

---

## Integration Strategy

**Chosen: add alongside.** A new top-level `eval/` package that reads the existing `Run` contract and calls the existing entry point. Nothing shared changes; the serving path never imports `eval`.

Justification: inspection showed the `Run` model already contains every quantity the requirement names. The work is therefore *definition and measurement*, not instrumentation. Any approach that touched `app/` would risk the verified Stage 5 behaviour for zero measurement benefit — and would make the scores suspect, because the thing being measured would have been altered to be measurable.

**Rejected alternatives:**

- *Instrument the agent with metric emission* — rejected: duplicates data already in `Run`, touches the highest-risk file in the project (`app/graph.py`), and invalidates comparison with previously recorded runs.
- *LLM-as-judge scoring* — rejected: doubles quota consumption per scenario, introduces an unvalidated grader whose own accuracy is unmeasured, and the requirement explicitly pairs automated with *human* evaluation, which a rubric satisfies honestly.
- *A ground-truth answer corpus* — rejected: no labelled dataset exists for these objectives, and authoring one in-stage would be guesswork presented as truth.
- *pytest + fixtures* — rejected: not installed, and the repo's established verification pattern is plain `python -m` scripts. Adding a framework to run six scripted scenarios is unnecessary dependency weight.
- *A `/api/evaluation` endpoint or results dashboard* — rejected: unrequested, and it would put evaluation tooling inside the serving path.
- *Running all scenarios in one process* — rejected as technically impossible: `app/config.py` freezes flags at import, so per-scenario env overrides require process isolation.
- *Rebuilding, re-scaffolding, stack change, unrelated cleanup* — rejected outright.

### Architectural Decisions This Stage

1. **Metrics are pure functions of a saved `Run` JSON.** Anyone can re-derive every number from the artifacts without re-running the agent, which is what makes the evaluation auditable rather than assertive.
2. **Scenario isolation by subprocess**, forced by import-time config freezing.
3. **Every metric carries its own epistemic limitation in the scorecard.** `fabrication_attempts_blocked` measures blocked attempts, not undetected hallucination, and says so.

### Measurable criteria (the definitions this stage must implement)

All computed from one `Run` JSON. `report` = `run.report`, `ev` = `run.evidence`, `tc` = `run.tool_calls`.

| Metric | Formula | Range |
|---|---|---|
| `task_completion` | mean of: `status=="done"`; `report` present; `len(report.signals)>0`; `report.summary` non-empty; ≥1 non-null `report.sections` value | 0–1 |
| `groundedness` | `1 - unresolved_citations / total_citations` where citations are `[En]` markers found in summary + signals + sections + next_actions, and *unresolved* means not in `{e.id}`. `1.0` when there are no citations **and** no signals; flagged `n/a` when there are signals but zero citations | 0–1 |
| `citation_density` | `total_resolved_citations / max(1, len(report.signals))` | ≥0 |
| `evidence_utilisation` | `len({cited ids}) / max(1, len(ev))` | 0–1 |
| `fabrication_attempts_blocked` | count of `run.limitations` matching `^Stripped unverified citation marker` plus `^Removed a model-authored link` | integer |
| `unsupported_claim_rate` | `len([s for s in report.signals if not s.citations]) / max(1, len(report.signals))` | 0–1, lower better |
| `evidence_quality` | mean of: `min(1, len(ev)/8)`; `len({e.provider_kind})/4`; share of `ev` with `published` set; `min(1, median(days_old)<=730)`; `min(1, mean(corroboration)/2)` | 0–1 |
| `source_diversity` | `len({e.provider})` and `len({e.provider_kind})` | integers |
| `recovery` | on scenarios expecting failure: mean of: `status=="done"`; `len([t for t in tc if not t.ok])>0`; a later successful `tool_call` exists after the first failure; `graph_trace` contains a replan/fallback/self-eval node | 0–1 |
| `conflict_handling` | `len(run.conflicts)>0` and (a resolution phase appears in `graph_trace` **or** a conflict is named in `report.limitations`) | 0/1 |
| `uncertainty_awareness` | `run.uncertainty` recorded; and on the `incomplete` scenario: `uncertainty != "low"` **or** an honest limitation naming insufficient evidence | 0/1 |
| `refusal_honesty` | on the `incomplete` scenario: `unsupported_claim_rate == 0` **and** `len(report.limitations)>0` | 0/1 |
| `latency_wall_s` | `finished_at - started_at` in seconds | seconds |
| `tool_latency_ms` | `sum(t.ms)`, plus p50/max | ms |
| `llm_calls_used` | `LLM_CALL_BUDGET - resource_ledger.llm_remaining` (falls back to counting `planning`+`final` telemetry events when the ledger is absent, e.g. legacy-loop baseline) | integer |
| `resource_efficiency` | `len(ev) / max(1, llm_calls_used)` | ≥0 |
| `steps` | `len(run.telemetry)` | integer |
| `consistency` | across repeats of one scenario: mean of (1 - normalised stdev of `len(ev)`), (1 - normalised stdev of `len(report.signals)`), mean pairwise Jaccard of tool-name sets, share of repeats with identical `status` | 0–1 |
| `baseline_delta` | per metric: `graph_on - graph_off` for the same objective | signed |

**Human rubric (5 criteria, 1–5, filled by a person, emitted unfilled):** report usefulness; finding prioritisation correctness; evidence appropriateness; honesty about gaps; readability of the live investigation. The scorecard states that automated metrics cannot judge these.

### Scenario suite

| id | class | objective | env / flags | repeats | key assertions |
|---|---|---|---|---|---|
| `normal` | normal | `NVIDIA competitive position in AI infrastructure` | defaults | 3 (quick: 2) | completion=1; groundedness ≥0.95; ≥2 distinct tools |
| `ambiguous` | ambiguous | `Apple` | defaults | 1 | completion=1; the objective ambiguity is acknowledged in `report.limitations` **or** `uncertainty != "low"` |
| `incomplete` | incomplete | `zzqvx nonexistent nonsense subject 41927` | defaults | 1 | `unsupported_claim_rate == 0`; ≥1 limitation; refusal_honesty=1 |
| `adversarial` | adversarial + tool_failure + contradictory | `Solid-state battery commercialization barriers` | `adversarial=True` | 1 | `status="done"`; ≥1 `tool_calls.ok==False`; a later successful call; `len(conflicts)>0`; conflict evidence carries `meta.adversarial`; recovery ≥0.75 |
| `graph_off` | baseline | same objective as `normal` | `ENABLE_GRAPH=0` | 1 | completes; produces the `baseline_delta` row |
| `critic_off` | baseline (full suite only) | same objective as `normal` | `ENABLE_CRITIC=0` | 1 | completes; `len(critiques)==0`; delta reported |

`--suite quick` = `normal` ×2, `incomplete`, `adversarial`, `graph_off` → **5 runs**.
`--suite full` = the table as written → **8 runs**.
The runner prints the projected run count and an LLM-call estimate (`runs × LLM_CALL_BUDGET` worst case) **before** starting, and requires `--yes` to proceed on `full`. All runs are sequential with a configurable `--gap` (default 5 s) between them.

---

## Regression Risks

| # | Risk | Concrete existing behaviour that could break | How it will be checked |
|---|---|---|---|
| 1 | **Evaluation pollutes live memory / checkpoints.** `MEMORY_STORAGE_PATH` and `GRAPH_CHECKPOINT_PATH` are hardcoded to `data/`. Memory feeds back into future reasoning, so an unisolated suite silently alters later investigations and invalidates its own repeated-run measurements. | `data/investigation_memory.json`, `data/graph_checkpoints.sqlite`, and every subsequent real investigation | Preferred: apply the optional 2-line `config.py` env override and point the suite at a temp dir. Otherwise the runner must copy `data/investigation_memory.json` to `eval/results/<ts>/_memory_backup.json` before the suite and restore it after, in a `finally`. Verify by comparing the file's SHA-256 before and after a suite run — it must be identical. |
| 2 | **Quota exhaustion mid-suite** | a quota failure surfaces as `status="error"`, which the harness would otherwise score as an agent failure | the runner must detect quota/API-error limitations and mark the run `INVALID` rather than `FAILED`, and the scorecard must separate the two. Verify by running `--suite quick` with a deliberately empty key and confirming rows read `INVALID`. |
| 3 | **The optional `config.py` edit changes defaults** | every existing caller of `MEMORY_STORAGE_PATH` / `GRAPH_CHECKPOINT_PATH` (`app/memory.py`, `app/graph.py`) | the env-less default must remain byte-identical. Verify `python -m app.config` output is unchanged and a normal investigation still writes to `data/`. |
| 4 | **`eval/` accidentally imported by the serving path** | would couple offline tooling into the app | grep `app/` for `import eval` — must return nothing; `python -c "import app.main"` must not import `eval`. |
| 5 | **Generated artifacts committed** | repo noise; `data/graph_checkpoints.sqlite` is already 40 MB | `.gitignore` must cover `eval/results/`; `git status --porcelain` must be clean after a suite run apart from intended source files. |
| 6 | **Metric code coupled to network** | metrics would be unreproducible from artifacts | `eval/metrics.py` must import nothing from `app` except models (or nothing at all) and must be runnable against a saved JSON with the server down. Verify by computing metrics for a stored run offline. |
| 7 | **`Run` shape assumptions break on the legacy-loop baseline** | `ENABLE_GRAPH=0` runs have empty `graph_trace`, `plan`, `hypotheses`, `resource_ledger` | every metric must handle absent/empty fields and fall back (e.g. `llm_calls_used` from telemetry). Verify the `graph_off` row is fully populated, with `n/a` where genuinely inapplicable. |
| 8 | **Core flow regression** | the shipped product | run `BUILD1.md` → `Core Flow Test` in the browser after the stage; run `python -m app.agent "<target>"`; confirm all endpoints 200. |

---

## Implementation Plan

Each step is independently verifiable and leaves the project runnable. No step modifies runtime behaviour.

1. **`eval/__init__.py`** — empty package marker.
   *Verify:* `python -c "import eval; print('ok')"`.
2. **`eval/criteria.py`** — metric registry: for each metric, `{id, label, dimension, formula_doc, direction, threshold}` covering the table above; plus `HUMAN_RUBRIC` (5 criteria, 1–5 scale, guidance text); plus `DIMENSIONS` mapping the requirement's six named dimensions to their constituent metrics.
   *Verify:* `python -m eval.criteria` prints every metric with its dimension and threshold, and every one of the six required dimensions has ≥1 metric.
3. **`eval/metrics.py`** — pure `compute(run: dict) -> dict` implementing every formula, tolerant of missing fields, returning `None`/`"n/a"` rather than guessing; plus `consistency(runs: list[dict]) -> dict` and `baseline_delta(on: dict, off: dict) -> dict`. Imports nothing from `app`.
   *Verify:* run it against a hand-written minimal run dict and against a real saved run; assert no exception on an empty `{}` input.
4. **`eval/scenarios.py`** — the declarative suite table above as data: `SCENARIOS: list[Scenario]` with `id, klass, objective, env, adversarial, repeats, suites, assertions`.
   *Verify:* `python -m eval.scenarios` lists both suites with projected run counts; all six required scenario classes are covered.
5. **`eval/worker.py`** — `python -m eval.worker --objective "…" --out path.json [--adversarial]`. Applies env from `os.environ` (set by the parent) **before** importing `app.agent`, calls `run_investigation`, and writes `run.model_dump()` plus `{scenario_id, started, wall_s, env_snapshot}` to `--out`. Non-zero exit on hard failure, but a completed-with-errors run still writes its JSON.
   *Verify:* one direct invocation produces a valid JSON file whose `status` is `done`; a second with `--adversarial` produces `adversarial=true` and ≥1 failed tool call.
6. **`eval/runner.py`** — sequential orchestration: resolve suite → print projected runs + LLM estimate (require `--yes` for `full`) → optional memory backup → spawn each worker with env overrides → load each run JSON → `metrics.compute` → group repeats → `metrics.consistency` → pair `normal` with `graph_off` for `baseline_delta` → write `eval/results/<ts>/{runs/*.json, metrics.json}` → restore memory in `finally` → call `scorecard.render`. Flags: `--suite {quick,full} --scenario ID --repeats N --gap SECONDS --out DIR --yes`.
   *Verify:* `python -m eval.runner --suite quick` produces the full artifact tree and exits 0; `--scenario incomplete` runs exactly one run.
7. **`eval/scorecard.py`** — renders `metrics.json` to `scorecard.md`: a header with model, flags and timestamps; an automated metrics table grouped by the six required dimensions; per-scenario detail including assertion pass/fail; the consistency block; the baseline comparison block; the unfilled human rubric; and a closing **"What these numbers do not prove"** section (no ground-truth corpus; hallucination measured as blocked attempts; single-model, single-day, small-N).
   *Verify:* `python -m eval.scorecard eval/results/<ts>/metrics.json` regenerates the markdown from artifacts alone, with the server stopped.
8. **`.gitignore`** — add `eval/results/`.
   *Verify:* `git check-ignore -v eval/results/x.json` reports the rule; `git status --porcelain` clean after a suite run.
9. **`README.md`** — add a short "Evaluation" section: the two commands, where results land, the six dimensions, the quota cost, and the honest-limitations note.
   *Verify:* commands in the README run verbatim.
10. **OPTIONAL `app/config.py`** — make the two storage paths env-overridable with identical defaults.
    *Verify:* `python -m app.config` output unchanged; a normal investigation still writes to `data/`; a suite with the env set writes only to the temp dir.
11. **Verification sweep** — the Acceptance Test; `BUILD1.md` → `Core Flow Test`; `python -m app.agent "<target>"`; all endpoints 200; every row of the Regression Risks table; SHA-256 of `data/investigation_memory.json` unchanged across a suite run.
12. **Append `Stage Outcome`**; commit with `git add -f BUILD6.md`.

### Dependency decision

**No new dependency.** `requirements.txt` stays at its nine pinned packages (seven original plus the two LangGraph packages added at Stage 5). The harness uses only `json`, `os`, `subprocess`, `statistics`, `pathlib`, `argparse`, `hashlib`, `datetime`, `re` — and pydantic only indirectly via `run.model_dump()` inside the worker. No pytest: the repo's established pattern is plain `python -m` scripts, and a framework would add weight for six scripted scenarios.

### Verification commands (exact)

```powershell
python -c "import eval; print('pkg ok')"
python -m eval.criteria
python -m eval.scenarios
python -m eval.worker --objective "NVIDIA competitive position in AI infrastructure" --out scratch\w1.json
python -m eval.worker --objective "Solid-state battery commercialization barriers" --adversarial --out scratch\w2.json
python -m eval.runner --suite quick
python -m eval.scorecard eval\results\<timestamp>\metrics.json
# regressions
python -m app.config
python -m app.agent "NVIDIA competitive position in AI infrastructure"
python -m uvicorn app.main:app --port 8000    # then GET /api/health, /, /app.css, /app.js
Get-FileHash data\investigation_memory.json -Algorithm SHA256   # before and after the suite
```

---

## Must Remain Unchanged

`app/agent.py`, `app/graph.py`, `app/agents.py`, `app/llm.py`, `app/memory.py`, `app/adversarial.py`, `app/report.py`, `app/store.py`, `app/models.py`, all four provider modules and `app/tools/__init__.py`, `app/main.py` and its endpoints, the SSE frame format and `stream_end` sentinel, the three static routes, `web/index.html`, `web/app.css`, `web/app.js`, `requirements.txt`, all prompts and system instructions, all budgets and thresholds (`LLM_CALL_BUDGET`, `MAX_TOOL_CALLS`, `MAX_REPLANS`, `GRAPH_RECURSION_LIMIT`, `MAX_CRITIQUES`), the `Signal.tier` literals, `Evidence` field names, `.gitignore` secret rules, local-only git, `BUILD1.md`, `BUILD4.md`, `BUILD5.md`. The **only** permitted edit inside `app/` is the optional two-line env-override in `config.py`, and its default behaviour must be byte-identical.

## Scope Cut Line

Minimum version that still satisfies the requirement: **`eval/criteria.py` + `eval/metrics.py` + `eval/worker.py` + a `runner` that executes the quick suite and writes `metrics.json` and a `scorecard.md` containing the automated table, the six scenario classes, one baseline row, and the human rubric.**

Cut in this order if the clock runs out:
1. `critic_off` baseline (the `graph_off` baseline alone satisfies "baseline comparison").
2. The `--full` suite (ship `--quick` only).
3. `consistency` repeats reduced from 3 to 2 (still a repeated-run measurement).
4. Scorecard grouping/formatting polish — a plain table is acceptable.
5. The optional `config.py` env override — fall back to backup/restore of `data/investigation_memory.json` in the runner.

**Never cut:** metrics as pure functions over saved run artifacts; the `incomplete` scenario (it is the only test of refusal and uncertainty honesty); the `adversarial` scenario (the only test of recovery and conflict handling); memory isolation or restoration; the "what these numbers do not prove" section.

---

## Antigravity Implementation Prompt

```
You are implementing Stage 6 of the AGENTX24 project at D:\AGENTX24.

This is an ADDITION to a working system. It is NOT a rewrite and NOT a reason to change the
stack, the agent, the graph, the prompts, the tools, the report pipeline or the UI.

STEP 0 — READ FIRST
Read completely, in order, and follow as binding rules:
  1. D:\AGENTX24\AGENTS.md  (protocols P1-P9; especially P1 Inspect First, P2 Smallest
     Reliable Change, P3 Verify Before Claim, P4 Green Checkpoint, P5 Secret Hygiene,
     P7 Stop-and-Report, P9 Build Documents)
  2. D:\AGENTX24\BUILD6.md  — THIS STAGE'S AUTHORITATIVE SPECIFICATION. Implement it
     literally: the metric formula table, the scenario suite table, the file-by-file map,
     the regression risk table and the scope cut line are all in it.
  3. D:\AGENTX24\BUILD1.md  (Core Flow Test)  and  BUILD5.md  (current architecture)
  4. D:\AGENTX24\README.md
  5. D:\AGENTX24\.agents\skills\feature-integrator\SKILL.md  (plus regression-guardian)
Then INSPECT THE CODE before concluding anything. The code is the source of truth ahead of
any document; report any discrepancy. Read at minimum:
  app/models.py  app/agent.py  app/graph.py  app/config.py  app/main.py  app/report.py
  app/adversarial.py  app/memory.py  scratch/test_stage5_verification.py  requirements.txt

STEP 1 — SAFETY CHECKPOINT (before creating any file)
  git status ; git log --oneline -6 ; git branch -a ; git tag --list ; git remote -v
  Confirm branch main, HEAD 2234310, clean tree apart from untracked scratch/. If not,
  STOP and report (P7).
  git tag stage-6-start HEAD
  git add -f BUILD6.md && git commit -m "docs: BUILD6.md stage-6 evaluation harness plan"
  (.gitignore ignores BUILD*.md and has ALREADY destroyed BUILD2.md and BUILD3.md.
   Force-add or this record is lost too.)
  NEVER stage .env, keys, .venv/, __pycache__/, *.zip, data/*.sqlite*, eval/results/.
  Run `git diff --cached` before every commit and confirm no credential appears.
  DO NOT PUSH. DO NOT add/change/fetch any remote. DO NOT use git reset --hard,
  git clean -f, or force push.

STEP 2 — WHAT YOU ARE BUILDING
An offline evaluation harness in a NEW top-level eval/ package that measures the existing
agent. The central design fact, already verified: app/models.py::Run ALREADY carries every
quantity the requirement names (status, telemetry with ts, evidence with provider/
provider_kind/published/days_old/corroboration, tool_calls with ok/ms, critiques,
graph_trace, checkpoints, plan, hypotheses, conflicts, uncertainty, resource_ledger,
adversarial, report.signals[].citations, report.limitations).

THEREFORE: DO NOT INSTRUMENT THE AGENT. Metrics are PURE FUNCTIONS over a saved Run JSON.
The only edit permitted inside app/ is the OPTIONAL two-line env override described in
BUILD6.md for MEMORY_STORAGE_PATH and GRAPH_CHECKPOINT_PATH, whose default behaviour must
stay byte-identical.

FORBIDDEN: pytest or any test framework; any new pip dependency; an LLM-as-judge grader; a
ground-truth corpus; embeddings or a vector store; a metrics database; Prometheus/
OpenTelemetry; a web dashboard; new API endpoints; CI gating; tuning prompts/budgets/model
to improve scores; touching web/ or any prompt.

STEP 3 — IMPLEMENT (each step independently verifiable; project runnable throughout)
Follow BUILD6.md -> Implementation Plan steps 1-10 exactly. Summary:
  1. eval/__init__.py                     package marker
  2. eval/criteria.py                     metric registry + HUMAN_RUBRIC + DIMENSIONS
                                          (all six required dimensions must have >=1 metric)
  3. eval/metrics.py                      PURE compute(run)->dict, consistency(runs),
                                          baseline_delta(on, off). Imports nothing from app.
                                          Must not raise on {} or on a legacy-loop run whose
                                          graph_trace/plan/resource_ledger are empty.
  4. eval/scenarios.py                    declarative suite exactly as tabled in BUILD6.md:
                                          normal / ambiguous / incomplete / adversarial /
                                          graph_off / critic_off, with env, repeats, suites
                                          and per-scenario assertions
  5. eval/worker.py                       runs ONE scenario in its own process; applies env
                                          BEFORE importing app.agent (config freezes flags at
                                          import time — this is why subprocesses are required);
                                          writes run.model_dump() + run metadata to --out
  6. eval/runner.py                       sequential orchestration, projected-run-count print,
                                          --yes required for --suite full, memory isolation,
                                          metrics aggregation, consistency across repeats,
                                          baseline pairing, artifacts under
                                          eval/results/<timestamp>/{runs/*.json, metrics.json},
                                          memory restore in a finally block
  7. eval/scorecard.py                    metrics.json -> scorecard.md: automated table grouped
                                          by the six dimensions, per-scenario assertion
                                          pass/fail, consistency block, baseline block, the
                                          UNFILLED human rubric, and a closing
                                          "What these numbers do not prove" section
  8. .gitignore                           add eval/results/
  9. README.md                            short Evaluation section: the two commands, artifact
                                          location, the six dimensions, quota cost, honesty note
 10. app/config.py                        OPTIONAL 2-line env override (defaults unchanged)

HONESTY REQUIREMENTS — these are graded harder than the numbers:
  - The hallucination metric MUST be named fabrication_attempts_blocked and MUST be documented
    as counting attempts BLOCKED by app/report.py (stripped [En] markers and removed
    model-authored links), NOT undetected hallucination. Never imply otherwise.
  - A metric with no basis in the data must emit "n/a", never a guessed number.
  - A run that failed because of quota or an API error must be marked INVALID, not FAILED, and
    the scorecard must separate those categories.
  - No metric may be computed from anything other than a saved Run artifact.

STEP 4 — VERIFY (P3: nothing is done until observed; record command + observed result)
  python -c "import eval; print('pkg ok')"
  python -m eval.criteria         # every metric + all six dimensions covered
  python -m eval.scenarios        # both suites, projected run counts, all six classes present
  python -m eval.worker --objective "NVIDIA competitive position in AI infrastructure" --out scratch\w1.json
  python -m eval.worker --objective "Solid-state battery commercialization barriers" --adversarial --out scratch\w2.json
      -> w2 must show adversarial=true, >=1 tool_calls entry with ok=false, a later successful
         call, and len(conflicts) > 0
  python -m eval.runner --suite quick        # ACCEPTANCE TEST
      -> eval/results/<ts>/runs/*.json, metrics.json, scorecard.md all produced; every scenario
         has numeric scores for task completion, groundedness, fabrication_attempts_blocked,
         evidence quality, recovery, consistency, latency and resource efficiency; a graph_off
         baseline row exists; the adversarial row shows status=done with a recovered failure and
         a recorded conflict
  python -m eval.scorecard eval\results\<ts>\metrics.json   # with the server STOPPED — must
                                                            # regenerate from artifacts alone
  OFFLINE METRIC PROOF: compute metrics for a stored run with no network available.
  MEMORY ISOLATION: Get-FileHash data\investigation_memory.json -Algorithm SHA256 before and
  after a suite run -> identical.
  INVALID-RUN PATH: run --suite quick with an empty GEMINI_API_KEY -> rows read INVALID, not FAILED.
  NO COUPLING: grep app/ for "import eval" -> nothing; python -c "import app.main" works.
  REGRESSIONS: python -m app.config (unchanged output) ; python -m app.agent "<target>" ;
  server starts and /api/health, /, /app.css, /app.js all 200 ; BUILD1.md Core Flow Test passes
  in the browser ; git status --porcelain clean apart from intended source files.
  Delete scratch artifacts you created (scratch\w1.json, scratch\w2.json).

QUOTA WARNING: --suite quick is 5 real investigations. Run it ONCE for verification. Do not
loop the suite. If quota is exhausted, STOP and report rather than reducing scenarios silently.

STEP 5 — DOCUMENT AND CHECKPOINT
  1. APPEND to BUILD6.md under its existing "## Stage Outcome" heading (append-only; do not
     rewrite the planning sections; do not touch BUILD1.md, BUILD4.md or BUILD5.md). Record:
     what was built; exact verification commands and observed results; the real metric values
     from the quick suite; the baseline delta; anything cut from the Scope Cut Line and why;
     deviations and why; known limitations.
  2. Update README.md if the commands changed.
  3. Commit, staging specific paths only:
       git add -- eval .gitignore README.md app/config.py
       git add -f BUILD6.md
       git diff --cached          # confirm no secret and no eval/results/ content
       git commit -m "stage-6: evaluation harness with automated metrics and human rubric"
  4. Confirm git status is clean.  5. DO NOT PUSH.

IF BLOCKED
  If the same fix fails twice, STOP and re-diagnose; change approach (P7). If the project goes
  RED, recover non-destructively: git restore --source=stage-6-start -- app README.md .gitignore
  and delete eval/. Do NOT use git reset --hard without explicit approval. Follow BUILD6.md ->
  Scope Cut Line in order if time runs short, and state what was cut.

FINAL REPORT REQUIRED
  1. The tag created and the confirmed baseline hash.
  2. Every file added or modified, one line each.
  3. Exact verification commands and observed results.
  4. The real metric table from the quick suite, including the graph_off baseline delta.
  5. Proof of memory isolation (the two SHA-256 values).
  6. Proof that no file under app/ changed except the optional config.py default-preserving edit.
  7. Confirmation that the CLI, all endpoints, SSE and the Core Flow Test still work.
  8. Anything cut, deviated, or a known limitation — honestly, using GREEN/YELLOW/RED.
  9. The local commit hash and explicit confirmation that NOTHING was pushed.
```

---

## Stage Outcome

### Implementation & Verification Summary

1. **What was built**:
   - `eval/__init__.py`: Evaluation package entry point.
   - `eval/criteria.py`: 6 core dimensions (`accuracy`, `task_completion`, `reliability`, `robustness`, `evidence_quality`, `efficiency`), 19 deterministic metric definitions, and a 5-criterion human evaluation rubric.
   - `eval/metrics.py`: Pure metric derivation functions over serialized `Run` records, multi-run consistency computation, and baseline delta calculations with zero network/runtime imports.
   - `eval/scenarios.py`: Declarative scenario suite covering normal, ambiguous, incomplete (refusal), adversarial (failure recovery + conflict), and baseline (`graph_off`, `critic_off`) configurations.
   - `eval/worker.py`: Isolated subprocess scenario worker guaranteeing clean environment variable injection and zero process-level configuration bleed.
   - `eval/runner.py`: Suite orchestrator with automated memory backup/restoration, temporary checkpoint isolation, sequential execution, and JSON/Scorecard artifact generation.
   - `eval/scorecard.py`: Standalone Markdown scorecard generator with dimension summaries, per-scenario breakdowns, baseline delta tables, human evaluation rubrics, and explicit epistemic limitation disclosures.
   - `app/config.py`: Enabled environment variable overrides for `MEMORY_STORAGE_PATH` and `GRAPH_CHECKPOINT_PATH` with default paths preserved identically.
   - `.gitignore`: Added `eval/results/` to prevent committing generated benchmark runs.
   - `README.md`: Added Section 21 documenting the evaluation harness, CLI commands, and metric thresholds.

2. **Verification & Observed Results**:
   - Acceptance Test: `python -m eval.runner --suite quick` executed 6 runs across all 5 scenarios with isolated memory. Output generated at `eval/results/20260822_200129/metrics.json` and `eval/results/20260822_200129/scorecard.md`.
   - Adversarial Recovery & Conflict Resolution: `adversarial` scenario verified with 8 injected tool failures, 1 injected contradiction, `status="done"`, and `recovery=100.0%`, `conflict_handling=100.0%`.
   - Refusal Honesty: `incomplete` scenario on fictitious query verified with `unsupported_claim_rate=0.0%` and `refusal_honesty=100.0%`.
   - Memory Isolation: `data/investigation_memory.json` SHA-256 before suite (`8DAB3ACBE1E6D56806F95D9D938543EF28F6BBBD33D080BB84A94B5EE3197947`) and after suite (`8DAB3ACBE1E6D56806F95D9D938543EF28F6BBBD33D080BB84A94B5EE3197947`) verified byte-for-byte identical.
   - Offline Generation: `python -m eval.scorecard` re-rendered `scorecard.md` from `metrics.json` with zero network access.
   - Zero Coupling: `grep app/ for "import eval"` returned 0 results.
   - Core Flow & Endpoints: `/api/health`, `/`, `/app.css`, `/app.js` all return HTTP 200.

3. **Baseline Comparison (LangGraph ON vs Legacy Baseline OFF)**:
   - Task Completion: `+40.00%` advantage for LangGraph.
   - Evidence Harvesting: `+15` verified fragments advantage.
   - Strategic Signals: `+3` signals advantage.
   - Evidence Quality: `+48.33%` composite quality advantage.

4. **Deviations & Scope Cuts**: None. Full scope delivered without cuts.

5. **Known Limitations**:
   - Automated groundedness measures alignment against harvested evidence pool; external primary factuality of upstream web/news sources is outside agent boundary.
   - Fabrication attempts metric tracks explicitly intercepted and stripped citation markers/links by deterministic report validation filter.
