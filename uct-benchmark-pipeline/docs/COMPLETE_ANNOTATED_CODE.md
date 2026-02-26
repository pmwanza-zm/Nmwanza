# 💻 Complete Annotated Code
**Line-by-Line Explanation of the Pipeline**

---

## Table of Contents

1. [Imports & Setup](#imports)
2. [Configuration Block](#configuration)
3. [Authentication](#authentication)
4. [Regime Detection](#regime)
5. [Search Strategy](#strategy)
6. [API Query Logic](#query)
7. [Data Validation](#validation)
8. [Track Binning](#binning)
9. [Tier Routing](#routing)
10. [Downsampling](#downsampling)
11. [Simulation Logic](#simulation)
12. [Helper Functions](#helpers)

---

## Imports & Setup {#imports}

### Standard Library Imports
```python
import os
import sys
from datetime import datetime, timedelta
import math
```

**Why these?**
- `os`: File paths, environment variables
- `sys`: System configuration, exit codes
- `datetime`: Time calculations, UTC handling
- `math`: Orbital mechanics calculations (π, sqrt, etc.)

### Data Processing
```python
import pandas as pd
import numpy as np
```

**pandas:**
- DataFrame operations (like Excel in Python)
- Filter, sort, group satellite data
- Read/write CSV files

**numpy:**
- Numerical arrays
- Fast math operations
- Random number generation (noise)

### API & Networking
```python
import requests
import aiohttp
import asyncio
from dotenv import load_dotenv
```

**requests:** Synchronous HTTP (simple API calls)  
**aiohttp:** Asynchronous HTTP (batch queries, faster)  
**asyncio:** Event loop for concurrent operations  
**dotenv:** Load credentials from `.env` file

### UCT Benchmark Modules
```python
from uct_benchmark.api.apiIntegration import (
    UDLTokenGen,           # Generate auth token
    UDLQuery,              # Single API query
    asyncUDLBatchQuery,    # Batch API queries
)
```

**Why custom modules?**
- Encapsulate UDL API logic
- Reusable across projects
- Easier testing and maintenance

---

## Configuration Block {#configuration}

### Lines 50-65: Pipeline Parameters
```python
config = {
    'satellite_ids': [26608, 42915],
    'start_time': datetime.now() - timedelta(days=30),
    'end_time': datetime.now(),
    'quality_tier': 'T3',
    'search_strategy': 'auto',
}
```

**Breaking it down:**
```python
'satellite_ids': [26608, 42915]
```
- NORAD catalog numbers (unique satellite IDs)
- Can be 1-100+ satellites
- Found at celestrak.org or space-track.org
```python
'start_time': datetime.now() - timedelta(days=30)
```
- `datetime.now()` = current moment (UTC)
- `timedelta(days=30)` = 30 days before
- Result: query last 30 days of data
```python
'quality_tier': 'T3'
```
- T1 = highest quality, no simulation
- T2 = standard, no simulation
- T3 = degraded, with simulation (default)
- T4 = lowest, heavy simulation
```python
'search_strategy': 'auto'
```
- `auto` = let pipeline decide
- `fast` = single query per satellite
- `windowed` = split time into chunks
- `hybrid` = check count, then decide

---

## Authentication {#authentication}

### Lines 70-85: UDL Token Generation
```python
load_dotenv()
username = os.getenv('UDL_USERNAME')
password = os.getenv('UDL_PASSWORD')
```

**What `load_dotenv()` does:**
```
1. Look for .env file in current directory
2. Read each line: KEY=value
3. Set as environment variables: os.environ['KEY'] = value
```

**Security note:**
- Never hardcode credentials in Python files
- `.env` is in `.gitignore` (not committed)
- Each user has their own `.env` with their credentials
```python
if not username or not password:
    raise ValueError("No UDL credentials found! Create .env file")
```
- Fail fast if credentials missing
- Better to crash early than fail 5 minutes in
```python
token = UDLTokenGen(username, password)
```
**Inside UDLTokenGen:**
```python
def UDLTokenGen(username, password):
    # Combine credentials
    credentials = f"{username}:{password}"
    
    # Encode to Base64
    encoded = base64.b64encode(credentials.encode()).decode()
    
    # Create Basic Auth header
    return f"Basic {encoded}"
```

**Result:**
```
Username: patrick.mwanza
Password: SecurePass123
Token: Basic cGF0cmljay5td2FuemE6U2VjdXJlUGFzczEyMw==
```

---

## Regime Detection {#regime}

### Lines 90-150: Orbital Classification
```python
def detect_orbital_regime(satellite_id, tle_df):
    """Classify satellite orbit type using Kepler's 3rd Law"""
```

**Step 1: Get TLE data**
```python
tle_row = tle_df[tle_df['satNo'] == satellite_id].iloc[0]
mean_motion = float(tle_row['meanMotion'])
eccentricity = float(tle_row['eccentricity'])
```

**Why float()?**
- TLE data might be strings: "1.0027"
- Need numbers for math: 1.0027
- Explicit conversion prevents type errors

**Step 2: Calculate semi-major axis**
```python
MU = 398600.4418  # km³/s² (Earth's gravitational parameter)
n_rad_per_sec = mean_motion * (2 * math.pi) / 86400
a_km = (MU / (n_rad_per_sec ** 2)) ** (1/3)
```

**The math explained:**

Mean motion in revolutions/day → radians/second:
```
1 rev/day × (2π rad/rev) ÷ 86400 sec/day = n rad/s
```

Kepler's 3rd Law rearranged:
```
T² = (4π²/μ) × a³
n² = μ / a³
a³ = μ / n²
a = (μ / n²)^(1/3)
```

**Step 3: Classify orbit**
```python
if a_km < 8378:
    return 'LEO', 6    # Low Earth, 6-hour windows
elif 8378 <= a_km < 20000:
    return 'MEO', 12   # Medium (GPS), 12-hour windows
elif a_km >= 42164:
    return 'GEO', 24   # Geostationary, 24-hour windows
else:
    return 'HEO', 8    # Highly Elliptical, 8-hour windows
```

**Threshold values:**
- 8,378 km = 2,000 km altitude (LEO upper limit)
- 20,000 km = MEO/GEO boundary
- 42,164 km = Geostationary altitude

**Example:**
```
Input: Satellite 26608
  Mean motion: 1.0027 rev/day
  Eccentricity: 0.0001

Calculation:
  n = 1.0027 × 2π / 86400 = 7.292e-5 rad/s
  a = (398600 / (7.292e-5)²)^(1/3) = 42,534 km
  
Classification: GEO (a ≥ 42,164)
Window size: 24 hours
```

---

## Search Strategy {#strategy}

### Lines 155-200: Query Strategy Selection
```python
def select_search_strategy(satellites, days, regime):
    """Choose optimal API query approach"""
```

**Decision tree:**
```python
if strategy == 'auto':
    if num_satellites <= 5 and days <= 7:
        return 'FAST'
```
**Why?** 
- Few satellites + short time = small data volume
- One query per satellite is efficient
- Example: 5 sats × 1 query = 5 API calls
```python
    elif num_satellites >= 10 or days >= 30:
        return 'WINDOWED'
```
**Why?**
- Many satellites or long time = large data volume
- Single query might timeout or return too much data
- Split into manageable chunks
- Example: 30 days ÷ 24hr = 31 windows, 2 sats = 62 calls
```python
    else:
        return 'HYBRID'
```
**Why?**
- Uncertain data volume
- Check record count first
- If count < 10,000 → use FAST
- If count ≥ 10,000 → use WINDOWED

**Our case:**
```
Satellites: 2 (≤ 5) ✅
Days: 30 (≥ 30) ⚠️
Decision: WINDOWED (days trigger)
```

---

## API Query Logic {#query}

### Lines 205-350: WINDOWED Strategy Implementation
```python
async def fetch_windowed_data(token, satellites, start, end, window_hours):
    """Query API in time windows"""
```

**Step 1: Create time windows**
```python
windows = []
current_time = start_time

while current_time < end_time:
    window_end = current_time + timedelta(hours=window_hours)
    windows.append((current_time, window_end))
    current_time = window_end
```

**Example:**
```
Start: 2026-01-27 00:00
End: 2026-02-26 00:00
Window size: 24 hours

Windows created:
  [2026-01-27 00:00 to 2026-01-28 00:00]
  [2026-01-28 00:00 to 2026-01-29 00:00]
  ...
  [2026-02-25 00:00 to 2026-02-26 00:00]

Total: 31 windows
```

**Step 2: Build query parameters**
```python
params = []
for satellite_id in satellite_ids:
    for window_start, window_end in windows:
        params.append({
            'satNo': str(satellite_id),
            'epoch': f"{to_udl_time(window_start)}..{to_udl_time(window_end)}"
        })
```

**Result:**
```
params = [
    {'satNo': '26608', 'epoch': '2026-01-27T00:00:00Z..2026-01-28T00:00:00Z'},
    {'satNo': '26608', 'epoch': '2026-01-28T00:00:00Z..2026-01-29T00:00:00Z'},
    ...
    {'satNo': '42915', 'epoch': '2026-02-25T00:00:00Z..2026-02-26T00:00:00Z'},
]

Total params: 31 windows × 2 satellites = 62
```

**Step 3: Batch async query**
```python
async with aiohttp.ClientSession() as session:
    tasks = []
    for param in params:
        task = query_single_window(session, token, param)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
```

**Why async?**
```
Synchronous (slow):
  Query 1 → wait 2 sec → Query 2 → wait 2 sec → ...
  Total: 62 × 2 = 124 seconds

Asynchronous (fast):
  All 62 queries start at once
  Wait for slowest (maybe 5-10 seconds)
  Total: ~10 seconds
```

**Step 4: Combine results**
```python
all_data = []
for result in results:
    if result:  # Skip failed queries
        all_data.append(result)

sv_df = pd.concat(all_data, ignore_index=True)
```

**Result:**
```
Retrieved: 95 state vectors
  Satellite 26608: 28 records
  Satellite 42915: 67 records
Failed queries: 0
Success rate: 100%
```

---

## Data Validation {#validation}

### Lines 355-410: Deduplication & Validation
```python
def validate_data(sv_df):
    """Clean and validate state vectors"""
```

**Step 1: Deduplication**
```python
original_count = len(sv_df)
sv_df = sv_df.drop_duplicates(subset=['satNo', 'epoch'])
duplicates = original_count - len(sv_df)
```

**What are duplicates?**
```
Record 1: satNo=26608, epoch=2026-02-15T12:00:00Z
Record 2: satNo=26608, epoch=2026-02-15T12:00:00Z  ← Duplicate!

Cause: Overlapping time windows
  Window 1: 12:00 - 00:00 (next day)
  Window 2: 00:00 - 12:00 (next day)
  Both contain 12:00!
```

**Result:**
```
Original: 95 records
Duplicates: 2
Valid: 93 records
Retention: 97.9%
```

**Step 2: Field validation**
```python
required_fields = ['satNo', 'epoch', 'xpos', 'ypos', 'zpos', 
                   'xvel', 'yvel', 'zvel']
missing = [f for f in required_fields if f not in sv_df.columns]

if missing:
    raise ValueError(f"Missing fields: {missing}")
```

**Step 3: Range validation**
```python
sv_df['distance'] = np.sqrt(
    sv_df['xpos']**2 + 
    sv_df['ypos']**2 + 
    sv_df['zpos']**2
)

# GEO should be ~42,000 km
if (sv_df['distance'] < 35000).any() or (sv_df['distance'] > 50000).any():
    print("⚠️  Warning: Some orbits outside expected GEO range")
```

---

## Downsampling {#downsampling}

### Lines 500-580: Uniform Sampling Algorithm
```python
def apply_downsampling(df, tier_config):
    """Reduce observation density uniformly"""
    
    max_obs_per_sat = tier_config['max_obs_per_sat']
```

**For each satellite:**
```python
for sat_id in df['satNo'].unique():
    sat_data = df[df['satNo'] == sat_id].sort_values('obTime')
    
    if len(sat_data) > max_obs_per_sat:
        # Calculate indices to keep
        indices = np.linspace(0, len(sat_data)-1, max_obs_per_sat)
        indices = indices.astype(int)
        
        # Select observations at those indices
        downsampled = sat_data.iloc[indices]
```

**How linspace works:**
```
Input: 66 observations, want 30

np.linspace(0, 65, 30) = 
  [0, 2.23, 4.46, 6.69, 8.92, ... , 62.77, 65]

Convert to integers:
  [0, 2, 4, 6, 8, ... , 62, 65]

Result: Evenly spaced observations
```

**Visual example:**
```
Original (66 obs):
  |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||

Downsampled (30 obs):
  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||  ||

Spacing is uniform!
```

**Results:**
```
Satellite 26608:
  Original: 27 obs
  Limit: 30 obs
  Action: NO downsampling (within limit)
  Final: 27 obs

Satellite 42915:
  Original: 66 obs
  Limit: 30 obs
  Action: Downsample
  Final: 30 obs

Total: 93 → 57 observations (61.3% retained)
```

---

## Simulation Logic {#simulation}

### Lines 700-950: Gap-Filling Implementation
```python
def generate_synthetic_observations(df, tle_df, tier):
    """Fill gaps with simulated observations"""
```

**Step 1: Bin time period**
```python
period_hours = 24.3  # Orbital period for GEO
bins_per_period = 10
bin_size = period_hours / bins_per_period  # 2.43 hours

time_span = (df['obTime'].max() - df['obTime'].min()).total_seconds() / 3600
num_bins = int(time_span / bin_size)  # 275 bins for 28 days
```

**Step 2: Identify gaps**
```python
obs_per_bin = df.groupby(pd.cut(df['obTime'], bins=num_bins)).size()
empty_bins = obs_per_bin[obs_per_bin == 0]  # Bins with 0 observations
```

**Step 3: Generate synthetic epochs**
```python
synthetic_epochs = []
for bin in empty_bins:
    epoch = bin.mid  # Middle of time bin
    # Create track of 3-5 observations around this epoch
    for i in range(3):
        synthetic_epochs.append(epoch + timedelta(seconds=i*30))
```

**Step 4: Propagate with SGP4**
```python
from sgp4.earth_gravity import wgs84
from sgp4.io import twoline2rv

# Get TLE
tle1 = tle_row['tle_line1']
tle2 = tle_row['tle_line2']
satellite = twoline2rv(tle1, tle2, wgs84)

# Propagate to epoch
position, velocity = satellite.propagate(
    year, month, day, hour, minute, second
)
```

**What SGP4 does:**
```
Input: TLE (orbital elements at epoch T0)
       Target time T1

Process:
  1. Calculate time delta: Δt = T1 - T0
  2. Apply Kepler's equations
  3. Account for perturbations:
     - Earth's oblateness (J2, J3, J4)
     - Atmospheric drag
     - Solar radiation pressure
  4. Output position & velocity at T1

Result: (x, y, z, vx, vy, vz) in ECI coordinates
```

**Step 5: Check visibility**
```python
# Convert ECI to topocentric (sensor view)
ra, dec = eci_to_radec(x, y, z, sensor_lat, sensor_lon)

# Check if above horizon
elevation = 90 - angular_distance(ra, dec, zenith_ra, zenith_dec)

if elevation > 6:  # Minimum elevation
    if is_in_sunlight(x, y, z, time):
        # Observable!
        synthetic_observations.append({
            'satNo': sat_id,
            'obTime': epoch,
            'ra': ra,
            'declination': dec,
            'is_simulated': True
        })
```

**Step 6: Add noise**
```python
# Realistic measurement errors
ra_noise = np.random.normal(0, 0.3 / 3600)  # 0.3 arcsec
dec_noise = np.random.normal(0, 0.3 / 3600)

ra += ra_noise
dec += dec_noise
```

**Results:**
```
Input: 57 real observations with gaps
Gaps detected: 120 empty bins
Synthetic epochs generated: 360 (120 × 3 obs each)
Passed visibility: 30 observations
Added noise: ✅
Flagged as simulated: ✅

Output: 87 total (57 real + 30 simulated = 34.5% synthetic)
```

---

## Helper Functions {#helpers}

### Time Conversion
```python
def datetime_to_udl(dt):
    """Convert Python datetime to UDL format"""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# Example:
datetime(2026, 2, 26, 12, 30, 0) → "2026-02-26T12:30:00Z"
```

### Coordinate Transformations
```python
def eci_to_radec(x, y, z, time):
    """ECI (Earth-Centered Inertial) to RA/Dec"""
    
    # Distance
    r = sqrt(x² + y² + z²)
    
    # Right Ascension (0-360°)
    ra = atan2(y, x) * 180 / π
    if ra < 0:
        ra += 360
    
    # Declination (-90 to +90°)
    dec = asin(z / r) * 180 / π
    
    return ra, dec
```

**Example:**
```
Position: x=12345, y=23456, z=34567 km
Distance: r = sqrt(12345² + 23456² + 34567²) = 43210 km
RA = atan2(23456, 12345) = 62.3°
Dec = asin(34567 / 43210) = 53.1°
```

---

## Complete Flow Summary
```
1. Configuration      →  Set parameters
2. Authentication     →  Get UDL token
3. Regime Detection   →  Classify orbit (GEO)
4. Search Strategy    →  Choose WINDOWED
5. API Query          →  62 calls → 95 state vectors
6. Validation         →  Remove 2 duplicates → 93
7. Track Binning      →  Create 64 tracks (no filtering)
8. Tier Routing       →  T3 → downsample + simulate
9. Downsampling       →  93 → 57 observations
10. Simulation Check  →  Requirements met ✅
11. Simulation        →  Generate 30 synthetic
    
Output: 87 observations (34.5% synthetic)
Time: ~5 minutes
```

---

**Now you understand every line of code!** 🎓

**Patrick Mwanza** | UCT Benchmark | Feb 2026
