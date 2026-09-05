# PayRoute AI — Feature Dictionary & Data Governance Specification

This document defines every feature in the PayRoute AI data architecture, its temporal availability relative to payment execution, and whether it is permitted in the Machine Learning feature space to prevent data leakage.

---

## 🛡️ Data Leakage & Availability Governance

In real-world payment infrastructure, the feature store must strictly distinguish between:
1. **Pre-Transaction Request Context** (known when the user clicks "Pay"): Device, amount, merchant category, network, customer history.
2. **Pre-Transaction Infrastructure Telemetry** (known via background health checks & rolling heartbeat logs): Real-time rolling bank success rate, rolling gateway success rate, estimated median latency.
3. **In-Flight / Simulated Route Latency**: Measured latency for the selected route. (For ML pre-routing evaluation, the router passes historical/estimated latency of candidate routes).
4. **Post-Transaction Outcome** (known only AFTER payment completes): `payment_status`, `failure_reason`, actual observed latency.

> [!CAUTION]
> **Strict Anti-Leakage Rules**:
> - `payment_status` is the **Target Variable** and must NEVER appear in the feature matrix $X$.
> - `failure_reason` is generated ONLY after a transaction fails and must NEVER be used to predict `payment_status`.
> - Customer historical features (`historical_failure_rate`) must use only prior transactions, strictly excluding the current attempt.

---

## 📋 Comprehensive Feature Specification

| Feature Name | Category | Data Type | Available Before Payment? | Used in ML ($X$)? | Description & Transformation Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `transaction_id` | Metadata | String | Yes | ❌ No | Unique primary key (e.g. `txn_00000001`). Excluded to prevent overfitting to ID sequence. |
| `currency` | Metadata | String | Yes | ❌ No | Fixed currency (`INR`). Zero variance in prototype. |
| `created_at` | Metadata | Timestamp | Yes | ❌ No | Absolute timestamp. Used for chronological partitioning, not direct model input. |
| **`payment_status`** | **Target** | **Binary (0/1)** | **No (Post-Outcome)** | **❌ Target ($y$)** | $0 = \text{SUCCESS}$, $1 = \text{FAILED}$. Supervised binary classification target. |
| **`failure_reason`** | **Target Diagnostic** | **Categorical** | **No (Post-Outcome)** | **❌ Excluded** | Root cause diagnostic (`BANK_DOWNTIME`, `GATEWAY_TIMEOUT`, `USER_AUTHENTICATION_ERROR`, `INSUFFICIENT_FUNDS`, `NETWORK_DROP`). Used only for Stage-2 post-failure diagnostics. |
| `payment_method` | Raw Categorical | String | Yes | ✅ Yes | `UPI`, `CREDIT_CARD`, `DEBIT_CARD`, `NET_BANKING`. One-hot encoded. |
| `bank` | Raw Categorical | String | Yes | ✅ Yes | Issuing bank: `HDFC`, `SBI`, `ICICI`, `AXIS`. One-hot encoded. |
| `merchant_category` | Raw Categorical | String | Yes | ✅ Yes | Merchant domain: `ECOMMERCE`, `FOOD`, `TRAVEL`, `UTILITIES`, `ENTERTAINMENT`, `HEALTHCARE`, `EDUCATION`. One-hot encoded. |
| `device_type` | Raw Categorical | String | Yes | ✅ Yes | Client hardware form-factor: `MOBILE`, `DESKTOP`, `TABLET`. One-hot encoded. |
| `network_type` | Raw Categorical | String | Yes | ✅ Yes | Connection quality: `5G`, `4G`, `WIFI`, `3G`, `2G`. One-hot encoded. |
| `hour` | Raw Temporal | Integer ($0-23$) | Yes | 🔄 Engineered | Raw hour. Transformed into `hour_sin` and `hour_cos` to preserve circular 24h continuity. |
| `day_of_week` | Raw Temporal | Integer ($0-6$) | Yes | 🔄 Engineered | Raw day. Transformed into `day_sin` and `day_cos` to preserve weekly continuity. |
| `hour_sin`, `hour_cos` | Engineered Temporal | Float | Yes | ✅ Yes | $\sin(2\pi h / 24)$ and $\cos(2\pi h / 24)$. Captures diurnal maintenance and traffic peaks. |
| `day_sin`, `day_cos` | Engineered Temporal | Float | Yes | ✅ Yes | $\sin(2\pi d / 7)$ and $\cos(2\pi d / 7)$. Captures weekend vs weekday payment patterns. |
| `customer_age_days` | Raw Customer | Integer | Yes | 🔄 Engineered | Days since customer profile creation. |
| `account_maturity_years` | Engineered Customer | Float | Yes | ✅ Yes | `customer_age_days / 365.0`. Standardized account age. |
| `previous_transactions` | Raw Customer | Integer | Yes | 🔄 Engineered | Total prior transactions completed by customer. |
| `previous_failed_transactions` | Raw Customer | Integer | Yes | 🔄 Engineered | Total prior failed transactions for customer. |
| `historical_failure_rate` | Engineered Customer | Float | Yes | ✅ Yes | $\frac{\text{previous\_failed}}{\text{previous\_tx} + 1.0}$. Laplace-smoothed user-level failure propensity. |
| `previous_attempts` | Raw Session | Integer ($0-4$) | Yes | 🔄 Engineered | Number of prior failed attempts in current session. |
| `retry_risk` | Engineered Session | Float | Yes | ✅ Yes | $\log(1 + \text{previous\_attempts})$. Captures non-linear retry fatigue. |
| `transaction_velocity` | Raw Customer | Integer | Yes | 🔄 Engineered | Transactions initiated in rolling 1-hour window. |
| `velocity_log` | Engineered Customer | Float | Yes | ✅ Yes | $\log(1 + \text{transaction\_velocity})$. Normalized transaction burst score. |
| `is_new_device` | Raw Security | Binary ($0/1$) | Yes | ✅ Yes | Flag indicating whether device was seen previously for this customer profile. |
| `amount` | Raw Financial | Float | Yes | 🔄 Engineered | Transaction monetary value in INR. |
| `amount_log` | Engineered Financial | Float | Yes | ✅ Yes | $\log(1 + \text{amount})$. Normalizes heavy right-tailed financial distributions. |
| `high_ticket_new_device` | Engineered Security | Binary ($0/1$) | Yes | ✅ Yes | Interaction term: $(\text{amount} \ge 10,000) \land (\text{is\_new\_device} == 1)$. Captures high-scrutiny auth risk. |
| `bank_latency_ms` | Infrastructure | Integer | Yes (Telemetry) | 🔄 Engineered | Estimated/observed bank processing latency in ms. |
| `gateway_latency_ms` | Infrastructure | Integer | Yes (Telemetry) | 🔄 Engineered | Estimated/observed gateway hop latency in ms. |
| `total_latency_ms` | Engineered Infra | Float | Yes (Telemetry) | ✅ Yes | $\text{bank\_latency} + \text{gateway\_latency}$. Cumulative network & processing delay. |
| `latency_ratio` | Engineered Infra | Float | Yes (Telemetry) | ✅ Yes | $\frac{\text{gateway\_latency}}{\max(10, \text{bank\_latency})}$. Identifies gateway bottlenecks relative to the bank. |
| `bank_success_rate` | Infrastructure | Float ($0-1$) | Yes (Telemetry) | 🔄 Engineered | Real-time rolling 5-minute success rate of the issuing bank. |
| `gateway_success_rate` | Infrastructure | Float ($0-1$) | Yes (Telemetry) | 🔄 Engineered | Real-time rolling 5-minute success rate of the payment gateway. |
| `combined_route_health` | Engineered Infra | Float ($0-1$) | Yes (Telemetry) | ✅ Yes | $\text{bank\_success\_rate} \times \text{gateway\_success\_rate}$. Composite route reliability score. |
| `health_deficit` | Engineered Infra | Float | Yes (Telemetry) | ✅ Yes | $(1 - \text{bank\_success\_rate}) + (1 - \text{gateway\_success\_rate})$. Aggregate degradation penalty. |

