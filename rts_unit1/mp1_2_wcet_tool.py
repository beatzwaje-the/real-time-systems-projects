"""Mini Project 1.2 - Measurement-based WCET estimation and confidence tool.

Usage as a library:
    from mp1_2_wcet_tool import WCETTool
    tool = WCETTool(target_fn, {"random": gen1, "adversarial": gen2})
    report = tool.run(n=500, margin_pct=50)

An input generator is any callable  gen(rng) -> tuple_of_args  (the tool assumes
nothing about the target function's internals).

Run:  python3 mp1_2_wcet_tool.py
Outputs (in ./out): wcet_hist_<target>.png, wcet_table.md, results_1_2.json
"""
import gc
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


# ------------------------------------------------------------- harness ------
def measure(target, input_gen, n, seed=0, warmup=20):
    """Time `target(*args)` n times with perf_counter; keep EVERY sample.

    Returns (durations: ndarray[s], inputs: list of arg tuples).
    The tool never inspects the function - black-box measurement only.
    """
    rng = np.random.default_rng(seed)
    inputs = [input_gen(rng) for _ in range(n)]
    for args in inputs[:warmup]:          # warm caches / interpreter, not recorded
        target(*args)
    gc.collect()
    gc.disable()                          # avoid GC pauses polluting samples
    try:
        d = np.empty(n)
        for i, args in enumerate(inputs):
            t0 = time.perf_counter()
            target(*args)
            d[i] = time.perf_counter() - t0
    finally:
        gc.enable()
    return d, inputs


# ------------------------------------------------------------ statistics ----
def summarize(d, outlier_ratio=1.5):
    """Required statistics + outlier flag (max far above p99)."""
    s = {"n": int(len(d)), "mean": d.mean(), "std": d.std(), "min": d.min(),
         "max": d.max(), "p90": np.percentile(d, 90),
         "p95": np.percentile(d, 95), "p99": np.percentile(d, 99)}
    s = {k: (float(v) if k != "n" else v) for k, v in s.items()}
    s["outlier_flag"] = bool(s["max"] > outlier_ratio * s["p99"])
    return s


def margined(max_obs, margin_pct):
    """Recommended WCET-for-scheduling = observed max * (1 + margin).

    margin_pct = 50  ->  factor 1.5 = 1/0.667, i.e. the estimate is inflated so a
    task set built on it uses only ~67% of the budget it could, matching the
    60-70% utilisation-budget convention of Section 1.7.
    """
    return max_obs * (1.0 + margin_pct / 100.0)


# ----------------------------------------------------------------- tool -----
class WCETTool:
    def __init__(self, target, strategies):
        self.target = target
        self.strategies = strategies       # {name: input_gen}

    def run(self, n=500, margin_pct=50, seed=0):
        rep = {"strategies": {}}
        for name, gen in self.strategies.items():
            d, inputs = measure(self.target, gen, n, seed)
            rep["strategies"][name] = {"samples": d, "inputs": inputs,
                                       "stats": summarize(d)}
        overall_max = max(v["stats"]["max"] for v in rep["strategies"].values())
        rep["overall_max"] = overall_max
        rep["margin_pct"] = margin_pct
        rep["recommended"] = margined(overall_max, margin_pct)
        rnd = rep["strategies"].get("random")["stats"]["max"]
        adv = rep["strategies"].get("adversarial")["stats"]["max"]
        rep["adversarial_over_random"] = adv / rnd
        rep["adversarial_was_largest"] = adv >= rnd
        return rep

    @staticmethod
    def limitations(rep):
        """Honest statement that accompanies every number."""
        return ("Measured maximum over {n} runs per strategy; NOT a sound bound. "
                "Unexercised paths, hardware state (cache/pipeline) and OS noise may "
                "give longer times. Margin of {m}% is a heuristic, not a proof."
                ).format(n=next(iter(rep["strategies"].values()))["stats"]["n"],
                         m=rep["margin_pct"])


# ------------------------------------------------------- target functions ---
def search_early_exit(data, key):
    """T1: early-exit linear search. Time depends on where key sits."""
    for i, v in enumerate(data):
        if v == key:
            return i
    return -1


def collatz_steps(n):
    """T2: data-dependent loop count (steps until n reaches 1)."""
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps


