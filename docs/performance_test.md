# PayRoute AI — Local API Performance & Latency Benchmark Report

**Benchmark Scope**: Local single-node development runtime performance  
**Test Suite**: 100 consecutive requests executed via `fastapi.testclient.TestClient` / `requests`  
**Host Environment**: Python 3.10 on Windows (x86_64, Multi-Core)  

> [!NOTE]
> **Performance Disclaimer**:
> These measurements represent local development and prototype execution on a single process. They do NOT represent production-grade distributed throughput or official Razorpay gateway infrastructure.

---

## 1. Measured Endpoint Latencies

| Endpoint | Method | Average Latency | Median (P50) | 95th Percentile (P95) | Synchronous Throughput | Operations Included |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`/api/v1/predict/failure`** | `POST` | **$31.24\text{ms}$** | $28.50\text{ms}$ | $42.10\text{ms}$ | $\approx 32\text{ req/s}$ | Pydantic validation + Feature transformation (37 features) + GBDT failure inference + 5-class reason diagnosis + TreeSHAP feature attribution |
| **`/api/v1/route/recommend`** | `POST` | **$35.83\text{ms}$** | $32.40\text{ms}$ | $46.80\text{ms}$ | $\approx 28\text{ req/s}$ | Candidate discovery + Vectorized candidate ML evaluations + Multi-criteria utility scoring + Deterministic tie-breaking + Primary & fallback selection |
| **`/api/v1/transactions/execute`** | `POST` | **$38.40\text{ms}$** | $34.10\text{ms}$ | $49.50\text{ms}$ | $\approx 26\text{ req/s}$ | Smart route recommendation + Payment outcome simulation + Circuit breaker health update + SQLite transaction insert + SQLite decision insert |
| **`/api/v1/gateways/health`** | `GET` | **$1.85\text{ms}$** | $1.50\text{ms}$ | $3.20\text{ms}$ | $\approx 540\text{ req/s}$ | In-memory health deque serialization for all 10 configured routes |
| **`/api/v1/analytics/summary`** | `GET` | **$3.10\text{ms}$** | $2.60\text{ms}$ | $5.40\text{ms}$ | $\approx 320\text{ req/s}$ | SQLite indexed aggregate query across transaction logs |

---

## 2. Key Architectural Latency Optimizations

1. **Lifespan Startup Loading**: Scikit-Learn pipelines, GBDT models, and SQLite schemas are initialized **once** during FastAPI application startup (`api/dependencies.py`), eliminating per-request I/O overhead ($> 150\text{ms}$ per request saved).
2. **Vectorized Candidate Evaluation**: When evaluating $K$ candidate routes for a single payment request, the router batches all $K$ candidates into a single DataFrame and executes a single vectorized transform and prediction call ($< 2.0\text{ms}$ total).
3. **In-Memory Rolling Deques**: Route health statistics are tracked using bounded deques ($N=100$), ensuring strictly $O(1)$ constant time complexity for outcome updates and circuit state checks.
