"""
SECTION 9: DOWNSAMPLING
Reduces observation density to meet tier requirements
"""
import json
import pandas as pd
import numpy as np

print("="*80)
print("SECTION 9: DOWNSAMPLING")
print("="*80)

# Load previous sections
print("\n📥 Loading previous sections...")
binned_df = pd.read_csv('pipeline_binned_data.csv')
binned_df['epoch'] = pd.to_datetime(binned_df['epoch'])

with open('pipeline_routing.json', 'r') as f:
    routing = json.load(f)

tier_config = routing['tier_config']
max_obs = tier_config['max_obs_per_sat']

print(f"   ✅ Loaded {len(binned_df)} observations")
print(f"   Tier: {routing['tier']} ({routing['tier_name']})")
print(f"   Max observations per satellite: {max_obs}")

# Simple downsampling strategy for sparse state vector data
print(f"\n📊 Downsampling Strategy:")
print(f"   For each satellite exceeding limit:")
print(f"   1. Calculate required reduction ratio")
print(f"   2. Sample uniformly across time range")
print(f"   3. Preserve first and last observations")

downsampled_data = []

for sat in sorted(binned_df['satNo'].unique()):
    sat_data = binned_df[binned_df['satNo'] == sat].copy()
    sat_data = sat_data.sort_values('epoch').reset_index(drop=True)
    
    current_count = len(sat_data)
    
    print(f"\n   Satellite {sat}:")
    print(f"      Current: {current_count} observations")
    print(f"      Limit: {max_obs} observations")
    
    if current_count > max_obs:
        # Need to downsample
        print(f"      ⚠️ Exceeds limit by {current_count - max_obs}")
        
        # Calculate sampling rate
        # Keep max_obs observations uniformly distributed
        indices_to_keep = np.linspace(0, len(sat_data) - 1, max_obs, dtype=int)
        
        # Ensure we keep first and last
        indices_to_keep = np.unique(indices_to_keep)
        
        sat_downsampled = sat_data.iloc[indices_to_keep].copy()
        
        print(f"      ✅ Downsampled to {len(sat_downsampled)} observations")
        print(f"      Retention: {len(sat_downsampled)/current_count*100:.1f}%")
        
        # Calculate new gaps
        sat_downsampled_sorted = sat_downsampled.sort_values('epoch')
        gaps = sat_downsampled_sorted['epoch'].diff().dt.total_seconds() / 3600
        
        print(f"      New mean gap: {gaps.mean():.1f} hours")
        print(f"      New max gap: {gaps.max():.1f} hours")
        
        downsampled_data.append(sat_downsampled)
    else:
        # Already within limit
        print(f"      ✅ Already within limit, no downsampling needed")
        downsampled_data.append(sat_data)

# Combine all satellites
downsampled_df = pd.concat(downsampled_data, ignore_index=True)

# Summary
print(f"\n📊 DOWNSAMPLING SUMMARY:")
print("="*80)
print(f"   Original observations: {len(binned_df)}")
print(f"   Downsampled observations: {len(downsampled_df)}")
print(f"   Removed: {len(binned_df) - len(downsampled_df)}")
print(f"   Retention rate: {len(downsampled_df)/len(binned_df)*100:.1f}%")

print(f"\n   Per-Satellite Results:")
for sat in sorted(downsampled_df['satNo'].unique()):
    original = len(binned_df[binned_df['satNo'] == sat])
    final = len(downsampled_df[downsampled_df['satNo'] == sat])
    print(f"      Satellite {sat}: {original} → {final} observations")

# Gap analysis after downsampling
print(f"\n📊 Gap Analysis After Downsampling:")
downsampled_df = downsampled_df.sort_values(['satNo', 'epoch'])
downsampled_df['gap_hours'] = downsampled_df.groupby('satNo')['epoch'].diff().dt.total_seconds() / 3600

gaps = downsampled_df['gap_hours'].dropna()
if len(gaps) > 0:
    print(f"   Mean gap: {gaps.mean():.1f} hours")
    print(f"   Median gap: {gaps.median():.1f} hours")
    print(f"   Max gap: {gaps.max():.1f} hours")
    print(f"   Min gap: {gaps.min():.1f} hours")

# Save downsampled data
print(f"\n📦 Saving downsampled data...")

downsampled_df.to_csv('pipeline_downsampled_data.csv', index=False)
print(f"   ✅ Data saved to pipeline_downsampled_data.csv")

downsampling_metadata = {
    'original_count': len(binned_df),
    'downsampled_count': len(downsampled_df),
    'removed_count': len(binned_df) - len(downsampled_df),
    'retention_rate': len(downsampled_df) / len(binned_df) if len(binned_df) > 0 else 0,
    'tier': routing['tier'],
    'max_obs_per_sat': max_obs,
    'per_satellite': {}
}

for sat in downsampled_df['satNo'].unique():
    original = len(binned_df[binned_df['satNo'] == sat])
    final = len(downsampled_df[downsampled_df['satNo'] == sat])
    downsampling_metadata['per_satellite'][int(sat)] = {
        'original': int(original),
        'final': int(final),
        'removed': int(original - final)
    }

with open('pipeline_downsampling_metadata.json', 'w') as f:
    json.dump(downsampling_metadata, f, indent=2)

print(f"   ✅ Downsampling metadata saved")

print("\n✅ Section 9 Complete!")
print(f"   Downsampled to {len(downsampled_df)} observations")
print(f"   Ready to proceed to Section 10 (Simulation Decision)")
print("="*80)
