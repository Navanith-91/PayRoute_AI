"""
Unit tests for the SQLite database manager and schema initialization.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from src.data_generator.generator import PaymentDataGenerator


class TestDatabaseManager(unittest.TestCase):
    """Test suite for validating SQLite schema, seed data, and batch transaction insertion."""

    def setUp(self):
        """Creates an isolated temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_payroute.db")
        self.manager = DatabaseManager(db_path=self.db_path)
        
        schema_path = PROJECT_ROOT / "database" / "schema.sql"
        self.manager.initialize_schema(schema_file=str(schema_path))
        self.manager.seed_initial_entities()

    def tearDown(self):
        """Cleans up temporary directory and database file."""
        self.temp_dir.cleanup()

    def test_schema_tables_created(self):
        """Verifies that all 5 relational tables exist in SQLite."""
        expected_tables = {
            "merchants",
            "gateways",
            "transactions",
            "routing_decisions",
            "gateway_health_logs",
        }

        with self.manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}

        self.assertTrue(expected_tables.issubset(tables))

    def test_seed_data_inserted(self):
        """Verifies that default gateways and merchants are seeded."""
        stats = self.manager.get_summary_stats()
        self.assertGreaterEqual(stats["gateways_count"], 4)
        self.assertGreaterEqual(stats["merchants_count"], 7)

    def test_batch_transaction_insertion(self):
        """Verifies batch inserting generated DataFrame into SQLite transactions table."""
        gen = PaymentDataGenerator(random_seed=42)
        df = gen.generate(num_records=500)

        inserted = self.manager.insert_transactions_dataframe(df, batch_size=200)
        self.assertEqual(inserted, 500)

        stats = self.manager.get_summary_stats()
        self.assertEqual(stats["total_transactions"], 504)  # 500 batch inserted + 4 demo records
        self.assertEqual(stats["success_transactions"], (500 - int(df["payment_status"].sum())) + 2)



if __name__ == "__main__":
    unittest.main()
