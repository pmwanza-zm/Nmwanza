"""
Event Labeling Pipeline
========================
Labels events in UCT benchmark observations.

Events detected:
  SPARSE_OBJECT     - satellite with < 100 obs in window
  SINGLE_OBS_TRACK  - track with only 1 observation
  MANEUVER          - sudden range_rate change between tracks
  CONJUNCTION       - close approach warning from UDL
  TRACK_GAP         - 12+ hour observation gap

Results (Jan 24-28 2026, 11 satellites):
  TRACK_GAP            19 events
  SPARSE_OBJECT         5 events
  CONJUNCTION           3 events
  SINGLE_OBS_TRACK      2 events
  MANEUVER              1 event
  Total:               30 events
"""

import duckdb
import pandas as pd
import numpy as np
import requests
import base64
import getpass
import uuid
import os
from datetime import datetime, timezone


# ─────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────
SAT_NOS = [
    19751, 22314, 23613, 24876, 27566,
    32711, 39070, 39086, 39504, 40730, 42915
]

TIME_RANGE = (
    "2026-01-24T00:00:00.000Z"
    ".."
    "2026-01-28T23:59:59.000Z"
)

GAP_THRESHOLD_HRS  = 12    # hours before flagging gap
MANEUVER_THRESHOLD = 0.5   # km/s delta range_rate
SPARSE_THRESHOLD   = 100   # obs count below = sparse


# ─────────────────────────────────────────────────
# UDL CONNECTION
# ─────────────────────────────────────────────────
def get_headers(username, password):
    token = base64.b64encode(
        "{}:{}".format(username, password).encode()
    ).decode("ascii")
    return {"Authorization": "Basic " + token}


def pull_udl(service, params, headers):
    r = requests.get(
        "https://unifieddatalibrary.com/udl/"
        + service,
        headers=headers,
        params=params,
        timeout=60
    )
    if r.status_code != 200:
        print(f"  Error {r.status_code}: "
              f"{r.text[:100]}")
        return []
    rows = r.json()
    return rows if isinstance(rows, list) \
           else rows.get("data", [])


# ─────────────────────────────────────────────────
# TRACK BUILDING
# ─────────────────────────────────────────────────
def build_tracks(df_eo):
    """Group observations into tracks by satellite
    and sensor. Gap > 120s = new track."""
    df_eo = df_eo.copy()
    df_eo["obTime"] = pd.to_datetime(df_eo["obTime"])
    df_eo["range"]  = pd.to_numeric(
        df_eo["range"], errors="coerce"
    )
    df_eo["track_id"]   = None
    df_eo["range_rate"] = np.nan

    track_counter = 1
    track_stats   = []

    for sat in df_eo["satNo"].unique():
        for sensor in df_eo[
            df_eo["satNo"] == sat
        ]["idSensor"].unique():
            mask   = (
                (df_eo["satNo"] == sat) &
                (df_eo["idSensor"] == sensor)
            )
            sen_df = df_eo[mask].sort_values("obTime")
            track     = []
            prev_time = None

            for idx, row in sen_df.iterrows():
                t = row["obTime"]
                if prev_time is None:
                    track = [idx]
                else:
                    gap = (t - prev_time).total_seconds()
                    if gap <= 120:
                        track.append(idx)
                    else:
                        if track:
                            tid = f"TRK{track_counter:06d}"
                            df_eo.loc[track, "track_id"] = tid
                            ts = df_eo.loc[track[0],  "obTime"]
                            te = df_eo.loc[track[-1], "obTime"]
                            track_stats.append({
                                "track_id": tid,
                                "sat_no":   sat,
                                "sensor":   sensor,
                                "n_obs":    len(track),
                                "start":    ts,
                                "end":      te,
                                "duration": (te-ts).total_seconds()
                            })
                            track_counter += 1
                        track = [idx]
                prev_time = t

            if track:
                tid = f"TRK{track_counter:06d}"
                df_eo.loc[track, "track_id"] = tid
                ts = df_eo.loc[track[0],  "obTime"]
                te = df_eo.loc[track[-1], "obTime"]
                track_stats.append({
                    "track_id": tid,
                    "sat_no":   sat,
                    "sensor":   sensor,
                    "n_obs":    len(track),
                    "start":    ts,
                    "end":      te,
                    "duration": (te-ts).total_seconds()
                })
                track_counter += 1

    # Calculate range rate
    for sat in df_eo["satNo"].unique():
        mask   = df_eo["satNo"] == sat
        sat_df = df_eo[mask].sort_values("obTime")
        rates  = np.full(len(sat_df), np.nan)
        for i in range(1, len(sat_df)):
            dt = (
                sat_df["obTime"].iloc[i] -
                sat_df["obTime"].iloc[i-1]
            ).total_seconds()
            if 0 < dt <= 120:
                dr = (sat_df["range"].iloc[i] -
                      sat_df["range"].iloc[i-1])
                rate = dr / dt
                if abs(rate) <= 8:
                    rates[i] = rate
        df_eo.loc[mask, "range_rate"] = rates

    df_tracks = pd.DataFrame(track_stats)
    if len(df_tracks) > 0:
        df_tracks["start"] = pd.to_datetime(
            df_tracks["start"]
        )
        df_tracks["end"] = pd.to_datetime(
            df_tracks["end"]
        )
    return df_eo, df_tracks


