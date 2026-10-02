"""Mini Project 1.1 - Simulating and measuring real-time task timing in Python.

Run:  python3 mp1_1_task_timing.py
Outputs (in ./out): fig1_3_timeline_*.png, fig1_1_response_utility_*.png, results_1_1.json
"""
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rtlib import (BackgroundLoad, busy_work, completion_jitter, jitter_summary,
                   release_jitter, run_periodic)

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

LONG_PATH_THRESHOLD = 0.95   # inputs x >= this take the job's longest code path


# ----------------------------------------------------------- Step 1: job ----
def job_body(x):
    """Body of the real-time job. x in [0, 1] controls the workload.

    * Base cost grows linearly with x (data-dependent loop length).
    * Inputs x >= 0.95 take an extra branch (the 'longest path').
    This imitates the execution-time variability of Section 1.7.
    """
    acc = busy_work(60_000 + int(60_000 * x))
    if x >= LONG_PATH_THRESHOLD:
        acc += busy_work(60_000)
    return acc


# --------------------------------------------------------------- Step 2 ----
def measure_isolated(inputs):
    """Time job_body once per input with perf_counter; returns durations (s)."""
    job_body(0.5)  # warm-up call, not recorded
    d = np.empty(len(inputs))
    for i, x in enumerate(inputs):
        t0 = time.perf_counter()
        job_body(x)
        d[i] = time.perf_counter() - t0
    return d


def exec_stats(d):
    return {"mean": float(d.mean()), "std": float(d.std()), "max": float(d.max()),
            "p95": float(np.percentile(d, 95))}


# ------------------------------------------------------------- Steps 3-6 ----
def utilities(R, D, hard_penalty=-10.0, tau=None):
    """Hard / firm / soft utility of each job from its response time R (fig1_1).

    hard : 1 while R <= D, hard_penalty (large negative) once R > D
    firm : 1 while R <= D, exactly 0 once R > D
    soft : 1 while R <= D, then exp(-(R-D)/tau) -> 0 gradually
    """
    if tau is None:
        tau = 0.25 * D
    met = R <= D
    hard = np.where(met, 1.0, hard_penalty)
    firm = np.where(met, 1.0, 0.0)
    soft = np.where(met, 1.0, np.exp(-(R - D) / tau))
    return hard, firm, soft


def run_experiment(T, D_frac, n_jobs, seed, bg_load=False):
    """Periodic release loop + full instrumentation (Steps 3-6)."""
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0.0, 0.9, n_jobs)           # ordinary inputs
    D = D_frac * T
    job_fn = lambda k: job_body(xs[k])
    if bg_load:
        with BackgroundLoad(duty=1.0):
            ts = run_periodic(n_jobs, T, job_fn)
    else:
        ts = run_periodic(n_jobs, T, job_fn)
    R = ts["complete"] - ts["release"]            # response time
    rj, cj = release_jitter(ts), completion_jitter(ts)
    met = R <= D
    res = {"T": T, "D": D, "n_jobs": n_jobs, "bg_load": bg_load,
           "R_mean": float(R.mean()), "R_max": float(R.max()),
           "R_p95": float(np.percentile(R, 95)),
           "release_jitter_std": jitter_summary(rj)[0],
           "release_jitter_max": jitter_summary(rj)[1],
           "completion_jitter_std": jitter_summary(cj)[0],
           "completion_jitter_max": jitter_summary(cj)[1],
           "hit_fraction": float(met.mean()), "misses": int((~met).sum())}
    return ts, R, D, res


# ----------------------------------------------------------- Steps 7 & 8 ----
def plot_timeline(ts, D, tag, n_show=12):
    """fig1_3-style diagram: one bar per job, deadline marker, misses in red."""
    # show the n_show-job window that contains the most deadline misses
    miss = ((ts["complete"] - ts["release"]) > D).astype(int)
    starts = range(len(miss) - n_show + 1)
    s0 = max(starts, key=lambda s_: miss[s_:s_ + n_show].sum())
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for k in range(s0, s0 + n_show):
        rel, comp = ts["release"][k], ts["complete"][k]
        missed = (comp - rel) > D
        ax.broken_barh([(rel * 1e3, (comp - rel) * 1e3)], (k - 0.35, 0.7),
                       facecolors="tab:red" if missed else "tab:blue")
        ax.plot((rel + D) * 1e3, k, marker="v", color="k", ms=6)
        ax.axvline(ts["ideal"][k] * 1e3, color="gray", lw=0.6, ls=":")
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("job index k")
    ax.set_yticks(range(s0, s0 + n_show))
    ax.invert_yaxis()
    ax.set_title(f"Timing diagram ({tag}): bar = release→completion, ▼ = deadline, "
                 "dotted = ideal release")
    fig.tight_layout()
    fig.savefig(OUT / f"fig1_3_timeline_{tag}.png", dpi=150)
    plt.close(fig)


