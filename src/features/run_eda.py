"""
Comprehensive Exploratory Data Analysis (EDA) and Visualization Runner for PayRoute AI.
Loads dataset from data/raw/, computes detailed statistical profiles,
and generates 10 high-resolution analytical figures under data/processed/eda/.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("EDA_Runner")

# Configure Clean Matplotlib Style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["figure.dpi"] = 150
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.labelsize"] = 10


def find_raw_dataset(raw_dir: Optional[str] = None) -> Path:
    """
    Automatically discovers the primary raw payment dataset (.csv or .parquet) in data/raw/.
    """
    if raw_dir is None:
        target_dir = PROJECT_ROOT / "data" / "raw"
    else:
        target_dir = Path(raw_dir)

    if not target_dir.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {target_dir}")

    # Search for files
    candidates = list(target_dir.glob("*.csv")) + list(target_dir.glob("*.parquet"))
    if not candidates:
        raise FileNotFoundError(f"No CSV or Parquet files found in {target_dir}")

    # Prefer payments_synthetic.csv or the largest file
    preferred = [f for f in candidates if "synthetic" in f.name.lower()]
    if preferred:
        selected = preferred[0]
    else:
        selected = max(candidates, key=lambda f: f.stat().st_size)

    logger.info(f"Discovered raw dataset: {selected} ({selected.stat().st_size / (1024*1024):.2f} MB)")
    return selected


def load_dataset(file_path: Path) -> pd.DataFrame:
    """Loads CSV or Parquet into a Pandas DataFrame."""
    if file_path.suffix.lower() == ".parquet":
        return pd.read_parquet(file_path)
    return pd.read_csv(file_path)


def generate_eda_figures(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Generates and saves 10 high-resolution analytical charts for the PayRoute AI portfolio.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating 10 analytical figures in {output_dir}...")

    palette_blue = "#1f77b4"
    palette_red = "#d62728"
    palette_green = "#2ca02c"
    palette_orange = "#ff7f0e"
    palette_colors = ["#2b5c8f", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d"]

    # -------------------------------------------------------------------------
    # 1. Payment Status Distribution (Class Balance)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 4))
    status_counts = df["payment_status"].value_counts().rename({0: "SUCCESS (0)", 1: "FAILED (1)"})
    bars = ax.bar(status_counts.index, status_counts.values, color=[palette_green, palette_red], width=0.5, edgecolor="black", alpha=0.85)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + (len(df) * 0.01), f"{height:,}\n({height/len(df)*100:.1f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title("Target Distribution: Payment Status (Class Imbalance)", fontweight="bold")
    ax.set_ylabel("Transaction Count")
    ax.set_ylim(0, len(df) * 1.08)
    plt.tight_layout()
    fig.savefig(output_dir / "01_payment_status_distribution.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 2. Failure Reasons Breakdown
    # -------------------------------------------------------------------------
    failed_df = df[df["payment_status"] == 1]
    if len(failed_df) > 0:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        reason_counts = failed_df["failure_reason"].value_counts()
        bars = ax.barh(reason_counts.index[::-1], reason_counts.values[::-1], color="#3b528b", edgecolor="black", alpha=0.85)
        for bar in bars:
            width = bar.get_width()
            ax.text(width + (len(failed_df) * 0.01), bar.get_y() + bar.get_height() / 2.0, f"{width:,} ({width/len(failed_df)*100:.1f}%)", ha="left", va="center", fontsize=9, fontweight="bold")
        ax.set_title("Distribution of Failure Reasons (Conditional on Failed Payments)", fontweight="bold")
        ax.set_xlabel("Failure Count")
        ax.set_xlim(0, max(reason_counts.values) * 1.25)
        plt.tight_layout()
        fig.savefig(output_dir / "02_failure_reasons_distribution.png")
        plt.close(fig)

    # -------------------------------------------------------------------------
    # 3. Failure Rate by Payment Method
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4))
    meth_agg = df.groupby("payment_method")["payment_status"].agg(["mean", "count"]).reset_index()
    meth_agg["mean_pct"] = meth_agg["mean"] * 100.0
    meth_agg = meth_agg.sort_values("mean_pct", ascending=False)
    bars = ax.bar(meth_agg["payment_method"], meth_agg["mean_pct"], color=palette_colors[:len(meth_agg)], edgecolor="black", alpha=0.85)
    for bar, (_, row) in zip(bars, meth_agg.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.4, f"{row['mean_pct']:.1f}%\n(N={int(row['count']):,})", ha="center", va="bottom", fontsize=8)
    ax.axhline(df["payment_status"].mean() * 100.0, color="gray", linestyle="--", alpha=0.7, label=f"Global Avg ({df['payment_status'].mean()*100:.1f}%)")
    ax.set_title("Payment Failure Rate by Payment Method", fontweight="bold")
    ax.set_ylabel("Failure Rate (%)")
    ax.set_ylim(0, max(meth_agg["mean_pct"]) * 1.25)
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.savefig(output_dir / "03_failure_rate_by_payment_method.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 4. Failure Rate by Bank
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6.5, 4))
    bank_agg = df.groupby("bank")["payment_status"].agg(["mean", "count"]).reset_index()
    bank_agg["mean_pct"] = bank_agg["mean"] * 100.0
    bank_agg = bank_agg.sort_values("mean_pct", ascending=False)
    bars = ax.bar(bank_agg["bank"], bank_agg["mean_pct"], color=["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"], edgecolor="black", alpha=0.85)
    for bar, (_, row) in zip(bars, bank_agg.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.4, f"{row['mean_pct']:.1f}%\n(N={int(row['count']):,})", ha="center", va="bottom", fontsize=8)
    ax.axhline(df["payment_status"].mean() * 100.0, color="gray", linestyle="--", alpha=0.7, label=f"Global Avg ({df['payment_status'].mean()*100:.1f}%)")
    ax.set_title("Payment Failure Rate by Issuing Bank", fontweight="bold")
    ax.set_ylabel("Failure Rate (%)")
    ax.set_ylim(0, max(bank_agg["mean_pct"]) * 1.25)
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.savefig(output_dir / "04_failure_rate_by_bank.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 5. Failure Rate by Network Type
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 4))
    net_agg = df.groupby("network_type")["payment_status"].agg(["mean", "count"]).reindex(["2G", "3G", "4G", "5G", "WIFI"]).reset_index()
    net_agg["mean_pct"] = net_agg["mean"] * 100.0
    bars = ax.bar(net_agg["network_type"], net_agg["mean_pct"], color="#e7298a", edgecolor="black", alpha=0.85)
    for bar, (_, row) in zip(bars, net_agg.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.6, f"{row['mean_pct']:.1f}%\n(N={int(row['count']):,})", ha="center", va="bottom", fontsize=8)
    ax.axhline(df["payment_status"].mean() * 100.0, color="gray", linestyle="--", alpha=0.7, label=f"Global Avg ({df['payment_status'].mean()*100:.1f}%)")
    ax.set_title("Payment Failure Rate by Client Network Type (Friction Impact)", fontweight="bold")
    ax.set_ylabel("Failure Rate (%)")
    ax.set_ylim(0, max(net_agg["mean_pct"]) * 1.25)
    ax.legend(loc="upper right")
    plt.tight_layout()
    fig.savefig(output_dir / "05_failure_rate_by_network.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 6. Diurnal Failure Rate & Volume by Hour
    # -------------------------------------------------------------------------
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    hour_agg = df.groupby("hour").agg(failure_rate=("payment_status", "mean"), volume=("payment_status", "count")).reset_index()
    hour_agg["failure_rate_pct"] = hour_agg["failure_rate"] * 100.0

    ax2 = ax1.twinx()
    ax1.bar(hour_agg["hour"], hour_agg["volume"], color="#9ecae1", alpha=0.6, width=0.7, label="Hourly Volume")
    ax2.plot(hour_agg["hour"], hour_agg["failure_rate_pct"], color="#de2d26", marker="o", linewidth=2.0, label="Failure Rate (%)")

    ax1.set_xlabel("Hour of Day (00:00 - 23:00)")
    ax1.set_ylabel("Transaction Volume", color="#3182bd")
    ax2.set_ylabel("Failure Rate (%)", color="#de2d26")
    ax1.set_xticks(range(0, 24, 2))
    ax1.set_title("Diurnal Dynamics: Transaction Volume vs Payment Failure Rate (Maintenance Windows)", fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_dir / "06_failure_rate_by_hour.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 7. Failure Rate by Merchant Category
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4))
    cat_agg = df.groupby("merchant_category")["payment_status"].agg(["mean", "count"]).reset_index()
    cat_agg["mean_pct"] = cat_agg["mean"] * 100.0
    cat_agg = cat_agg.sort_values("mean_pct", ascending=True)
    bars = ax.barh(cat_agg["merchant_category"], cat_agg["mean_pct"], color="#41b6c4", edgecolor="black", alpha=0.85)
    for bar, (_, row) in zip(bars, cat_agg.iterrows()):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2.0, f"{row['mean_pct']:.1f}%", ha="left", va="center", fontsize=8)
    ax.axvline(df["payment_status"].mean() * 100.0, color="gray", linestyle="--", alpha=0.7, label=f"Global Avg ({df['payment_status'].mean()*100:.1f}%)")
    ax.set_title("Payment Failure Rate across Merchant Categories", fontweight="bold")
    ax.set_xlabel("Failure Rate (%)")
    ax.set_xlim(0, max(cat_agg["mean_pct"]) * 1.25)
    ax.legend(loc="lower right")
    plt.tight_layout()
    fig.savefig(output_dir / "07_failure_rate_by_merchant_category.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 8. Bank Latency Quantiles vs Failure Rate
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 4))
    df["bank_lat_bin"] = pd.qcut(df["bank_latency_ms"], q=5, duplicates="drop")
    lat_agg = df.groupby("bank_lat_bin", observed=False)["payment_status"].mean() * 100.0
    bin_labels = [f"Q{i+1}\n({int(interval.left)}-{int(interval.right)}ms)" for i, interval in enumerate(lat_agg.index)]
    bars = ax.bar(bin_labels, lat_agg.values, color="#feb24c", edgecolor="black", alpha=0.85)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.5, f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_title("Bank Latency Quintiles vs Observed Payment Failure Rate", fontweight="bold")
    ax.set_ylabel("Failure Rate (%)")
    ax.set_xlabel("Bank Latency Range")
    ax.set_ylim(0, max(lat_agg.values) * 1.25)
    plt.tight_layout()
    fig.savefig(output_dir / "08_latency_vs_failure.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 9. Historical User Failure Rate vs Current Payment Failure
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7.5, 4))
    hist_fail_rate = df["previous_failed_transactions"] / (df["previous_transactions"] + 1.0)
    df["hist_fail_bin"] = pd.cut(hist_fail_rate, bins=[-0.01, 0.05, 0.15, 0.30, 1.0], labels=["0-5% (Low)", "5-15% (Med-Low)", "15-30% (Med-High)", ">30% (High)"])
    hist_agg = df.groupby("hist_fail_bin", observed=False)["payment_status"].agg(["mean", "count"]).reset_index()
    hist_agg["mean_pct"] = hist_agg["mean"] * 100.0
    bars = ax.bar(hist_agg["hist_fail_bin"].astype(str), hist_agg["mean_pct"], color="#74a9cf", edgecolor="black", alpha=0.85)
    for bar, (_, row) in zip(bars, hist_agg.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.4, f"{row['mean_pct']:.1f}%\n(N={int(row['count']):,})", ha="center", va="bottom", fontsize=8)
    ax.set_title("User Historical Failure Rate Tier vs Current Failure Probability", fontweight="bold")
    ax.set_ylabel("Current Failure Rate (%)")
    ax.set_xlabel("Historical Failure Rate Tier")
    ax.set_ylim(0, max(hist_agg["mean_pct"]) * 1.25)
    plt.tight_layout()
    fig.savefig(output_dir / "09_historical_failure_rate_vs_current.png")
    plt.close(fig)

    # -------------------------------------------------------------------------
    # 10. Correlation Heatmap (Continuous Features)
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    num_cols = [
        "amount",
        "customer_age_days",
        "previous_transactions",
        "previous_failed_transactions",
        "previous_attempts",
        "transaction_velocity",
        "bank_latency_ms",
        "gateway_latency_ms",
        "bank_success_rate",
        "gateway_success_rate",
        "payment_status",
    ]
    corr = df[num_cols].corr()
    im = ax.imshow(corr, cmap="coolwarm", vmin=-0.6, vmax=0.6)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Pearson Correlation", rotation=270, labelpad=15)
    ax.set_xticks(range(len(num_cols)))
    ax.set_yticks(range(len(num_cols)))
    ax.set_xticklabels(num_cols, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(num_cols, fontsize=8)
    for i in range(len(num_cols)):
        for j in range(len(num_cols)):
            val = corr.iloc[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="white" if abs(val) > 0.35 else "black", fontsize=7)
    ax.set_title("Linear Correlation Heatmap (Numerical Attributes & Target)", fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_dir / "10_correlation_heatmap.png")
    plt.close(fig)

    logger.info("All 10 analytical figures generated successfully.")


def run_full_eda() -> pd.DataFrame:
    """Executes the complete EDA pipeline and outputs key summary tables."""
    data_path = find_raw_dataset()
    df = load_dataset(data_path)

    eda_output_dir = PROJECT_ROOT / "data" / "processed" / "eda"
    generate_eda_figures(df, eda_output_dir)

    logger.info(f"Dataset Dimensions: {df.shape[0]:,} rows x {df.shape[1]} columns")
    logger.info(f"Missing Values: {df.isnull().sum().to_dict()}")
    logger.info(f"Duplicate Transaction IDs: {df['transaction_id'].duplicated().sum()}")
    logger.info(f"Overall Failure Rate: {df['payment_status'].mean()*100:.2f}%")

    return df


if __name__ == "__main__":
    run_full_eda()
