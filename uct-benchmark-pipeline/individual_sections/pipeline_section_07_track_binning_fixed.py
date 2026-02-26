"""
SECTION 7: TRACK BINNING (FIXED)
Groups observations into tracks based on time gaps - Manual approach
"""
import json
import pandas as pd
import numpy as np

print("="*80)
print("SECTION 7: TRACK BINNING")
print("="*80)

# Load validated data
print("\n📥 Loading validated data from Section 6...")
sv_df = pd.read_csv('pipeline_validated_data.csv')
sv_df['epoch'] = pd.to_datetime(sv_df['epoch'])

print(f"   ✅ Loaded {len(sv_df)} validated state vectors")

# Manual track binning based on time gaps
print(f"\n📊 Manual Track Binning Algorithm:")
print(f"   Gap threshold: 90 minutes (1.5 hours)")
print(f"   Logic: Gap > 90 min → New track")

# Sort by satellite and time
sv_df = sv_df.sort_values(['satNo', 'epoch']).reset_index(drop=True)

# Initialize track IDs
sv_df['trackId'] = None
current_track_id = 1

for sat in sv_df['satNo'].unique():
    print(f"\n   Processing Satellite {sat}...")
    
    sat_mask = sv_df['satNo'] == sat
    sat_indices = sv_df[sat_mask].index
    
    # First observation starts first track
    sv_df.loc[sat_indices[0], 'trackId'] = current_track_id
    current_sat_track = current_track_id
    
    # Process subsequent observations
    for i in range(1, len(sat_indices)):
        prev_idx = sat_indices[i-1]
        curr_idx = sat_indices[i]
        
        # Calculate time gap
        time_gap = (sv_df.loc[curr_idx, 'epoch'] - sv_df.loc[prev_idx, 'epoch']).total_seconds() / 3600  # hours
        
        # If gap > 90 minutes, start new track
        if time_gap > 1.5:
            current_track_id += 1
            current_sat_track = current_track_id
        
        sv_df.loc[curr_idx, 'trackId'] = current_sat_track
    
    # Summary for this satellite
    sat_data = sv_df[sat_mask]
    num_tracks = sat_data['trackId'].nunique()
    print(f"      Created {num_tracks} tracks from {len(sat_data)} observations")
    
    current_track_id += 1  # Move to next satellite's tracks

# Convert trackId to integer
sv_df['trackId'] = sv_df['trackId'].astype(int)

# Analyze tracks
print(f"\n📊 Track Analysis:")
num_tracks = sv_df['trackId'].nunique()
print(f"   Total tracks created: {num_tracks}")

# Per-satellite breakdown
print(f"\n   Per-Satellite Track Breakdown:")
for sat in sorted(sv_df['satNo'].unique()):
    sat_data = sv_df[sv_df['satNo'] == sat].copy()
    sat_tracks = sat_data['trackId'].nunique()
    sat_obs = len(sat_data)
    
    print(f"\n      Satellite {sat}:")
    print(f"         Tracks: {sat_tracks}")
    print(f"         Observations: {sat_obs}")
    print(f"         Avg obs/track: {sat_obs/sat_tracks:.1f}")
    
    # Track size distribution
    track_sizes = sat_data.groupby('trackId').size()
    print(f"         Track sizes: {track_sizes.min()}-{track_sizes.max()} obs")
    print(f"         Track size distribution:")
    for track_id in sat_data['trackId'].unique():
        track_obs = len(sat_data[sat_data['trackId'] == track_id])
        track_start = sat_data[sat_data['trackId'] == track_id]['epoch'].min()
        track_end = sat_data[sat_data['trackId'] == track_id]['epoch'].max()
        duration = (track_end - track_start).total_seconds() / 3600
        print(f"            Track {track_id}: {track_obs} obs, {duration:.1f}h duration")

# Filter tracks with < 3 observations
print(f"\n📊 Filtering tracks with < 3 observations...")

track_sizes = sv_df.groupby('trackId').size()
small_tracks = track_sizes[track_sizes < 3]

if len(small_tracks) > 0:
    print(f"   Found {len(small_tracks)} tracks with < 3 observations:")
    for track_id, size in small_tracks.items():
        print(f"      Track {track_id}: {size} obs")
    
    # Remove small tracks
    original_count = len(sv_df)
    sv_df = sv_df[~sv_df['trackId'].isin(small_tracks.index)].copy()
    
    print(f"\n   ✅ Removed {len(small_tracks)} small tracks")
    print(f"   Removed {original_count - len(sv_df)} observations")
    print(f"   Remaining observations: {len(sv_df)}")
    print(f"   Remaining tracks: {sv_df['trackId'].nunique()}")
else:
    print(f"   ✅ All tracks have ≥ 3 observations")

# Gap analysis
print(f"\n📊 Gap Analysis:")
sv_df['gap_hours'] = sv_df.groupby('satNo')['epoch'].diff().dt.total_seconds() / 3600

gaps = sv_df['gap_hours'].dropna()
if len(gaps) > 0:
    print(f"   Mean gap: {gaps.mean():.1f} hours")
    print(f"   Median gap: {gaps.median():.1f} hours")
    print(f"   Max gap: {gaps.max():.1f} hours")
    print(f"   Min gap: {gaps.min():.1f} hours")
    
    # Count track boundaries (gaps > 90 min)
    track_boundaries = gaps[gaps > 1.5]
    print(f"   Track boundaries (gap > 90 min): {len(track_boundaries)}")

# Save binned data
print(f"\n📦 Saving binned data...")

sv_df.to_csv('pipeline_binned_data.csv', index=False)
print(f"   ✅ Binned data saved to pipeline_binned_data.csv")

binning_metadata = {
    'input_observations': 93,
    'output_observations': len(sv_df),
    'tracks_created': int(sv_df['trackId'].nunique()),
    'small_tracks_removed': int(len(small_tracks)) if len(small_tracks) > 0 else 0,
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

print(f"   ✅ Binning metadata saved to pipeline_binning_metadata.json")

print("\n✅ Section 7 Complete!")
print(f"   Created {sv_df['trackId'].nunique()} tracks from {len(sv_df)} observations")
print(f"   Ready to proceed to Section 8 (Tier-Based Routing)")
print("="*80)
