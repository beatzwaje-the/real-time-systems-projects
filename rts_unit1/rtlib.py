"""Shared helpers for the Unit 1 Real-Time Systems mini projects.

Everything here is pure standard library + numpy. It provides:
  * busy_work()        - a CPU-bound numerical routine whose cost scales with n
  * run_periodic()     - a drift-free periodic release loop with full instrumentation
  * BackgroundLoad     - a duty-cycle CPU-hog thread (interference, Section 1.6)
  * jitter helpers     - release / completion jitter and summary statistics
"""
import math
import threading
import time

import numpy as np


def busy_work(n):
    """CPU-bound numerical loop; running time grows linearly with n."""
    x = 0.0
    for i in range(n):
        x += math.sqrt(i + 1.0) * math.sin(i)
    return x


def run_periodic(n_jobs, T, job_fn, pre_job_hook=None, start_delay=0.05):
    """Run n_jobs of job_fn(k) with period T and return instrumented timestamps.

    Drift-free: the target instant of job k is ALWAYS recomputed from the fixed
    origin r0 as r0 + k*T, never as "previous wake-up + T", so a late wake-up
    does not push later releases back.

    pre_job_hook(k), if given, runs after the wake-up but BEFORE the release
    timestamp is taken. Disturbances that delay dispatch (interrupt/DMA-like
    stalls) are injected here so they show up as release jitter.

    Returns a dict of numpy arrays, all in seconds relative to r0:
      ideal    - ideal release instants  k*T
      release  - actual release instants (job body starts)
      complete - completion instants
    """
    ideal = np.empty(n_jobs)
    release = np.empty(n_jobs)
    complete = np.empty(n_jobs)
    r0 = time.perf_counter() + start_delay
    for k in range(n_jobs):
        target = r0 + k * T
        ideal[k] = k * T
        dt = target - time.perf_counter()
        if dt > 0:
            time.sleep(dt)
        if pre_job_hook is not None:
            pre_job_hook(k)
        release[k] = time.perf_counter() - r0
        job_fn(k)
        complete[k] = time.perf_counter() - r0
    return {"ideal": ideal, "release": release, "complete": complete}


class BackgroundLoad:
    """Background thread that burns CPU with a given duty cycle (0..1).

    duty = 1.0 -> continuous busy work. Work is done in short chunks so the
    thread behaves like a normal competing thread. NOTE: in CPython the GIL is
    shared, so this competes directly with the measured task for the interpreter.
    """

    def __init__(self, duty=1.0, slice_s=0.01):
        self.duty = duty
        self.slice_s = slice_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            if self.duty <= 0:
                time.sleep(self.slice_s)
                continue
            end = time.perf_counter() + self.duty * self.slice_s
            while time.perf_counter() < end and not self._stop.is_set():
                busy_work(200)
            rest = (1.0 - self.duty) * self.slice_s
            if rest > 0:
                time.sleep(rest)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


# ---------------------------------------------------------------- jitter ----
def release_jitter(ts):
    """Release jitter: actual release - ideal release (seconds)."""
    return ts["release"] - ts["ideal"]


def completion_jitter(ts):
    """Completion (output) jitter.

    The ideal completion instant of job k is ideal_k + c, where c is the typical
    (median) completion offset from the ideal release. Jitter is the deviation of
    each completion from that constant-offset periodic grid, so a constant
    latency is NOT counted as jitter - only the variation is.
    """
    offset = ts["complete"] - ts["ideal"]
    return offset - np.median(offset)


def jitter_summary(dev):
    """(std, max |jitter|) in seconds."""
    return float(np.std(dev)), float(np.max(np.abs(dev)))
