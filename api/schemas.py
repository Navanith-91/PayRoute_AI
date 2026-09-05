"""
Pydantic v2 Request and Response Schemas for the PayRoute AI FastAPI Backend.
Includes robust input validation, field descriptions, and clean defaults.
"""

from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field, field_validator


class PaymentContextInput(BaseModel):
    """Incoming payment transaction context with validation and sensible defaults."""

    transaction_id: Optional[str] = Field(
        default=None,
        description="Unique transaction reference ID (auto-generated if omitted).",
        examples=["txn_987654"],
    )
    amount: float = Field(
        default=1500.0,
        gt=0,
        description="Transaction amount in local currency (must be positive).",
        examples=[1500.0],
    )
    currency: str = Field(
        default="INR",
        description="Three-letter ISO currency code.",
        examples=["INR"],
    )
    payment_method: str = Field(
        default="UPI",
        description="Payment rail / instrument.",
        examples=["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"],
    )
    bank: str = Field(
        default="HDFC",
        description="Customer's issuing bank.",
        examples=["HDFC", "SBI", "ICICI", "AXIS"],
    )
    merchant_id: Optional[str] = Field(
        default="m_ecom_01",
        description="Registered merchant identifier.",
        examples=["m_ecom_01"],
    )
    merchant_category: str = Field(
        default="ECOMMERCE",
        description="Merchant MCC classification.",
        examples=["ECOMMERCE", "FOOD", "TRAVEL", "UTILITIES", "ENTERTAINMENT", "HEALTHCARE", "EDUCATION"],
    )
    hour: int = Field(
        default=14,
        ge=0,
        le=23,
        description="Hour of the day in 24-hour format (0-23).",
    )
    day_of_week: int = Field(
        default=2,
        ge=0,
        le=6,
        description="Day of week (0=Monday, 6=Sunday).",
    )
    device_type: str = Field(
        default="MOBILE",
        description="Client hardware form factor.",
        examples=["MOBILE", "DESKTOP", "TABLET"],
    )
    network_type: str = Field(
        default="4G",
        description="User connectivity network.",
        examples=["4G", "5G", "WIFI", "3G", "2G"],
    )
    customer_age_days: int = Field(
        default=180,
        ge=0,
        description="Customer account tenure in days.",
    )
    previous_transactions: int = Field(
        default=10,
        ge=0,
        description="Total lifetime transactions completed by customer.",
    )
    previous_failed_transactions: int = Field(
        default=0,
        ge=0,
        description="Total lifetime failed transactions for customer.",
    )
    previous_attempts: int = Field(
        default=0,
        ge=0,
        description="Prior immediate retry attempts for this payment session.",
    )
    transaction_velocity: int = Field(
        default=1,
        ge=0,
        description="Transactions attempted within the last 10 minutes.",
    )
    is_new_device: int = Field(
        default=0,
        ge=0,
        le=1,
        description="1 if device fingerprint is unrecognized, 0 otherwise.",
    )
    bank_latency_ms: Optional[int] = Field(
        default=150,
        ge=0,
        description="Real-time bank processing latency in milliseconds.",
    )
    gateway_latency_ms: Optional[int] = Field(
        default=80,
        ge=0,
        description="Real-time gateway processing latency in milliseconds.",
    )
    bank_success_rate: Optional[float] = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Rolling bank success rate [0.0 - 1.0].",
    )
    gateway_success_rate: Optional[float] = Field(
        default=0.96,
        ge=0.0,
        le=1.0,
        description="Rolling gateway success rate [0.0 - 1.0].",
    )

    @field_validator("payment_method", mode="before")
    @classmethod
    def validate_payment_method(cls, v: Any) -> str:
        s = str(v).upper().strip()
        allowed = {"UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"}
        if s not in allowed:
            raise ValueError(f"Invalid payment_method '{v}'. Must be one of {allowed}")
        return s

    @field_validator("bank", mode="before")
    @classmethod
    def validate_bank(cls, v: Any) -> str:
        s = str(v).upper().strip()
        allowed = {"HDFC", "SBI", "ICICI", "AXIS"}
        if s not in allowed:
            raise ValueError(f"Invalid bank '{v}'. Supported simulated banks: {allowed}")
        return s

    def to_dict(self) -> Dict[str, Any]:
        """Exports dictionary with generated transaction_id if missing."""
        d = self.model_dump()
        if not d.get("transaction_id"):
            d["transaction_id"] = f"txn_{uuid.uuid4().hex[:12]}"
        return d


