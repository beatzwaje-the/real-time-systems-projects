

"""
REAL-TIME SYSTEMS
Mini Project 1.2:
Measurement-Based WCET Estimation and Confidence Tool

Requirements:
- Python 3
- NumPy
- Matplotlib
"""

import time
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# SETTINGS
# ============================================================

NUMBER_OF_RUNS = 400

# Configurable safety margin
SAFETY_MARGIN = 0.30

RESULTS_FOLDER = Path("results_1_2")
RESULTS_FOLDER.mkdir(exist_ok=True)


# ============================================================
# TARGET FUNCTION 1
# Early-exit branch
# ============================================================

def target_early_exit(x):

    result = 0

    if x < 0.15:

        # Short path
        for i in range(300):
            result += i * i

    else:

        # Long path
        for i in range(1200):
            result += i * i

    return result


# ============================================================
# TARGET FUNCTION 2
# Data-dependent loop
# ============================================================

def target_data_dependent(n):

    result = 0

    for i in range(int(n)):

        result = (
            result + i * i
        ) % 10000019

    return result


# ============================================================
# TARGET FUNCTION 3
# Nested conditionals
# ============================================================

def target_nested_conditionals(x):

    result = 0

    x = int(x)

    workload = 300 + (
        x % 900
    )

    for i in range(workload):

        if x % 2 == 0:

            result += i * i

        else:

            result += i + 3

        if x % 7 == 0:

            result ^= (
                i & 31
            )

    return result


# ============================================================
# MEASUREMENT FUNCTION
# ============================================================

def measure_function(
    function,
    inputs
):

    durations = []

    for value in inputs:

        start = time.perf_counter()

        function(value)

        finish = time.perf_counter()

        duration = (
            finish - start
        )

        durations.append(
            duration
        )

    return np.array(
        durations
    )


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics(
    execution_times
):

    return {

        "mean_ms":
            np.mean(
                execution_times
            ) * 1000,

        "standard_deviation_ms":
            np.std(
                execution_times,
                ddof=1
            ) * 1000,

        "minimum_ms":
            np.min(
                execution_times
            ) * 1000,

        "maximum_ms":
            np.max(
                execution_times
            ) * 1000,

        "p90_ms":
            np.percentile(
                execution_times,
                90
            ) * 1000,

        "p95_ms":
            np.percentile(
                execution_times,
                95
            ) * 1000,

        "p99_ms":
            np.percentile(
                execution_times,
                99
            ) * 1000
    }


# ============================================================
# SAFETY MARGIN
# ============================================================

def calculate_margined_estimate(
    random_times,
    adversarial_times
):

    observed_max = max(
        np.max(random_times),
        np.max(adversarial_times)
    )

    recommended = (
        observed_max
        * (1 + SAFETY_MARGIN)
    )

    return (
        observed_max,
        recommended
    )


# ============================================================
# HISTOGRAM
# ============================================================

def create_histogram(
    name,
    random_times,
    adversarial_times,
    observed_max,
    recommended
):

    plt.figure(
        figsize=(10, 6)
    )

    plt.hist(
        random_times * 1000,
        bins=25,
        alpha=0.6,
        label="Random / representative"
    )

    plt.hist(
        adversarial_times * 1000,
        bins=25,
        alpha=0.6,
        label="Adversarial"
    )

    plt.axvline(
        observed_max * 1000,
        linestyle="--",
        linewidth=2,
        label=(
            f"Observed maximum = "
            f"{observed_max * 1000:.3f} ms"
        )
    )

    plt.axvline(
        recommended * 1000,
        linestyle=":",
        linewidth=2,
        label=(
            f"30% margined estimate = "
            f"{recommended * 1000:.3f} ms"
        )
    )

    plt.xlabel(
        "Execution time (ms)"
    )

    plt.ylabel(
        "Number of measurements"
    )

    plt.title(
        f"WCET Measurement - {name}"
    )

    plt.legend()

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()

    filename = (
        RESULTS_FOLDER /
        f"{name}_histogram.png"
    )

    plt.savefig(
        filename,
        dpi=160
    )

    plt.show()


