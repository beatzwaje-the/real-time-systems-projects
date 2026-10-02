| Target | Random max (µs) | Adversarial max (µs) | Adv / Rand | Adversarial largest? | Margined (+50%) (µs) | Outlier flag (rand / adv) |
|---|---|---|---|---|---|---|
| search_early_exit | 122.2 | 676.8 | 5.54x | yes | 1015.3 | False / True |
| collatz_steps | 98.5 | 218.9 | 2.22x | yes | 328.3 | True / True |
| mode_controller | 211.9 | 5307.9 | 25.05x | yes | 7961.9 | True / False |

All statistics (µs):

| Target | Strategy | mean | std | min | max | p90 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|
| search_early_exit | random | 33.5 | 21.4 | 0.5 | 122.2 | 59.5 | 63.7 | 86.5 |
| search_early_exit | adversarial | 72.9 | 44.0 | 56.8 | 676.8 | 103.0 | 116.3 | 281.9 |
| collatz_steps | random | 7.5 | 6.4 | 1.3 | 98.5 | 11.7 | 13.2 | 30.0 |
| collatz_steps | adversarial | 25.7 | 16.6 | 21.8 | 218.9 | 26.8 | 34.6 | 72.8 |
| mode_controller | random | 3.2 | 16.3 | 0.2 | 211.9 | 13.1 | 14.9 | 19.6 |
| mode_controller | adversarial | 2739.3 | 628.0 | 2259.1 | 5307.9 | 3758.1 | 4495.7 | 4703.5 |
