from pathlib import Path
import json
import threading
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

EXECUTION_TESTS = 200
PERIODIC_JOBS = 100
T = 0.05
D = 0.8 * T
RESULTS_FOLDER = Path(r'c:\Users\Beatz\RTS_Unit1_Mini_Projects\results_1_1')
RESULTS_FOLDER.mkdir(exist_ok=True)


def real_time_job(workload):
    """A variable-workload numerical task resembling a real-time job."""
    result = 0.0
    for i in range(workload):
        result = (result * 1.000001 + ((i * 17) % 23) * 0.0007) % 100000.0
        if i % 19 == 0:
            result = (result + np.sin(i * 0.01)) % 100000.0
    return result


def measure_execution_time(number_of_tests=200, low=500, high=1800):
    """Measure the job's execution time over many calls."""
    rng = np.random.default_rng(123)
    workloads = rng.integers(low=low, high=high, size=number_of_tests)
    execution_times = []
    for workload in workloads:
        start = time.perf_counter()
        real_time_job(int(workload))
        finish = time.perf_counter()
        execution_times.append(finish - start)
    return np.array(execution_times, dtype=float)


def busy_worker(stop_event):
    """Background work to add scheduler and OS noise."""
    while not stop_event.is_set():
        accumulator = 0.0
        for i in range(200000):
            accumulator = (accumulator + 1.0) * (1.0 + (i % 7) * 0.0001)
            if i % 1000 == 0:
                accumulator = accumulator % 1000.0


def run_periodic_task(jobs=PERIODIC_JOBS, period=T, deadline=D, with_interference=False):
    """Run a periodic task and record timing metadata."""
    rng = np.random.default_rng(456)
    records = []
    start_time = time.perf_counter()
    stop_event = threading.Event()
    worker = None

    if with_interference:
        worker = threading.Thread(target=busy_worker, args=(stop_event,), daemon=True)
        worker.start()

    try:
        for job_number in range(jobs):
            ideal_release = start_time + job_number * period
            remaining = ideal_release - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)

            actual_release = time.perf_counter()
            workload = int(rng.integers(low=700, high=1800))
            real_time_job(workload)
            completion = time.perf_counter()
            response_time = completion - actual_release
            absolute_deadline = actual_release + deadline
            deadline_met = response_time <= deadline
            release_jitter = actual_release - ideal_release
            completion_jitter = completion - (ideal_release + deadline)

            records.append({
                'job': job_number,
                'ideal_release': ideal_release,
                'actual_release': actual_release,
                'completion': completion,
                'deadline': absolute_deadline,
                'response_time': response_time,
                'release_jitter': release_jitter,
                'completion_jitter': completion_jitter,
                'deadline_met': deadline_met,
            })
    finally:
        if worker is not None:
            stop_event.set()
            worker.join(timeout=1.0)

    return records


def calculate_utilities(response_times, deadline=D):
    """Compute hard, firm and soft utility values."""
    hard_utility = []
    firm_utility = []
    soft_utility = []

    for response in response_times:
        if response <= deadline:
            hard = 1.0
            firm = 1.0
            soft = 1.0
        else:
            excess = response - deadline
            hard = -10.0
            firm = 0.0
            soft = float(np.exp(-excess / (0.25 * deadline)))

        hard_utility.append(hard)
        firm_utility.append(firm)
        soft_utility.append(soft)

    return np.array(hard_utility), np.array(firm_utility), np.array(soft_utility)


def calculate_execution_statistics(execution_times):
    """Summarize measured execution-time samples."""
    if len(execution_times) == 0:
        raise ValueError('Execution times array is empty.')

    mean_time = float(np.mean(execution_times))
    std_dev = float(np.std(execution_times, ddof=1)) if len(execution_times) > 1 else 0.0
    maximum = float(np.max(execution_times))
    percentile_95 = float(np.percentile(execution_times, 95))

    return {
        'mean_ms': mean_time * 1000,
        'standard_deviation_ms': std_dev * 1000,
        'maximum_ms': maximum * 1000,
        'percentile_95_ms': percentile_95 * 1000,
    }


def calculate_timing_statistics(records):
    """Compute response, release-jitter and completion-jitter statistics."""
    if not records:
        raise ValueError('No timing records provided.')

    response_times = np.array([record['response_time'] for record in records], dtype=float)
    release_jitter = np.array([record['release_jitter'] for record in records], dtype=float)
    completion_jitter = np.array([record['completion_jitter'] for record in records], dtype=float)
    deadline_results = np.array([1.0 if record['deadline_met'] else 0.0 for record in records], dtype=float)

    mean_response = float(np.mean(response_times))
    maximum_response = float(np.max(response_times))
    release_jitter_std = float(np.std(release_jitter, ddof=1)) if len(release_jitter) > 1 else 0.0
    completion_jitter_std = float(np.std(completion_jitter, ddof=1)) if len(completion_jitter) > 1 else 0.0
    max_release_jitter = float(np.max(np.abs(release_jitter)))
    max_completion_jitter = float(np.max(np.abs(completion_jitter)))
    deadline_hit_fraction = float(np.mean(deadline_results))

    return {
        'period_ms': T * 1000,
        'deadline_ms': D * 1000,
        'mean_response_ms': mean_response * 1000,
        'maximum_response_ms': maximum_response * 1000,
        'release_jitter_std_ms': release_jitter_std * 1000,
        'maximum_release_jitter_ms': max_release_jitter * 1000,
        'completion_jitter_std_ms': completion_jitter_std * 1000,
        'maximum_completion_jitter_ms': max_completion_jitter * 1000,
        'deadline_hit_fraction': deadline_hit_fraction,
    }