# ============================================================
# EXPERIMENT
# ============================================================

def run_experiment(
    name,
    function,
    random_input_generator,
    adversarial_input_generator,
    seed
):

    print("\n" + "=" * 60)
    print(name.upper())
    print("=" * 60)

    rng = np.random.default_rng(
        seed
    )

    # --------------------------------------------------------
    # Random / representative inputs
    # --------------------------------------------------------

    random_inputs = (
        random_input_generator(
            rng,
            NUMBER_OF_RUNS
        )
    )

    # --------------------------------------------------------
    # Adversarial inputs
    # --------------------------------------------------------

    adversarial_inputs = (
        adversarial_input_generator(
            NUMBER_OF_RUNS
        )
    )

    # --------------------------------------------------------
    # Measurements
    # --------------------------------------------------------

    random_times = measure_function(
        function,
        random_inputs
    )

    adversarial_times = measure_function(
        function,
        adversarial_inputs
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    random_statistics = (
        calculate_statistics(
            random_times
        )
    )

    adversarial_statistics = (
        calculate_statistics(
            adversarial_times
        )
    )

    # --------------------------------------------------------
    # WCET estimate
    # --------------------------------------------------------

    observed_max, recommended = (
        calculate_margined_estimate(
            random_times,
            adversarial_times
        )
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print("\nRandom / Representative:")

    for key, value in random_statistics.items():

        print(
            f"{key}: {value:.4f}"
        )

    print("\nAdversarial:")

    for key, value in adversarial_statistics.items():

        print(
            f"{key}: {value:.4f}"
        )

    print(
        f"\nObserved maximum: "
        f"{observed_max * 1000:.4f} ms"
    )

    print(
        f"Safety margin: "
        f"{SAFETY_MARGIN * 100:.0f}%"
    )

    print(
        f"Recommended scheduling value: "
        f"{recommended * 1000:.4f} ms"
    )

    # --------------------------------------------------------
    # Plot
    # --------------------------------------------------------

    create_histogram(
        name,
        random_times,
        adversarial_times,
        observed_max,
        recommended
    )

    return {

        "random": random_statistics,

        "adversarial":
            adversarial_statistics,

        "observed_max_ms":
            observed_max * 1000,

        "safety_margin_percent":
            SAFETY_MARGIN * 100,

        "recommended_WCET_ms":
            recommended * 1000,

        "adversarial_exceeded_random":
            bool(
                np.max(adversarial_times)
                >
                np.max(random_times)
            )
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("REAL-TIME SYSTEMS - MINI PROJECT 1.2")
    print("=" * 60)

    results = {}

    # --------------------------------------------------------
    # Function 1
    # --------------------------------------------------------

    results["early_exit"] = run_experiment(

        "early_exit",

        target_early_exit,

        lambda rng, n:
            rng.random(n),

        lambda n:
            np.ones(n) * 0.99,

        100
    )

    # --------------------------------------------------------
    # Function 2
    # --------------------------------------------------------

    results["data_dependent_loop"] = run_experiment(

        "data_dependent_loop",

        target_data_dependent,

        lambda rng, n:
            rng.integers(
                300,
                1100,
                size=n
            ),

        lambda n:
            np.ones(n) * 1100,

        200
    )

    # --------------------------------------------------------
    # Function 3
    # --------------------------------------------------------

    results["nested_conditionals"] = run_experiment(

        "nested_conditionals",

        target_nested_conditionals,

        lambda rng, n:
            rng.integers(
                0,
                1200,
                size=n
            ),

        lambda n:
            np.ones(n) * 1197,

        300
    )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    with open(
        RESULTS_FOLDER /
        "results_1_2.json",
        "w"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    print("\nResults saved in:")
    print(RESULTS_FOLDER)


if __name__ == "__main__":
    main()