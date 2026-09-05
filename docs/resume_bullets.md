# PayRoute AI — Metrics-Driven Resume Bullet Points

Formatted specifically for Software Engineering (Backend / Distributed Systems) and Machine Learning Engineering resumes.

---

## Option 1: Software Engineer / Backend / Distributed Systems

* **PayRoute AI — AI-Powered Payment Reliability & Smart Routing Engine** | *Python, FastAPI, SQLite, Streamlit, Scikit-Learn*
  * Architected a high-throughput smart payment routing system evaluating multi-objective utility functions ($60\%$ success, $20\%$ latency, $10\%$ cost, $10\%$ health) across 10 candidate bank/gateway routes.
  * Designed a 3-state dynamic circuit breaker (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN`) with guarded rolling telemetry deques, isolating degraded providers and delivering a **$+6.40\%$ success rate uplift** and **$198$ recovered transactions** during simulated outages.
  * Built sub-35ms REST API endpoints using FastAPI and Pydantic v2 with automated lifespan caching, paired with a 4-page Streamlit operations dashboard backed by SQLite persistence.
  * Engineered a comprehensive automated test suite of 41 unit and API integration tests achieving $100\%$ pass rate.

---

## Option 2: Machine Learning Engineer / Applied AI

* **PayRoute AI — Real-Time Payment Failure Prediction & Routing Platform** | *Python, GBDT, Isotonic Calibration, TreeSHAP, FastAPI*
  * Trained and tuned a two-stage Gradient Boosted Decision Tree pipeline over 100,000 transactions, achieving **$0.3694$ PR-AUC** (**$+150.9\%$ lift** over random baseline) on an out-of-time test set.
  * Implemented non-parametric **Isotonic Probability Calibration**, reducing uncalibrated probability error by **$45.6\%$** (Brier score $0.2008 \rightarrow 0.1092$) to enable mathematically rigorous financial utility scoring.
  * Formulated an asymmetric business loss matrix ($\text{Cost}_{\text{FN}} = 5 \cdot \text{Cost}_{\text{FP}}$) to establish an optimal decision threshold ($T^* = 0.20$), cutting financial false-negative risk by $38.5\%$.
  * Integrated local TreeSHAP attribution and a 5-class failure mode classifier to provide sub-32ms real-time explainability and root-cause diagnosis.

---

## Option 3: Concise 2-Bullet Format

* **PayRoute AI — AI-Powered Payment Failure Prediction & Smart Routing**
  * Engineered an intelligent payment routing platform using calibrated GBDT models, multi-objective utility scoring, and 3-state dynamic circuit breakers, increasing transaction success rate by **$+6.40\%$ points** ($+8.10\%$ relative) and reducing mean latency by **$60.5\text{ms}$** across a 3,000-transaction outage benchmark.
  * Built a modular FastAPI backend serving sub-35ms inference endpoints with SQLite persistence, validated by a 41-test automated suite and demonstrated via an interactive 4-page Streamlit console.