class FeatureImpactSchema(BaseModel):
    """Feature attribution contributor."""
    feature: str = Field(description="Engineered feature key.")
    name: str = Field(description="Human-readable business name.")
    impact: float = Field(description="Attribution magnitude / directional SHAP score.")
    direction: str = Field(description="RISK_INCREASING or PROTECTIVE.")


class PredictionResponseSchema(BaseModel):
    """Response payload for payment failure prediction."""
    transaction_id: str
    failure_probability: float
    success_probability: float
    risk_level: str
    is_high_risk: bool
    decision_threshold: float
    predicted_failure_reason: Optional[str] = None
    reason_probabilities: Optional[Dict[str, float]] = None
    top_risk_factors: Optional[List[FeatureImpactSchema]] = None
    top_protective_factors: Optional[List[FeatureImpactSchema]] = None


class CandidateRouteSchema(BaseModel):
    """Scored candidate route evaluation."""
    route_id: str
    route_name: Optional[str] = None
    gateway: str
    bank: str
    failure_probability: float
    success_probability: float
    risk_level: str
    expected_latency_ms: int
    base_fee_pct: float
    rolling_health: float
    circuit_state: str
    utility_score: float


class ExcludedCandidateSchema(BaseModel):
    """Candidate excluded during filtering."""
    route_id: str
    reason: str


class RoutingRecommendationResponseSchema(BaseModel):
    """Response payload for smart routing recommendation."""
    status: str
    transaction_id: str
    primary_route: Optional[str] = None
    fallback_route: Optional[str] = None
    routing_strategy: str
    primary_predicted_success_prob: Optional[float] = None
    primary_predicted_failure_prob: Optional[float] = None
    primary_utility_score: Optional[float] = None
    primary_circuit_state: Optional[str] = None
    candidates: List[CandidateRouteSchema] = []
    excluded_candidates: List[ExcludedCandidateSchema] = []
    explanation: Optional[Dict[str, Any]] = None


class TransactionExecuteRequestSchema(BaseModel):
    """Request payload to execute and simulate a payment transaction."""
    payment_request: PaymentContextInput
    preferred_route: Optional[str] = Field(
        default=None,
        description="Optional manual route override. If omitted, SmartRouter selects optimal route.",
    )
    simulate_outage: Optional[bool] = Field(
        default=False,
        description="If True, injects high failure latency on the selected route.",
    )


class TransactionExecuteResponseSchema(BaseModel):
    """Result of executed payment simulation."""
    transaction_id: str
    status: str = Field(description="SUCCESS or FAILED.")
    payment_status: int = Field(description="0 for success, 1 for failed.")
    selected_route: Optional[str] = None
    routing_strategy: str
    latency_ms: int
    failure_reason: Optional[str] = None
    circuit_state: Optional[str] = None
    created_at: Optional[str] = None


class GatewayHealthRouteSchema(BaseModel):
    """Real-time circuit breaker and health telemetry for a single route."""
    route_id: str
    circuit_state: str
    rolling_success_rate: float
    rolling_failure_rate: float
    median_latency_ms: float
    total_transactions: int
    total_failures: int
    tripped_at: Optional[float] = None


class GatewayHealthResponseSchema(BaseModel):
    """System-wide gateway health overview."""
    routes: List[GatewayHealthRouteSchema]
    timestamp: str


class AnalyticsSummaryResponseSchema(BaseModel):
    """Aggregated platform metrics and routing statistics."""
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    overall_success_rate_pct: float
    overall_failure_rate_pct: float
    average_amount: float
    average_latency_ms: float
    gateways_count: int
    merchants_count: int
    routing_decisions_recorded: int


class ExplanationResponseSchema(BaseModel):
    """Feature attribution breakdown for a specific transaction."""
    transaction_id: str
    selected_route: str
    failure_probability: float
    routing_strategy: str
    predicted_failure_reason: Optional[str] = None
    top_risk_contributors: List[FeatureImpactSchema] = []
    top_protective_factors: List[FeatureImpactSchema] = []


