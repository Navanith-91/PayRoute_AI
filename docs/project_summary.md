# PayRoute AI — 1-Page Executive Project Summary

**Project Title**: PayRoute AI — AI-Powered Payment Failure Prediction & Smart Routing  
**Domain**: Fintech Reliability, Machine Learning Engineering, System Design  
**Status**: Completed & Verified  

---

## 1. Problem Statement
In digital payment platforms, electronic transactions suffer unexpected failures ($12\% - 18\%$ failure rates) due to bank core outages, aggregator latencies, network degradation, and session drop-offs. Static and naive routing policies fail to adapt dynamically to upstream infrastructure faults, causing severe merchant revenue loss, abandoned checkouts, and degraded customer trust.

---

## 2. Solution Overview
PayRoute AI is an intelligent payment routing and reliability platform that dynamically optimizes transaction routing across multiple bank and gateway rails. The system:
1. Predicts transaction failure probability $P(\text{Fail})$ in real time using a calibrated Gradient Boosted Decision Tree.
2. Evaluates candidate routes using a multi-objective utility scoring function that balances success probability, latency, fees, and telemetry.
3. Automatically isolates degraded providers using 3-state dynamic circuit breakers (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN`) with automatic recovery probing.
4. Exposes sub-35ms REST API endpoints (FastAPI) and an interactive multi-page dashboard (Streamlit) backed by SQLite persistence.

---

## 3. Key Technical Highlights
* **Anti-Leakage Data Pipeline**: 22 raw telemetry features transformed into 37 scaled numerical and cyclic features with strict chronological train/validation/test partitioning.
* **Isotonic Probability Calibration**: Aligns model confidence with empirical reality, reducing uncalibrated Brier score error by **$45.6\%$** ($0.2008 \rightarrow 0.1092$).
* **Cost-Sensitive Decision Optimization**: Threshold optimization ($T^* = 0.20$) minimizing financial loss under asymmetric risk ($\text{Cost}_{\text{FN}} = 5 \cdot \text{Cost}_{\text{FP}}$).
* **High-Precision Failure Diagnosis**: 5-class failure friction diagnoser achieving $41.86\%$ test accuracy across unobserved friction modes.
* **Local Feature Attribution**: TreeSHAP gradient explainer decomposing risk contributors and protective factors for live transactions.
* **Production-Grade API & UI**: Modular FastAPI backend delivering sub-35ms inference paired with a 4-page interactive Streamlit console.

---

## 4. Measured Benchmark Results (3,000 Txn Benchmark)
* **Payment Success Rate**: **$85.43\%$** (Smart Routing) vs **$79.03\%$** (Naive Routing).
* **Success Rate Uplift**: **$+6.40\%$ percentage points** (**$+8.10\%$ relative improvement**).
* **Prevented Payment Failures**: **$198$ transactions recovered**.
* **Average Latency Reduction**: **$-60.5\text{ms}$** ($454.2\text{ms} \rightarrow 393.7\text{ms}$).
* **API Response Time**: **$31.2\text{ms}$** for risk prediction, **$35.8\text{ms}$** for route recommendation.

---

## 5. Technology Stack
* **Languages & Frameworks**: Python 3.10+, FastAPI, Streamlit, Pydantic v2, Scikit-Learn, Pandas, NumPy, Matplotlib.
* **Database & Persistence**: SQLite 3 (Parameterized DDL/DML, Foreign Keys, B-Tree Indices).
* **Quality Assurance**: Python Unittest, Pytest, FastAPI TestClient (**41 Tests Passing**).
