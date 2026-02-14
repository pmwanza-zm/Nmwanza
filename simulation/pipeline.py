"""
Master Simulation Pipeline
===========================
Runs the complete simulation workflow end to end.

Steps:
  1. Load raw observations
  2. Calculate range_km (physics)
  3. Calculate range_rate_km_s (consecutive obs)
  4. Assign track_ids (grouping)
  5. Fill remaining range_rate gaps (mean)
  6. Simulate sparse satellites
  7. Validate results
  8. Save to observations_final

Usage:
  python pipeline.py

Runtime: ~5 seconds for 19,322 observations
"""

import duckdb
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, timedelta, timezone
import uuid


def find_database():
    for root, dirs, files in os.walk("/content"):
        for file in files:
            if file.endswith(".duckdb"):
                return os.path.join(root, file)
    raise FileNotFoundError("No .duckdb file found")


def estimate_range(el, alt=500):
    R = 6371.0
    el_rad = np.radians(el)
    return (-R*np.sin(el_rad) +
            np.sqrt((R*np.sin(el_rad))**2 +
                    alt**2 + 2*R*alt))


def calc_range_rate(ranges, times, max_rate=8.0):
    rates = np.full(len(ranges), np.nan)
    for i in range(1, len(ranges)):
        dt = (times[i]-times[i-1]).total_seconds()
        if 0 < dt <= 120:
            dr = ranges[i] - ranges[i-1]
            rate = dr / dt
            if abs(rate) <= max_rate:
                rates[i] = rate
    return rates


def assign_track_ids(df):
    df = df.copy().sort_values(
        "ob_time"
    ).reset_index(drop=True)
    df["track_id"] = df["track_id"].astype(object)
    counter = 1

    for sat in df["sat_no"].unique():
        sat_mask = df["sat_no"] == sat
        for sensor in df[sat_mask]["sensor_name"].unique():
            mask = sat_mask & (
                df["sensor_name"] == sensor
            )
            obs = df[mask].sort_values("ob_time")
            track = []
            prev_t = None

            for idx, row in obs.iterrows():
                t = pd.to_datetime(row["ob_time"])
                if prev_t is None:
                    track = [idx]
                else:
                    gap = (t - prev_t).total_seconds()
                    if gap <= 120:
                        track.append(idx)
                    else:
                        tid = f"TRK{counter:06d}"
                        for i in track:
                            df.at[i, "track_id"] = tid
                        counter += 1
                        track = [idx]
                prev_t = t

            if track:
                tid = f"TRK{counter:06d}"
                for i in track:
                    df.at[i, "track_id"] = tid
                counter += 1

    return df, counter - 1


def simulate_sparse(con, threshold=100):
    """Generate observations for sparse satellites."""
    sparse = con.execute(f"""
        SELECT sat_no, COUNT(*) as n
        FROM observations
        WHERE is_simulated = false
        GROUP BY sat_no
        HAVING COUNT(*) < {threshold}
    """).fetchdf()

    all_sim = []

    for _, row in sparse.iterrows():
        sat = int(row["sat_no"])
        obs = con.execute(f"""
            SELECT * FROM observations
            WHERE sat_no = {sat}
            AND is_simulated = false
            ORDER BY ob_time
        """).fetchdf()

        if len(obs) >= 2:
            ra_rates, dec_rates, el_rates = [], [], []
            for i in range(1, len(obs)):
                t1 = pd.to_datetime(obs["ob_time"].iloc[i-1])
                t2 = pd.to_datetime(obs["ob_time"].iloc[i])
                dt = (t2-t1).total_seconds()
                if 0 < dt <= 120:
                    ra_rates.append(
                        (obs["ra"].iloc[i]-obs["ra"].iloc[i-1])/dt)
                    dec_rates.append(
                        (obs["declination"].iloc[i]-obs["declination"].iloc[i-1])/dt)
                    el_rates.append(
                        (obs["elevation"].iloc[i]-obs["elevation"].iloc[i-1])/dt)

            if ra_rates:
                ra_r = np.median(ra_rates)
                dec_r = np.median(dec_rates)
                el_r = np.median(el_rates)
            else:
                ra_r, dec_r, el_r = 0.055, -0.020, -0.008
        else:
            ra_r, dec_r, el_r = 0.055, -0.020, -0.008

        base_ra  = float(obs["ra"].iloc[-1])
        base_dec = float(obs["declination"].iloc[-1])
        base_el  = float(obs["elevation"].mean())
        base_az  = float(obs["azimuth"].iloc[-1])
        base_t   = pd.to_datetime(obs["ob_time"].max())
        sensor   = obs["sensor_name"].iloc[-1]

        for i in range(5):
            start = base_t + timedelta(
                seconds=(i+1)*90*60
            )
            for j in range(30):
                dt = j * 10
                new_el = base_el + el_r * dt
                if new_el < 5 or new_el > 85:
                    break
                all_sim.append({
                    "id": str(uuid.uuid4()),
                    "sat_no": sat,
                    "ob_time": start + timedelta(
                        seconds=dt
                    ),
                    "ra": round(
                        (base_ra+ra_r*dt)%360, 6
                    ),
                    "declination": round(
                        base_dec+dec_r*dt, 6
                    ),
                    "range_km": round(
                        estimate_range(new_el), 4
                    ),
                    "range_rate_km_s": None,
                    "azimuth": round(
                        (base_az+ra_r*dt*0.8)%360, 6
                    ),
                    "elevation": round(new_el, 6),
                    "sensor_name": sensor,
                    "data_mode": "SIMULATED",
                    "track_id": f"TRK_SIM_{sat}_{i:03d}",
                    "is_uct": False,
                    "is_simulated": True,
                    "created_at": datetime.now(timezone.utc)
                })

    if all_sim:
        sim_df = pd.DataFrame(all_sim)
        con.execute(
            "DROP TABLE IF EXISTS observations_simulated"
        )
        con.register("sim_df", sim_df)
        con.execute("""
            CREATE TABLE observations_simulated AS
            SELECT * FROM sim_df
        """)
        return len(sim_df)
    return 0


