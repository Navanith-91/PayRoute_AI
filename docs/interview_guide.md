# PayRoute AI — Comprehensive Technical Interview Guide

*29 In-Depth Questions and Answers covering System Design, Machine Learning, Multi-Objective Routing, Distributed Reliability, and Honest Boundaries.*

---

## 📌 Section 1: Basic & Problem Context

### Q1: What core problem does PayRoute AI solve?
**Answer**: In digital payments, $12\% - 18\%$ of transactions fail due to bank downtime, gateway latency spikes, network degradation, and authentication friction. Static or naive routing sends traffic into failing rails, leading to lost revenue and cart abandonment. PayRoute AI predicts transaction failure probability in real time and dynamically routes payments across optimal gateway rails to maximize success.

### Q2: Why did you choose this problem?
**Answer**: Payment reliability is a mission-critical infrastructure challenge at top fintechs (e.g., Razorpay, Stripe). It requires a delicate intersection of low-latency machine learning (<35ms inference), asymmetric cost optimization, and distributed fault tolerance (circuit breakers).

### Q3: How does the end-to-end system work?
**Answer**: When a payment request arrives, PayRoute AI:
1. Filters eligible candidate routes based on bank and payment method.
2. Uses an Isotonic-calibrated Gradient Boosted Decision Tree to evaluate $P(\text{Fail})$ across all candidates.
3. Scores each candidate using a multi-objective utility function ($0.60\text{ Success} - 0.20\text{ Latency} - 0.10\text{ Cost} + 0.10\text{ Health}$).
4. Selects a primary route and backup fallback, while 3-state circuit breakers isolate degraded providers.
5. Records the transaction outcome and updates rolling telemetry in SQLite.

---

## 🧠 Section 2: Machine Learning, Calibration & Explainability

### Q4: Why Gradient Boosted Decision Trees (HistGradientBoosting / LightGBM) over other models?
**Answer**: GBDT models are the state-of-the-art for tabular fintech data. They handle heterogeneous feature distributions, non-linear interactions (e.g., high amounts on 2G networks), require minimal feature scaling, and achieve sub-5ms CPU inference without GPU dependencies.

### Q5: Why not deep neural networks?
**Answer**: Deep neural networks typically overfit on tabular payment data, require extensive hyperparameter tuning, and introduce inference latency overhead (>50ms) without providing accuracy gains over tree ensembles for structured tabular inputs.

### Q6: Why was probability calibration necessary?
**Answer**: Raw tree ensemble leaf scores are not true posterior probabilities; they tend to push confidence toward 0 and 1. By applying **Isotonic Regression** on a validation split, we reduced Brier score error by **$45.6\%$** ($0.2008 \rightarrow 0.1092$). True calibrated probabilities are essential because the routing engine uses $P(\text{Success})$ directly in mathematical utility calculations.

### Q7: Why focus on PR-AUC instead of ROC-AUC or Accuracy?
**Answer**: Payment failures are an imbalanced class ($14.7\%$ positive rate). Accuracy is misleading (an 85% accuracy model could simply predict "Success" every time). ROC-AUC can be overly optimistic under class imbalance because false positive rates remain small. PR-AUC measures the exact trade-off between precision and recall on the minority failure class. PayRoute AI achieved $0.3694$ PR-AUC (+150.9% lift over the $0.1472$ no-skill baseline).

### Q8: How did you strictly prevent data leakage?
**Answer**:
1. Partitioned the dataset **chronologically** (earliest 70% Train, middle 15% Val, latest 15% Test) rather than random shuffling.
2. Fitted all transformers, encoders, and target encodings exclusively on the training split.
3. Strictly excluded post-outcome telemetry (observed latency, actual failure reason) from the feature matrix during training and inference.

### Q9: Why is temporal train/test splitting critical in payments?
**Answer**: In production payment systems, future transactions cannot leak into the past. Random K-fold cross-validation shuffles future customer behavioral patterns and bank outage clusters into training sets, producing inflated, unrepresentative accuracy metrics.

### Q10: How did you handle class imbalance?
**Answer**: Rather than artificially distorting the real-world probability distribution using SMOTE or random oversampling, we retained the natural $14.7\%$ distribution to preserve probability calibration, and tuned the decision threshold ($T^* = 0.20$) using cost-matrix optimization.

### Q11: How does local feature attribution (TreeSHAP) work in your project?
**Answer**: For each prediction, we compute Shapley values to decompose the model's logit prediction into additive feature contributions. The dashboard visualizes these as **Key Risk Contributors (+)** (e.g., repeated retries, high amount) and **Key Protective Factors (-)** (e.g., 5G network, high bank health score).

---

## 🔀 Section 3: Smart Routing & Optimization

### Q12: How does the multi-objective utility scoring algorithm work?
**Answer**: Each candidate route $i$ is scored using:
$$\text{Score}_i = 0.60 \cdot P(\text{Success}_i) - 0.20 \cdot \widetilde{\text{Latency}}_i - 0.10 \cdot \widetilde{\text{Cost}}_i + 0.10 \cdot \text{Health}_i$$
Normalized latency and interchange fee penalties prevent the system from picking a route with a $0.1\%$ higher success probability if it incurs a $600\text{ms}$ latency penalty or double the processing fee.

