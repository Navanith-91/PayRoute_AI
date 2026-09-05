# PayRoute AI — Clean Project Structure & Module Index

```text
payroute-ai/
│
├── api/                                # FastAPI REST Service Layer
│   ├── routes/                         # Modular API Controllers
│   │   ├── __init__.py                 # API Router Aggregator
│   │   ├── analytics.py                # GET /api/v1/analytics/summary
│   │   ├── health.py                   # GET /health, GET /api/v1/health, GET /api/v1/gateways/health
│   │   ├── prediction.py               # POST /api/v1/predict/failure
│   │   ├── routing.py                  # POST /api/v1/route/recommend
│   │   └── transaction.py              # POST /api/v1/transactions/execute, GET /transactions/{id}
│   ├── dependencies.py                 # Service Dependency Injection Providers
│   ├── main.py                         # FastAPI App Factory & Lifespan Event Handler
│   └── schemas.py                      # Pydantic v2 Request/Response Validation Models
│
├── config/                             # Centralized Declarative Configurations
│   ├── config.yaml                     # Database, Seeds, and Preprocessing Directories
│   ├── data_generation.yaml            # Synthetic Hazard & Diurnal Parameters
│   └── routes_config.yaml              # Route Catalogue, Scoring Weights & CB Thresholds
│
├── dashboard/                          # Streamlit Multi-Page Client Application
│   ├── components/                     # Reusable UI Widgets
│   │   ├── __init__.py                 # Component Exports
│   │   ├── charts.py                   # TreeSHAP & Candidate Ranking Visualizers
│   │   ├── explanation.py              # Local Attribution Section Cards
│   │   ├── metrics_cards.py            # KPI & Status Badges
│   │   └── route_table.py              # Formatted Comparison Tables
│   ├── pages/                          # Multipage Screens
│   │   ├── 1_⚡_Live_Payment_Simulator.py  # Interactive Transaction Tester & Execution
│   │   ├── 2_🧠_Smart_Routing_Console.py   # Multi-Objective Scoring Breakdown
│   │   ├── 3_🩺_Gateway_Health_Monitor.py  # Real-Time Telemetry & Outage Simulator
│   │   └── 4_📊_Model_Analytics.py         # Evaluation Curves & Business ROI Reports
│   ├── api_client.py                   # Centralized HTTP Client for FastAPI
│   └── app.py                          # Streamlit Landing Portal & Architecture
│
├── data/                               # Data Assets
│   ├── raw/payments_synthetic.csv      # 100,000 Synthetic Payment Transactions
│   └── processed/                      # EDA Figures and 10 ML Result Artifacts
│       ├── eda/                        # 10 Phase-2 EDA Plots
│       └── ml_results/                 # 10 Phase-3 Evaluation Curves
│
├── database/                           # Relational Persistence Layer
│   ├── db_manager.py                   # Parameterized SQLite Repository Methods
│   ├── init_db.py                      # SQLite Initialization CLI
│   ├── payroute.db                     # SQLite Database File
│   └── schema.sql                      # DDL Schema with Foreign Keys & Indices
│
├── docs/                               # Comprehensive Technical Documentation
│   ├── ablation_study.md               # 4-Variant Routing Policy Ablation Report
│   ├── architecture.md                 # System Architecture Specification & Mermaid Diagrams
│   ├── circuit_breaker.md              # 3-State Dynamic Circuit Breaker Specification
│   ├── demo_script.md                  # 5-Minute Live Interview Demonstration Script
│   ├── future_architecture.md          # Production Microservices Roadmap
│   ├── interview_guide.md              # 29 Technical Interview Questions & Model Answers
│   ├── ml_results.md                   # Stage-1 & Stage-2 Test Set Evaluation Report
│   ├── performance_test.md             # Local API Response Latency Report
│   ├── project_pitch.md                # 60-Second Verbal Elevator Pitch
│   ├── project_structure.md            # Clean Project Structure & Index
│   ├── project_summary.md              # 1-Page Executive Project Summary
│   ├── resume_bullets.md               # Metrics-Driven Resume Bullet Points
│   ├── system_audit.md                 # Complete System Audit & Data Flow
│   └── test_report.md                  # Consolidated 41-Test QA Report
│
├── models/                             # Serialized Model Artifacts
│   ├── calibrated_failure_model.joblib # Isotonic Calibrated GBDT Predictor
│   ├── failure_model.joblib            # Base HistGradientBoostingClassifier
│   ├── feature_metadata.json           # Categorical Encodings & Decision Threshold (T=0.20)
│   ├── model_metrics.json              # Validation & Test Evaluation Metrics
│   ├── preprocessor.joblib             # Fitted Scikit-Learn ColumnTransformer
│   └── reason_model.joblib             # 5-Class Failure Reason Diagnoser
│
├── notebooks/                          # Interactive Jupyter Notebooks
│   ├── 02_exploratory_data_analysis.ipynb
│   ├── 03_model_training_and_calibration.ipynb
│   └── 04_smart_routing_simulation.ipynb
│
├── src/                                # Core Source Code
│   ├── data_generator/                 # Synthetic Data Generation
│   │   ├── distributions.py            # Log-Normal Amounts & Diurnal Curve Logic
│   │   └── generator.py                # 100k Transaction Generator CLI
│   ├── features/                       # Feature Engineering & Preprocessing
│   │   ├── build_features.py           # Scikit-Learn Pipeline & Chronological Split
│   │   ├── encoders.py                 # Custom Scikit-Learn Transformers
│   │   └── run_eda.py                  # Automated EDA Runner
│   ├── ml/                             # Machine Learning Engine
│   │   ├── evaluate.py                 # Evaluation & Plot Generation Runner
│   │   ├── explainer.py                # TreeSHAP & Gradient Local Feature Attribution
│   │   ├── predictor.py                # Real-time Inference Wrapper (<5ms)
│   │   └── train.py                    # End-to-end Training & Calibration Pipeline
│   ├── router/                         # Smart Routing & Reliability Layer
│   │   ├── ablation.py                 # 4-Model Policy Ablation Runner
│   │   ├── candidate_filter.py         # Route Compatibility & State Filtering
│   │   ├── circuit_breaker.py          # 3-State Dynamic Circuit Breaker State Machine
│   │   ├── router.py                   # SmartRouter Orchestrator
│   │   ├── scorer.py                   # Multi-Objective Utility Scorer & Tie-Breaking
│   │   └── simulator.py                # Outage Benchmark Simulation Runner
│   └── utils/                          # Shared Utilities
│       └── logger.py                   # Structured Colored Logging
│
├── tests/                              # Automated Test Suite (41 Tests)
│   ├── test_api_endpoints.py           # FastAPI Controller Tests
│   ├── test_dashboard_client.py        # Streamlit API Client Tests
│   ├── test_data_generator.py          # Synthetic Generator Tests
│   ├── test_database.py                # SQLite Schema & Repository Tests
│   ├── test_feature_pipeline.py        # Feature Pipeline Tests
│   ├── test_ml_pipeline.py             # ML Predictor & Calibration Tests
│   └── test_smart_router.py            # Smart Router & Circuit Breaker Tests
│
├── .gitignore                          # Git Exclusions
├── README.md                           # Comprehensive GitHub Landing Documentation
└── requirements.txt                    # Pinned Python Dependencies
```
