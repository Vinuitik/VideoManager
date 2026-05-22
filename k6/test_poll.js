/**
 * k6 load test — Polling download flow (Version A)
 *
 * Tests the full poll cycle: POST /api/v1/download → poll /api/v1/jobs/:id until done.
 * Does NOT actually download YouTube videos (that would be slow and abuse YouTube).
 * Instead, it hammers the API endpoints with a pre-existing job_id to measure
 * poll throughput and latency under concurrent load.
 *
 * Run:
 *   k6 run k6/test_poll.js
 *   k6 run --out json=results.json k6/test_poll.js   (save raw results)
 *   k6 run --out influxdb=http://localhost:8086/k6 k6/test_poll.js  (stream to InfluxDB for Grafana)
 *
 * Environment variables:
 *   BASE_URL   default: http://localhost
 *   TEST_URL   YouTube URL to actually download (only used in the real_download scenario)
 */
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const BASE_URL = __ENV.BASE_URL || 'http://localhost'
const TEST_URL  = __ENV.TEST_URL  || ''

const pollErrors       = new Rate('poll_errors')
const pollLatency      = new Trend('poll_latency_ms', true)
const jobCreateLatency = new Trend('job_create_latency_ms', true)

export const options = {
  scenarios: {
    // Scenario 1 — Steady state: constant moderate load
    steady: {
      executor: 'constant-vus',
      vus: 10,
      duration: '30s',
      tags: { scenario: 'steady' },
    },

    // Scenario 2 — Spike: sudden burst (simulates "things going badly")
    spike: {
      executor: 'ramping-vus',
      startTime: '35s',
      startVUs: 0,
      stages: [
        { duration: '5s',  target: 100 },  // ramp up hard
        { duration: '20s', target: 100 },  // sustain
        { duration: '5s',  target: 0   },  // recover
      ],
      tags: { scenario: 'spike' },
    },

    // Scenario 3 — Soak: low load over time (finds memory leaks in state.jobs)
    soak: {
      executor: 'constant-vus',
      startTime: '65s',
      vus: 5,
      duration: '60s',
      tags: { scenario: 'soak' },
    },
  },

  // These are your pass/fail gates — k6 exits with code 1 if breached
  thresholds: {
    'http_req_duration':     ['p95<500'],   // 95% of poll requests under 500ms
    'poll_errors':           ['rate<0.05'], // error rate under 5%
    'job_create_latency_ms': ['p95<200'],   // job creation under 200ms
  },
}

// Create a throwaway job to get a valid job_id for polling
function createJob() {
  const start = Date.now()
  const res = http.post(
    `${BASE_URL}/api/v1/download`,
    JSON.stringify({ url: 'https://example.com/fake' }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'create_job' } },
  )
  jobCreateLatency.add(Date.now() - start)
  check(res, { 'job created (200)': r => r.status === 200 }) || pollErrors.add(1)
  return res.status === 200 ? JSON.parse(res.body).job_id : null
}

// Poll a job_id and measure response time
function pollJob(jobId) {
  const start = Date.now()
  const res = http.get(`${BASE_URL}/api/v1/jobs/${jobId}`, {
    tags: { name: 'poll_job' },
  })
  pollLatency.add(Date.now() - start)
  check(res, {
    'poll 200': r => r.status === 200,
    'has status field': r => JSON.parse(r.body).status !== undefined,
  }) || pollErrors.add(1)
}

export default function () {
  const jobId = createJob()
  if (!jobId) return

  // Simulate a client polling 5 times at 1s intervals
  for (let i = 0; i < 5; i++) {
    pollJob(jobId)
    sleep(1)
  }
}