# ─────────────────────────────────────────────────
# EVENT DETECTION
# ─────────────────────────────────────────────────
def label_events(df_eo, df_tracks, df_conj):
    """Run all 5 event detection methods."""
    all_events = []

    def add(sat_no, event_type, event_time,
            track_id, confidence, source, details):
        all_events.append({
            "id":         str(uuid.uuid4()),
            "sat_no":     int(sat_no),
            "event_type": event_type,
            "event_time": str(event_time),
            "track_id":   str(track_id),
            "confidence": float(confidence),
            "source":     source,
            "details":    str(details),
            "created_at": datetime.now(
                timezone.utc
            ).isoformat()
        })

    # Event 1 — Sparse objects
    sat_counts = df_eo.groupby(
        "satNo"
    ).size().reset_index(name="n_obs")
    for _, row in sat_counts[
        sat_counts["n_obs"] < SPARSE_THRESHOLD
    ].iterrows():
        first = df_eo[
            df_eo["satNo"] == row["satNo"]
        ]["obTime"].min()
        add(row["satNo"], "SPARSE_OBJECT", first,
            "N/A", 1.0, "COMPUTED",
            {"n_obs": int(row["n_obs"]),
             "threshold": SPARSE_THRESHOLD})

    # Event 2 — Single obs tracks
    for _, row in df_tracks[
        df_tracks["n_obs"] == 1
    ].iterrows():
        add(row["sat_no"], "SINGLE_OBS_TRACK",
            str(row["start"]), row["track_id"],
            0.7, "COMPUTED",
            {"reason": "only 1 observation",
             "sensor": row["sensor"]})

    # Event 3 — Maneuvers
    for sat in df_eo["satNo"].unique():
        sat_tr = df_tracks[
            df_tracks["sat_no"] == sat
        ].sort_values("start").reset_index(drop=True)
        if len(sat_tr) < 2:
            continue
        for i in range(1, len(sat_tr)):
            t1  = sat_tr.iloc[i-1]
            t2  = sat_tr.iloc[i]
            gap = (
                t2["start"] - t1["end"]
            ).total_seconds()
            if gap < 60 or gap > 7200:
                continue
            end_rr = df_eo[
                df_eo["track_id"] == t1["track_id"]
            ].tail(3)["range_rate"].median()
            start_rr = df_eo[
                df_eo["track_id"] == t2["track_id"]
            ].head(3)["range_rate"].median()
            if pd.isna(end_rr) or pd.isna(start_rr):
                continue
            delta = abs(start_rr - end_rr)
            if delta > MANEUVER_THRESHOLD:
                add(sat, "MANEUVER",
                    str(t2["start"]),
                    t2["track_id"],
                    min(0.5 + delta*0.1, 0.95),
                    "COMPUTED",
                    {"delta_range_rate": round(
                        float(delta), 4),
                     "gap_seconds": round(gap, 1)})

    # Event 4 — Conjunctions
    for _, row in df_conj.iterrows():
        try:
            sat1 = int(row["satNo1"]) \
                   if pd.notna(row["satNo1"]) else None
            sat2 = int(row["satNo2"]) \
                   if pd.notna(row["satNo2"]) else None
        except Exception:
            continue
        matched = None
        if sat1 and sat1 in SAT_NOS:
            matched = sat1
        elif sat2 and sat2 in SAT_NOS:
            matched = sat2
        if matched is None:
            continue
        dist = float(row["missDistance"]) \
               if pd.notna(row.get("missDistance")) \
               else 999.0
        conf = (0.99 if dist < 1   else
                0.85 if dist < 10  else
                0.60 if dist < 100 else 0.30)
        add(matched, "CONJUNCTION",
            str(row.get("tca", "")),
            "N/A", conf, "UDL",
            {"sat1": sat1, "sat2": sat2,
             "missDistance": round(dist, 3)})

    # Event 5 — Track gaps
    for sat in df_eo["satNo"].unique():
        sat_df = df_eo[
            df_eo["satNo"] == sat
        ].sort_values("obTime").reset_index(drop=True)
        if len(sat_df) < 2:
            continue
        total_hrs = (
            sat_df["obTime"].max() -
            sat_df["obTime"].min()
        ).total_seconds() / 3600
        if total_hrs < GAP_THRESHOLD_HRS:
            continue
        for i in range(1, len(sat_df)):
            gap_hrs = (
                sat_df["obTime"].iloc[i] -
                sat_df["obTime"].iloc[i-1]
            ).total_seconds() / 3600
            if gap_hrs >= GAP_THRESHOLD_HRS:
                add(sat, "TRACK_GAP",
                    str(sat_df["obTime"].iloc[i-1]),
                    "N/A", 0.6, "COMPUTED",
                    {"gap_hours": round(gap_hrs, 2),
                     "threshold": GAP_THRESHOLD_HRS})

    return pd.DataFrame(all_events)


