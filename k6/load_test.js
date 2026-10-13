import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const redirectLatency = new Trend("successful_redirect_duration", true);
const successfulRedirects = new Rate("successful_redirects");
const rateLimited = new Counter("rate_limited_requests");
const unexpectedFailures = new Rate("unexpected_failures");

export const options = {
  stages: [
    { duration: "10s", target: 50 },
    { duration: "30s", target: 50 },
    { duration: "5s", target: 0 },
  ],
  thresholds: {
    successful_redirect_duration: ["p(95)<500"],
    successful_redirects: ["rate>0.95"],
    unexpected_failures: ["rate<0.01"],
  },
};

export function setup() {
  const uniqueId = `k6_${Date.now().toString().slice(-10)}`;
  const registration = http.post(
    `${BASE_URL}/api/users/register`,
    JSON.stringify({ username: uniqueId, email: `${uniqueId}@test.invalid`, password: "load-test-only-123" }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(registration, { "test user registered": (response) => response.status === 201 });

  const login = http.post(`${BASE_URL}/api/users/token`, { username: uniqueId, password: "load-test-only-123" });
  if (login.status !== 200) throw new Error(`Login failed: ${login.status} ${login.body}`);

  const token = login.json("access_token");
  const created = http.post(
    `${BASE_URL}/api/urls`,
    JSON.stringify({ long_url: "https://example.com/load-test" }),
    { headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } },
  );
  if (created.status !== 201) throw new Error(`URL creation failed: ${created.status} ${created.body}`);
  return { shortCode: created.json("short_code") };
}

export default function ({ shortCode }) {
  const response = http.get(`${BASE_URL}/${shortCode}`, { redirects: 0 });
  const redirected = response.status === 307 && response.headers.Location?.startsWith("https://example.com/");
  if (response.status === 429) rateLimited.add(1);
  successfulRedirects.add(redirected);
  unexpectedFailures.add(response.status !== 307 && response.status !== 429);
  if (redirected) redirectLatency.add(response.timings.duration);
  check(response, { "redirect succeeds or limiter returns 429": () => redirected || response.status === 429 });
  sleep(0.1);
}
