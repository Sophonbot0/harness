# Rate Limiter Middleware

Implement a sliding-window rate limiter middleware. Support per-IP and per-API-key limits. Return 429 with Retry-After header. Include bypass for health check endpoints.

- Category: feature
- Difficulty: medium
- Verify: `cd . && python3 -m pytest -v`
