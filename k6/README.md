# Load Testing with k6

## Install

```bash
# Windows (Chocolatey)
choco install k6

# Mac
brew install k6

# Docker (no install needed)
docker run --rm -i grafana/k6 run - < k6/test_poll.js
```

## Run Tests

```bash
# Poll flow — steady + spike + soak scenarios
k6 run k6/test_poll.js

# WebSocket flow — concurrency + breakpoint scenarios
k6 run k6/test_ws.js

# With a real download URL
k6 run -e TEST_URL="https://www.youtube.com/watch?v=jNQXAC9IVRw" k6/test_ws.js

# Save results to JSON for later analysis
k6 run --out json=results.json k6/test_poll.js

# Stream results live into Grafana (requires InfluxDB)
k6 run --out influxdb=http://localhost:8086/k6 k6/test_poll.js
```

## Scenarios Explained

### test_poll.js
| Scenario | VUs | Duration | Simulates |
|----------|-----|----------|-----------|
| `steady` | 10 | 30s | Normal usage |
| `spike`  | 0→100→0 | 30s | Sudden burst (DDoS-like) |
| `soak`   | 5 | 60s | Long-running memory leak detection |

### test_ws.js
| Scenario | VUs | Duration | Simulates |
|----------|-----|----------|-----------|
| `concurrent`  | 20 | 30s | Many simultaneous WS connections |
| `breakpoint`  | 0→200 | 40s | Ramp until the server breaks |

## Reading Results

k6 reports at the end of each run. Key lines:

```
http_req_duration.........: p95=142ms   ← 95% of requests faster than this
ws_errors.................: 2.5%        ← WebSocket error rate
poll_errors...............: 0.8%        ← compare against 5% threshold
✓ thresholds: 3/3                       ← all pass/fail gates passed
✗ thresholds: 1/3                       ← something breached — check which one
```

## Thresholds (pass/fail gates)

Edit the `thresholds` object in each script. k6 exits with code 1 if any breach —
useful for CI pipelines ("deploy blocked if p95 latency > 500ms").