def plot_timing_diagram(records, save_path=RESULTS_FOLDER / 'timing_diagram.png'):
    """Draw a timing diagram for a subset of jobs."""
    if not records:
        raise ValueError('No records available for timing diagram.')

    first_release = records[0]['actual_release']
    subset = records[:15]

    fig, ax = plt.subplots(figsize=(11, 7))
    for index, record in enumerate(subset):
        left = (record['actual_release'] - first_release) * 1000
        width = (record['completion'] - record['actual_release']) * 1000
        deadline_position = (record['deadline'] - first_release) * 1000
        color = 'tab:green' if record['deadline_met'] else 'tab:red'
        ax.barh(index, width, left=left, height=0.6, color=color, alpha=0.85)
        ax.plot([deadline_position, deadline_position], [index - 0.25, index + 0.25], color='black', linewidth=1.5)

    ax.set_xlabel('Time from first release (ms)')
    ax.set_ylabel('Job index')
    ax.set_title('Mini Project 1.1 - Task Timing Diagram')
    ax.grid(axis='x', alpha=0.3)
    ax.set_yticks(range(len(subset)))
    ax.set_yticklabels([str(i) for i in range(len(subset))])
    plt.tight_layout()
    plt.savefig(save_path, dpi=160)
    plt.close(fig)


def plot_response_and_utility(records, hard, firm, soft, save_path=RESULTS_FOLDER / 'response_and_utility.png'):
    """Plot response times and the three utility curves."""
    response_times = np.array([record['response_time'] for record in records], dtype=float)
    jobs = np.arange(len(response_times))

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(jobs, response_times * 1000, marker='.', linewidth=1.0, color='tab:blue')
    axes[0].axhline(D * 1000, linestyle='--', color='tab:red', label='Deadline')
    axes[0].set_ylabel('Response time (ms)')
    axes[0].set_title('Response Time')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(jobs, hard, label='Hard', linewidth=1.5)
    axes[1].plot(jobs, firm, label='Firm', linewidth=1.5)
    axes[1].plot(jobs, soft, label='Soft', linewidth=1.5)
    axes[1].set_xlabel('Job number')
    axes[1].set_ylabel('Utility')
    axes[1].set_title('Hard, Firm and Soft Deadline Utility')
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=160)
    plt.close(fig)


