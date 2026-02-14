"""
Data Quality Analysis
======================
Phase 1: Analyze missing data in UCT benchmark.

Identifies:
- Which fields are missing and by how much
- Why they are missing (MCAR / MAR / MNAR)
- Which satellites have sparse coverage
- Decision table: imputation vs calculation
"""

import duckdb
import pandas as pd
import numpy as np
import os


def find_database():
    for root, dirs, files in os.walk("/content"):
        for file in files:
            if file.endswith(".duckdb"):
                return os.path.join(root, file)
    raise FileNotFoundError("No .duckdb file found")


def analyze_missing(con):
    """Profile all fields for missing values."""
    df = con.execute(
        "SELECT * FROM observations"
    ).fetchdf()

    print(f"Total observations: {len(df):,}")
    print(f"Satellites:         "
          f"{df.sat_no.nunique()}")
    print(f"Sensors:            "
          f"{df.sensor_name.nunique()}")
    print(f"Time range:         "
          f"{df.ob_time.min()} → "
          f"{df.ob_time.max()}")

    print("\n--- MISSING VALUES PER FIELD ---")
    for col in df.columns:
        n_missing = df[col].isna().sum()
        pct = n_missing / len(df) * 100
        print(f"  {col:<25} {n_missing:>6} "
              f"({pct:>6.1f}%)")

    return df


def classify_missing(df):
    """
    Classify missing data mechanism:
    MCAR = Missing Completely At Random
    MAR  = Missing At Random
    MNAR = Missing Not At Random
    """
    print("\n--- MISSING DATA CLASSIFICATION ---")
    decisions = {
        "range_km": {
            "pct": 100,
            "type": "MNAR",
            "reason": "Optical sensors cannot "
                      "measure range",
            "method": "CALCULATE from physics"
        },
        "range_rate_km_s": {
            "pct": 100,
            "type": "MNAR",
            "reason": "Derived from range over time",
            "method": "CALCULATE from consecutive obs"
        },
        "track_id": {
            "pct": round(
                df.track_id.isna().sum() /
                len(df) * 100, 1
            ),
            "type": "MAR",
            "reason": "Observations not yet grouped",
            "method": "ASSIGN by grouping"
        }
    }

    for field, info in decisions.items():
        print(f"\n  {field}")
        print(f"    Missing: {info['pct']}%")
        print(f"    Type:    {info['type']}")
        print(f"    Reason:  {info['reason']}")
        print(f"    Method:  {info['method']}")

    return decisions


def identify_sparse_satellites(df, threshold=100):
    """Find satellites with insufficient coverage."""
    print("\n--- SPARSE SATELLITES ---")
    counts = df.groupby("sat_no").size()
    sparse = counts[counts < threshold]

    for sat, count in sparse.items():
        print(f"  sat {sat}: {count} observations")

    return sparse.index.tolist()


if __name__ == "__main__":
    db_path = find_database()
    con = duckdb.connect(db_path)

    print("=" * 55)
    print("DATA QUALITY ANALYSIS")
    print("=" * 55)

    df = analyze_missing(con)
    decisions = classify_missing(df)
    sparse = identify_sparse_satellites(df)

    print(f"\nSparse satellites: {sparse}")
    print("\nDone ✅")
    con.close()
