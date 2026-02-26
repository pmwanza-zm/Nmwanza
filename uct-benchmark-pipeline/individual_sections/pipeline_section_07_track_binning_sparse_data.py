"""
SECTION 7: TRACK BINNING (For Sparse State Vector Data)
For sparse data like state vectors, skip track filtering
"""
import json
import pandas as pd

print("="*80)
print("SECTION 7: TRACK BINNING (SPARSE DATA MODE)")
print("="*80)

# Load validated data
print("\n📥 Loading validated data from Section 6...")
sv_df = pd.read_csv('pipeline_validated_data.csv')
sv_df['epoch'] = pd.to_datetime(sv_df['epoch'])

print(f"   ✅ Loaded {len(sv_df)} validated state vectors")

print(f"\n⚠️ NOTE: State Vector Data Characteristics:")
print(f"   State vectors are inherently sparse (hours between observations)")
print(f"   Unlike optical observations which come in dense tracking passes")
print(f"   Track binning with <3 obs filter would remove all data")
print(f"   Proceeding WITHOUT track filtering for sparse data")

# Simple track assignment based on time gaps (for metadata only)
print(f"\n📊 Assigning Track IDs (for metadata, not filtering):")

sv_df = sv_df.sort_values(['satNo', 'epoch']).reset_index(drop=True)
sv_df['trackId'] = None
current_track_id = 1

for sat in sv_df['satNo'].unique():
    sat_mask = sv_df['satNo'] == sat
    sat_indices = sv_df[sat_mask].index
    
    # Assign track IDs based on gaps
    sv_df.loc[sat_indices[0], 'trackId'] = current_track_id
    current_sat_track = current_track_id
    
    for i in range(1, len(sat_indices)):
        prev_idx = sat_indices[i-1]
        curr_idx = sat_indices[i]
        
        time_gap = (sv_df.loc[curr_idx, 'epoch'] - sv_df.loc[prev_idx, 'epoch']).total_seconds() / 3600
        
        if time_gap > 6.0:  # 6-hour gap for GEO
            current_track_id += 1
            current_sat_track = current_track_id
        
        sv_df.loc[curr_idx, 'trackId'] = current_sat_track
    
    current_track_id += 1

sv_df['trackId'] = sv_df['trackId'].astype(int)

print(f"   ✅ Assigned track IDs to {len(sv_df)} observations")
print(f"   Total tracks: {sv_df['trackId'].nunique()}")

# Gap analysis
print(f"\n📊 Gap Analysis:")
sv_df['gap_hours'] = sv_df.groupby('satNo')['epoch'].diff().dt.total_seconds() / 3600

gaps = sv_df['gap_hours'].dropna()
if len(gaps) > 0:
    print(f"   Mean gap: {gaps.mean():.1f} hours")
    print(f"   Median gap: {gaps.median():.1f} hours")
    print(f"   Max gap: {gaps.max():.1f} hours")
    print(f"   Min gap: {gaps.min():.1f} hours")

# Per-satellite summary
print(f"\n📊 Per-Satellite Summary:")
for sat in sorted(sv_df['satNo'].unique()):
    sat_data = sv_df[sv_df['satNo'] == sat]
    print(f"   Satellite {sat}:")
    print(f"      Observations: {len(sat_data)}")
    print(f"      Tracks: {sat_data['trackId'].nunique()}")
    print(f"      Time span: {(sat_data['epoch'].max() - sat_data['epoch'].min()).days} days")

# Save data (keeping ALL observations - no filtering)
print(f"\n📦 Saving track-labeled data (NO FILTERING APPLIED)...")

sv_df.to_csv('pipeline_binned_data.csv', index=False)
print(f"   ✅ Data saved to pipeline_binned_data.csv")

binning_metadata = {
    'input_observations': len(sv_df),
    'output_observations': len(sv_df),
    'tracks_created': int(sv_df['trackId'].nunique()),
    'filtering_applied': False,
    'reason': 'Sparse state vector data - track filtering skipped',
    'has_track_ids': True,
    'satellites': sv_df['satNo'].unique().tolist(),
    'per_satellite': {}
}

for sat in sv_df['satNo'].unique():
    sat_data = sv_df[sv_df['satNo'] == sat]
    binning_metadata['per_satellite'][int(sat)] = {
        'tracks': int(sat_data['trackId'].nunique()),
        'observations': int(len(sat_data))
    }

with open('pipeline_binning_metadata.json', 'w') as f:
    json.dump(binning_metadata, f, indent=2)

print(f"   ✅ Binning metadata saved")

print("\n✅ Section 7 Complete!")
print(f"   Kept ALL {len(sv_df)} observations (sparse data mode)")
print(f"   Ready to proceed to Section 8 (Tier-Based Routing)")
print("="*80)
