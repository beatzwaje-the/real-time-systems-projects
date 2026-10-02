# Real-Time Systems — Unit 1 Mini Projects: Lab Report

All numbers below come from one run of the included scripts on a shared, **single-core Linux sandbox** (Python, `perf_counter`). On your own machine the absolute values will differ — and from run to run — which is itself the lesson of Section 1.6. Re-run the scripts and paste your own numbers before submitting.

Files: `rtlib.py` (shared helpers) · `mp1_1_task_timing.py` · `mp1_2_wcet_tool.py` · `mp1_3_jitter_analyzer.py` · `out/` (plots, tables, JSON/CSV).
Run: `python3 mp1_1_task_timing.py`, `python3 mp1_2_wcet_tool.py`, `python3 mp1_3_jitter_analyzer.py` (needs numpy, matplotlib).

---
## Mini Project 1.1 — Task timing simulation

**Setup.** Job = `job_body(x)`: a numerical loop whose length grows with input x ∈ [0,1], plus an extra long path when x ≥ 0.95. Period T = 50 ms, deadline D = 0.8·T = 40 ms, 120 jobs. Release loop recomputes `r0 + k·T` each iteration (no drift). Utilities: hard = +1 / −10, firm = 1 / 0, soft = 1 then `exp(−(R−D)/τ)`, τ = 0.25·D.

**Step 2 – isolated execution time (300 calls, ordinary inputs):**

| mean | std | max (*measured*, not proven WCET) | p95 |
|---|---|---|---|
| 10.7 ms | 3.2 ms | 29.1 ms | 16.1 ms |

The max is only the largest value seen in 300 samples. It is not a bound: another input or a bad cache/OS moment can exceed it (Section 1.7). A static analysis would derive a bound from the code's worst path, without running it.

**Step 9 summary (unloaded run).**

| Quantity | Value |
|---|---|
| mean / max execution time vs T, D | 10.7 ms / 29.1 ms vs T = 50, D = 40 → max uses 73% of D |
| Response time R (mean / p95 / max) | 12.7 / 25.0 / 27.4 ms |
| Release jitter (std / max) | 0.035 ms / 0.38 ms |
| Completion jitter (std / max) | 5.1 ms / 16.2 ms |
| Deadline-hit fraction | 100% (0 / 120 missed) |

Completion jitter is ~150× release jitter: the job's own data-dependent running time dominates, not the timer.

**Which cost function would apply?** The task is a periodic filter/control-style update with a tail that sits close to D. In a Section 1.1 domain such as an automotive or industrial control loop, a miss can destabilise the plant, so a **hard** (or at least firm) cost function is realistic. If it were audio/video streaming, a **soft** function is realistic (a late frame is degraded, not catastrophic). A task this variable that must be hard needs a proper WCET bound, not these measurements.

**Plots:** `out/fig1_3_timeline_unloaded.png`, `out/fig1_1_response_utility_unloaded.png` (and `_loaded` versions).

**Lab Task 1 – background busy thread (continuous):**

| | R mean | R p95 | R max | Release jitter std / max | Hit |
|---|---|---|---|---|---|
| Unloaded | 12.7 ms | 25.0 ms | 27.4 ms | 0.035 / 0.38 ms | 100% |
| Loaded | 18.9 ms | 39.8 ms | 58.4 ms | 1.02 / 13.7 ms | 95.8% (5 misses) |

The competing thread shares the interpreter (GIL) and CPU, so R grows ~50%, the tail crosses D, and release jitter grows ~30×. This reproduces the Section 1.6 interference effect.

