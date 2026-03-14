/**
 * k6 Load-Test: Public Beta (TASK-148)
 *
 * Validates that PWBS infrastructure handles 1.000+ concurrent users.
 *
 * Scenarios:
 *   1. Ramp-up to 1.000 virtual users over 5 minutes
 *   2. Sustain 1.000 VUs for 10 minutes
 *   3. Spike to 1.500 VUs for 2 minutes
 *   4. Ramp-down over 3 minutes
 *
 * Thresholds (p95):
 *   - HTTP request duration < 500ms (general API)
 *   - HTTP request duration < 2000ms (search)
 *   - HTTP request duration < 10000ms (briefing generation)
 *   - Error rate < 1%
 *
 * Usage:
 *   k6 run --env BASE_URL=https://api.pwbs.example.com tests/load/k6-public-beta.js
 *   k6 run --env BASE_URL=http://localhost:8000 tests/load/k6-public-beta.js
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;

export const options = {
  scenarios: {
    public_beta_load: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "5m", target: 1000 },  // Ramp-up
        { duration: "10m", target: 1000 }, // Sustain
        { duration: "2m", target: 1500 },  // Spike
        { duration: "3m", target: 0 },     // Ramp-down
      ],
      gracefulRampDown: "30s",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<500"],
    "http_req_duration{type:search}": ["p(95)<2000"],
    "http_req_duration{type:briefing}": ["p(95)<10000"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

// Custom metrics
const errorRate = new Rate("errors");
const dashboardDuration = new Trend("dashboard_duration", true);
const searchDuration = new Trend("search_duration", true);

// ---------------------------------------------------------------------------
// Setup: Register + Login a pool of test users
// ---------------------------------------------------------------------------

export function setup() {
  // Create a single test user for the entire run
  const email = `k6-beta-${uuidv4().substring(0, 8)}@pwbs-test.local`;
  const password = "K6LoadTest!Secure#2026";

  const regResp = http.post(
    `${API}/auth/register`,
    JSON.stringify({
      email: email,
      password: password,
      display_name: "k6 Beta Tester",
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  const loginResp = http.post(
    `${API}/auth/login`,
    JSON.stringify({ email: email, password: password }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (loginResp.status !== 200) {
    throw new Error(`Login failed: ${loginResp.status} ${loginResp.body}`);
  }

  const body = JSON.parse(loginResp.body);
  return { token: body.access_token };
}

// ---------------------------------------------------------------------------
// Default function: Mixed workload per VU iteration
// ---------------------------------------------------------------------------

export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.token}`,
    "Content-Type": "application/json",
  };

  // 60% Dashboard load, 25% Search, 10% Reminders, 5% Briefing
  const roll = Math.random();

  if (roll < 0.6) {
    dashboardLoad(headers);
  } else if (roll < 0.85) {
    searchQuery(headers);
  } else if (roll < 0.95) {
    remindersLoad(headers);
  } else {
    briefingGeneration(headers);
  }

  sleep(Math.random() * 2 + 1); // 1-3s think time
}

// ---------------------------------------------------------------------------
// Scenario groups
// ---------------------------------------------------------------------------

function dashboardLoad(headers) {
  group("Dashboard Load", () => {
    const responses = http.batch([
      ["GET", `${API}/briefings?type=morning&limit=1`, null, {
        headers,
        tags: { type: "dashboard" },
      }],
      ["GET", `${API}/connectors/status`, null, {
        headers,
        tags: { type: "dashboard" },
      }],
      ["GET", `${API}/reminders?limit=5`, null, {
        headers,
        tags: { type: "dashboard" },
      }],
    ]);

    for (const resp of responses) {
      const ok = check(resp, {
        "dashboard: status 200": (r) => r.status === 200,
      });
      errorRate.add(!ok);
      dashboardDuration.add(resp.timings.duration);
    }
  });
}

function searchQuery(headers) {
  group("Search", () => {
    const queries = [
      "Projektbriefing letzte Woche",
      "Meeting-Notizen Architektur",
      "Follow-up Entscheidungen Q3",
      "DSGVO Compliance Status",
    ];
    const query = queries[Math.floor(Math.random() * queries.length)];

    const resp = http.post(
      `${API}/search/`,
      JSON.stringify({ query: query, mode: "hybrid", top_k: 10 }),
      { headers, tags: { type: "search" } }
    );

    const ok = check(resp, {
      "search: status 200": (r) => r.status === 200,
    });
    errorRate.add(!ok);
    searchDuration.add(resp.timings.duration);
  });
}

function remindersLoad(headers) {
  group("Reminders", () => {
    const resp = http.get(`${API}/reminders?limit=20`, {
      headers,
      tags: { type: "reminders" },
    });

    check(resp, {
      "reminders: status 200": (r) => r.status === 200,
    });
  });
}

function briefingGeneration(headers) {
  group("Briefing Generation", () => {
    const resp = http.post(
      `${API}/briefings/generate`,
      JSON.stringify({ briefing_type: "morning" }),
      { headers, tags: { type: "briefing" } }
    );

    check(resp, {
      "briefing: status 200 or 201": (r) =>
        r.status === 200 || r.status === 201,
    });
  });
}
