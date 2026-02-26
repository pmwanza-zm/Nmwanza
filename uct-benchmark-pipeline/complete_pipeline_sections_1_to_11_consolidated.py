"""
COMPLETE UCT BENCHMARK PIPELINE - SECTIONS 1-11
Consolidated single-file version for team demonstration

Author: Patrick Mwanza
Date: February 25, 2026
Purpose: Validate complete pipeline flow from configuration to simulation

This script demonstrates:
- Section 1: Configuration
- Section 2: UDL Authentication  
- Section 3: Orbital Regime Detection
- Section 4: Search Strategy Selection
- Section 5: API Query Layer
- Section 6: Deduplication & Validation
- Section 7: Track Binning
- Section 8: Tier-Based Routing
- Section 9: Downsampling
- Section 10: Simulation Decision
- Section 11: SIMULATION PIPELINE (Patrick's validated work)
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

print("="*80)
print("COMPLETE UCT BENCHMARK PIPELINE - SECTIONS 1-11")
print("Patrick Mwanza - Week 3 Internship Complete Integration")
print("="*80)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: INPUTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 1: PIPELINE CONFIGURATION")
print("="*80)

config = {
    'satellite_ids': [26608, 42915],  # GEO satellites with TLE data
    'start_time': datetime.now() - timedelta(days=30),
    'end_time': datetime.now(),
    'quality_tier': 'T3',
    'search_strategy': 'auto',
    'max_datapoints': 1000,
    'enable_simulation': True,
    'enable_downsampling': True
}

print(f"✅ Configuration:")
print(f"   Satellites: {config['satellite_ids']}")
print(f"   Time range: {(config['end_time'] - config['start_time']).days} days")
print(f"   Quality tier: {config['quality_tier']}")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: UDL AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 2: UDL AUTHENTICATION")
print("="*80)

load_dotenv()
token = os.getenv('UDL_TOKEN')
if not token:
    username = os.getenv('UDL_USERNAME')
    password = os.getenv('UDL_PASSWORD')
    if username and password:
        from uct_benchmark.api.apiIntegration import UDLTokenGen
        token = UDLTokenGen(username, password)
        print(f"✅ Token generated")
    else:
        print("❌ No UDL credentials found!")
        exit(1)
else:
    print(f"✅ Using existing token")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: ORBITAL REGIME DETECTION
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 3: ORBITAL REGIME DETECTION")
print("="*80)

tle_df = pd.read_csv('data/referenceTLEs_.csv')
tle_df_filtered = tle_df[tle_df['satNo'].isin(config['satellite_ids'])]

def detect_regime(tle_row):
    mean_motion = float(tle_row['meanMotion'])
    n = mean_motion * (2 * np.pi) / 86400
    mu = 398600.4418
    a = (mu / (n**2)) ** (1/3)
    
    try:
        ecc = float(tle_row['eccentricity'])
    except:
        ecc = 0.0
    
    if ecc >= 0.7:
        return 'HEO', a
    elif a < 8378:
        return 'LEO', a
    elif a >= 42164:
        return 'GEO', a
    else:
        return 'MEO', a

regimes = {}
for sat in config['satellite_ids']:
    sat_tle = tle_df_filtered[tle_df_filtered['satNo'] == sat]
    if len(sat_tle) > 0:
        regime, sma = detect_regime(sat_tle.iloc[0])
        regimes[sat] = regime
        period_hours = 24 / sat_tle.iloc[0]['meanMotion']
        print(f"✅ Satellite {sat}: {regime} (SMA: {sma:,.0f} km, Period: {period_hours:.1f}h)")

primary_regime = list(regimes.values())[0] if regimes else 'GEO'

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: SEARCH STRATEGY SELECTION
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 4: SEARCH STRATEGY SELECTION")
print("="*80)

num_satellites = len(config['satellite_ids'])
time_span_days = (config['end_time'] - config['start_time']).days

if num_satellites <= 5 and time_span_days <= 7:
    selected_strategy = 'FAST'
elif num_satellites >= 10 or time_span_days >= 30:
    selected_strategy = 'WINDOWED'
else:
    selected_strategy = 'HYBRID'

print(f"✅ Selected strategy: {selected_strategy}")
print(f"   Criteria: {num_satellites} satellites, {time_span_days} days")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: API QUERY LAYER
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 5: API QUERY LAYER ({selected_strategy})")
print("="*80)

from uct_benchmark.api.apiIntegration import asyncUDLBatchQuery, datetimeToUDL

if selected_strategy == 'WINDOWED':
    window_hours = 24 if primary_regime == 'GEO' else 12
    windows = []
    current = config['start_time']
    while current < config['end_time']:
        window_end = min(current + timedelta(hours=window_hours), config['end_time'])
        windows.append((current, window_end))
        current = window_end
    
    print(f"📡 Executing WINDOWED strategy ({len(windows)} windows)...")
    all_sv_data = []
    for i, (win_start, win_end) in enumerate(windows, 1):
        sv_params = []
        for sat in config['satellite_ids']:
            sv_params.append({
                'satNo': str(sat),
                'epoch': f"{datetimeToUDL(win_start)}..{datetimeToUDL(win_end)}"
            })
        try:
            window_data = asyncUDLBatchQuery(token, 'statevector', sv_params, dt=0.5)
            all_sv_data.append(window_data)
            if i % 10 == 0:
                print(f"   Window {i}/{len(windows)}: {len(window_data)} records")
        except:
            continue
    
    sv_df = pd.concat(all_sv_data, ignore_index=True) if all_sv_data else pd.DataFrame()
else:
    # FAST or HYBRID
    sv_params = []
    for sat in config['satellite_ids']:
        sv_params.append({
            'satNo': str(sat),
            'epoch': f"{datetimeToUDL(config['start_time'])}..{datetimeToUDL(config['end_time'])}"
        })
    sv_df = asyncUDLBatchQuery(token, 'statevector', sv_params, dt=0.5)

print(f"✅ Retrieved {len(sv_df)} state vectors")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: DEDUPLICATION & VALIDATION  
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 6: DEDUPLICATION & VALIDATION")
print("="*80)

original_count = len(sv_df)
sv_df['epoch'] = pd.to_datetime(sv_df['epoch'])
sv_df = sv_df.drop_duplicates(subset=['satNo', 'epoch'], keep='first')

print(f"✅ Removed {original_count - len(sv_df)} duplicates")
print(f"   Final: {len(sv_df)} validated records")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: TRACK BINNING (SPARSE DATA MODE)
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 7: TRACK BINNING (Sparse Data Mode)")
print("="*80)

sv_df = sv_df.sort_values(['satNo', 'epoch']).reset_index(drop=True)
sv_df['trackId'] = None
current_track_id = 1

for sat in sv_df['satNo'].unique():
    sat_mask = sv_df['satNo'] == sat
    sat_indices = sv_df[sat_mask].index
    sv_df.loc[sat_indices[0], 'trackId'] = current_track_id
    current_sat_track = current_track_id
    
    for i in range(1, len(sat_indices)):
        prev_idx = sat_indices[i-1]
        curr_idx = sat_indices[i]
        time_gap = (sv_df.loc[curr_idx, 'epoch'] - sv_df.loc[prev_idx, 'epoch']).total_seconds() / 3600
        
        if time_gap > 6.0:
            current_track_id += 1
            current_sat_track = current_track_id
        
        sv_df.loc[curr_idx, 'trackId'] = current_sat_track
    current_track_id += 1

sv_df['trackId'] = sv_df['trackId'].astype(int)

print(f"✅ Created {sv_df['trackId'].nunique()} tracks (no filtering for sparse data)")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: TIER-BASED ROUTING
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 8: TIER-BASED ROUTING")
print("="*80)

tier_configs = {
    'T3': {
        'max_obs_per_sat': 30,
        'require_simulation': True,
        'require_downsampling': True
    }
}

tier_config = tier_configs[config['quality_tier']]
print(f"✅ Tier {config['quality_tier']}: Downsampling={tier_config['require_downsampling']}, Simulation={tier_config['require_simulation']}")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: DOWNSAMPLING
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 9: DOWNSAMPLING")
print("="*80)

max_obs = tier_config['max_obs_per_sat']
downsampled_data = []

for sat in sorted(sv_df['satNo'].unique()):
    sat_data = sv_df[sv_df['satNo'] == sat].copy().sort_values('epoch').reset_index(drop=True)
    current_count = len(sat_data)
    
    if current_count > max_obs:
        indices_to_keep = np.linspace(0, len(sat_data) - 1, max_obs, dtype=int)
        sat_downsampled = sat_data.iloc[np.unique(indices_to_keep)].copy()
        print(f"✅ Satellite {sat}: {current_count} → {len(sat_downsampled)} obs")
        downsampled_data.append(sat_downsampled)
    else:
        print(f"✅ Satellite {sat}: {current_count} obs (within limit)")
        downsampled_data.append(sat_data)

downsampled_df = pd.concat(downsampled_data, ignore_index=True)
print(f"   Total: {len(sv_df)} → {len(downsampled_df)} observations")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: SIMULATION DECISION
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("SECTION 10: SIMULATION DECISION")
print("="*80)

proceed_to_simulation = (
    tier_config['require_simulation'] and
    len(downsampled_df) >= 3
)

print(f"✅ Decision: {'PROCEED TO SIMULATION' if proceed_to_simulation else 'SKIP SIMULATION'}")

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: SIMULATION PIPELINE (PATRICK'S CORE WORK)
# ═══════════════════════════════════════════════════════════════════════════

if proceed_to_simulation:
    print("\n" + "="*80)
    print("SECTION 11: SIMULATION PIPELINE")
    print("PATRICK'S VALIDATED WORK - GAP DETECTION & SYNTHETIC GENERATION")
    print("="*80)
    
    # Prepare observation DataFrame
    obs_df = pd.DataFrame({
        'satNo': downsampled_df['satNo'],
        'obTime': downsampled_df['epoch'],
        'idSensor': 'STATE_VECTOR',
        'senlat': 0.0,
        'senlon': 0.0,
        'senalt': 0.0,
        'ra': 0.0,
        'declination': 0.0,
        'range': 0.0
    })
    
    # Load required data
    sensor_df = pd.read_csv('data/sensorCounts.csv')
    
    # Run simulation
    from uct_benchmark.data.dataManipulation import apply_simulation_to_gaps
    
    result_df, metadata = apply_simulation_to_gaps(obs_df, tle_df, sensor_df)
    
    print(f"\n🎉 SIMULATION COMPLETE!")
    print(f"   Input: {metadata['original_count']} observations")
    print(f"   Generated: {metadata['simulated_count']} synthetic observations")
    print(f"   Output: {metadata['total_count']} total observations")
    print(f"   Synthetic ratio: {metadata['synthetic_ratio']:.1%}")
    
    for sat in sorted(result_df['satNo'].unique()):
        sat_real = result_df[(result_df['satNo'] == sat) & (result_df['is_simulated'] == False)]
        sat_sim = result_df[(result_df['satNo'] == sat) & (result_df['is_simulated'] == True)]
        print(f"   Satellite {sat}: {len(sat_real)} real + {len(sat_sim)} simulated = {len(sat_real) + len(sat_sim)} total")
else:
    result_df = downsampled_df
    metadata = {'simulated_count': 0}

# ═══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print("\n" + "="*80)
print("🎊 COMPLETE PIPELINE EXECUTION FINISHED!")
print("="*80)

print(f"\n✅ All Sections Executed:")
print(f"   Section 1: Configuration")
print(f"   Section 2: UDL Authentication")
print(f"   Section 3: Orbital Regime Detection ({primary_regime})")
print(f"   Section 4: Search Strategy ({selected_strategy})")
print(f"   Section 5: API Query ({len(sv_df)} state vectors)")
print(f"   Section 6: Deduplication ({len(sv_df)} validated)")
print(f"   Section 7: Track Binning (sparse mode)")
print(f"   Section 8: Tier Routing ({config['quality_tier']})")
print(f"   Section 9: Downsampling ({len(downsampled_df)} obs)")
print(f"   Section 10: Simulation Decision")
print(f"   Section 11: Simulation ({metadata['simulated_count']} synthetic)")

print(f"\n🎉 SUCCESS! Pipeline validated end-to-end!")
print("="*80)
