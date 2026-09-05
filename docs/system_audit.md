# PayRoute AI — Complete System Audit

**Project**: PayRoute AI — AI-Powered Payment Failure Prediction & Smart Routing  
**Type**: Independent Fintech Reliability Prototype  
**Scope**: Educational / Internship-Ready Machine Learning & Reliability Architecture  

---

## 1. Executive Summary

PayRoute AI is an end-to-end payment reliability prototype inspired by real-world payment aggregators (such as Razorpay). The system addresses a fundamental challenge in electronic payment processing: **transactions fail due to bank downtime, gateway latency, network degradation, and user friction**.

PayRoute AI combines:
1. **Predictive Machine Learning**: Stage-1 Calibrated Gradient Boosted Decision Tree estimating $P(\text{Fail})$ and Stage-2 Multi-Class Failure Reason Diagnosis.
2. **Multi-Objective Smart Routing**: Utility optimization balancing predicted success ($60\%$), normalized latency ($20\%$), interchange cost ($10\%$), and recent provider health ($10\%$).
3. **Dynamic 3-State Circuit Breakers**: `CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN` state machine isolating degraded routes and testing recovery with probe traffic.
4. **FastAPI REST Backend**: Sub-35ms API exposing prediction, recommendation, simulation, and telemetry endpoints.
5. **Streamlit Multi-Page Console**: Interactive frontend providing live simulations, routing visualizers, and model analytics.

---

## 2. Directory Structure & Module Index

```text
payroute-ai/
├── api/                                # FastAPI REST Service Layer
│   ├── routes/                         # Route Controllers (health, predict, route, transactions, analytics)
│   ├── dependencies.py                 # Dependency Injection Providers
│   ├── main.py                         # FastAPI App Factory & Lifespan Handler
│   └── schemas.py                      # Pydantic v2 Request/Response Validation Models
├── config/                             # Centralized YAML Configurations
│   ├── config.yaml                     # Database, Seed, and Feature Paths
│   ├── data_generation.yaml            # Synthetic Distribution & Hazard Parameters
│   └── routes_config.yaml              # Route Catalogue, Weights, and CB Thresholds
├── dashboard/                          # Streamlit Multipage Frontend
│   ├── components/                     # Reusable KPI Cards, Tables, and Charts
│   ├── pages/                          # 4 Interactive Pages (Simulator, Console, Health, Analytics)
│   ├── api_client.py                   # Centralized HTTP Client for FastAPI
│   └── app.py                          # Main Landing Portal
├── data/                               # Data Store (Raw & Processed)
│   ├── raw/payments_synthetic.csv      # 100,000 Synthetic Payment Records
│   └── processed/                      # EDA and 10 Evaluation Artifacts
├── database/                           # Relational Persistence Layer
│   ├── db_manager.py                   # Parameterized SQLite Repository Methods
│   ├── init_db.py                      # Database Initialization CLI
│   ├── payroute.db                     # SQLite Database File
│   └── schema.sql                      # DDL Schema with Foreign Keys & Indices
├── docs/                               # Comprehensive Technical Documentation
├── models/                             # Serialized ML Artifacts
│   ├── preprocessor.joblib             # Fitted Scikit-Learn ColumnTransformer
│   ├── failure_model.joblib            # Base HistGradientBoostingClassifier
│   ├── calibrated_failure_model.joblib # Isotonic Calibrated Classifier
│   ├── reason_model.joblib             # Multi-Class Failure Reason Diagnoser
│   ├── feature_metadata.json           # Risk Thresholds & Encodings
│   └── model_metrics.json              # Serialized Evaluation Metrics
├── notebooks/                          # Interactive Jupyter Notebooks
│   ├── 02_exploratory_data_analysis.ipynb
│   ├── 03_model_training_and_calibration.ipynb
│   └── 04_smart_routing_simulation.ipynb
├── src/                                # Core Business & ML Logic
│   ├── data_generator/                 # Synthetic Data Generation
│   ├── features/                       # Transformers & Preprocessing Pipeline
│   ├── ml/                             # Training, Calibration, Evaluation, Explainer
│   ├── router/                         # Candidate Filtering, Scoring, Circuit Breakers
│   └── utils/                          # Structured Logging
└── tests/                              # Automated Test Suite (41 Unit & API Tests)
```

---

## 3. End-to-End Data Flow

```text
Payment Request (Amount, Rail, Bank, Customer History)
       │
       ▼
[ Candidate Filter ] ── Validates Payment Method, Issuing Bank, Active Flag & Circuit State
       │
       ▼
[ Feature Pipeline ] ── Transforms 22 Raw Telemetry Fields into 37 Preprocessed Scaled Features
       │
       ▼
[ ML Risk Predictor ] ── Evaluates Calibrated P(Fail) and Diagnoses Failure Reason Mode
       │
       ▼
[ Multi-Objective Scorer ] ── Computes Utility: 0.60*Success - 0.20*Latency - 0.10*Cost + 0.10*Health
       │
       ▼
[ Route Selector ] ── Assigns Primary Route, Fallback Route, and Explanations
       │
       ▼
[ Execution Engine ] ── Simulates Payment Outcome, Records Latency, Updates Health Deques
       │
       ▼
[ Circuit Breakers ] ── Evaluates Rolling Failure Rates (Trips CLOSED -> OPEN if Fr >= 40% & N >= 20)
       │
       ▼
[ SQLite Database ] ── Records Transactions & Routing Audits in Relational Tables
```

---

## 4. Dependencies & Technology Stack

* **Language & Runtime**: Python 3.10+ on Windows / Linux / macOS.
* **Data Science & ML**: `scikit-learn`, `pandas`, `numpy`, `matplotlib`, `joblib`.
* **API Backend**: `fastapi`, `uvicorn`, `pydantic` (v2), `requests`.
* **Frontend**: `streamlit`.
* **Database**: SQLite 3 with PRAGMA foreign keys and index optimization.
* **Testing**: Python `unittest`, `pytest`, and FastAPI `TestClient`.

---

## 5. Scope & Honest Prototype Boundaries

1. **Synthetic Data**: The dataset was generated specifically for this project using logit hazard formulations. It does not use proprietary internal data from Razorpay or any commercial payment processor.
2. **Simulation Layer**: Payment outcomes and route latencies are simulated locally rather than calling live bank core banking systems.
3. **In-Memory Health Store**: Route health is tracked in-memory with thread-safe rolling deques; production systems would sync this across nodes using Redis or Kafka.
