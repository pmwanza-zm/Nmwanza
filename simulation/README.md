# UCT Benchmark — Simulation Pipeline

Simulation and imputation pipeline for the UCT Benchmark Dataset.
Fills missing fields in space observation data and generates synthetic
observations for satellites with sparse coverage.

---

## Background

The UCT Benchmark collects observations from 59 optical sensors (EXO prefix)
tracking 11 satellites over a 4-day window (Jan 24–28, 2026). Optical sensors
cannot measure range directly, so three fields arrive empty:

| Field | Missing | Reason | Method |
|---|---|---|---|
| `range_km` | 100% | Optical sensors cannot measure distance | Physics calculation |
| `range_rate_km_s` | 100% | Derived from range over time | Consecutive obs + mean |
| `track_id` | 28% | Observations not grouped into passes | Grouping algorithm |

---

## Files

| File | Purpose |
|---|---|
| `pipeline.py` | **Master script** — runs everything end to end |
| `data_quality.py` | Phase 1: analyze missing data and classify mechanism |
| `imputation.py` | Phase 2: fill range\_km, range\_rate, track\_id |
| `sparse_simulator.py` | Phase 3: generate synthetic obs for sparse satellites |
| `method_comparison.py` | Phase 4: compare Mean vs KNN vs MICE vs VAE |

---

## How To Run

```bash
# Run the full pipeline
python simulation/pipeline.py

# Or run individual steps
python simulation/data_quality.py
python simulation/imputation.py
python simulation/sparse_simulator.py
python simulation/method_comparison.py
```

Requires a `.duckdb` database file accessible under `/content/`.

---

## How Each Field Is Filled

### range\_km (slant range)

Calculated from elevation angle using geometry:

```
range = -R·sin(el) + sqrt((R·sin(el))² + h² + 2Rh)

where:
  R = 6371 km  (Earth radius)
  h = 500 km   (assumed LEO altitude)
  el = elevation angle (available from sensors)
```

Result: 100% filled, values 503–1968 km, elevation-range correlation −0.96.

### range\_rate\_km\_s

Calculated from consecutive observations:

```
range_rate = (range₂ - range₁) / (t₂ - t₁)

Rules:
  - Only if time gap ≤ 120 seconds
  - Clamped to ±8 km/s (physical LEO limit)
  - First observation of each pass = NaN → filled with mean
```

Result: 95% filled by physics, 5% filled by mean imputation.

### track\_id

Grouped by rule:

```
same satellite + same sensor + gap ≤ 120 seconds → same track
```

Result: 865 tracks identified, 100% filled.

---

## Sparse Satellite Simulation

Five satellites had insufficient observations for algorithm evaluation:

| Satellite | Real obs | After simulation | Method |
|---|---|---|---|
| 39086 | 1 | 91 | Typical LEO rates |
| 19751 | 4 | 154 | Motion extrapolation |
| 24876 | 5 | 155 | Motion extrapolation |
| 40730 | 18 | 168 | Motion extrapolation |
| 32711 | 64 | 238 | Motion extrapolation |

All simulated observations are flagged `is_simulated=True`, `data_mode='SIMULATED'`.

---

## Method Comparison Results

Tested on 3,684 held-out rows (20% of known range\_rate values):

| Method | RMSE | MAE | Corr | Time |
|---|---|---|---|---|
| **Mean** | **0.0946** | 0.0051 | ~0.0 | <1s |
| VAE | 0.0946 | 0.0057 | 0.015 | 22s |
| RL-DQN | 0.0947 | 0.0050 | 0.005 | 1324s |
| KNN (k=3) | 0.1374 | 0.0074 | 0.051 | 3s |

### Key Finding

All methods except KNN achieve near-identical RMSE. The RL agent independently
confirmed this by choosing Mean 44% of the time. The reason: `range_rate`
depends on **time** (where the satellite was 10 seconds ago), not on position
features (ra, dec, azimuth, elevation, range). Physics calculation already
captures this correctly for 95% of rows. For the remaining 5% (first
observation of each pass), Mean imputation is optimal.

**Recommendation:**
- Primary: physics calculation (covers 95%)
- Fallback: mean imputation (covers remaining 5%)
- VAE: better suited for generating new observations, not filling missing values

---

## Final Dataset Coverage

| Field | Before | After |
|---|---|---|
| `range_km` | 0% | 100% ✅ |
| `range_rate_km_s` | 0% | 100% ✅ |
| `track_id` | 72% | 100% ✅ |

Total observations: 19,322 real + 804 simulated = **20,126**

---

## Physical Validity Checks

All 690 new simulated observations pass:

- RA: 0–360° ✅
- Declination: −90° to +90° ✅
- Elevation: 5°–85° (horizon limits) ✅
- Azimuth: 0–360° ✅
- Range: 400–2500 km (LEO bounds) ✅

---

## Author

Pat Mwanza — SDA TAP Lab / SpOC UCT Benchmark Project
