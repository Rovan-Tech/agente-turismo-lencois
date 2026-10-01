// Teste de carga leve da API (k6): leitura do painel sob 30 requisições por segundo durante 30 s.
// Os limiares abaixo reprovam a execução: erro acima de 1% ou p95 acima de 500 ms.
// Uso: k6 run -e BASE_URL=http://127.0.0.1:8000 -e TOKEN=<token-do-painel> backend/tests/load/api.js
import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    painel: {
      executor: "constant-arrival-rate",
      rate: 30,
      timeUnit: "1s",
      duration: "30s",
      preAllocatedVUs: 20,
      maxVUs: 50,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
    checks: ["rate>0.99"],
  },
};

const base = __ENV.BASE_URL;
const headers = { Authorization: `Bearer ${__ENV.TOKEN}` };

export default function () {
  const responses = http.batch([
    ["GET", `${base}/health`],
    ["GET", `${base}/api/tours`, null, { headers }],
    ["GET", `${base}/api/conversations`, null, { headers }],
  ]);
  for (const response of responses) {
    check(response, { "status 200": (r) => r.status === 200 });
  }
}
