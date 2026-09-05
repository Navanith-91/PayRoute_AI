"""
Database initialization CLI script.
Creates tables, creates indices, seeds gateways/merchants, and optionally ingests synthetic data.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from database.db_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger("InitDB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize PayRoute AI SQLite Database")
    parser.add_argument("--db-path", type=str, default="database/payroute.db", help="Path to SQLite database file")
    parser.add_argument("--schema", type=str, default="database/schema.sql", help="Path to schema.sql DDL")
    parser.add_argument("--seed-csv", type=str, default=None, help="Optional path to synthetic CSV to load into database")

    args = parser.parse_args()

    db_manager = DatabaseManager(db_path=args.db_path)
    db_manager.initialize_schema(schema_file=args.schema)
    db_manager.seed_initial_entities()

    if args.seed_csv and Path(args.seed_csv).exists():
        logger.info(f"Loading data from CSV: {args.seed_csv}...")
        df = pd.read_csv(args.seed_csv)
        db_manager.insert_transactions_dataframe(df)

    stats = db_manager.get_summary_stats()
    logger.info(f"Database Initialization Complete: {stats}")


if __name__ == "__main__":
    main()
