
# ./vegeta attack -duration=10s -rate=100 -max-workers=20

## fastapi

### Local

```text
Requests      [total, rate, throughput]         1000, 100.09, 100.08
Duration      [total, attack, wait]             9.992s, 9.991s, 859.607µs
Latencies     [min, mean, 50, 90, 95, 99, max]  809.031µs, 1.015ms, 883.263µs, 991.531µs, 1.072ms, 1.382ms, 42.519ms
Bytes In      [total, mean]                     602000, 602.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:1000
```

### remote

```text
Requests      [total, rate, throughput]         951, 95.18, 93.28
Duration      [total, attack, wait]             10.195s, 9.992s, 203.53ms
Latencies     [min, mean, 50, 90, 95, 99, max]  184.98ms, 210.101ms, 204.274ms, 213.903ms, 223.73ms, 403.554ms, 617.334ms
Bytes In      [total, mean]                     572502, 602.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:951
```

## flask

### Local

```text
Requests      [total, rate, throughput]         1000, 100.10, 100.08
Duration      [total, attack, wait]             9.992s, 9.99s, 1.542ms
Latencies     [min, mean, 50, 90, 95, 99, max]  1.004ms, 1.314ms, 1.293ms, 1.489ms, 1.551ms, 1.723ms, 3.202ms
Bytes In      [total, mean]                     602000, 602.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:1000
```

### remote

```text
Requests      [total, rate, throughput]         473, 47.26, 45.40
Duration      [total, attack, wait]             10.417s, 10.009s, 408.365ms
Latencies     [min, mean, 50, 90, 95, 99, max]  394.736ms, 426.432ms, 408.838ms, 426.61ms, 441.863ms, 1.41s, 1.453s
Bytes In      [total, mean]                     284746, 602.00
Bytes Out     [total, mean]                     0, 0.00
Success       [ratio]                           100.00%
Status Codes  [code:count]                      200:473
```