# ─────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────
def run(db_path, username, password):
    headers = get_headers(username, password)
    con     = duckdb.connect(db_path)

    print("Loading observations...")
    df_eo = con.execute("""
        SELECT satNo, obTime, ra, declination,
               azimuth, elevation, range, idSensor
        FROM eoobservation
        ORDER BY satNo, obTime
    """).fetchdf()
    print(f"  {len(df_eo):,} observations")

    print("Building tracks...")
    df_eo, df_tracks = build_tracks(df_eo)
    print(f"  {len(df_tracks):,} tracks")

    print("Loading conjunctions...")
    df_conj = con.execute(
        "SELECT * FROM conjunction"
    ).fetchdf()

    print("Labeling events...")
    df_events = label_events(df_eo, df_tracks, df_conj)
    print(f"  {len(df_events):,} events labeled")

    con.execute("DROP TABLE IF EXISTS events")
    con.register("df_ev", df_events)
    con.execute("CREATE TABLE events AS SELECT * FROM df_ev")

    con.execute("DROP TABLE IF EXISTS tracks")
    con.register("df_tr", df_tracks)
    con.execute("CREATE TABLE tracks AS SELECT * FROM df_tr")

    print("\nEvents by type:")
    print(con.execute("""
        SELECT event_type,
               COUNT(*) as count,
               ROUND(AVG(confidence),3) as avg_conf
        FROM events
        GROUP BY event_type
        ORDER BY count DESC
    """).fetchdf().to_string(index=False))

    con.close()
    print("\nDone ✅")


if __name__ == "__main__":
    username = input("UDL username: ")
    password = getpass.getpass("UDL password: ")
    run(
        db_path  = "/content/uct_benchmark.duckdb",
        username = username,
        password = password
    )
