"""
REAL-TIME SYSTEMS
Mini Project 1.3:
Real-Time Jitter Analyzer Under Simulated System Noise

Requirements:
- Python 3
- NumPy
- Matplotlib
- threading
"""

import time
import threading
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# SETTINGS
# ============================================================

T = 0.02

# Deadline = 90% of period
D = 0.9 * T

NUMBER_OF_JOBS = 200

RESULTS_FOLDER = Path("results_1_3")
RESULTS_FOLDER.mkdir(exist_ok=True)


# ============================================================
# REAL-TIME JOB
# ============================================================

def real_time_job(workload):

    result = 0

    for i in range(
        max(1, int(workload))
    ):

        result = (
            result + i * i
        ) % 100003

    return result


# ============================================================
# BACKGROUND CPU LOAD
# ============================================================

class BackgroundLoad(
    threading.Thread
):

    def __init__(
        self,
        stop_event,
        intensity
    ):

        super().__init__(
            daemon=True
        )

        self.stop_event = (
            stop_event
        )

        self.intensity = intensity

    def run(self):

        while not self.stop_event.is_set():

            # More intensity = more arithmetic work
            iterations = max(
                1,
                int(
                    2000
                    * self.intensity
                )
            )

            for _ in range(
                iterations
            ):

                _ = (
                    12345
                    * 67891
                )

            # Low intensity gives the
            # real-time task some space.
            if self.intensity < 0.5:

                time.sleep(
                    0.001
                )


# ============================================================
# SINGLE EXPERIMENT
# ============================================================

def run_experiment(

    load_intensity=0.0,

    delay_probability=0.0,

    delay_ms=0.0,

    execution_spread=0.0,

    seed=123

):

    rng = np.random.default_rng(
        seed
    )

    stop_event = (
        threading.Event()
    )

    background_thread = None

    # --------------------------------------------------------
    # Start background load
    # --------------------------------------------------------

    if load_intensity > 0:

        background_thread = (
            BackgroundLoad(
                stop_event,
                load_intensity
            )
        )

        background_thread.start()

    # --------------------------------------------------------
    # Reference start time
    # --------------------------------------------------------

    start_time = (
        time.perf_counter()
    )

    actual_releases = []

    completions = []

    response_times = []

    try:

        # ====================================================
        # PERIODIC JOB LOOP
        # ====================================================

        for job_number in range(
            NUMBER_OF_JOBS
        ):

            # ------------------------------------------------
            # Ideal release
            # ------------------------------------------------

            ideal_release = (
                start_time
                + job_number * T
            )

            # ------------------------------------------------
            # Sleep until ideal release
            # ------------------------------------------------

            remaining = (
                ideal_release
                - time.perf_counter()
            )

            if remaining > 0:

                time.sleep(
                    remaining
                )

            # ------------------------------------------------
            # Actual release
            # ------------------------------------------------

            actual_release = (
                time.perf_counter()
            )

            actual_releases.append(
                actual_release
            )

            # ------------------------------------------------
            # Random extra delay
            # ------------------------------------------------

            if (
                rng.random()
                <
                delay_probability
            ):

                time.sleep(
                    delay_ms / 1000
                )

            # ------------------------------------------------
            # Variable execution workload
            # ------------------------------------------------

            base_workload = 450

            if execution_spread > 0:

                factor = (
                    rng.normal(
                        1.0,
                        execution_spread
                    )
                )

                # Do not allow negative workload
                factor = max(
                    0.2,
                    factor
                )

                workload = (
                    base_workload
                    * factor
                )

            else:

                workload = (
                    base_workload
                )

            # ------------------------------------------------
            # Execute task
            # ------------------------------------------------

            real_time_job(
                workload
            )

            # ------------------------------------------------
            # Completion
            # ------------------------------------------------

            completion = (
                time.perf_counter()
            )

            completions.append(
                completion
            )

            # ------------------------------------------------
            # Response time
            # ------------------------------------------------

            response = (
                completion
                - actual_release
            )

            response_times.append(
                response
            )

    finally:

        # ----------------------------------------------------
        # Stop background thread
        # ----------------------------------------------------

        if background_thread:

            stop_event.set()

            background_thread.join(
                timeout=0.2
            )

    # ========================================================
    # CALCULATE JITTER
    # ========================================================

    actual_releases = np.array(
        actual_releases
    )

    completions = np.array(
        completions
    )

    response_times = np.array(
        response_times
    )

    ideal_releases = np.array([
        start_time + i * T
        for i in range(
            NUMBER_OF_JOBS
        )
    ])

    # --------------------------------------------------------
    # Release jitter
    # --------------------------------------------------------

    release_jitter = (
        actual_releases
        - ideal_releases
    )

    # --------------------------------------------------------
    # Completion jitter
    #
    # We compare actual completion against
    # ideal release + measured response.
    # --------------------------------------------------------

    ideal_completions = (
        ideal_releases
        + response_times
    )

    completion_jitter = (
        completions
        - ideal_completions
    )

    # ========================================================
    # STATISTICS
    # ========================================================

    release_jitter_std = (
        np.std(
            release_jitter,
            ddof=1
        )
    )

    release_jitter_max = (
        np.max(
            np.abs(
                release_jitter
            )
        )
    )

    completion_jitter_std = (
        np.std(
            completion_jitter,
            ddof=1
        )
    )

    completion_jitter_max = (
        np.max(
            np.abs(
                completion_jitter
            )
        )
    )

    # --------------------------------------------------------
    # Deadline hit fraction
    # --------------------------------------------------------

    deadline_met = (
        response_times <= D
    )

    deadline_hit_fraction = (
        np.mean(
            deadline_met
        )
    )

    return {

        "release_jitter_std_ms":
            release_jitter_std * 1000,

        "release_jitter_max_abs_ms":
            release_jitter_max * 1000,

        "completion_jitter_std_ms":
            completion_jitter_std * 1000,

        "completion_jitter_max_abs_ms":
            completion_jitter_max * 1000,

        "deadline_hit_fraction":
            deadline_hit_fraction
    }


