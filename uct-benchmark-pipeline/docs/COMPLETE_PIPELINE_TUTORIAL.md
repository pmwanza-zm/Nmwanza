# 🚀 Complete UCT Benchmark Pipeline Tutorial
**Step-by-Step Guide Through All 11 Sections**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Section 1: Configuration](#section1)
4. [Section 2: Authentication](#section2)
5. [Section 3: Orbital Regime Detection](#section3)
6. [Section 4: Search Strategy](#section4)
7. [Section 5: API Query](#section5)
8. [Section 6: Data Validation](#section6)
9. [Section 7: Track Binning](#section7)
10. [Section 8: Tier Routing](#section8)
11. [Section 9: Downsampling](#section9)
12. [Section 10: Simulation Decision](#section10)
13. [Section 11: Simulation](#section11)
14. [Results & Next Steps](#results)

---

## Introduction {#introduction}

### What This Pipeline Does

The UCT Benchmark pipeline processes satellite tracking data through 11 stages:

**Input:** Satellite IDs + Time Range  
**Output:** Validated observations (real + simulated)

### Why 11 Sections?

Each section handles a specific part of the data processing:
- Sections 1-4: Setup & Planning
- Sections 5-7: Data Retrieval & Organization
- Sections 8-10: Quality Control
- Section 11: Gap Filling (Simulation)

### Expected Results

**Example run:**
```
Input: 2 satellites, 30-day period
Retrieved: 95 state vectors
Validated: 93 records
Downsampled: 57 observations
Simulated: 30 synthetic observations
Output: 87 total observations (34.5% synthetic)
```

---

## Prerequisites {#prerequisites}

Before starting:
- ✅ Python 3.12+ installed
- ✅ All dependencies installed (`pip install -r requirements.txt`)
- ✅ UDL credentials in `.env` file
- ✅ Data files in `data/` directory

**Quick check:**
```bash
python --version  # 3.12+
ls .env  # Exists
ls data/referenceTLEs_.csv  # Exists
```

---

## Section 1: Configuration {#section1}

### Purpose
Set up pipeline parameters before execution.

### What It Does
```python
config = {
    'satellite_ids': [26608, 42915],  # Which satellites to track
    'start_time': datetime.now() - timedelta(days=30),  # Start date
    'end_time': datetime.now(),  # End date
    'quality_tier': 'T3',  # Quality level (T1/T2/T3/T4)
    'search_strategy': 'auto',  # Query strategy
}
```

### Understanding Parameters

**satellite_ids:**
- NORAD catalog numbers
- 26608 = Intelsat 10-02 (GEO)
- 42915 = Intelsat 33e (GEO)
- Find more: https://celestrak.org/

**quality_tier:**
- T1: High quality (200 obs/sat, no simulation)
- T2: Standard (50 obs/sat, no simulation)
- T3: Degraded (30 obs/sat, with simulation) ← Default
- T4: Lowest (20 obs/sat, heavy simulation)

**search_strategy:**
- `auto`: Let pipeline decide (recommended)
- `fast`: Few satellites, short time
- `windowed`: Many satellites or long time
- `hybrid`: Check count first, then decide

### Try It Yourself

**Run just Section 1:**
```bash
python individual_sections/pipeline_section_01_configuration.py
```

**Output:**
```
✅ Configuration:
   Satellites: [26608, 42915]
   Time range: 30 days
   Quality tier: T3
```

### Common Modifications

**Different satellites:**
```python
'satellite_ids': [25544],  # ISS
```

**Shorter time range:**
```python
'start_time': datetime.now() - timedelta(days=7),  # Last week
```

**Higher quality:**
```python
'quality_tier': 'T1',  # No downsampling or simulation
```

---

## Section 2: Authentication {#section2}

### Purpose
Connect to UDL API with credentials.

### What It Does
1. Loads credentials from `.env` file
2. Generates authentication token
3. Tests connection

### The Code
```python
from dotenv import load_dotenv
import os

load_dotenv()
username = os.getenv('UDL_USERNAME')
password = os.getenv('UDL_PASSWORD')

from uct_benchmark.api.apiIntegration import UDLTokenGen
token = UDLTokenGen(username, password)
```

### How Authentication Works

**Step 1:** Read credentials
```
.env file → username & password → Python variables
```

**Step 2:** Generate token
```
username:password → Base64 encode → UDL API → token
```

**Step 3:** Use token
```
All API requests → include token in headers → access granted
```

### Troubleshooting

**"No credentials found":**
```bash
# Check .env file exists
cat .env

# Should show:
UDL_USERNAME=your_username
UDL_PASSWORD=your_password
```

**"401 Unauthorized":**
- Wrong username/password
- Account inactive
- Token expired

**Try:**
```bash
python individual_sections/pipeline_section_02_authentication.py
```

---

## Section 3: Orbital Regime Detection {#section3}

### Purpose
Classify satellites by orbit type (LEO/MEO/GEO/HEO).

### Why This Matters
Different orbits need different processing:
- **LEO** (Low Earth): Fast (90 min period), 6-hour query windows
- **MEO** (Medium): GPS orbits (12 hr period), 12-hour windows
- **GEO** (Geostationary): Slow (24 hr period), 24-hour windows
- **HEO** (Highly Elliptical): Variable, 8-hour windows

### The Math

**Kepler's 3rd Law:**
```
T² = (4π²/μ) × a³

Where:
T = orbital period
μ = Earth's gravitational parameter (398,600 km³/s²)
a = semi-major axis
```

**From TLE, we get mean motion (n):**
```python
mean_motion = 1.0  # revolutions per day (for GEO)
```

**Calculate semi-major axis:**
```python
n_rad_per_sec = mean_motion * (2 * π) / 86400
a = (μ / n²)^(1/3)
```

**Classify:**
```python
if a < 8,378 km: LEO
elif a >= 42,164 km: GEO
else: MEO
```

### Example Results
```
Satellite 26608:
  Mean motion: 1.0027 rev/day
  Semi-major axis: 42,534 km
  Orbital period: 24.3 hours
  Classification: GEO ✅
```

### Try It
```bash
python individual_sections/pipeline_section_03_regime_detection_fixed.py
```

---

## Section 4: Search Strategy Selection {#section4}

### Purpose
Choose optimal way to query the UDL API.

### The Three Strategies

**FAST Strategy:**
```
Use when: ≤5 satellites AND ≤7 days
Method: One query per satellite (full time range)
API calls: num_satellites × 1
Example: 2 satellites = 2 calls
```

**WINDOWED Strategy:**
```
Use when: ≥10 satellites OR ≥30 days
Method: Split time into chunks, query each chunk
API calls: num_windows × num_satellites
Example: 30 days ÷ 24hr windows = 31 windows
         31 windows × 2 satellites = 62 calls
```

**HYBRID Strategy:**
```
Use when: Uncertain data volume
Method: Check count first, then choose FAST or WINDOWED
API calls: 1 (count) + FAST or WINDOWED
```

### Decision Logic
```python
if satellites <= 5 and days <= 7:
    strategy = 'FAST'
elif satellites >= 10 or days >= 30:
    strategy = 'WINDOWED'
else:
    strategy = 'HYBRID'
```

### Our Example
```
Input: 2 satellites, 30 days, GEO regime
Decision: WINDOWED (because days >= 30)
Window size: 24 hours (GEO regime)
Windows: 30 days ÷ 24 hours = 31 windows
API calls: 31 windows × 2 satellites = 62 calls
```

---

## Section 5: API Query Layer {#section5}

### Purpose
Fetch satellite state vector data from UDL.

### WINDOWED Strategy Execution

**Step 1: Create time windows**
```python
windows = []
current = start_time

while current < end_time:
    window_end = current + timedelta(hours=24)
    windows.append((current, window_end))
    current = window_end

# Result: 31 windows for 30 days
```

**Step 2: Query each window**
```python
for window_start, window_end in windows:
    params = []
    for sat in [26608, 42915]:
        params.append({
            'satNo': str(sat),
            'epoch': f"{start}..{end}"
        })
    
    data = asyncUDLBatchQuery(token, 'statevector', params)
    all_data.append(data)
```

**Step 3: Combine results**
```python
sv_df = pd.concat(all_data, ignore_index=True)
```

### What We Got
```
Total queries: 62 (31 windows × 2 satellites)
Total data: 95 state vectors
  Satellite 26608: 28 state vectors
  Satellite 42915: 67 state vectors
Time span: 29 days actual coverage
```

### State Vector Structure

Each record contains:
```
satNo: 26608
epoch: 2026-02-16T06:45:51.371Z
xpos: 12345.67 km (ECI coordinates)
ypos: 23456.78 km
zpos: 34567.89 km
xvel: 1.234 km/s
yvel: 2.345 km/s
zvel: 3.456 km/s
+ 50 more fields (covariance, drag, etc.)
```

---

## Section 6: Data Validation {#section6}

### Purpose
Clean and validate retrieved data.

### Validation Steps

**1. Deduplication**
```python
original = 95 records
duplicates = 2 (same satNo + epoch)
valid = 93 records
```

**2. Field validation**
```python
required_fields = ['satNo', 'epoch', 'xpos', 'ypos', 'zpos', 
                   'xvel', 'yvel', 'zvel']
all present ✅
```

**3. Range validation**
```python
distance = sqrt(xpos² + ypos² + zpos²)
GEO range: 42,165 - 42,534 km ✅
All records within valid range ✅
```

**4. TLE availability**
```python
satellites_with_tle = [26608, 42915]
all_satellites_have_tle ✅
```

### Results
```
Original: 95 state vectors
After deduplication: 93
After validation: 93
Retention rate: 97.9% ✅
```

---

## Section 7: Track Binning {#section7}

### Purpose (for optical observations)
Group observations into continuous tracking passes.

### Our Adaptation
**Original design:** Dense optical observations (30-sec intervals)
**Our data:** Sparse state vectors (hours apart)

**Solution:** Assign track IDs but don't filter
```python
# Create track IDs based on time gaps
gap_threshold = 6 hours  # For GEO
if gap > 6 hours: start new track

# Result: 64 tracks created
# No filtering applied (would remove all data)
```

### Why We Adapted
```
Optical observations:
  08:00:00, 08:00:30, 08:01:00 → Track 1 (3 obs) ✅
  [gap]
  14:00:00, 14:00:30 → Track 2 (2 obs) ❌ filtered

State vectors:
  00:00 → Track 1 (1 obs) ❌ would be filtered
  06:00 → Track 2 (1 obs) ❌ would be filtered
  12:00 → Track 3 (1 obs) ❌ would be filtered
  
All data would be removed! So we skip filtering.
```

---

## Section 8: Tier Routing {#section8}

### Purpose
Determine required processing based on quality tier.

### Tier Decision Matrix

| Tier | Max Obs/Sat | Downsampling? | Simulation? |
|------|-------------|---------------|-------------|
| T1   | 200         | No            | No          |
| T2   | 50          | Yes           | No          |
| T3   | 30          | Yes           | Yes         |
| T4   | 20          | Yes           | Yes         |

### Our Case: T3

**Check volumes:**
```
Satellite 26608: 27 obs ≤ 30 limit ✅ (no downsampling needed)
Satellite 42915: 66 obs > 30 limit ⚠️ (downsampling required)
```

**Routing decision:**
```
Proceed to Section 9 (Downsampling): YES
Proceed to Section 11 (Simulation): YES
```

---

## Section 9: Downsampling {#section9}

### Purpose
Reduce observation density to meet tier limits.

### Algorithm: Uniform Sampling
```python
max_obs = 30  # T3 limit

for satellite:
    if count > max_obs:
        # Select evenly spaced indices
        indices = linspace(0, count-1, max_obs)
        keep observations at these indices
```

### Example: Satellite 42915

**Before:**
```
66 observations over 28 days
Mean gap: 10.1 hours
```

**After:**
```
30 observations (selected uniformly)
Mean gap: 23.7 hours
66 → 30 = 45.5% retained
```

### Results
```
Satellite 26608: 27 → 27 (no change, within limit)
Satellite 42915: 66 → 30 (downsampled)
Total: 93 → 57 observations
Retention: 61.3%
```

---

## Section 10: Simulation Decision {#section10}

### Purpose
Check if simulation should run.

### Requirements Checklist

**1. Tier requires simulation?**
```
T3: YES ✅
```

**2. Minimum observations?**
```
Have: 57 observations
Need: ≥3
Result: YES ✅
```

**3. Orbital period coverage?**
```
Satellite 26608:
  Period: 24.3 hours
  Time span: 666.9 hours
  Coverage: 27.5 periods ✅

Satellite 42915:
  Period: 23.9 hours
  Time span: 687.8 hours
  Coverage: 28.7 periods ✅
```

### Decision
```
All requirements met → PROCEED TO SIMULATION ✅
```

---

## Section 11: Simulation {#section11}

### Purpose
Fill observation gaps with synthetic observations.

### Algorithm Overview

**Step 1: Gap Detection**
```
Divide time window into bins (10 bins per orbital period)
Identify empty or sparse bins
Generate synthetic epochs at bin centers
```

**Step 2: Track Generation**
```
For each synthetic epoch:
  Create track of 3-5 observations (30-sec spacing)
```

**Step 3: Propagation**
```
For each synthetic time:
  Use SGP4 to propagate TLE
  Get satellite position at that time
```

**Step 4: Visibility**
```
Check if satellite visible from sensor:
  - Above horizon (elevation > 0°)
  - In sunlight (not in Earth's shadow)
  - Above minimum elevation (typically 6°)
```

**Step 5: Add Noise**
```
Add realistic measurement errors:
  - Angular error: 0.3-0.5 arcseconds
  - Timing error: ~1 millisecond
```

**Step 6: Tag & Merge**
```
Mark: is_simulated = True
Combine with real observations
Sort by time
```

### Results

**Input:**
```
57 real observations
  Satellite 26608: 27
  Satellite 42915: 30
```

**Generated:**
```
30 synthetic observations
  Satellite 26608: 15
  Satellite 42915: 15
```

**Output:**
```
87 total observations
  Satellite 26608: 42 (+56% increase)
  Satellite 42915: 45 (+50% increase)
Synthetic ratio: 34.5%
```

**Gap Reduction:**
```
Before: Mean 24.6h, Max 70.2h
After: Mean 15.9h, Max 47.9h
Improvement: 35% reduction
```

---

## Results & Next Steps {#results}

### Pipeline Summary
```
✅ Section 1: Configuration complete
✅ Section 2: Authentication successful
✅ Section 3: Regime detection (GEO)
✅ Section 4: Strategy selection (WINDOWED)
✅ Section 5: API query (95 state vectors)
✅ Section 6: Validation (93 valid)
✅ Section 7: Track binning (64 tracks)
✅ Section 8: Tier routing (T3)
✅ Section 9: Downsampling (57 obs)
✅ Section 10: Simulation decision (PROCEED)
✅ Section 11: Simulation (30 synthetic)

Final: 95 → 87 observations (34.5% synthetic)
Processing time: ~5 minutes
Success rate: 100%
```

### What You Learned

- How to configure satellite tracking pipelines
- UDL API authentication and querying
- Orbital mechanics (regime classification)
- Data validation and quality control
- Downsampling strategies
- Gap-filling simulation with SGP4

### Next Steps

1. **Experiment with different configurations:**
   - Try different satellites
   - Change time ranges
   - Test different quality tiers

2. **Explore individual sections:**
   - Run each section script separately
   - Modify parameters
   - Understand each component

3. **Read the code:**
   - See `COMPLETE_ANNOTATED_CODE.md`
   - Understand implementation details
   - Learn Python best practices

4. **Contribute:**
   - Report bugs
   - Suggest improvements
   - Share your results

---

**Congratulations!** You've completed the full pipeline tutorial! 🎉

**Patrick Mwanza** | UCT Benchmark | Feb 2026