def validate(df):
    """Run physical validity checks."""
    n = len(df)
    checks = {
        "RA (0-360)":       ((df.ra>=0)&(df.ra<=360)).sum(),
        "Dec (-90 to +90)": ((df.declination>=-90)&
                             (df.declination<=90)).sum(),
        "Elevation (5-85)": ((df.elevation>=5)&
                             (df.elevation<=85)).sum(),
        "Range (400-2500)": ((df.range_km>=400)&
                             (df.range_km<=2500)).sum(),
    }
    all_pass = True
    for name, count in checks.items():
        status = "✅" if count == n else "❌"
        if count != n:
            all_pass = False
        print(f"  {name:<25} {count}/{n} {status}")
    return all_pass


def run():
    t0 = time.time()
    db = find_database()
    con = duckdb.connect(db)

    print("=" * 55)
    print("SIMULATION PIPELINE")
    print("=" * 55)

    print("\n[1/7] Loading observations...")
    df = con.execute("""
        SELECT * FROM observations
        ORDER BY sat_no, ob_time
    """).fetchdf()
    print(f"      {len(df):,} rows")

    print("[2/7] Calculating range_km...")
    df["range_km"] = df["elevation"].apply(
        estimate_range
    )
    print(f"      {df.range_km.notna().sum():,} filled")

    print("[3/7] Calculating range_rate_km_s...")
    df["range_rate_km_s"] = np.nan
    for sat in df["sat_no"].unique():
        mask = df["sat_no"] == sat
        sat_df = df[mask].copy()
        times = pd.to_datetime(
            sat_df["ob_time"]
        ).tolist()
        rates = calc_range_rate(
            sat_df["range_km"].values, times
        )
        df.loc[mask, "range_rate_km_s"] = rates
    filled = df.range_rate_km_s.notna().sum()
    print(f"      {filled:,} filled "
          f"({filled/len(df)*100:.1f}%)")

    print("[4/7] Assigning track IDs...")
    df, n_tracks = assign_track_ids(df)
    print(f"      {n_tracks} tracks")

    print("[5/7] Filling remaining range_rate "
          "with mean...")
    mean_rr = df["range_rate_km_s"].mean()
    before = df["range_rate_km_s"].isna().sum()
    df["range_rate_km_s"] = df[
        "range_rate_km_s"
    ].fillna(mean_rr)
    print(f"      Filled {before} rows with "
          f"mean={mean_rr:.5f}")

    print("[6/7] Simulating sparse satellites...")
    con.execute("DROP TABLE IF EXISTS observations_final")
    con.register("df_pipe", df)
    con.execute("""
        CREATE TABLE observations_final AS
        SELECT * FROM df_pipe
    """)
    n_sim = simulate_sparse(con)
    print(f"      {n_sim} new observations generated")

    print("[7/7] Validating...")
    sim_df = con.execute("""
        SELECT * FROM observations_simulated
    """).fetchdf()
    if len(sim_df) > 0:
        validate(sim_df)
    else:
        print("  No simulated obs to validate")

    elapsed = time.time() - t0
    print(f"\n{'='*55}")
    print(f"PIPELINE COMPLETE in {elapsed:.1f}s ✅")
    print(f"{'='*55}")
    print(f"\nFinal dataset:")
    print(f"  Real observations:      "
          f"{df.is_simulated.eq(False).sum():>7,}")
    print(f"  Original simulated:     "
          f"{df.is_simulated.eq(True).sum():>7,}")
    print(f"  New sparse simulated:   {n_sim:>7,}")
    print(f"  range_km complete:      "
          f"{df.range_km.notna().sum():>7,}")
    print(f"  range_rate complete:    "
          f"{df.range_rate_km_s.notna().sum():>7,}")
    print(f"  track_id complete:      "
          f"{df.track_id.notna().sum():>7,}")

    con.close()


if __name__ == "__main__":
    run()
