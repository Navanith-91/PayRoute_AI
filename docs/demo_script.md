# PayRoute AI — 5-Minute Live Interview Demonstration Script

*Step-by-step walkthrough for demonstrating PayRoute AI live to a technical interviewer.*

---

## ⏱️ Timeline & Action Script

### 0:00 – 0:45 | Introduction & Problem Context
* **Screen**: Main Dashboard Landing Page (`http://localhost:8501`).
* **Talking Points**:
  - *"Welcome! Electronic transactions often fail due to sudden bank outages, network drops, or gateway spikes. PayRoute AI is an intelligent routing prototype that predicts transaction failure and isolates unhealthy routes before money is lost."*
  - Point to the live FastAPI connection badge (🟢 Online) and SQLite integration.

---

### 0:45 – 1:45 | Page 1: Live Payment Simulator (Healthy Transaction)
* **Screen**: Navigate to **⚡ Live Payment Simulator**.
* **Action**:
  1. Click **`Scenario 1: Healthy UPI Payment`** (₹350, HDFC, 5G).
  2. Click **`🔍 1. Predict Failure Risk`**.
  3. Point out: Failure probability ($5.4\%$), `LOW RISK` badge, and local TreeSHAP attribution chart showing positive infrastructure health factors.
  4. Click **`🧠 2. Find Best Route`**.
  5. Show: `ROUTE_HDFC_RAZORPAY` selected as primary, with `ROUTE_HDFC_CASHFREE` as fallback.
  6. Click **`💳 3. Execute Simulated Payment`**.
  7. Show: Instant `SUCCESS` balloon banner, observed $145\text{ms}$ latency, and generated SQLite transaction ID.

---

### 1:45 – 2:45 | Page 1: High-Risk Detection & Failure Diagnosis
* **Action**:
  1. Click **`Scenario 2: High-Risk Degraded Session`** (₹18,500, SBI, 2G, 3 Retries, New Device).
  2. Click **`🔍 1. Predict Failure Risk`**.
  3. Point out: Failure probability spikes to **$100\%$**, risk level shifts to **`HIGH RISK`**, and the Stage-2 Diagnoser identifies `NETWORK_DROP` as the primary cause.
  4. Point to the local SHAP attribution chart highlighting retries, network type, and velocity as key risk drivers.

---

### 2:45 – 3:45 | Page 3: Gateway Health & Outage Injection (Circuit Breakers)
* **Screen**: Navigate to **🩺 Gateway Health Monitor**.
* **Action**:
  1. Review the live telemetry grid showing all 10 routes in **`CLOSED (🟢)`** state.
  2. Scroll down to **Interactive Outage Simulator**.
  3. Select route **`ROUTE_SBI_DIRECT`** and click **`🔴 1. Inject Outage & Trip Circuit`**.
  4. Point out: The circuit breaker instantly trips to **`OPEN (🔴)`** after detecting a rolling failure rate $\ge 40\%$.
  5. Navigate back to Page 1 and query SBI NetBanking: show that `ROUTE_SBI_DIRECT` is now **strictly excluded** from candidate routes and traffic has seamlessly cascaded to `ROUTE_SBI_RAZORPAY`.
  6. Return to Page 3 and click **`🟢 2. Send Recovery Probe`** to show transition to **`HALF_OPEN (🟡)`** $\rightarrow$ **`CLOSED (🟢)`**.

---

### 3:45 – 4:30 | Page 2: Smart Routing Console (Scoring & Ranking)
* **Screen**: Navigate to **🧠 Smart Routing Console**.
* **Talking Points**:
  - Explain the multi-objective utility formula:
    $$\text{Score}_i = 0.60 \cdot P(\text{Success}_i) - 0.20 \cdot \widetilde{\text{Latency}}_i - 0.10 \cdot \widetilde{\text{Cost}}_i + 0.10 \cdot \text{Health}_i$$
  - Point to the live candidate ranking bar chart demonstrating that utility balances success, latency, fees, and telemetry rather than just picking the lowest failure probability.

---

### 4:30 – 5:00 | Page 4: Model Analytics & Business ROI Wrap-up
* **Screen**: Navigate to **📊 Model Analytics & ROI**.
* **Talking Points**:
  - *"In an identical 3,000-transaction outage benchmark against naive static routing, PayRoute AI delivered a **+6.40% success rate uplift** and recovered **198 payment failures**, while reducing mean latency by **60.5ms**."*
  - Show the Isotonic calibration curve reducing Brier error by $45.6\%$, and the cost-optimal decision threshold ($T^* = 0.20$).
  - Conclude: *"The entire system is modular, backed by 41 passing automated tests, and ready to scale."*
