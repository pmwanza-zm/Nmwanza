"""
SECTION 3: ORBITAL REGIME DETECTION (FIXED)
Classifies satellites into orbital regimes (LEO/MEO/GEO/HEO)
"""
import json
import pandas as pd
import numpy as np

print("="*80)
print("SECTION 3: ORBITAL REGIME DETECTION")
print("="*80)

# Load configuration and authentication
print("\n📥 Loading previous sections...")
with open('pipeline_config.json', 'r') as f:
    config = json.load(f)
    
with open('pipeline_auth.json', 'r') as f:
    auth = json.load(f)

token = auth['token']
satellite_ids = config['satellite_ids']

print(f"   ✅ Configuration loaded: {len(satellite_ids)} satellites")
print(f"   ✅ Authentication loaded: Token status = {auth['auth_status']}")

# Load local TLE file
print(f"\n📂 Loading TLE data...")
tle_df = pd.read_csv('data/referenceTLEs_.csv')
print(f"   ✅ Loaded {len(tle_df)} TLE records from local file")

# Filter to only our satellites
tle_df_filtered = tle_df[tle_df['satNo'].isin(satellite_ids)]
print(f"   📊 TLE data available for {len(tle_df_filtered)} of {len(satellite_ids)} satellites")

# Manual regime detection function
def detect_regime_manual(tle_row):
    """
    Manually detect orbital regime from TLE parameters
    
    Rules:
    - HEO: eccentricity >= 0.7
    - LEO: SMA < 8,378 km
    - GEO: SMA >= 42,164 km  
    - MEO: everything else
    """
    try:
        # Calculate Semi-Major Axis from mean motion
        # Kepler's 3rd law: T^2 = (4π^2/μ) * a^3
        # where μ = 398600.4418 km³/s² (Earth's gravitational parameter)
        
        mean_motion = float(tle_row['meanMotion'])  # revolutions per day
        
        # Convert to radians per second
        n = mean_motion * (2 * np.pi) / 86400  # rad/s
        
        # Calculate SMA
        mu = 398600.4418  # km³/s²
        a = (mu / (n**2)) ** (1/3)  # km
        
        # Get eccentricity (handle different formats)
        try:
            ecc = float(tle_row['eccentricity'])
        except:
            ecc = 0.0
        
        # Classify regime
        if ecc >= 0.7:
            regime = 'HEO'
        elif a < 8378:
            regime = 'LEO'
        elif a >= 42164:
            regime = 'GEO'
        else:
            regime = 'MEO'
        
        return regime, a, ecc, mean_motion
        
    except Exception as e:
        return 'UNKNOWN', 0, 0, 0

# Detect orbital regime for each satellite
print(f"\n🛰️ Classifying Orbital Regimes:")
print(f"   Rules:")
print(f"      HEO: eccentricity ≥ 0.7")
print(f"      LEO: SMA < 8,378 km")
print(f"      GEO: SMA ≥ 42,164 km")
print(f"      MEO: everything else")
print()

regimes = {}
regime_details = {}

for sat in satellite_ids:
    sat_tle = tle_df_filtered[tle_df_filtered['satNo'] == sat]
    
    if len(sat_tle) > 0:
        tle_row = sat_tle.iloc[0]
        
        # Detect regime manually
        regime, sma, ecc, mean_motion = detect_regime_manual(tle_row)
        
        regimes[sat] = regime
        
        # Calculate orbital period
        period_minutes = (24 * 60) / mean_motion if mean_motion > 0 else 0
        period_hours = period_minutes / 60
        
        regime_details[sat] = {
            'regime': regime,
            'sma_km': float(sma),
            'eccentricity': float(ecc),
            'period_hours': float(period_hours),
            'mean_motion': float(mean_motion)
        }
        
        print(f"   Satellite {sat}:")
        print(f"      Regime: {regime}")
        print(f"      Semi-Major Axis: {sma:,.1f} km")
        print(f"      Orbital Period: {period_hours:.2f} hours ({period_minutes:.1f} min)")
        print(f"      Mean Motion: {mean_motion:.2f} rev/day")
        if ecc > 0:
            print(f"      Eccentricity: {ecc:.6f}")
        
    else:
        print(f"   Satellite {sat}:")
        print(f"      ❌ No TLE data available")
        regimes[sat] = 'NO_TLE'
        regime_details[sat] = {'regime': 'NO_TLE'}

# Summary statistics
print(f"\n📊 Regime Distribution:")
regime_counts = {}
for regime in regimes.values():
    regime_counts[regime] = regime_counts.get(regime, 0) + 1

for regime, count in sorted(regime_counts.items()):
    print(f"   {regime}: {count} satellite(s)")

# Determine primary regime for pipeline decisions
valid_regimes = [r for r in regimes.values() if r not in ['NO_TLE', 'UNKNOWN']]
if valid_regimes:
    primary_regime = max(set(valid_regimes), key=valid_regimes.count)
else:
    primary_regime = 'GEO'  # Default assumption

print(f"\n🎯 Primary Regime for Pipeline: {primary_regime}")
print(f"   (Most common regime among satellites with TLE data)")

# Save regime data for next section
print(f"\n📦 Saving regime detection data...")

regime_data = {
    'regimes': regimes,
    'regime_details': regime_details,
    'primary_regime': primary_regime,
    'regime_counts': regime_counts,
    'satellites_with_tle': len([r for r in regimes.values() if r not in ['NO_TLE', 'UNKNOWN']]),
    'satellites_without_tle': len([r for r in regimes.values() if r in ['NO_TLE', 'UNKNOWN']])
}

with open('pipeline_regimes.json', 'w') as f:
    json.dump(regime_data, f, indent=2)

print(f"   ✅ Regime data saved to pipeline_regimes.json")

print("\n✅ Section 3 Complete!")
print(f"   Primary regime: {primary_regime}")
print(f"   Satellites classified: {len(valid_regimes)}/{len(satellite_ids)}")
print(f"   Ready to proceed to Section 4 (Search Strategy Selection)")
print("="*80)
