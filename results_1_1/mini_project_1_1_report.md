# Mini Project 1.1 Lab Report

## Summary of measured timing behavior
The measured average execution time was 3.834 ms, while the largest observed execution time reached 27.229 ms. With a period T = 50.0 ms and a relative deadline D = 40.0 ms, the mean execution time was about 7.7% of the period and the observed maximum was about 68.1% of the deadline budget.
The release jitter standard deviation was 41.8304 ms and the completion jitter standard deviation was 51.8844 ms. The measured deadline-hit fraction was 95.00%, which confirms that the task is close to the schedulability boundary and sensitive to tail latency rather than only the mean.

## Interpretation of the cost functions
This task most closely resembles a firm-deadline system. The deadline is explicit, a late result is no longer useful, and the utility drops sharply to zero once the deadline is missed. In control, monitoring and data-acquisition workloads, a missed deadline often loses value immediately, yet a single late job is not necessarily catastrophic in the same way as a hard real-time safety shutdown. This is why the firm utility curve is a reasonable model for many real-time monitoring tasks.

## Lab task results
### 1. Background interference: with a busy-thread workload, the measured release jitter was 15.6814 ms and the deadline-hit fraction was 100.00%. Relative to the unloaded case, this shows how scheduler noise and OS interference raise release variability and reduce miss-free execution.
### 2. Adversarial input check: the ordinary-input maximum was 6.483 ms and the adversarial-input maximum was 8.164 ms. The adversarial input produced the larger value, confirming that worst-path inputs matter.
### 3. Soft-deadline utility: a slower decay keeps some value for jobs that are late, while a faster decay punishes lateness much more aggressively. The decay rate should be chosen from the application semantics, not arbitrarily: a sensor reporting process can accept a shallow decay, while control or safety logic needs a much sharper penalty.
### 4. Period variation: when T is reduced while keeping D = 0.8*T, the same absolute jitter becomes a larger fraction of the period. This means jitter matters even when every deadline is met because it changes the usable slack and can reduce the margin available for the next job.

## Final observation
The measured maximum and 95th percentile are much more informative than the mean for real-time correctness. A task can appear healthy on average while still failing its deadlines when timing tails move beyond the designed slack. This is exactly why average-case measurements are not enough for real-time schedulability reasoning.

### Period sweep
- Period 20.0 ms, D = 16.0 ms, release-jitter std = 1.9013 ms, jitter/period ratio = 9.51%
- Period 50.0 ms, D = 40.0 ms, release-jitter std = 10.0488 ms, jitter/period ratio = 20.10%
- Period 100.0 ms, D = 80.0 ms, release-jitter std = 3.5432 ms, jitter/period ratio = 3.54%
