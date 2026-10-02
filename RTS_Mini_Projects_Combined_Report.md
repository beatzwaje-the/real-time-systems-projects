# Real-Time Systems (RTS) Unit 1 Mini Projects: 

## 1. Overview

This report consolidates the results of the three mini-projects completed in the RTS Unit 1 lab. The work covered:

- Project 1.1: timing behavior, deadline compliance, and jitter analysis
- Project 1.2: measurement-based WCET estimation and adversarial workload study
- Project 1.3: analysis of jitter under background CPU load, random delays, and execution-time variability

The outputs were generated as runnable Python simulations and saved as result files and plots in their respective folders:

- [results_1_1](./results_1_1)
- [results_1_2](./results_1_2)
- [results_1_3](./results_1_3)

---

## 2. Project 1.1: Timing Behavior and Deadline Compliance

### Objective
This project simulated a periodic real-time task and analyzed its release timing, completion timing, jitter, deadline hit rate, and utility behavior.

### Key results
From the generated output file [results_1_1/results_1_1.json](./results_1_1/results_1_1.json):

- Mean execution time: 3.834 ms
- Standard deviation: 4.143 ms
- Maximum observed execution time: 27.229 ms
- 95th percentile execution time: 11.848 ms
- Mean response time: 11.116 ms
- Maximum response time: 186.504 ms
- Release jitter standard deviation: 41.830 ms
- Completion jitter standard deviation: 51.884 ms
- Deadline hit fraction: 0.95 (95%)

### Interpretation
The task averages appear acceptable, but the timing tail is significant. The maximum response time is far larger than the mean, which shows that the system does not behave predictably in the worst case. This is the central issue in real-time design: average performance can hide deadline risk.

The measured completion jitter and missed deadlines indicate that the system is vulnerable to timing variability. Even with 95% deadline compliance, a small fraction of jobs are late enough to matter in realistic real-time schedules.

### Additional observations
The report also examined how the task behaves under background interference and different periods. The results show that timing disturbances increase jitter and reduce reliability, especially when the period becomes shorter or when unrelated system load increases.

---

## 3. Project 1.2: Measurement-Based WCET Estimation

### Objective
This project estimated worst-case execution time by measuring task execution under random and adversarial workloads. The purpose was to understand how measurement-based WCET estimation differs from a formally valid bound.

### Key results
From [results_1_2/results_1_2.json](./results_1_2/results_1_2.json):

#### Early-exit function
- Observed maximum under random input: 100.630 ms
- Safety-margin estimate: 130.819 ms
- Adversarial input did not exceed the random maximum in this run

#### Data-dependent loop
- Observed maximum under random input: 10.620 ms
- Safety-margin estimate: 13.807 ms
- Adversarial input did not exceed the random maximum in this run

#### Nested conditionals
- Observed maximum under random input: 11.219 ms
- Safety-margin estimate: 14.585 ms
- Adversarial input did not exceed the random maximum in this run

### Interpretation
The results confirm an important real-time systems principle: measured execution time can be used as an engineering estimate, but it is not the same as a provable WCET bound. Even if the random and adversarial searches do not produce a larger value in this run, real workloads can still trigger worse-case behavior.

This means that the recommended WCET values are useful planning estimates, but they should not be treated as fully sound guarantees for hard real-time systems without deeper static or formal analysis.

---

## 4. Project 1.3: Jitter Under Simulated Noise and Load

### Objective
This project studied how jitter and deadline misses change under different operating conditions: background CPU load, random extra delays, and execution-time variability.

### Key results
From [results_1_3/results_1_3.json](./results_1_3/results_1_3.json):

#### A. Background CPU load
| Load intensity | Release jitter std (ms) | Deadline hit fraction |
|---|---:|---:|
| 0.0 | 21.820 | 1.000 |
| 0.25 | 164.486 | 0.995 |
| 0.50 | 48.370 | 0.995 |
| 0.75 | 48.318 | 1.000 |

Observation: background load can sharply increase timing variability, though the effect is not monotonic across all loads. The highest observed jitter in this dataset occurs at a moderate load level, showing that interference is not always easy to predict.

#### B. Random extra delay
| Delay probability | Release jitter std (ms) | Deadline hit fraction |
|---|---:|---:|
| 0.0 | 21.191 | 0.995 |
| 0.05 | 11.297 | 0.985 |
| 0.15 | 23.249 | 0.980 |
| 0.30 | 192.288 | 0.855 |

Observation: rare random delays accumulate over time and can substantially reduce deadline compliance. The 0.30 case shows that even a moderate delay probability can strongly damage timing reliability.

#### C. Execution-time variability
| Execution spread | Release jitter std (ms) | Deadline hit fraction |
|---|---:|---:|
| 0.0 | 13.798 | 1.000 |
| 0.10 | 10.019 | 1.000 |
| 0.25 | 4.857 | 0.995 |
| 0.40 | 2.104 | 1.000 |

Observation: variability in execution time alone does not always dominate the schedule, but it still contributes to unpredictability and must be included in design margin calculations.

### Interpretation
Project 1.3 shows that timing reliability is highly sensitive to several forms of system noise. Even when average timing is acceptable, jitter can distort the effective schedule and reduce the usable slack margin. This is why real-time systems rely on careful margin design, scheduling analysis, and sometimes admission control or deadlines that are conservative relative to measured values.

---

## 5. Combined Analysis and Conclusions

Across all three projects, the following conclusions are consistent:

1. Average timing is not enough for real-time correctness.
   - The mean execution time and response time are not the decisive metrics.
   - The upper tail of the distribution, jitter, and deadline misses matter more.

2. Jitter is a critical design parameter.
   - Small changes in interference or execution variability can quickly reduce the slack available for meeting deadlines.

3. WCET estimation should be treated as an estimate, not a strict guarantee.
   - Measurement-based estimates help with design, but for hard real-time systems they must be combined with formal analysis or conservative scheduling assumptions.

4. Deadline hit rate is an essential validation metric.
   - A task may look healthy on average while still causing unacceptable late completions in a subset of jobs.

5. Real-time performance depends on both the software and the execution environment.
   - Background load, OS delays, and workload variability all reduce predictability even when the task logic itself is correct.

---

## 6. Final Assessment

The RTS mini-project work was completed successfully. The simulation scripts were corrected and validated, and the output artifacts were generated for each project.

The system behavior demonstrated in the simulations matches the course themes of:

- deadline analysis,
- response-time variability,
- release/completion jitter,
- utility of late jobs,
- WCET estimation,
- and environmental interference effects.

The overall result is a strong understanding of how timing uncertainty affects real-time performance in practice.