### Q13: Why isn't choosing the lowest failure probability enough?
**Answer**: In payments, two routes may have virtually identical failure probabilities (e.g., $5.0\%$ vs $5.2\%$), but one might have $150\text{ms}$ latency and $1.1\%$ fees while the other has $450\text{ms}$ latency and $1.8\%$ fees. Single-objective routing ignores merchant margins and user experience.

### Q14: Why include latency in the routing formula?
**Answer**: Excessive latency causes checkout timeouts, user frustration, and accidental double-clicks, which directly triggers secondary payment failures.

### Q15: Why include interchange cost?
**Answer**: Merchants operate on thin margins (1-3%). By incorporating fee penalties ($10\%$), the router breaks ties in favor of lower-cost rails without sacrificing payment reliability.

### Q16: Why include rolling health telemetry?
**Answer**: ML models reflect trained historical weights. Recent 5-minute rolling success telemetry detects sudden, unannounced upstream bank degradation before batch model retraining occurs.

### Q17: How does fallback routing work?
**Answer**: The router selects the highest-scoring candidate as the `primary_route` and the second highest-scoring candidate as the `fallback_route`. If the primary route times out or fails at execution, the orchestrator cascades the transaction to the fallback rail.

---

## 🛡️ Section 4: Distributed Reliability & Circuit Breakers

### Q18: What is a Circuit Breaker in payment routing?
**Answer**: A reliability pattern that prevents an application from repeatedly executing an operation that is failing. It temporarily disables routing traffic to a degraded bank or gateway rail to prevent systemic failure propagation.

### Q19: Why a 3-state state machine (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN`)?
**Answer**:
* `CLOSED`: Normal operation; all traffic flows through.
* `OPEN`: Severe failure detected ($\ge 40\%$ failure rate over $\ge 20$ txns); traffic is isolated to protect overall success.
* `HALF_OPEN`: Recovery timer ($30\text{s}$) has elapsed; a $5\%$ sample of probe traffic is allowed through to safely test if the provider has recovered.

### Q20: How does the system detect route degradation?
**Answer**: Each route maintains in-memory circular deques ($N=100$) tracking the most recent outcomes. When the rolling failure rate crosses $40\%$ with at least $20$ recorded transactions, the circuit trips to `OPEN`.

### Q21: How does route recovery work?
**Answer**: When a route is `OPEN` for $30$ seconds, it transitions to `HALF_OPEN`. If a test probe succeeds, the state resets to `CLOSED`. If the probe fails, it re-trips to `OPEN` for another $30$ seconds.

---

## ⚙️ Section 5: Engineering & System Architecture

### Q22: Why FastAPI for the backend?
**Answer**: FastAPI provides asynchronous native performance, automatic Pydantic v2 data validation, interactive OpenAPI/Swagger documentation, and clean dependency injection singletons via `lifespan` handlers.

### Q23: Why SQLite for persistence in this prototype?
**Answer**: SQLite requires zero external server setup, provides full ACID compliance, supports parameterized SQL and foreign keys, and executes queries in $<3\text{ms}$ locally, making the project portable and self-contained.

### Q24: How does Streamlit communicate with FastAPI?
**Answer**: The Streamlit dashboard acts strictly as a presentation frontend consuming the REST API via a centralized `PayRouteAPIClient`. No ML models are loaded or retrained in Streamlit.

### Q25: How would you scale this system to $10,000+\text{ TPS}$?
**Answer**:
1. Export GBDT models to ONNX / Treelite and serve them via Triton Inference Server (<1ms latency).
2. Move route health deques from in-memory Python to a distributed Redis Cluster with atomic Lua scripts.
3. Stream payment transaction logs asynchronously to Apache Kafka topics consumed by PostgreSQL/ClickHouse.

### Q26: What would you change for a production banking integration?
**Answer**: Add PCI-DSS compliant tokenization (vaults for card PANs), mTLS and HMAC-SHA256 signature verification for webhook callbacks, and dual-region active-active database replication.

---

## ⚖️ Section 6: Honest Limitations & Prototype Boundaries

### Q27: What are the limitations of synthetic data?
**Answer**: Synthetic data, while generated using realistic logit hazard models and diurnal curves, cannot capture all black-swan market events, sudden regulatory changes, or unpredictable multi-bank simultaneous cascade collapses.

### Q28: What assumptions were made in the simulation?
**Answer**: We assumed fixed base interchange fee rates per gateway, localized network latency distributions, and an immediate 30-second recovery window for bank health probes.

### Q29: What would you need real payment data for?
**Answer**: To train deep temporal sequence models (e.g., LSTMs or Transformers for bank outage forecasting), tune exact per-merchant fee elasticity, and validate real-world user OTP drop-off distributions.