def mode_controller(a, b, c):
    """T3: nested conditionals; the deepest branch is rare and expensive."""
    acc = 0.0
    if a > 0.9:                       # ~10% of random inputs
        if b > 0.9:                   # ~10% of those
            if c > 0.9:               # ~10% of those -> ~0.1% overall
                for i in range(30_000):
                    acc += (i * 0.5) ** 0.5
            else:
                for i in range(3_000):
                    acc += i * 0.5
        else:
            for i in range(300):
                acc += i
    return acc


DATA = list(range(2000))

TARGETS = {
    "search_early_exit": (
        search_early_exit,
        {"random": lambda r: (DATA, int(r.integers(0, 2000))),
         # hand-derived worst case: key absent -> scan all 2000 elements
         "adversarial": lambda r: (DATA, -1)}),
    "collatz_steps": (
        collatz_steps,
        {"random": lambda r: (int(r.integers(1, 100_000)),),
         # hand-derived: 77031 has the longest trajectory (350 steps) below 100000
         "adversarial": lambda r: (77031,)}),
    "mode_controller": (
        mode_controller,
        {"random": lambda r: tuple(r.random(3)),
         # hand-derived: satisfy all three nested conditions
         "adversarial": lambda r: (0.95, 0.95, 0.95)}),
}


# ---------------------------------------------------------- visualisation ---
def plot_hist(name, rep):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = {"random": "tab:blue", "adversarial": "tab:orange"}
    allv = np.concatenate([v["samples"] for v in rep["strategies"].values()]) * 1e6
    bins = np.linspace(allv.min(), np.percentile(allv, 99.5) * 1.05, 60)
    for sname, v in rep["strategies"].items():
        ax.hist(v["samples"] * 1e6, bins=bins, alpha=0.6, color=colors[sname],
                label=f"{sname} (n={v['stats']['n']})")
    ax.axvline(rep["overall_max"] * 1e6, color="r", ls="--",
               label=f"measured max = {rep['overall_max']*1e6:.0f} µs")
    ax.axvline(rep["recommended"] * 1e6, color="k", ls="-",
               label=f"margined (+{rep['margin_pct']}%) = {rep['recommended']*1e6:.0f} µs")
    ax.set_xlabel("execution time (µs)")
    ax.set_ylabel("count")
    ax.set_title(f"Execution-time distribution: {name}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / f"wcet_hist_{name}.png", dpi=150)
    plt.close(fig)


def main(n=500, margin_pct=50):
    all_results, md = {}, []
    md.append("| Target | Random max (µs) | Adversarial max (µs) | Adv / Rand | "
              "Adversarial largest? | Margined (+%d%%) (µs) | Outlier flag (rand / adv) |"
              % margin_pct)
    md.append("|---|---|---|---|---|---|---|")
    stat_rows = ["| Target | Strategy | mean | std | min | max | p90 | p95 | p99 |",
                 "|---|---|---|---|---|---|---|---|---|"]
    for name, (fn, strategies) in TARGETS.items():
        tool = WCETTool(fn, strategies)
        rep = tool.run(n=n, margin_pct=margin_pct)
        plot_hist(name, rep)
        r, a = rep["strategies"]["random"]["stats"], rep["strategies"]["adversarial"]["stats"]
        md.append(f"| {name} | {r['max']*1e6:.1f} | {a['max']*1e6:.1f} | "
                  f"{rep['adversarial_over_random']:.2f}x | "
                  f"{'yes' if rep['adversarial_was_largest'] else 'no'} | "
                  f"{rep['recommended']*1e6:.1f} | {r['outlier_flag']} / {a['outlier_flag']} |")
        for sname in ("random", "adversarial"):
            s = rep["strategies"][sname]["stats"]
            stat_rows.append(f"| {name} | {sname} | " + " | ".join(
                f"{s[k]*1e6:.1f}" for k in ["mean", "std", "min", "max", "p90", "p95", "p99"]) + " |")
        all_results[name] = {
            "stats": {k: v["stats"] for k, v in rep["strategies"].items()},
            "overall_max": rep["overall_max"], "recommended": rep["recommended"],
            "adversarial_over_random": rep["adversarial_over_random"],
            "adversarial_was_largest": rep["adversarial_was_largest"],
            "limitations": WCETTool.limitations(rep)}
    text = "\n".join(md) + "\n\nAll statistics (µs):\n\n" + "\n".join(stat_rows) + "\n"
    (OUT / "wcet_table.md").write_text(text)
    (OUT / "results_1_2.json").write_text(json.dumps(all_results, indent=2))
    print(text)


if __name__ == "__main__":
    main()
