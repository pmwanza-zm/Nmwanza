"""
SECTION 3: ORBITAL REGIME DETECTION
Classifies satellites into orbital regimes (LEO/MEO/GEO/HEO)
"""
import json
import pandas as pd

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

# Fetch TLE data for regime classification
print(f"\n📡 Fetching TLE data for regime detection...")
print(f"   Satellites: {satellite_ids}")

from uct_benchmark.api.apiIntegration import asyncUDLBatchQuery

# Create TLE query parameters
tle_params = [{'satNo': str(sat)} for sat in satellite_ids]

try:
    tle_df = asyncUDLBatchQuery(token, 'elset', tle_params, dt=0.5)
    print(f"   ✅ Retrieved {len(tle_df)} TLE records from UDL")
except Exception as e:
    print(f"   ⚠️ UDL query failed: {e}")
    print(f"   📂 Falling back to local TLE file...")
    tle_df = pd.read_csv('data/referenceTLEs_.csv')
    print(f"   ✅ Loaded {len(tle_df)} TLE records from local file")

# Filter to only our satellites
tle_df_filtered = tle_df[tle_df['satNo'].isin(satellite_ids)]
print(f"   📊 TLE data available for {len(tle_df_filtered)} of {len(satellite_ids)} satellites")

# Detect orbital regime for each satellite
print(f"\n🛰️ Classifying Orbital Regimes:")
print(f"   Rules:")
print(f"      HEO: eccentricity ≥ 0.7")
print(f"      LEO: SMA < 8,378 km")
print(f"      GEO: SMA ≥ 42,164 km")
print(f"      MEO: everything else")
print()

from uct_benchmark.api.apiIntegration import determine_orbital_regime

regimes = {}

for sat in satellite_ids:
    sat_tle = tle_df_filtered[tle_df_filtered['satNo'] == sat]
    
    if len(sat_tle) > 0:
        try:
            # Get TLE data
            tle_row = sat_tle.iloc[0]
            
            # Determine regime
            regime = determine_orbital_regime(tle_row)
            regimes[sat] = regime
            
            # Calculate orbital period
            mean_motion = tle_row['meanMotion']  # revolutions per day
            period_minutes = (24 * 60) / mean_motion
            period_hours = period_minutes / 60
            
            # Get eccentricity if available
            eccentricity = tle_row.get('eccentricity', 0.0)
            
            print(f"   Satellite {sat}:")
            print(f"      Regime: {regime}")
            print(f"      Orbital Period: {period_hours:.2f} hours ({period_minutes:.1f} min)")
            print(f"      Mean Motion: {mean_motion:.2f} rev/day")
            if eccentricity > 0:
                print(f"      Eccentricity: {eccentricity:.6f}")
            
        except Exception as e:
            print(f"   Satellite {sat}:")
            print(f"      ⚠️ Could not determine regime: {e}")
            regimes[sat] = 'UNKNOWN'
    else:
        print(f"   Satellite {sat}:")
        print(f"      ❌ No TLE data available")
        regimes[sat] = 'NO_TLE'

# Summary statistics
print(f"\n📊 Regime Distribution:")
regime_counts = {}
for regime in regimes.values():
    regime_counts[regime] = regime_counts.get(regime, 0) + 1

for regime, count in sorted(regime_counts.items()):
    print(f"   {regime}: {count} satellite(s)")

# Determine primary regime for pipeline decisions
if regimes:
    # Get most common regime (excluding NO_TLE and UNKNOWN)
    valid_regimes = [r for r in regimes.values() if r not in ['NO_TLE', 'UNKNOWN']]
    if valid_regimes:
        primary_regime = max(set(valid_regimes), key=valid_regimes.count)
    else:
        primary_regime = 'GEO'  # Default assumption
else:
    primary_regime = 'GEO'

print(f"\n🎯 Primary Regime for Pipeline: {primary_regime}")
print(f"   (Most common regime among satellites with TLE data)")

# Save regime data for next section
print(f"\n📦 Saving regime detection data...")

regime_data = {
    'regimes': regimes,
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
print(f"   Ready to proceed to Section 4 (Search Strategy Selection)")
print("="*80)