---

## 🔬 Summary of Feature Transformations in Pipeline

```text
Raw Features In (20 fields)
├── Categoricals (5) -> OneHotEncoder(handle_unknown="ignore")
│   ├── payment_method (4 classes)
│   ├── bank (4 classes)
│   ├── merchant_category (7 classes)
│   ├── device_type (3 classes)
│   └── network_type (5 classes)
│       └── Output: 23 binary dummy features
│
├── Temporal (2) -> CyclicTemporalTransformer -> StandardScaler
│   ├── hour -> [hour_sin, hour_cos]
│   └── day_of_week -> [day_sin, day_cos]
│       └── Output: 4 continuous scaled features
│
├── Customer Behavior (5) -> CustomerBehaviorTransformer -> StandardScaler
│   └── [historical_failure_rate, retry_risk, velocity_log, account_maturity_years]
│       └── Output: 4 continuous scaled features
│
├── Infrastructure Health (4) -> InfrastructureHealthTransformer -> StandardScaler
│   └── [total_latency_ms, latency_ratio, combined_route_health, health_deficit]
│       └── Output: 4 continuous scaled features
│
└── Amount & Risk (2) -> AmountRiskTransformer -> StandardScaler
    └── [amount_log, high_ticket_new_device]
        └── Output: 2 continuous/scaled features
─────────────────────────────────────────────────────────────
Total Output Dimensionality: 37 Scaled Feature Columns for ML
```
