# PayRoute AI — 60-Second Verbal Project Pitch

*Designed for technical recruiters, engineering hiring managers, and interview introductions.*

---

## 🎯 The Pitch (45–60 Seconds)

> "In digital payment platforms, 12 to 18 percent of transactions fail due to bank downtime, gateway latency, network degradation, and session drop-offs. When providers degrade, static and naive routing algorithms keep sending traffic into failing routes, causing massive revenue loss and checkout abandonment.
>
> To solve this, I built **PayRoute AI** — an end-to-end payment reliability prototype inspired by systems like Razorpay. 
>
> The platform uses a calibrated Gradient Boosted Decision Tree to predict real-time failure probabilities with Isotonic calibration, cutting probability error by 45%. It then uses a multi-objective utility scoring algorithm that dynamically evaluates candidate routes across success rate, latency, fees, and telemetry. When a provider degrades, dynamic 3-state circuit breakers automatically trip to isolate the failing route and cascade traffic to fallbacks, testing recovery with probe traffic.
>
> In a 3,000-transaction outage benchmark, PayRoute AI achieved a **+6.40% success rate uplift**, prevented **198 payment failures**, and reduced average latency by **60.5 milliseconds**. The entire system is exposed via a sub-35ms FastAPI backend and an interactive 4-page Streamlit dashboard, validated by 41 automated tests."