**Expected-observation check – shrinking D** (computed from the unloaded run's own R values):

| D | 30.0 ms (1.2·p95) | 25.0 (1.0·p95) | 22.5 (0.9) | 20.0 (0.8) | 17.5 (0.7) | 15.0 (0.6) |
|---|---|---|---|---|---|---|
| Miss fraction | 0% | 5% | 7.5% | 13.3% | 16.7% | 25.8% |

The tail (p95), not the mean (12.7 ms), governs schedulability. At D = 15 ms, well above the mean, a quarter of jobs still miss.

**Lab Task 2 – adversarial inputs (x = 1.0, 300 calls):** mean 22.9 ms, p95 37.8 ms, **max 60.8 ms** vs ordinary max 29.1 ms — about 2× larger, and it exceeds D = 40 ms. So ordinary testing would have certified a task that can miss its deadline. Even this adversarial max is not a sound bound: it covers only the one path I wrote and not cache, pipeline or OS effects. Only static analysis (or a hardware model) can claim to cover all paths and states, at the price of pessimism.

**Lab Task 3 – soft-decay rate** (utility at R = 1.1·D / 1.5·D / 2.0·D):

| τ | 1.1D | 1.5D | 2.0D |
|---|---|---|---|
| 0.05·D (fast) | 0.135 | 0.000 | 0.000 |
| 0.25·D (default) | 0.670 | 0.135 | 0.018 |
| 1.0·D (slow) | 0.905 | 0.607 | 0.368 |

A fast decay makes the "soft" task behave almost like a firm one; a slow decay says lateness is nearly harmless. τ must come from the application — e.g. how much a user notices a late video frame, or the plant's tolerance — not be chosen to make the results look good.

**Lab Task 4 – vary T, D = 0.8·T:**

| T | D | Release-jitter std (% of T) | Release-jitter max (% of T) | Hit |
|---|---|---|---|---|
| 20 ms | 16 ms | 28.7% | 111% | 59% |
| 50 ms | 40 ms | 0.75% | 6.9% | 100% |
| 100 ms | 80 ms | 0.04% | 0.3% | 100% |

Jitter is roughly an absolute amount (set by OS and timer), so it eats a larger share of a shorter period. At T = 20 ms the jitter is a large part of the period and, together with the job tail, causes 41% misses. Caveat: the T = 50 ms row here (0.75%) is much worse than in the main run (0.07%); the sandbox's noise is not constant, which is why jitter must be measured, not assumed.

---
## Mini Project 1.2 — Measurement-based WCET tool

**Design.** `WCETTool(target, strategies).run(n, margin_pct)` treats the function as a black box: `measure()` times every call (`perf_counter`, warm-up excluded, GC disabled), keeps all samples; `summarize()` gives mean/std/min/max/p90/p95/p99 and flags an **outlier** when max > 1.5·p99; `margined()` returns `max·(1 + margin)`. Default margin 50% (factor 1.5 ≈ planning to use only ~67% of the budget, matching Section 1.7's 60–70% convention). Every report carries a limitations statement. 500 samples per strategy per target.

**Targets and hand-derived adversarial inputs.**
1. `search_early_exit` (early-exit loop): adversarial = key absent → scans all 2000 elements.
2. `collatz_steps` (data-dependent loop count): adversarial = 77031, which has the longest trajectory (350 steps) below 100 000.
3. `mode_controller` (three nested conditionals; deepest branch needs a>0.9, b>0.9, c>0.9 → ~0.1% of random inputs): adversarial = (0.95, 0.95, 0.95).

**Comparison table** (µs; `out/wcet_table.md`):

| Target | Random max | Adversarial max | Adv / Rand | Adversarial largest? | Margined (+50%) | Outlier flag (rand / adv) |
|---|---|---|---|---|---|---|
| search_early_exit | 122.2 | 676.8 | 5.54× | yes | 1015.3 | no / yes |
| collatz_steps | 98.5 | 218.9 | 2.22× | yes | 328.3 | yes / yes |
| mode_controller | 211.9 | 5307.9 | **25.05×** | yes | 7961.9 | yes / no |

Distribution statistics (mean / p99 / max, µs): search random 33.5 / 86.5 / 122.2, adversarial 72.9 / 281.9 / 676.8; collatz random 7.5 / 30.0 / 98.5, adversarial 25.7 / 72.8 / 218.9; mode_controller random 3.2 / 19.6 / 211.9, adversarial 2739 / 4704 / 5308. Full tables are in `out/wcet_table.md`; histograms: `out/wcet_hist_<target>.png`.

**Discussion.**
- *Estimated confidently:* `search_early_exit` and `collatz_steps`. Their worst case is easy to reason about and random sampling reaches within 2–5× of it; the margin plus the adversarial run covers it, but the adversarial **max** is inflated by timing noise (the max is far above p99 — the outlier flag fires), so part of what we call "WCET" is OS noise, not code.
- *Underestimated:* `mode_controller`. The deepest branch occurs in about 1 in 1000 random inputs, so 500 random runs never reached it: the random-strategy max (212 µs) is **25× below** the adversarial value (5.3 ms). Without the hand-derived input the tool would have recommended ~318 µs — wrong by a factor of ~17. Measurement finds only paths the inputs exercise; that is the unsoundness of Section 1.7.
- *Soundness vs pessimism.* Static analysis is safe but pessimistic (it may charge a path or cache state that never happens); measurement is tight but unsafe. The margin is a heuristic that cannot fix a missed path, as `mode_controller` shows.
- *Certification (Section 1.8)* would not accept this tool alone: it has no proof that the worst-case path was covered, no model of cache/pipeline/interrupt state, runs on a general-purpose OS with an interpreter, and the margin has no justification. It is a useful engineering estimate and a way to test an analyser's results, not a certified bound.

---
## Mini Project 1.3 — Jitter analyzer under simulated noise

**Setup.** T = 10 ms, D = 8 ms (fixed), 250 jobs per configuration, ~1 ms nominal job. *Release* = job body starts (after wake-up and any injected stall); *absolute deadline* = ideal release + D, so late releases eat the slack. Completion jitter = deviation of completion offset from its median. Disturbances: (1) `BackgroundLoad(duty)` thread; (2) Bernoulli stall before the job, `(probability, ms)`; (3) per-job workload from a normal (σ/mean) or heavy-tailed (Pareto) distribution.

**Control (all disturbances off, 3 runs):** release-jitter std 0.13 / 0.16 / 0.29 ms, hit 100 / 100 / 99.6%. Even undisturbed, jitter is non-zero and varies between runs (timer resolution, scheduler, other tenants).

**Sweeps** (release-jitter std ms / max ms / hit %; full table `out/results_1_3.md`, `.csv`):

| Mechanism | Setting → result |
|---|---|
| Background load (duty) | 0.25 → 0.73 / 2.8 / 100 · 0.5 → 1.66 / 5.2 / 100 · 0.75 → 1.94 / 7.5 / 98.4 · 1.0 → 2.43 / 33.8 / 91.6 |
| Stall probability (3 ms) | 0.02 → 0.53 / 3.5 / 100 · 0.05 → 0.67 / 3.3 / 100 · 0.10 → 1.07 / 7.4 / 99.6 · 0.20 → 1.28 / 4.4 / 100 |
| Stall magnitude (p = 0.05) | 1 ms → 0.28 / 1.8 / 100 · 3 → 0.69 / 3.4 / 100 · 5 → 1.12 / 5.5 / 99.6 · 8 → 1.75 / 8.5 / 95.2 |
| Variability (normal σ/mean) | 0.25 → 0.04 / 0.5 / 100 · 0.5 → 0.09 / 1.2 / 100 · 1.0 → 0.06 / 0.6 / 100 (completion-jitter std 0.54 → 0.92 → 1.10 ms) |
| Variability (heavy tail) | 0.5 → 0.06 / 0.9 / 99.6 · 1.0 → 0.04 / 0.5 / 99.2 · 2.0 → 1.30 / 13.7 / 92.8 (completion-jitter std 1.06 → 1.58 → 3.50 ms) |

Plots: `out/sweep_*.png` (jitter + hit rate per sweep), `out/combined_jitter_vs_hit.png`.

**Jitter without misses (the core demonstration).** Several configurations kept the hit rate ≥ 95% while release-jitter std grew ≥ 5× over the 0.195 ms baseline mean: 50% load (1.66 ms, 100% hit), 20% stall probability (1.28 ms, 100%), 5 ms stalls (1.12 ms, 99.6%), 8 ms stalls (1.75 ms, 95.2%). All deadlines were met while the release instants were 5–9× more irregular. Meeting every deadline and having low jitter are different properties.

Two cautions from the data: (1) normal-distribution workload spread barely moves **release** jitter (the job's own length can't change when it starts) but raises **completion** jitter — see the completion columns; (2) the single spread = 0.1 point (0.77 ms, max 11.7 ms) is an OS-noise spike, not an effect of the setting, so one run per point is not enough for conclusions; repeat each point several times and report the median/range.

**Mapping to Section 1.6 (and where it breaks down).**
- *Background load* ≈ OS/other-process interference and shared-resource (bus/cache) contention. Breaks down: here the contention is for the CPython GIL and a single core; a real RTOS would use priorities/preemption, and cache contention is not modelled.
- *Random stall* ≈ interrupts and DMA bus stealing, which delay dispatch at unpredictable moments. Breaks down: `time.sleep` yields the CPU (a real interrupt or DMA transfer does not free it for others), and real interrupts are not Bernoulli-independent — they are often periodic or bursty.
- *Workload variability* ≈ cache misses, branch mispredictions and pipeline hazards that change execution time by input and state. Breaks down: the random draw is independent per job, whereas real variation depends on history (cache state, predictor) and is correlated.
- *OS jitter* itself is not simulated — it is the uncontrolled background in every run (see the baseline).
