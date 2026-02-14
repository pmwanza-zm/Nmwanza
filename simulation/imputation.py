"""
Imputation Pipeline
====================
Phase 2: Fill missing fields using physics
and grouping methods.

Fields filled:
- range_km:         geometric slant range from elevation
- range_rate_km_s:  dr/dt from consecutive observations
- track_id:         grouping by sat + sensor + time gap
"""

import duckdb
import pandas as pd
import numpy as np
import os


def estimate_range(elevation_deg, altitude_km=500):
    """
    Calculate slant range from elevation angle.

    Uses geometry of observer on Earth's surface
    looking up at a satellite at given altitude.

    Formula:
        range = -R*sin(el) + sqrt((R*sin(el))^2
                                   + h^2 + 2Rh)

    Args:
        elevation_deg: elevation angle in degrees
        altitude_km:   assumed satellite altitude

    Returns:
        range in km
    """
    R = 6371.0
    el_rad = np.radians(elevation_deg)
    return (
        -R * np.sin(el_rad) +
        np.sqrt(
            (R * np.sin(el_rad))**2 +
            altitude_km**2 +
            2 * R * altitude_km
        )
    )


def calculate_range_rate(ranges_km, times,
                          max_rate=8.0,
                          max_gap_sec=120):
    """
    Calculate range rate from consecutive observations.

    Args:
        ranges_km:    array of range values
        times:        list of datetime objects
        max_rate:     physical limit for LEO (km/s)
        max_gap_sec:  max time gap between obs

    Returns:
        array of range_rate values (NaN for first obs)
    """
    rates = np.full(len(ranges_km), np.nan)
    for i in range(1, len(ranges_km)):
        dt = (times[i] - times[i-1]).total_seconds()
        if 0 < dt <= max_gap_sec:
            dr = ranges_km[i] - ranges_km[i-1]
            rate = dr / dt
            if abs(rate) <= max_rate:
                rates[i] = rate
    return rates


def assign_track_ids(df):
    """
    Group observations into tracks.

    Rule: same satellite + same sensor +
          gap <= 120 seconds = same track

    Returns:
        df with track_id filled
        total number of tracks
    """
    df = df.copy().sort_values(
        "ob_time"
    ).reset_index(drop=True)
    df["track_id"] = df["track_id"].astype(object)
    track_counter = 1

    for sat_no in df["sat_no"].unique():
        sat_mask = df["sat_no"] == sat_no
        sat_obs  = df[sat_mask]

        for sensor in sat_obs["sensor_name"].unique():
            sen_mask = sat_obs["sensor_name"] == sensor
            sen_obs  = sat_obs[sen_mask].sort_values(
                "ob_time"
            )
            current_track = []
            prev_time     = None

            for idx, row in sen_obs.iterrows():
                curr_time = pd.to_datetime(row["ob_time"])
                if prev_time is None:
                    current_track = [idx]
                else:
                    gap = (
                        curr_time - prev_time
                    ).total_seconds()
                    if gap <= 120:
                        current_track.append(idx)
                    else:
                        tid = f"TRK{track_counter:06d}"
                        for i in current_track:
                            df.at[i, "track_id"] = tid
                        track_counter += 1
                        current_track = [idx]
                prev_time = curr_time

            if current_track:
                tid = f"TRK{track_counter:06d}"
                for i in current_track:
                    df.at[i, "track_id"] = tid
                track_counter += 1

    return df, track_counter - 1


def run_imputation(con):
    """Run full imputation pipeline."""
    print("Loading observations...")
    df = con.execute("""
        SELECT * FROM observations
        ORDER BY sat_no, ob_time
    """).fetchdf()
    print(f"  {len(df):,} rows loaded")

    # range_km
    print("Calculating range_km...")
    df["range_km"] = df["elevation"].apply(
        estimate_range
    )
    print(f"  Filled: {df.range_km.notna().sum():,}")

    # range_rate_km_s
    print("Calculating range_rate_km_s...")
    df["range_rate_km_s"] = np.nan
    for sat in df["sat_no"].unique():
        mask   = df["sat_no"] == sat
        sat_df = df[mask].copy()
        times  = pd.to_datetime(
            sat_df["ob_time"]
        ).tolist()
        rates  = calculate_range_rate(
            sat_df["range_km"].values, times
        )
        df.loc[mask, "range_rate_km_s"] = rates
    filled = df.range_rate_km_s.notna().sum()
    print(f"  Filled: {filled:,} "
          f"({filled/len(df)*100:.1f}%)")

    # track_id
    print("Assigning track IDs...")
    df, n_tracks = assign_track_ids(df)
    print(f"  {n_tracks} tracks assigned")

    # Save
    con.execute("DROP TABLE IF EXISTS observations_final")
    con.register("df_final", df)
    con.execute("""
        CREATE TABLE observations_final AS
        SELECT * FROM df_final
    """)
    print("  Saved to observations_final ✅")

    return df


if __name__ == "__main__":
    import os

    def find_database():
        for root, dirs, files in os.walk("/content"):
            for file in files:
                if file.endswith(".duckdb"):
                    return os.path.join(root, file)

    con = duckdb.connect(find_database())
    print("=" * 55)
    print("IMPUTATION PIPELINE")
    print("=" * 55)
    df = run_imputation(con)
    print("\nDone ✅")
    con.close()
