"""
Sparse Satellite Simulator
===========================
Generates synthetic observations for satellites
with insufficient real data coverage.

Strategy per satellite:
- 2+ obs: extract motion rates, project forward
- 1 obs:  use typical LEO angular rates

Generated observations are flagged:
  is_simulated = True
  data_mode    = SIMULATED
"""

import duckdb
import pandas as pd
import numpy as np
import uuid
import os
from datetime import datetime, timedelta, timezone


def estimate_range(elevation_deg, altitude_km=500):
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


def extract_motion_rates(obs_df):
    """
    Extract angular velocity from existing track.

    Returns:
        ra_rate, dec_rate, el_rate (deg/sec)
    """
    obs_df = obs_df.sort_values(
        "ob_time"
    ).reset_index(drop=True)

    ra_rates, dec_rates, el_rates = [], [], []

    for i in range(1, len(obs_df)):
        t1 = pd.to_datetime(obs_df["ob_time"].iloc[i-1])
        t2 = pd.to_datetime(obs_df["ob_time"].iloc[i])
        dt = (t2 - t1).total_seconds()
        if 0 < dt <= 120:
            ra_rates.append(
                (obs_df["ra"].iloc[i] -
                 obs_df["ra"].iloc[i-1]) / dt
            )
            dec_rates.append(
                (obs_df["declination"].iloc[i] -
                 obs_df["declination"].iloc[i-1]) / dt
            )
            el_rates.append(
                (obs_df["elevation"].iloc[i] -
                 obs_df["elevation"].iloc[i-1]) / dt
            )

    if not ra_rates:
        return None, None, None

    return (
        np.median(ra_rates),
        np.median(dec_rates),
        np.median(el_rates)
    )


def simulate_tracks(sat_no, obs_df, n_tracks=5,
                    obs_per_track=30,
                    step_seconds=10):
    """
    Generate synthetic observation tracks.

    Each track is placed ~90 minutes after the
    last real observation (one orbital period).

    Args:
        sat_no:        satellite number
        obs_df:        real observations for this sat
        n_tracks:      number of tracks to generate
        obs_per_track: max observations per track
        step_seconds:  time step between observations

    Returns:
        DataFrame of simulated observations
    """
    if len(obs_df) >= 2:
        ra_rate, dec_rate, el_rate = (
            extract_motion_rates(obs_df)
        )
        if ra_rate is None:
            # Fallback to typical LEO rates
            ra_rate, dec_rate, el_rate = (
                0.055, -0.020, -0.008
            )
        base_el = float(obs_df["elevation"].mean())
    else:
        # Single observation — use typical LEO rates
        ra_rate  =  0.055
        dec_rate = -0.020
        el_rate  = -0.008
        base_el  = float(obs_df["elevation"].iloc[0])

    base_ra   = float(obs_df["ra"].iloc[-1])
    base_dec  = float(obs_df["declination"].iloc[-1])
    base_az   = float(obs_df["azimuth"].iloc[-1])
    base_time = pd.to_datetime(obs_df["ob_time"].max())
    sensor    = obs_df["sensor_name"].iloc[-1]

    all_tracks = []

    for i in range(n_tracks):
        track_start = base_time + timedelta(
            seconds=(i + 1) * 90 * 60
        )
        rows = []

        for j in range(obs_per_track):
            dt_sec  = j * step_seconds
            new_el  = base_el  + el_rate  * dt_sec

            if new_el < 5 or new_el > 85:
                break

            new_ra  = (base_ra + ra_rate * dt_sec) % 360
            new_dec = base_dec + dec_rate * dt_sec
            new_az  = (base_az + ra_rate *
                       dt_sec * 0.8) % 360

            rows.append({
                "id": str(uuid.uuid4()),
                "sat_no": int(sat_no),
                "ob_time": track_start + timedelta(
                    seconds=dt_sec
                ),
                "ra": round(new_ra, 6),
                "declination": round(new_dec, 6),
                "range_km": round(
                    estimate_range(new_el), 4
                ),
                "range_rate_km_s": None,
                "azimuth": round(new_az, 6),
                "elevation": round(new_el, 6),
                "sensor_name": sensor,
                "data_mode": "SIMULATED",
                "track_id": (
                    f"TRK_SIM_{sat_no}_{i:03d}"
                ),
                "is_uct": False,
                "is_simulated": True,
                "created_at": datetime.now(
                    timezone.utc
                )
            })

        if rows:
            all_tracks.append(pd.DataFrame(rows))

    return (
        pd.concat(all_tracks, ignore_index=True)
        if all_tracks else pd.DataFrame()
    )


def run_sparse_simulation(con,
                           sparse_threshold=100):
    """Run simulation for all sparse satellites."""
    print("Identifying sparse satellites...")

    sparse_sats = con.execute(f"""
        SELECT sat_no, COUNT(*) as n_obs
        FROM observations
        WHERE is_simulated = false
        GROUP BY sat_no
        HAVING COUNT(*) < {sparse_threshold}
        ORDER BY n_obs
    """).fetchdf()

    print(f"  Found {len(sparse_sats)} sparse sats")

    all_sim = []

    for _, row in sparse_sats.iterrows():
        sat_no = int(row["sat_no"])
        n_real = int(row["n_obs"])

        obs = con.execute(f"""
            SELECT * FROM observations
            WHERE sat_no = {sat_no}
            AND is_simulated = false
            ORDER BY ob_time
        """).fetchdf()

        sim_df = simulate_tracks(sat_no, obs)

        if len(sim_df) > 0:
            all_sim.append(sim_df)
            print(f"  sat {sat_no}: "
                  f"{n_real} real → "
                  f"+{len(sim_df)} simulated")

    if all_sim:
        result = pd.concat(all_sim, ignore_index=True)
        con.execute(
            "DROP TABLE IF EXISTS observations_simulated"
        )
        con.register("sim_result", result)
        con.execute("""
            CREATE TABLE observations_simulated AS
            SELECT * FROM sim_result
        """)
        print(f"\nTotal simulated: {len(result):,}")
        print("Saved to observations_simulated ✅")
        return result

    return pd.DataFrame()


if __name__ == "__main__":
    def find_database():
        for root, dirs, files in os.walk("/content"):
            for file in files:
                if file.endswith(".duckdb"):
                    return os.path.join(root, file)

    con = duckdb.connect(find_database())
    print("=" * 55)
    print("SPARSE SATELLITE SIMULATION")
    print("=" * 55)
    run_sparse_simulation(con)
    print("\nDone ✅")
    con.close()