def plot_response_utility(R, D, tag, tau=None):
    hard, firm, soft = utilities(R, D, tau=tau)
    k = np.arange(len(R))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True)
    a1.plot(k, R * 1e3, ".-", lw=0.8)
    a1.axhline(D * 1e3, color="r", ls="--", label=f"deadline D = {D*1e3:.0f} ms")
    a1.set_ylabel("response time R (ms)")
    a1.legend()
    a1.set_title(f"Response time and hard/firm/soft utility ({tag})")
    a2.plot(k, hard, label="hard (−10 after miss)", drawstyle="steps-mid")
    a2.plot(k, firm, label="firm (0 after miss)", drawstyle="steps-mid")
    a2.plot(k, soft, label="soft (exp. decay)", drawstyle="steps-mid")
    a2.set_xlabel("job index")
    a2.set_ylabel("utility")
    a2.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / f"fig1_1_response_utility_{tag}.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------ main ----
def main():
    results = {}
    rng = np.random.default_rng(0)

    # Step 2 + Lab Task 2: ordinary vs adversarial inputs, 300 calls each
    d_ord = measure_isolated(rng.uniform(0.0, 0.9, 300))
    d_adv = measure_isolated(np.ones(300))        # x = 1.0 -> longest path
    results["exec_ordinary"] = exec_stats(d_ord)
    results["exec_adversarial"] = exec_stats(d_adv)

    # Steps 3-8: unloaded run (T = 50 ms, D = 0.8 T, 120 jobs)
    ts0, R0, D0, res0 = run_experiment(0.05, 0.8, 120, seed=1)
    results["unloaded"] = res0
    plot_timeline(ts0, D0, "unloaded")
    plot_response_utility(R0, D0, "unloaded")

    # Lab Task 1: continuous background thread
    ts1, R1, D1, res1 = run_experiment(0.05, 0.8, 120, seed=1, bg_load=True)
    results["loaded"] = res1
    plot_timeline(ts1, D1, "loaded")
    plot_response_utility(R1, D1, "loaded")

    # Shrinking D toward the mean (analysis on the unloaded run's own R values)
    sweep = {}
    for frac in [1.2, 1.0, 0.9, 0.8, 0.7, 0.6]:
        Dtest = frac * np.percentile(R0, 95)
        sweep[f"D={frac}*p95"] = {"D_ms": float(Dtest * 1e3),
                                  "miss_fraction": float((R0 > Dtest).mean())}
    results["D_sweep_unloaded"] = sweep

    # Lab Task 3: soft-deadline decay rate (analytic, utility at R = k*D)
    tau_table = {}
    for name, tau_f in [("fast (tau=0.05D)", 0.05), ("default (tau=0.25D)", 0.25),
                        ("slow (tau=1.0D)", 1.0)]:
        _, _, soft = utilities(np.array([1.1, 1.5, 2.0]) * D0, D0, tau=tau_f * D0)
        tau_table[name] = [round(float(s), 3) for s in soft]
    results["soft_utility_at_1.1D_1.5D_2.0D"] = tau_table

    # Lab Task 4: vary T with D = 0.8 T
    t_sweep = []
    for T in [0.02, 0.05, 0.1]:
        _, _, _, r = run_experiment(T, 0.8, 100, seed=2)
        r["release_jitter_std_pct_of_T"] = 100 * r["release_jitter_std"] / T
        r["release_jitter_max_pct_of_T"] = 100 * r["release_jitter_max"] / T
        t_sweep.append(r)
    results["T_sweep"] = t_sweep

    (OUT / "results_1_1.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
