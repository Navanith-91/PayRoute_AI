import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.utils.auth import hash_password, verify_password
from src.utils.logger import get_logger

logger = get_logger("DatabaseManager")



class DatabaseManager:
    """
    Manages SQLite database connections, schema setup, and bulk data operations.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initializes DatabaseManager with target SQLite database path.

        Args:
            db_path: Path to .db file. If None, defaults to database/payroute.db.
        """
        if db_path is None:
            default_dir = Path(__file__).resolve().parent
            self.db_path = str(default_dir / "payroute.db")
        else:
            self.db_path = db_path

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self, schema_file: Optional[str] = None) -> None:
        """
        Executes schema.sql DDL to create database tables and indices, and seeds baseline records.

        Args:
            schema_file: Path to schema.sql. If None, looks in default database/ directory.
        """
        if schema_file is None:
            schema_path = Path(__file__).resolve().parent / "schema.sql"
        else:
            schema_path = Path(schema_file)

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at: {schema_path}")

        logger.info(f"Applying schema from {schema_path} to {self.db_path}...")
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl = f.read()

        with self.get_connection() as conn:
            conn.executescript(ddl)
            conn.commit()

        logger.info("Database schema initialized successfully.")
        self.seed_initial_entities()


    def seed_initial_entities(self) -> None:
        """
        Inserts baseline gateways and sample merchants into the database.
        """
        gateways = [
            ("RAZORPAY_SIM", "Razorpay Simulated Engine", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.50, 1),
            ("CASHFREE_SIM", "Cashfree Simulated Aggregator", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.40, 1),
            ("PAYU_SIM", "PayU Simulated Gateway", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.45, 1),
            ("DIRECT_BANK", "Direct Bank Integration Node", json.dumps(["NET_BANKING", "UPI"]), 1.10, 1),
            # Seed Route IDs to satisfy foreign key constraints
            ("ROUTE_HDFC_RAZORPAY", "HDFC via Razorpay", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.50, 1),
            ("ROUTE_HDFC_CASHFREE", "HDFC via Cashfree", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.35, 1),
            ("ROUTE_HDFC_PAYU", "HDFC via PayU", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.40, 1),
            ("ROUTE_SBI_RAZORPAY", "SBI via Razorpay", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.50, 1),
            ("ROUTE_SBI_CASHFREE", "SBI via Cashfree", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.38, 1),
            ("ROUTE_SBI_DIRECT", "SBI Direct Bank", json.dumps(["NET_BANKING", "UPI"]), 1.10, 1),
            ("ROUTE_ICICI_RAZORPAY", "ICICI via Razorpay", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.50, 1),
            ("ROUTE_ICICI_PAYU", "ICICI via PayU", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.42, 1),
            ("ROUTE_AXIS_RAZORPAY", "AXIS via Razorpay", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.50, 1),
            ("ROUTE_AXIS_CASHFREE", "AXIS via Cashfree", json.dumps(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NET_BANKING"]), 1.38, 1),
        ]

        merchants = [
            ("m_ecom_01", "Bharat Mart Retail", "ECOMMERCE"),
            ("m_food_01", "QuickBite Delivery", "FOOD"),
            ("m_trav_01", "Desi Flights & Hotels", "TRAVEL"),
            ("m_util_01", "City Power & Gas", "UTILITIES"),
            ("m_entr_01", "StreamStream Media", "ENTERTAINMENT"),
            ("m_hlth_01", "CareFirst Pharmacy", "HEALTHCARE"),
            ("m_educ_01", "SkillUp Academy", "EDUCATION"),
        ]

        users = [
            (
                "usr_admin_01",
                "admin@payroute.ai",
                hash_password("Admin@12345"),
                "System Administrator",
                "PayRoute AI Operations",
                "SUPER_ADMIN",
            ),
            (
                "usr_merch_01",
                "merchant@bharatmart.com",
                hash_password("Merchant@12345"),
                "Bharat Mart Admin",
                "Bharat Mart Retail",
                "MERCHANT_ADMIN",
            ),
        ]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR IGNORE INTO gateways (gateway_id, gateway_name, supported_methods, base_fee_pct, is_active)
                VALUES (?, ?, ?, ?, ?);
                """,
                gateways,
            )
            cursor.executemany(
                """
                INSERT OR IGNORE INTO merchants (merchant_id, merchant_name, merchant_category)
                VALUES (?, ?, ?);
                """,
                merchants,
            )
            cursor.executemany(
                """
                INSERT OR IGNORE INTO users (user_id, email, password_hash, full_name, organization, role)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                users,
            )

            # Seed 4 realistic lifecycle demo transactions
            demo_txns = [
                (
                    "TXN_SUCCESS_001", 12000.0, "INR", "UPI", "SBI", "ECOMMERCE",
                    14, 2, "MOBILE", "4G", 180, 15, 0, 0, 1, 0,
                    150, 80, 0.95, 0.96, 0, None,
                    "SUCCESS", "CONFIRMED", "CONFIRMED", "ROUTE_SBI_RAZORPAY"
                ),
                (
                    "TXN_PENDING_001", 12000.0, "INR", "UPI", "SBI", "ECOMMERCE",
                    14, 2, "MOBILE", "4G", 180, 15, 0, 0, 1, 0,
                    450, 320, 0.70, 0.65, 0, None,
                    "PENDING", "CONFIRMED", "PENDING", "ROUTE_SBI_RAZORPAY"
                ),
                (
                    "TXN_FAILED_001", 8500.0, "INR", "CREDIT_CARD", "HDFC", "ECOMMERCE",
                    14, 2, "DESKTOP", "5G", 220, 8, 1, 1, 1, 0,
                    650, 780, 0.55, 0.40, 1, "GATEWAY_TIMEOUT",
                    "FAILED", "FAILED", "FAILED", "ROUTE_HDFC_RAZORPAY"
                ),
                (
                    "TXN_REFUND_001", 15000.0, "INR", "NET_BANKING", "ICICI", "TRAVEL",
                    14, 2, "MOBILE", "WIFI", 300, 25, 0, 0, 1, 0,
                    850, 200, 0.40, 0.90, 1, "BANK_DOWNTIME",
                    "REFUND_INITIATED", "CONFIRMED", "FAILED", "ROUTE_ICICI_PAYU"
                ),
            ]

            cursor.executemany(
                """
                INSERT OR IGNORE INTO transactions (
                    transaction_id, amount, currency, payment_method, bank,
                    merchant_category, hour, day_of_week, device_type, network_type,
                    customer_age_days, previous_transactions, previous_failed_transactions,
                    previous_attempts, transaction_velocity, is_new_device,
                    bank_latency_ms, gateway_latency_ms, bank_success_rate,
                    gateway_success_rate, payment_status, failure_reason,
                    lifecycle_status, customer_debit_status, merchant_confirmation_status, route_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                demo_txns,
            )

            # Seed default gateway credentials
            demo_creds = [
                (
                    "RAZORPAY", "Razorpay Payment Gateway", "SANDBOX",
                    "rzp_test_demo12345", "rzp_sec_demo67890", "m_razorpay_01",
                    None, "1", "whsec_rzp_demo", None, 1,
                    datetime.datetime.now().isoformat(), "CONNECTED", 135
                ),
                (
                    "PHONEPE", "PhonePe Payment Gateway", "SANDBOX",
                    None, None, "PGTESTPAYUAT",
                    "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399", "1", "whsec_phonepe_demo", None, 1,
                    datetime.datetime.now().isoformat(), "CONNECTED", 145
                ),
                (
                    "GPAY", "Google Pay UPI Gateway", "SANDBOX",
                    "gpay_live_demo123", "gpay_sec_demo456", "m_gpay_01",
                    None, "1", "whsec_gpay_demo", "merchant@okhdfcbank", 1,
                    datetime.datetime.now().isoformat(), "CONNECTED", 120
                ),
            ]
            cursor.executemany(
                """
                INSERT OR IGNORE INTO gateway_credentials (
                    provider_id, provider_name, environment,
                    api_key_id, api_key_secret, merchant_id,
                    salt_key, salt_index, webhook_secret, merchant_vpa, is_enabled,
                    last_tested_at, test_status, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                demo_creds,
            )
            conn.commit()

        logger.info(f"Seeded {len(gateways)} gateways/routes, {len(merchants)} merchants, {len(users)} demo users, {len(demo_txns)} demo transactions, and {len(demo_creds)} gateway credentials.")




    def insert_transactions_dataframe(self, df: pd.DataFrame, batch_size: int = 10000) -> int:
        """
        Performs high-performance batch insertion of synthetic transaction records.

        Args:
            df: Pandas DataFrame containing transaction records.
            batch_size: Number of rows per chunk.

        Returns:
            Total rows inserted.
        """
        logger.info(f"Inserting {len(df):,} transactions into {self.db_path}...")
        
        insert_sql = """
        INSERT OR REPLACE INTO transactions (
            transaction_id, amount, currency, payment_method, bank,
            merchant_category, hour, day_of_week, device_type, network_type,
            customer_age_days, previous_transactions, previous_failed_transactions,
            previous_attempts, transaction_velocity, is_new_device,
            bank_latency_ms, gateway_latency_ms, bank_success_rate,
            gateway_success_rate, payment_status, failure_reason
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
        """

        columns = [
            "transaction_id", "amount", "currency", "payment_method", "bank",
            "merchant_category", "hour", "day_of_week", "device_type", "network_type",
            "customer_age_days", "previous_transactions", "previous_failed_transactions",
            "previous_attempts", "transaction_velocity", "is_new_device",
            "bank_latency_ms", "gateway_latency_ms", "bank_success_rate",
            "gateway_success_rate", "payment_status", "failure_reason",
        ]

        data_tuples = df[columns].to_records(index=False).tolist()
        total_inserted = 0

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for i in range(0, len(data_tuples), batch_size):
                chunk = data_tuples[i : i + batch_size]
                cursor.executemany(insert_sql, chunk)
                conn.commit()
                total_inserted += len(chunk)

        logger.info(f"Successfully inserted {total_inserted:,} transaction records.")
        return total_inserted

    def create_transaction(self, txn: Dict[str, Any]) -> str:
        """
        Inserts a single transaction record into SQLite.

        Args:
            txn: Transaction dictionary.

        Returns:
            transaction_id: The unique primary key.
        """
        insert_sql = """
        INSERT OR REPLACE INTO transactions (
            transaction_id, amount, currency, payment_method, bank,
            merchant_category, hour, day_of_week, device_type, network_type,
            customer_age_days, previous_transactions, previous_failed_transactions,
            previous_attempts, transaction_velocity, is_new_device,
            bank_latency_ms, gateway_latency_ms, bank_success_rate,
            gateway_success_rate, payment_status, failure_reason,
            lifecycle_status, customer_debit_status, merchant_confirmation_status, route_id
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
        """
        payment_status = int(txn.get("payment_status", 0))
        failure_reason = txn.get("failure_reason")
        lifecycle_status = str(txn.get("lifecycle_status", "SUCCESS" if payment_status == 0 else "FAILED"))
        customer_debit = str(
            txn.get(
                "customer_debit_status",
                "CONFIRMED"
                if (payment_status == 0 or lifecycle_status in ["PENDING", "REFUND_INITIATED"])
                else "FAILED",
            )
        )
        merchant_confirm = str(
            txn.get(
                "merchant_confirmation_status",
                "CONFIRMED"
                if (payment_status == 0 and lifecycle_status == "SUCCESS")
                else ("PENDING" if lifecycle_status == "PENDING" else "FAILED"),
            )
        )
        route_id = str(txn.get("route_id", "ROUTE_DEFAULT"))

        values = (
            str(txn["transaction_id"]),
            float(txn.get("amount", 1000.0)),
            str(txn.get("currency", "INR")),
            str(txn.get("payment_method", "UPI")),
            str(txn.get("bank", "HDFC")),
            str(txn.get("merchant_category", "ECOMMERCE")),
            int(txn.get("hour", 14)),
            int(txn.get("day_of_week", 2)),
            str(txn.get("device_type", "MOBILE")),
            str(txn.get("network_type", "4G")),
            int(txn.get("customer_age_days", 180)),
            int(txn.get("previous_transactions", 10)),
            int(txn.get("previous_failed_transactions", 0)),
            int(txn.get("previous_attempts", 0)),
            int(txn.get("transaction_velocity", 1)),
            int(txn.get("is_new_device", 0)),
            int(txn.get("bank_latency_ms", 150)),
            int(txn.get("gateway_latency_ms", 80)),
            float(txn.get("bank_success_rate", 0.95)),
            float(txn.get("gateway_success_rate", 0.96)),
            payment_status,
            failure_reason,
            lifecycle_status,
            customer_debit,
            merchant_confirm,
            route_id,
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()

        return str(txn["transaction_id"])

    insert_transaction = create_transaction

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single transaction by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?;", (transaction_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves rich lifecycle status, debit/confirmation details, and step timeline for a transaction.
        Handles debited-but-unconfirmed and refund states.
        """
        txn = self.get_transaction(transaction_id)
        if not txn:
            return None

        status = txn.get("lifecycle_status") or ("SUCCESS" if txn.get("payment_status") == 0 else "FAILED")
        cust_debit = txn.get("customer_debit_status") or ("CONFIRMED" if (status in ["SUCCESS", "PENDING", "REFUND_INITIATED"]) else "FAILED")
        merch_conf = txn.get("merchant_confirmation_status") or ("CONFIRMED" if status == "SUCCESS" else ("PENDING" if status == "PENDING" else "FAILED"))
        amount = float(txn.get("amount", 0.0))
        method = txn.get("payment_method", "UPI")
        bank = txn.get("bank", "SBI")
        route_id = txn.get("route_id", "ROUTE_DEFAULT")
        failure_reason = txn.get("failure_reason")
        created_at = txn.get("created_at", datetime.datetime.utcnow().isoformat())

        if status == "SUCCESS":
            msg = "The merchant has received confirmation for this payment."
            debit_sub = "CONFIRMED"
            merch_sub = "CONFIRMED"
        elif status == "PENDING":
            msg = "Your account may have been debited, but the merchant confirmation is still pending. Please do not make another payment immediately."
            debit_sub = "CONFIRMED"
            merch_sub = "PENDING"
        elif status == "REFUND_INITIATED":
            msg = "The payment was unsuccessful and a refund has been initiated back to your source account."
            debit_sub = "CONFIRMED"
            merch_sub = "FAILED"
        else:  # FAILED
            msg = f"The payment was not completed successfully ({failure_reason or 'SERVICE_FAILURE'})."
            debit_sub = cust_debit
            merch_sub = "FAILED"

        # Generate stage timeline
        timeline = [
            {
                "stage": "Payment Initiated",
                "status": "COMPLETED",
                "icon": "✓",
                "detail": f"Registered payment for ₹{amount:,.2f}",
            },
            {
                "stage": "Bank Processing",
                "status": "COMPLETED" if (cust_debit == "CONFIRMED" or status in ["SUCCESS", "PENDING", "REFUND_INITIATED"]) else "FAILED",
                "icon": "✓" if (cust_debit == "CONFIRMED" or status in ["SUCCESS", "PENDING", "REFUND_INITIATED"]) else "✗",
                "detail": f"Processed via {bank}",
            },
            {
                "stage": "Customer Account Debit",
                "status": "COMPLETED" if debit_sub == "CONFIRMED" else ("PENDING" if debit_sub == "PENDING" else "FAILED"),
                "icon": "✓" if debit_sub == "CONFIRMED" else ("●" if debit_sub == "PENDING" else "✗"),
                "detail": "Money debited from bank account" if debit_sub == "CONFIRMED" else "Debit failed / not debited",
            },
            {
                "stage": "Merchant Confirmation",
                "status": "COMPLETED" if merch_sub == "CONFIRMED" else ("PENDING" if merch_sub == "PENDING" else "FAILED"),
                "icon": "✓" if merch_sub == "CONFIRMED" else ("●" if merch_sub == "PENDING" else "✗"),
                "detail": "Merchant settlement confirmed" if merch_sub == "CONFIRMED" else ("Awaiting gateway acknowledgment" if merch_sub == "PENDING" else "Confirmation not received"),
            },
            {
                "stage": "Final Status",
                "status": status,
                "icon": "✓" if status == "SUCCESS" else ("○" if status == "PENDING" else ("🔵" if status == "REFUND_INITIATED" else "✗")),
                "detail": f"Status: {status.replace('_', ' ')}",
            },
        ]

        return {
            "transaction_id": transaction_id,
            "status": status,
            "amount": amount,
            "currency": txn.get("currency", "INR"),
            "payment_method": method,
            "bank": bank,
            "route_id": route_id,
            "customer_debit_status": debit_sub,
            "merchant_confirmation_status": merch_sub,
            "failure_reason": failure_reason,
            "created_at": created_at,
            "updated_at": txn.get("updated_at", created_at),
            "message": msg,
            "timeline": timeline,
        }

    def create_routing_decision(self, decision: Dict[str, Any]) -> str:

        """
        Persists a smart routing decision audit record into SQLite.

        Args:
            decision: Routing decision dictionary.

        Returns:
            decision_id: The generated decision ID.
        """
        decision_id = decision.get("decision_id", f"dec_{decision['transaction_id']}")
        insert_sql = """
        INSERT OR REPLACE INTO routing_decisions (
            decision_id, transaction_id, primary_route_id, fallback_route_id,
            primary_fail_prob, predicted_failure_reason, shap_summary,
            routing_strategy
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        shap_json = json.dumps(decision.get("explanation", {}))
        values = (
            str(decision_id),
            str(decision["transaction_id"]),
            str(decision["primary_route"]),
            decision.get("fallback_route"),
            float(decision.get("primary_fail_prob", decision.get("primary_predicted_failure_prob", 0.15))),
            decision.get("predicted_failure_reason"),
            shap_json,
            str(decision.get("routing_strategy", "AI_OPTIMAL")),
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            conn.commit()

        return str(decision_id)

    def get_routing_decision(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a routing decision audit record by transaction ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM routing_decisions WHERE transaction_id = ?;", (transaction_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            res = dict(row)
            if res.get("shap_summary"):
                try:
                    res["explanation"] = json.loads(res["shap_summary"])
                except Exception:
                    res["explanation"] = {}
            return res

    def record_gateway_health(
        self,
        gateway_id: str,
        bank: str,
        rolling_5m_success_rate: float,
        median_latency_ms: int,
        circuit_state: str,
    ) -> int:
        """Logs periodic or transaction-driven gateway health snapshot."""
        insert_sql = """
        INSERT INTO gateway_health_logs (
            gateway_id, bank, rolling_5m_success_rate, median_latency_ms, circuit_state
        ) VALUES (?, ?, ?, ?, ?);
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                insert_sql,
                (gateway_id, bank, float(rolling_5m_success_rate), int(median_latency_ms), str(circuit_state)),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_gateway_health_history(
        self,
        gateway_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieves recent gateway health telemetry logs."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if gateway_id:
                cursor.execute(
                    "SELECT * FROM gateway_health_logs WHERE gateway_id = ? ORDER BY recorded_at DESC LIMIT ?;",
                    (gateway_id, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM gateway_health_logs ORDER BY recorded_at DESC LIMIT ?;",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Queries and returns aggregate transaction metrics for analytics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN payment_status = 0 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN payment_status = 1 THEN 1 ELSE 0 END) as failures,
                    AVG(amount) as avg_amount,
                    AVG(bank_latency_ms + gateway_latency_ms) as avg_latency
                FROM transactions;
            """)
            row = cursor.fetchone()
            total = row["total"] or 0
            successes = row["successes"] or 0
            failures = row["failures"] or 0
            avg_amt = row["avg_amount"] or 0.0
            avg_lat = row["avg_latency"] or 0.0

            cursor.execute("SELECT COUNT(*) FROM gateways;")
            gw_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM merchants;")
            merchant_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM routing_decisions;")
            decisions_count = cursor.fetchone()[0]

        sr = (successes / total * 100.0) if total > 0 else 0.0
        fr = (failures / total * 100.0) if total > 0 else 0.0

        return {
            "total_transactions": total,
            "successful_transactions": successes,
            "failed_transactions": failures,
            "overall_success_rate_pct": round(sr, 2),
            "overall_failure_rate_pct": round(fr, 2),
            "average_amount": round(avg_amt, 2),
            "average_latency_ms": round(avg_lat, 1),
            "gateways_count": gw_count,
            "merchants_count": merchant_count,
            "routing_decisions_recorded": decisions_count,
        }

    def get_summary_stats(self) -> Dict[str, Any]:
        """Queries and returns aggregate transaction statistics for tests and analytics."""
        stats = self.get_transaction_statistics()
        return {
            "total_transactions": stats["total_transactions"],
            "failed_transactions": stats["failed_transactions"],
            "success_transactions": stats["successful_transactions"],
            "failure_rate_pct": stats["overall_failure_rate_pct"],
            "avg_amount": stats["average_amount"],
            "avg_bank_latency_ms": stats["average_latency_ms"],
            "gateways_count": stats["gateways_count"],
            "merchants_count": stats["merchants_count"],
        }

    def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        organization: Optional[str] = None,
        role: str = "MERCHANT_ADMIN",
    ) -> Dict[str, Any]:
        """
        Creates and persists a new user account with hashed credentials.

        Args:
            email: Unique user email address.
            password: Raw plaintext password.
            full_name: User's display name.
            organization: Company/merchant name.
            role: Access role (e.g. "MERCHANT_ADMIN", "DEVELOPER", "SUPER_ADMIN").

        Returns:
            User profile dictionary (without password hash).
        """
        email_clean = email.strip().lower()
        if not email_clean or "@" not in email_clean:
            raise ValueError(f"Invalid email address '{email}'.")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        if not full_name.strip():
            raise ValueError("Full name cannot be empty.")

        existing = self.get_user_by_email(email_clean)
        if existing:
            raise ValueError(f"An account with email '{email_clean}' already exists.")

        import uuid
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        pwd_hash = hash_password(password)
        org_clean = organization.strip() if organization else "Independent Merchant"

        insert_sql = """
        INSERT INTO users (user_id, email, password_hash, full_name, organization, role)
        VALUES (?, ?, ?, ?, ?, ?);
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_sql, (user_id, email_clean, pwd_hash, full_name.strip(), org_clean, role))
            conn.commit()

        logger.info(f"Created new user account: {email_clean} ({user_id})")
        return {
            "user_id": user_id,
            "email": email_clean,
            "full_name": full_name.strip(),
            "organization": org_clean,
            "role": role,
        }

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves user record by email address."""
        email_clean = email.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?;", (email_clean,))
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user record by user ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates email and password credentials.

        Args:
            email: Account email.
            password: Raw plaintext password candidate.

        Returns:
            User profile dictionary if valid, None otherwise.
        """
        user = self.get_user_by_email(email)
        if not user:
            return None

        stored_hash = user.get("password_hash", "")
        if verify_password(password, stored_hash):
            return {
                "user_id": user["user_id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "organization": user.get("organization", ""),
                "role": user.get("role", "MERCHANT_ADMIN"),
                "created_at": user.get("created_at"),
            }
        return None

    # =========================================================================
    # Payment Gateway Credentials Management
    # =========================================================================

    def get_gateway_credentials(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves configured credentials for a specific payment gateway provider."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gateway_credentials WHERE provider_id = ?;", (provider_id.upper(),))
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    def list_all_gateway_credentials(self) -> List[Dict[str, Any]]:
        """Lists all configured payment gateway credentials."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gateway_credentials ORDER BY provider_id ASC;")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def save_gateway_credentials(self, provider_id: str, data: Dict[str, Any]) -> None:
        """
        Upserts API keys and credentials for a gateway provider.
        """
        p_id = provider_id.upper()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO gateway_credentials (
                    provider_id, provider_name, environment,
                    api_key_id, api_key_secret, merchant_id,
                    salt_key, salt_index, webhook_secret, merchant_vpa,
                    is_enabled, last_tested_at, test_status, latency_ms, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_id) DO UPDATE SET
                    provider_name = coalesce(excluded.provider_name, gateway_credentials.provider_name),
                    environment = coalesce(excluded.environment, gateway_credentials.environment),
                    api_key_id = coalesce(excluded.api_key_id, gateway_credentials.api_key_id),
                    api_key_secret = coalesce(excluded.api_key_secret, gateway_credentials.api_key_secret),
                    merchant_id = coalesce(excluded.merchant_id, gateway_credentials.merchant_id),
                    salt_key = coalesce(excluded.salt_key, gateway_credentials.salt_key),
                    salt_index = coalesce(excluded.salt_index, gateway_credentials.salt_index),
                    webhook_secret = coalesce(excluded.webhook_secret, gateway_credentials.webhook_secret),
                    merchant_vpa = coalesce(excluded.merchant_vpa, gateway_credentials.merchant_vpa),
                    is_enabled = coalesce(excluded.is_enabled, gateway_credentials.is_enabled),
                    last_tested_at = coalesce(excluded.last_tested_at, gateway_credentials.last_tested_at),
                    test_status = coalesce(excluded.test_status, gateway_credentials.test_status),
                    latency_ms = coalesce(excluded.latency_ms, gateway_credentials.latency_ms),
                    updated_at = excluded.updated_at;
                """,
                (
                    p_id,
                    data.get("provider_name", f"{p_id} Gateway"),
                    data.get("environment", "SANDBOX"),
                    data.get("api_key_id"),
                    data.get("api_key_secret"),
                    data.get("merchant_id"),
                    data.get("salt_key"),
                    data.get("salt_index", "1"),
                    data.get("webhook_secret"),
                    data.get("merchant_vpa"),
                    int(data.get("is_enabled", 1)),
                    data.get("last_tested_at"),
                    data.get("test_status", "UNCONFIGURED"),
                    int(data.get("latency_ms", 0)),
                    datetime.datetime.now().isoformat(),
                ),
            )
            conn.commit()

    # =========================================================================
    # Full Transactions Query & Filtering
    # =========================================================================

    def get_all_transactions(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves paginated list of transactions with optional filtering.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params: List[Any] = []

            if status_filter and status_filter.upper() != "ALL":
                conditions.append("lifecycle_status = ?")
                params.append(status_filter.upper())

            if search_query:
                q = f"%{search_query.strip()}%"
                conditions.append("(transaction_id LIKE ? OR bank LIKE ? OR payment_method LIKE ? OR route_id LIKE ?)")
                params.extend([q, q, q, q])

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            # Count total matching
            cursor.execute(f"SELECT COUNT(*) FROM transactions{where_clause};", tuple(params))
            total_count = cursor.fetchone()[0]

            # Fetch rows
            query = f"""
                SELECT transaction_id, amount, currency, payment_method, bank,
                       route_id, payment_status, lifecycle_status,
                       customer_debit_status, merchant_confirmation_status,
                       failure_reason, bank_latency_ms, gateway_latency_ms, created_at
                FROM transactions
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(query, tuple(params + [limit, offset]))
            rows = cursor.fetchall()
            return {
                "transactions": [dict(r) for r in rows],
                "total": total_count,
                "limit": limit,
                "offset": offset,
            }


