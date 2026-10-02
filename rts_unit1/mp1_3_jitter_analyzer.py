"""Mini Project 1.3 - Real-time jitter analyzer under simulated system noise.

Three independently configurable disturbances (Section 1.6 stand-ins):
  1. background CPU load  (duty cycle)           ~ general OS / bus / cache interference
  2. random pre-job stall (probability, magnitude) ~ interrupt / DMA stall
  3. execution-time variability (distribution spread) ~ cache / pipeline variation

Definitions used (documented so results are reproducible):
  * release = instant the job body starts (after wake-up AND any injected stall)
  * release jitter    = release - ideal release (k*T)
  * completion jitter = deviation of completion offset from its median
  * absolute deadline = IDEAL release + D (fixed, assigned in advance), so a late
    release eats into the job's slack; hit = completion <= ideal release + D.

Run:  python3 mp1_3_jitter_analyzer.py        (about 1-2 minutes)
Outputs (in ./out): sweep_*.png, combined_jitter_vs_hit.png, results_1_3.csv/.md
"""
import csv
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

T = 0.010            # 10 ms period
D = 0.8 * T          # fixed assigned relative deadline (8 ms)
N_JOBS = 250
BASE_WORK = 8_000    # ~1 ms of work


def run_config(bg_duty=0.0, stall_prob=0.0, stall_ms=0.0, work_spread=0.0,
               heavy_tail=False, seed=0):
    """Run one experiment and return a result row."""
    rng = np.random.default_rng(seed)

    # --- disturbance 3: per-job workload drawn from a distribution -------------
    if work_spread > 0:
        if heavy_tail:   # Pareto-type: mostly short, rarely very long
            sizes = BASE_WORK * (1 + work_spread * rng.pareto(2.5, N_JOBS))
        else:            # truncated normal
            sizes = np.clip(rng.normal(BASE_WORK, work_spread * BASE_WORK, N_JOBS),
                            0.2 * BASE_WORK, None)
    else:
        sizes = np.full(N_JOBS, BASE_WORK, dtype=float)
    sizes = sizes.astype(int)

    # --- disturbance 2: Bernoulli stall before the job starts ------------------
    stalls = rng.random(N_JOBS) < stall_prob
    def pre_job_hook(k):
        if stalls[k] and stall_ms > 0:
            time.sleep(stall_ms / 1e3)

    job_fn = lambda k: busy_work(int(sizes[k]))

    def go():
        return run_periodic(N_JOBS, T, job_fn, pre_job_hook)

    if bg_duty > 0:                               # disturbance 1
        with BackgroundLoad(duty=bg_duty):
            ts = go()
    else:
        ts = go()

    rj, cj = release_jitter(ts), completion_jitter(ts)
    hit = ts["complete"] <= ts["ideal"] + D
    return {"bg_duty": bg_duty, "stall_prob": stall_prob, "stall_ms": stall_ms,
            "work_spread": work_spread, "heavy_tail": heavy_tail,
            "rel_jit_std_ms": jitter_summary(rj)[0] * 1e3,
            "rel_jit_max_ms": jitter_summary(rj)[1] * 1e3,
            "cmp_jit_std_ms": jitter_summary(cj)[0] * 1e3,
            "cmp_jit_max_ms": jitter_summary(cj)[1] * 1e3,
            "hit_fraction": float(hit.mean())}


def sweep(name, param, values, **fixed):
    rows = []
    for v in values:
        row = run_config(**{**fixed, param: v})
        row["mechanism"] = name
        rows.append(row)
        print(f"{name:10s} {param}={v:<6} rel_std={row['rel_jit_std_ms']:.3f}ms "
              f"rel_max={row['rel_jit_max_ms']:.2f}ms hit={row['hit_fraction']:.3f}",
              flush=True)
    return rows


def plot_sweep(rows, param, xlabel, fname, title):
    x = [r[param] for r in rows]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(x, [r["rel_jit_std_ms"] for r in rows], "o-", label="release jitter std")
    ax.plot(x, [r["rel_jit_max_ms"] for r in rows], "s--", label="release jitter max |.|")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("release jitter (ms)")
    ax2 = ax.twinx()
    ax2.plot(x, [100 * r["hit_fraction"] for r in rows], "^:", color="tab:green",
             label="deadline hit %")
    ax2.set_ylabel("deadline hit (%)")
    ax2.set_ylim(0, 105)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=150)
    plt.close(fig)


