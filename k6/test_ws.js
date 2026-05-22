/**
 * k6 load test — WebSocket download flow (Version B)
 *
 * Tests WebSocket connection handling: open → send URL → receive messages → close.
 * Uses a fake URL so the backend will error quickly (we're testing connection overhead,
 * not actual download time). Set TEST_URL to a real YouTube URL if you want end-to-end.
 *
 * Run:
 *   k6 run k6/test_ws.js
 *   k6 run -e TEST_URL=https://www.youtube.com/watch?v=xxx k6/test_ws.js
 *
 * Environment variables:
 *   BASE_URL   default: ws://localhost
 *   TEST_URL   URL to send to the server (fake by default — triggers quick error response)
 */
import ws   from 'k6/ws'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const BASE_URL = __ENV.BASE_URL || 'ws://localhost'
const TEST_URL  = __ENV.TEST_URL  || 'https://example.com/not-a-video'

const wsErrors        = new Rate('ws_errors')
const connectLatency  = new Trend('ws_connect_latency_ms', true)
const firstMsgLatency = new Trend('ws_first_message_latency_ms', true)

export const options = {
  scenarios: {
    // Scenario 1 — Concurrency baseline: how many simultaneous WS connections hold up
    concurrent: {
      executor: 'constant-vus',
      vus: 20,
      duration: '30s',
      tags: { scenario: 'concurrent' },
    },

    // Scenario 2 — Ramp to breaking point
    breakpoint: {
      executor: 'ramping-vus',
      startTime: '35s',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 200 },  // keep ramping — find where it breaks
        { duration: '10s', target: 0   },
      ],
      tags: { scenario: 'breakpoint' },
    },
  },

  thresholds: {
    'ws_errors':              ['rate<0.1'],   // under 10% WS errors
    'ws_connect_latency_ms':  ['p95<1000'],   // connect in under 1s
    'ws_first_message_latency_ms': ['p95<2000'],
  },
}

export default function () {
  const connectStart = Date.now()

  const res = ws.connect(`${BASE_URL}/api/v2/download`, {}, function (socket) {
    connectLatency.add(Date.now() - connectStart)

    let firstMessage = true
    const sendStart = Date.now()

    socket.on('open', () => {
      socket.send(JSON.stringify({ url: TEST_URL }))
    })

    socket.on('message', (data) => {
      if (firstMessage) {
        firstMsgLatency.add(Date.now() - sendStart)
        firstMessage = false
      }

      const msg = JSON.parse(data)
      check(msg, {
        'message has type': m => m.type !== undefined,
      }) || wsErrors.add(1)

      // Close once we get a terminal message (done or error)
      if (msg.type === 'done' || msg.type === 'error') {
        socket.close()
      }
    })

    socket.on('error', (e) => {
      wsErrors.add(1)
      socket.close()
    })

    // Safety timeout — close after 30s regardless
    socket.setTimeout(() => socket.close(), 30000)
  })

  check(res, { 'WS status 101': r => r && r.status === 101 }) || wsErrors.add(1)

  sleep(1)
}