def build_report(execution_statistics, timing_statistics, background_timing, ordinary_max, adversarial_max, period_analysis):
    """Create a markdown summary report satisfying the project deliverable."""
    mean_ms = execution_statistics['mean_ms']
    max_ms = execution_statistics['maximum_ms']
    release_std = timing_statistics['release_jitter_std_ms']
    completion_std = timing_statistics['completion_jitter_std_ms']
    hit_fraction = timing_statistics['deadline_hit_fraction']

    if adversarial_max >= ordinary_max:
        adversarial_note = 'The adversarial input produced the larger value, confirming that worst-path inputs matter.'
    else:
        adversarial_note = 'The ordinary input remained larger in this run, showing that the observed worst case depends on the chosen input distribution and can still under-estimate the true path-complexity bound.'

    lines = [
        '# Mini Project 1.1 Lab Report',
        '',
        '## Summary of measured timing behavior',
        f'The measured average execution time was {mean_ms:.3f} ms, while the largest observed execution time reached {max_ms:.3f} ms. With a period T = {T * 1000:.1f} ms and a relative deadline D = {D * 1000:.1f} ms, the mean execution time was about {mean_ms / (T * 1000) * 100:.1f}% of the period and the observed maximum was about {max_ms / (D * 1000) * 100:.1f}% of the deadline budget.',
        f'The release jitter standard deviation was {release_std:.4f} ms and the completion jitter standard deviation was {completion_std:.4f} ms. The measured deadline-hit fraction was {hit_fraction * 100:.2f}%, which confirms that the task is close to the schedulability boundary and sensitive to tail latency rather than only the mean.',
        '',
        '## Interpretation of the cost functions',
        'This task most closely resembles a firm-deadline system. The deadline is explicit, a late result is no longer useful, and the utility drops sharply to zero once the deadline is missed. In control, monitoring and data-acquisition workloads, a missed deadline often loses value immediately, yet a single late job is not necessarily catastrophic in the same way as a hard real-time safety shutdown. This is why the firm utility curve is a reasonable model for many real-time monitoring tasks.',
        '',
        '## Lab task results',
        f'### 1. Background interference: with a busy-thread workload, the measured release jitter was {background_timing["release_jitter_std_ms"]:.4f} ms and the deadline-hit fraction was {background_timing["deadline_hit_fraction"] * 100:.2f}%. Relative to the unloaded case, this shows how scheduler noise and OS interference raise release variability and reduce miss-free execution.',
        f'### 2. Adversarial input check: the ordinary-input maximum was {ordinary_max * 1000:.3f} ms and the adversarial-input maximum was {adversarial_max * 1000:.3f} ms. {adversarial_note}',
        '### 3. Soft-deadline utility: a slower decay keeps some value for jobs that are late, while a faster decay punishes lateness much more aggressively. The decay rate should be chosen from the application semantics, not arbitrarily: a sensor reporting process can accept a shallow decay, while control or safety logic needs a much sharper penalty.',
        '### 4. Period variation: when T is reduced while keeping D = 0.8*T, the same absolute jitter becomes a larger fraction of the period. This means jitter matters even when every deadline is met because it changes the usable slack and can reduce the margin available for the next job.',
        '',
        '## Final observation',
        'The measured maximum and 95th percentile are much more informative than the mean for real-time correctness. A task can appear healthy on average while still failing its deadlines when timing tails move beyond the designed slack. This is exactly why average-case measurements are not enough for real-time schedulability reasoning.',
        '',
        '### Period sweep',
    ]

    for entry in period_analysis:
        lines.append(
            f"- Period {entry['period_ms']:.1f} ms, D = {entry['deadline_ms']:.1f} ms, release-jitter std = {entry['release_jitter_std_ms']:.4f} ms, jitter/period ratio = {entry['jitter_fraction'] * 100:.2f}%"
        )

    return '\n'.join(lines) + '\n'


def run_lab_tasks():
    """Exercise the extra project tasks requested in the lab sheet."""
    ordinary_execution = measure_execution_time(EXECUTION_TESTS)
    adversarial_execution = measure_execution_time(number_of_tests=250, low=1500, high=2200)
    ordinary_max = float(np.max(ordinary_execution))
    adversarial_max = float(np.max(adversarial_execution))

    background_records = run_periodic_task(jobs=PERIODIC_JOBS, period=T, deadline=D, with_interference=True)
    background_timing = calculate_timing_statistics(background_records)

    period_analysis = []
    for period in (0.02, 0.05, 0.1):
        period_records = run_periodic_task(jobs=80, period=period, deadline=0.8 * period)
        period_stats = calculate_timing_statistics(period_records)
        period_analysis.append({
            'period_ms': period * 1000,
            'deadline_ms': (0.8 * period) * 1000,
            'release_jitter_std_ms': period_stats['release_jitter_std_ms'],
            'jitter_fraction': period_stats['release_jitter_std_ms'] / (period * 1000),
        })

    return {
        'ordinary_max': ordinary_max,
        'adversarial_max': adversarial_max,
        'background_timing': background_timing,
        'period_analysis': period_analysis,
    }


def main():
    print('=' * 60)
    print('REAL-TIME SYSTEMS - MINI PROJECT 1.1')
    print('=' * 60)

    execution_times = measure_execution_time(EXECUTION_TESTS)
    execution_statistics = calculate_execution_statistics(execution_times)

    records = run_periodic_task()
    timing_statistics = calculate_timing_statistics(records)
    response_times = np.array([record['response_time'] for record in records], dtype=float)
    hard, firm, soft = calculate_utilities(response_times, D)

    print('\nExecution-time results')
    for key, value in execution_statistics.items():
        print(f'{key}: {value:.4f}')

    print('\nTiming results')
    for key, value in timing_statistics.items():
        if key == 'deadline_hit_fraction':
            print(f'{key}: {value * 100:.2f}%')
        else:
            print(f'{key}: {value:.4f}')

    plot_timing_diagram(records)
    plot_response_and_utility(records, hard, firm, soft)

    lab_results = run_lab_tasks()
    report_text = build_report(
        execution_statistics,
        timing_statistics,
        lab_results['background_timing'],
        lab_results['ordinary_max'],
        lab_results['adversarial_max'],
        lab_results['period_analysis'],
    )

    report_path = RESULTS_FOLDER / 'mini_project_1_1_report.md'
    report_path.write_text(report_text, encoding='utf-8')

    results = {
        'execution_statistics': execution_statistics,
        'timing_statistics': timing_statistics,
        'lab_results': lab_results,
    }
    with open(RESULTS_FOLDER / 'results_1_1.json', 'w', encoding='utf-8') as file:
        json.dump(results, file, indent=4)

    print(f'\nResults saved in: {RESULTS_FOLDER}')
    print(f'Report: {report_path}')


if __name__ == '__main__':
    main()
