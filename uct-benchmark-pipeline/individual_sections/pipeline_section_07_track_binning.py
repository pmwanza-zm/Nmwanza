"""
SECTION 7: TRACK BINNING
Groups observations into tracks based on time gaps
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

with open('pipeline_validation_metadata.json', 'r') as f:
    val_meta = json.load(f)

print(f"   ✅ Loaded {len(sv_df)} validated state vectors")
print(f"   Satellites: {val_meta['satellites']}")

# Load TLE data for orbital period calculation
tle_df = pd.read_csv('data/referenceTLEs_.csv')

# Convert state vectors to observation-like format
print(f"\n📊 Converting state vectors to observation format...")

obs_list = []
for _, row in sv_df.iterrows():
    obs = {
        'satNo': row['satNo'],
        'obTime': row['epoch'],
        'idSensor': 'STATE_VECTOR',
        'senlat': 0.0,
        'senlon': 0.0,
        'senalt': 0.0,
        'ra': 0.0,
        'declination': 0.0,
        'range': row['distance_km'] if 'distance_km' in row else 0.0
    }
    obs_list.append(obs)

obs_df = pd.DataFrame(obs_list)
print(f"   ✅ Created {len(obs_df)} observation records")

# Track binning using the module's binTracks function
print(f"\n📊 Applying track binning...")
print(f"   Algorithm:")
print(f"      1. Compute orbital period per satellite")
print(f"      2. Group observations by sensor + satellite")
print(f"      3. Gap threshold: 90 minutes")
print(f"         < 90 min → same track")
print(f"         > 90 min → new track")
print(f"      4. Discard tracks with < 3 observations")

from uct_benchmark.data.dataManipulation import binTracks

try:
    binned_df = binTracks(obs_df, tle_df)
    
    # Check if binning created trackId
    if 'trackId' in binned_df.columns:
        print(f"\n   ✅ Track binning successful!")
        
        # Analyze tracks
        num_tracks = binned_df['trackId'].nunique()
        print(f"\n📊 Track Analysis:")
        print(f"   Total tracks created: {num_tracks}")
        
        # Per-satellite track breakdown
        print(f"\n   Per-Satellite Track Breakdown:")
        for sat in sorted(binned_df['satNo'].unique()):
            sat_data = binned_df[binned_df['satNo'] == sat]
            sat_tracks = sat_data['trackId'].nunique()
            sat_obs = len(sat_data)
            
            print(f"\n      Satellite {sat}:")
            print(f"         Tracks: {sat_tracks}")
            print(f"         Observations: {sat_obs}")
            print(f"         Avg obs/track: {sat_obs/sat_tracks:.1f}")
            
            # Show track details
            track_sizes = sat_data.groupby('trackId').size()
            print(f"         Track size range: {track_sizes.min()}-{track_sizes.max()} obs")
            
            # Calculate gaps within tracks
            sat_sorted = sat_data.sort_values('obTime')
            sat_sorted['gap_hours'] = sat_sorted['obTime'].diff().dt.total_seconds() / 3600
            
            # Filter to gaps within same track
            track_gaps = []
            for track_id in sat_data['trackId'].unique():
                track_data = sat_sorted[sat_sorted['trackId'] == track_id].copy()
                if len(track_data) > 1:
                    track_data['gap'] = track_data['obTime'].diff().dt.total_seconds() / 3600
                    track_gaps.extend(track_data['gap'].dropna().tolist())
            
            if track_gaps:
                print(f"         Intra-track gaps: {np.mean(track_gaps):.1f}h mean, {np.max(track_gaps):.1f}h max")
        
        # Overall gap analysis
        print(f"\n   Overall Gap Analysis:")
        binned_sorted = binned_df.sort_values(['satNo', 'obTime'])
        binned_sorted['gap_hours'] = binned_sorted.groupby('satNo')['obTime'].diff().dt.total_seconds() / 3600
        
        gaps = binned_sorted['gap_hours'].dropna()
        if len(gaps) > 0:
            print(f"      Mean gap: {gaps.mean():.1f} hours")
            print(f"      Median gap: {gaps.median():.1f} hours")
            print(f"      Max gap: {gaps.max():.1f} hours")
            print(f"      Min gap: {gaps.min():.1f} hours")
            
            # Count gaps > 90 minutes (track boundaries)
            large_gaps = gaps[gaps > 1.5]  # 90 minutes = 1.5 hours
            print(f"      Gaps > 90 min (track boundaries): {len(large_gaps)}")
        
    else:
        print(f"   ⚠️ Warning: binTracks did not create trackId column")
        print(f"   Proceeding without track information...")
        binned_df = obs_df
        num_tracks = 0
        
except Exception as e:
    print(f"   ❌ Track binning failed: {e}")
    print(f"   Proceeding with unbinned data...")
    binned_df = obs_df
    num_tracks = 0

# Filter tracks with < 3 observations (if trackId exists)
if 'trackId' in binned_df.columns:
    print(f"\n📊 Filtering tracks with < 3 observations...")
    
    track_sizes = binned_df.groupby('trackId').size()
    small_tracks = track_sizes[track_sizes < 3]
    
    if len(small_tracks) > 0:
        print(f"   Found {len(small_tracks)} tracks with < 3 observations")
        
        # Remove small tracks
        binned_df = binned_df[~binned_df['trackId'].isin(small_tracks.index)]
        
        print(f"   ✅ Removed {len(small_tracks)} small tracks")
        print(f"   Remaining observations: {len(binned_df)}")
        print(f"   Remaining tracks: {binned_df['trackId'].nunique()}")
    else:
        print(f"   ✅ All tracks have ≥ 3 observations")

# Save binned data
print(f"\n📦 Saving binned data...")

binned_df.to_csv('pipeline_binned_data.csv', index=False)
print(f"   ✅ Binned data saved to pipeline_binned_data.csv")

binning_metadata = {
    'input_observations': len(obs_df),
    'output_observations': len(binned_df),
    'tracks_created': int(num_tracks) if num_tracks > 0 else 0,
    'has_track_ids': 'trackId' in binned_df.columns,
    'satellites': binned_df['satNo'].unique().tolist(),
    'per_satellite': {}
}

if 'trackId' in binned_df.columns:
    for sat in binned_df['satNo'].unique():
        sat_data = binned_df[binned_df['satNo'] == sat]
        binning_metadata['per_satellite'][int(sat)] = {
            'tracks': int(sat_data['trackId'].nunique()),
            'observations': int(len(sat_data))
        }

with open('pipeline_binning_metadata.json', 'w') as f:
    json.dump(binning_metadata, f, indent=2)

print(f"   ✅ Binning metadata saved to pipeline_binning_metadata.json")

print("\n✅ Section 7 Complete!")
print(f"   Created {num_tracks} tracks from {len(binned_df)} observations")
print(f"   Ready to proceed to Section 8 (Tier-Based Routing)")
print("="*80)