def main():
    rows = []
    # Control condition (all disturbances off) - repeated to show baseline spread
    base = [run_config(seed=s) for s in range(3)]
    for b in base:
        b["mechanism"] = "baseline"
        print("baseline", {k: round(v, 3) for k, v in b.items()
                           if k.endswith("ms") or k == "hit_fraction"}, flush=True)
    rows += base

    bg = sweep("bg_load", "bg_duty", [0.0, 0.25, 0.5, 0.75, 1.0])
    sp = sweep("stall_prob", "stall_prob", [0.0, 0.02, 0.05, 0.10, 0.20], stall_ms=3.0)
    sm = sweep("stall_mag", "stall_ms", [0.0, 1.0, 3.0, 5.0, 8.0], stall_prob=0.05)
    wn = sweep("var_normal", "work_spread", [0.0, 0.1, 0.25, 0.5, 1.0])
    wh = sweep("var_heavy", "work_spread", [0.0, 0.25, 0.5, 1.0, 2.0], heavy_tail=True)
    rows += bg + sp + sm + wn + wh

    plot_sweep(bg, "bg_duty", "background load duty cycle", "sweep_bg_load.png",
               "Disturbance 1: background CPU load")
    plot_sweep(sp, "stall_prob", "stall probability (3 ms stall)", "sweep_stall_prob.png",
               "Disturbance 2a: random stall probability")
    plot_sweep(sm, "stall_ms", "stall magnitude (ms, p=0.05)", "sweep_stall_mag.png",
               "Disturbance 2b: random stall magnitude")
    plot_sweep(wn, "work_spread", "workload spread (σ / mean, normal)",
               "sweep_var_normal.png", "Disturbance 3a: execution-time variability (normal)")
    plot_sweep(wh, "work_spread", "tail scale (heavy-tailed workload)",
               "sweep_var_heavy.png", "Disturbance 3b: execution-time variability (heavy tail)")

    # Combined plot: every non-baseline config, jitter vs hit rate
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for mech, mk in [("bg_load", "o"), ("stall_prob", "s"), ("stall_mag", "^"),
                     ("var_normal", "D"), ("var_heavy", "v")]:
        r = [x for x in rows if x["mechanism"] == mech]
        ax.scatter([x["rel_jit_std_ms"] for x in r], [100 * x["hit_fraction"] for x in r],
                   marker=mk, label=mech, s=55)
    ax.set_xlabel("release jitter std (ms)")
    ax.set_ylabel("deadline hit (%)")
    ax.set_title("Jitter vs deadline-hit rate (all configurations)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "combined_jitter_vs_hit.png", dpi=150)
    plt.close(fig)

    # Results table (csv + markdown)
    cols = ["mechanism", "bg_duty", "stall_prob", "stall_ms", "work_spread", "heavy_tail",
            "rel_jit_std_ms", "rel_jit_max_ms", "cmp_jit_std_ms", "cmp_jit_max_ms",
            "hit_fraction"]
    with open(OUT / "results_1_3.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows({c: r[c] for c in cols} for r in rows)
    md = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        md.append("| " + " | ".join(
            f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    # Highlight: configs with hit >= 95% but release jitter std well above baseline
    base_std = np.mean([b["rel_jit_std_ms"] for b in base])
    hl = [r for r in rows if r["mechanism"] != "baseline" and r["hit_fraction"] >= 0.95
          and r["rel_jit_std_ms"] >= 5 * base_std]
    md.append(f"\nBaseline mean release-jitter std = {base_std:.3f} ms.")
    md.append("\nConfigs with hit >= 95% but release-jitter std >= 5x baseline:\n")
    for r in hl:
        md.append(f"- {r['mechanism']} (bg={r['bg_duty']}, p={r['stall_prob']}, "
                  f"stall={r['stall_ms']}ms, spread={r['work_spread']}): "
                  f"jitter std {r['rel_jit_std_ms']:.3f} ms, hit {100*r['hit_fraction']:.1f}%")
    (OUT / "results_1_3.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