class UserRegisterRequestSchema(BaseModel):
    """Request payload for user registration."""
    email: str = Field(description="User email address.", examples=["user@company.com"])
    password: str = Field(min_length=6, description="Password with minimum 6 characters.")
    full_name: str = Field(min_length=1, description="User full display name.", examples=["Rohan Sharma"])
    organization: Optional[str] = Field(default="Independent Merchant", description="Merchant or Organization name.")
    role: Optional[str] = Field(default="MERCHANT_ADMIN", description="User role.")


class UserLoginRequestSchema(BaseModel):
    """Request payload for user authentication / login."""
    email: str = Field(description="User email address.", examples=["admin@payroute.ai"])
    password: str = Field(description="User password.")


class UserResponseSchema(BaseModel):
    """Sanitized user profile response without credentials."""
    user_id: str
    email: str
    full_name: str
    organization: Optional[str] = None
    role: str
    created_at: Optional[str] = None


class AuthTokenResponseSchema(BaseModel):
    """Authentication success payload with token and user details."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponseSchema


class DecisionPolicyResultSchema(BaseModel):
    """Structured decision policy recommendation."""
    action: str = Field(description="Policy action (PROCESS_NOW, SWITCH_ROUTE, WAIT_AND_RETRY, USE_ALTERNATIVE_PAYMENT_METHOD, NO_ROUTE_AVAILABLE)")
    title: str
    message: str
    recommended_route: Optional[str] = None
    original_route: Optional[str] = None
    fallback_route: Optional[str] = None
    expected_success_prob: float
    expected_latency_ms: int
    success_uplift_pct: Optional[float] = None
    latency_reduction_ms: Optional[int] = None
    alternative_payment_method: Optional[str] = None
    suggested_wait_seconds: int = 0
    key_drivers: List[str] = []


class InfrastructureStatusSchema(BaseModel):
    """Real-time infrastructure context."""
    traffic_level: str
    active_scenario: str
    scenario_description: str
    bank: str
    payment_method: str


class RiskAssessmentSummarySchema(BaseModel):
    """Summarized risk assessment for pre-payment analysis."""
    failure_probability: float
    success_probability: float
    risk_level: str
    predicted_reason: Optional[str] = None
    decision_threshold: float


class CandidateRouteDetailSchema(BaseModel):
    """Candidate route evaluation with load and health telemetry."""
    route_id: str
    route_name: str
    gateway: str
    bank: str
    expected_latency_ms: int
    base_fee_pct: float
    rolling_health: float
    circuit_state: str
    current_load: float
    load_level: str
    route_status: str
    failure_probability: float
    success_probability: float
    risk_level: str
    utility_score: Optional[float] = None


class PaymentAnalysisResponseSchema(BaseModel):
    """Unified pre-payment real-time analysis response."""
    transaction_id: str
    risk: RiskAssessmentSummarySchema
    infrastructure: InfrastructureStatusSchema
    decision: DecisionPolicyResultSchema
    method_alternatives: Dict[str, float] = {}
    routes: List[CandidateRouteDetailSchema] = []
    excluded_routes: List[Dict[str, str]] = []
    explanation: Optional[Dict[str, Any]] = None


class PaymentProcessRequestSchema(BaseModel):
    """Payload to execute payment transaction."""
    amount: float = Field(default=1000.0, ge=1.0, description="Amount in INR.")
    currency: str = Field(default="INR")
    payment_method: str = Field(default="UPI")
    bank: str = Field(default="HDFC")
    merchant_category: str = Field(default="ECOMMERCE")
    device_type: str = Field(default="MOBILE")
    network_type: str = Field(default="4G")
    preferred_route: Optional[str] = Field(default=None, description="Manually specified route ID or None for AI optimal.")
    simulate_forced_failure: bool = Field(default=False, description="Simulate provider error for testing circuit breaker.")


class PaymentProcessResponseSchema(BaseModel):
    """Payment transaction execution response."""
    transaction_id: str
    status: str  # SUCCESS / FAILED
    payment_status: int  # 0 or 1
    failure_reason: Optional[str] = None
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    latency_ms: int
    amount: float
    bank: str
    payment_method: str
    decision_action: Optional[str] = None
    circuit_state: str
    analysis: Optional[PaymentAnalysisResponseSchema] = None


class ScenarioInjectionRequestSchema(BaseModel):
    """Payload to activate a simulation scenario."""
    scenario: str = Field(description="NORMAL, HIGH_TRAFFIC, BANK_DEGRADATION, GATEWAY_OUTAGE, UPI_CONGESTION, FLASH_SALE")
    target_bank: Optional[str] = Field(default="SBI")
    target_gateway: Optional[str] = Field(default="RAZORPAY_SIM")


class ScenarioInjectionResponseSchema(BaseModel):
    """Response confirming applied demo scenario."""
    scenario: str
    target_bank: str
    target_gateway: str
    description: str


class SystemStatusResponseSchema(BaseModel):
    """System-wide infrastructure health, load, and session KPI overview."""
    active_scenario: str
    scenario_description: str
    routes: List[Dict[str, Any]]
    session_kpis: Dict[str, Any]
    timestamp: str


class EventFeedResponseSchema(BaseModel):
    """Stream of recent routing and infrastructure events."""
    events: List[Dict[str, Any]]
    total_events: int


class TimelineStageSchema(BaseModel):
    """Single stage in the transaction lifecycle timeline."""
    stage: str
    status: str
    icon: str
    detail: str


class TransactionStatusResponseSchema(BaseModel):
    """Comprehensive transaction lifecycle status and timeline response."""
    transaction_id: str
    status: str  # SUCCESS, PENDING, FAILED, REFUND_INITIATED
    amount: float
    currency: str = "INR"
    payment_method: str
    bank: str
    route_id: Optional[str] = None
    customer_debit_status: str  # CONFIRMED, PENDING, FAILED, REVERSED
    merchant_confirmation_status: str  # CONFIRMED, PENDING, FAILED
    failure_reason: Optional[str] = None
    created_at: str
    updated_at: str
    message: str
    timeline: List[TimelineStageSchema]


# =============================================================================
# Gateway Credentials & Settings Schemas
# =============================================================================

class GatewayCredentialSchema(BaseModel):
    """Configured credentials and health status for a payment gateway provider."""
    provider_id: str  # RAZORPAY, PHONEPE, GPAY
    provider_name: str
    environment: str = "SANDBOX"  # SANDBOX, PRODUCTION
    api_key_id: Optional[str] = None
    api_key_secret: Optional[str] = None  # Masked when returned
    merchant_id: Optional[str] = None
    salt_key: Optional[str] = None  # Masked
    salt_index: Optional[str] = "1"
    webhook_secret: Optional[str] = None  # Masked
    merchant_vpa: Optional[str] = None
    is_enabled: int = 1
    last_tested_at: Optional[str] = None
    test_status: str = "UNCONFIGURED"  # CONNECTED, FAILED, UNCONFIGURED
    latency_ms: int = 0


class GatewayCredentialUpdateSchema(BaseModel):
    """Payload to update credentials for a payment gateway."""
    provider_name: Optional[str] = None
    environment: str = "SANDBOX"
    api_key_id: Optional[str] = None
    api_key_secret: Optional[str] = None
    merchant_id: Optional[str] = None
    salt_key: Optional[str] = None
    salt_index: Optional[str] = "1"
    webhook_secret: Optional[str] = None
    merchant_vpa: Optional[str] = None
    is_enabled: int = 1


class GatewayTestConnectionResponseSchema(BaseModel):
    """Result of an active gateway connection probe."""
    provider_id: str
    success: bool
    status: str
    message: str
    latency_ms: int
    environment: str = "SANDBOX"


class TransactionItemSchema(BaseModel):
    """Single transaction record in the audit data table."""
    transaction_id: str
    amount: float
    currency: str = "INR"
    payment_method: str
    bank: str
    route_id: Optional[str] = None
    payment_status: int
    lifecycle_status: str
    customer_debit_status: str
    merchant_confirmation_status: str
    failure_reason: Optional[str] = None
    bank_latency_ms: int
    gateway_latency_ms: int
    created_at: str


class TransactionListResponseSchema(BaseModel):
    """Paginated list of all recorded transactions."""
    transactions: List[TransactionItemSchema]
    total: int
    limit: int
    offset: int