# ============================================================
# PLOT JITTER SWEEP
# ============================================================

def plot_jitter_sweep(
    title,
    x_values,
    y_values,
    x_label,
    filename
):

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        x_values,
        y_values,
        marker="o"
    )

    plt.xlabel(
        x_label
    )

    plt.ylabel(
        "Release jitter standard deviation (ms)"
    )

    plt.title(
        title
    )

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_FOLDER /
        filename,
        dpi=160
    )

    plt.show()


# ============================================================
# PLOT DEADLINE HIT RATE
# ============================================================

def plot_hit_rate(
    title,
    x_values,
    hit_rates,
    x_label,
    filename
):

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        x_values,
        np.array(hit_rates) * 100,
        marker="o"
    )

    plt.xlabel(
        x_label
    )

    plt.ylabel(
        "Deadline hit fraction (%)"
    )

    plt.title(
        title
    )

    plt.ylim(
        0,
        105
    )

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        RESULTS_FOLDER /
        filename,
        dpi=160
    )

    plt.show()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("REAL-TIME SYSTEMS - MINI PROJECT 1.3")
    print("=" * 60)

    results = {}

    # ========================================================
    # EXPERIMENT 1
    # BACKGROUND CPU LOAD
    # ========================================================

    print("\nBackground CPU Load Experiment")

    load_levels = [
        0.0,
        0.25,
        0.50,
        0.75
    ]

    load_results = []

    for index, level in enumerate(
        load_levels
    ):

        print(
            f"Testing load = {level}"
        )

        result = run_experiment(
            load_intensity=level,
            seed=100 + index
        )

        result["parameter"] = level

        load_results.append(
            result
        )

    results[
        "background_cpu_load"
    ] = load_results

    # ========================================================
    # EXPERIMENT 2
    # RANDOM EXTRA DELAY
    # ========================================================

    print("\nRandom Extra Delay Experiment")

    delay_probabilities = [
        0.0,
        0.05,
        0.15,
        0.30
    ]

    delay_results = []

    for index, probability in enumerate(
        delay_probabilities
    ):

        print(
            f"Testing probability = "
            f"{probability}"
        )

        result = run_experiment(

            delay_probability=probability,

            # 3 ms additional delay
            delay_ms=3.0,

            seed=200 + index
        )

        result["parameter"] = (
            probability
        )

        delay_results.append(
            result
        )

    results[
        "random_extra_delay"
    ] = delay_results

    # ========================================================
    # EXPERIMENT 3
    # EXECUTION-TIME VARIABILITY
    # ========================================================

    print(
        "\nExecution-Time Variability Experiment"
    )

    spread_levels = [
        0.0,
        0.10,
        0.25,
        0.40
    ]

    spread_results = []

    for index, spread in enumerate(
        spread_levels
    ):

        print(
            f"Testing spread = "
            f"{spread}"
        )

        result = run_experiment(

            execution_spread=spread,

            seed=300 + index
        )

        result["parameter"] = (
            spread
        )

        spread_results.append(
            result
        )

    results[
        "execution_time_variability"
    ] = spread_results

    # ========================================================
    # CREATE PLOTS
    # ========================================================

    # --------------------------------------------------------
    # Background load plot
    # --------------------------------------------------------

    load_x = [
        item["parameter"]
        for item in load_results
    ]

    load_y = [
        item[
            "release_jitter_std_ms"
        ]
        for item in load_results
    ]

    load_hits = [
        item[
            "deadline_hit_fraction"
        ]
        for item in load_results
    ]

    plot_jitter_sweep(

        "Release Jitter vs Background CPU Load",

        load_x,
        load_y,

        "Background CPU-load intensity",

        "background_load_jitter.png"
    )

    plot_hit_rate(

        "Deadline Hit Rate vs Background CPU Load",

        load_x,
        load_hits,

        "Background CPU-load intensity",

        "background_load_hit_rate.png"
    )

    # --------------------------------------------------------
    # Random delay plot
    # --------------------------------------------------------

    delay_x = [
        item["parameter"]
        for item in delay_results
    ]

    delay_y = [
        item[
            "release_jitter_std_ms"
        ]
        for item in delay_results
    ]

    delay_hits = [
        item[
            "deadline_hit_fraction"
        ]
        for item in delay_results
    ]

    plot_jitter_sweep(

        "Release Jitter vs Random Extra Delay",

        delay_x,
        delay_y,

        "Probability of extra delay",

        "random_delay_jitter.png"
    )

    plot_hit_rate(

        "Deadline Hit Rate vs Random Extra Delay",

        delay_x,
        delay_hits,

        "Probability of extra delay",

        "random_delay_hit_rate.png"
    )

    # --------------------------------------------------------
    # Execution variability plot
    # --------------------------------------------------------

    spread_x = [
        item["parameter"]
        for item in spread_results
    ]

    spread_y = [
        item[
            "release_jitter_std_ms"
        ]
        for item in spread_results
    ]

    spread_hits = [
        item[
            "deadline_hit_fraction"
        ]
        for item in spread_results
    ]

    plot_jitter_sweep(

        "Release Jitter vs Execution-Time Variability",

        spread_x,
        spread_y,

        "Execution-time spread",

        "execution_variability_jitter.png"
    )

    plot_hit_rate(

        "Deadline Hit Rate vs Execution-Time Variability",

        spread_x,
        spread_hits,

        "Execution-time spread",

        "execution_variability_hit_rate.png"
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    with open(
        RESULTS_FOLDER /
        "results_1_3.json",
        "w"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for experiment, data in results.items():

        print(
            f"\n{experiment}"
        )

        for result in data:

            print(
                f"Parameter: "
                f"{result['parameter']}"
            )

            print(
                f"Release jitter SD: "
                f"{result['release_jitter_std_ms']:.4f} ms"
            )

            print(
                f"Maximum release jitter: "
                f"{result['release_jitter_max_abs_ms']:.4f} ms"
            )

            print(
                f"Completion jitter SD: "
                f"{result['completion_jitter_std_ms']:.4f} ms"
            )

            print(
                f"Deadline hit rate: "
                f"{result['deadline_hit_fraction'] * 100:.2f}%"
            )

    print("\nResults saved in:")
    print(RESULTS_FOLDER)


if __name__ == "__main__":
    main()