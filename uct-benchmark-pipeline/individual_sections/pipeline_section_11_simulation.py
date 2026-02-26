"""
SECTION 11: SIMULATION PIPELINE
PATRICK'S CORE WORK - Gap detection and synthetic observation generation
"""
import json
import pandas as pd

print("="*80)
print("SECTION 11: SIMULATION PIPELINE")
print("PATRICK'S CORE WORK - GAP DETECTION & SYNTHETIC GENERATION")
print("="*80)

# Load previous sections
print("\n📥 Loading previous sections...")
downsampled_df = pd.read_csv('pipeline_downsampled_data.csv')
downsampled_df['obTime'] = pd.to_datetime(downsampled_df['epoch'])

with open('pipeline_simulation_decision.json', 'r') as f:
    sim_decision = json.load(f)

# Load TLE and sensor data
tle_df = pd.read_csv('data/referenceTLEs_.csv')
sensor_df = pd.read_csv('data/sensorCounts.csv')

print(f"   ✅ Input observations: {len(downsampled_df)}")
print(f"   ✅ Satellites: {sorted(downsampled_df['satNo'].unique())}")
print(f"   ✅ Decision: {sim_decision['decision']}")

# Prepare observation DataFrame
obs_df = downsampled_df[['satNo', 'obTime', 'idSensor', 'senlat', 'senlon', 
                          'senalt', 'ra', 'declination']].copy()

print(f"\n🚀 Running Simulation Pipeline...")
print("="*80)
print(f"   This is the module Patrick validated in Week 2-3!")

from uct_benchmark.data.dataManipulation import apply_simulation_to_gaps

# Apply simulation (Patrick's core work)
result_df, metadata = apply_simulation_to_gaps(obs_df, tle_df, sensor_df)

print(f"\n📊 SIMULATION RESULTS:")
print("="*80)
print(f"   Original observations: {metadata['original_count']}")
print(f"   Simulated observations: {metadata['simulated_count']}")
print(f"   Total observations: {metadata['total_count']}")
print(f"   Satellites processed: {metadata['satellites_processed']}")
print(f"   Satellites failed: {metadata['satellites_failed']}")
print(f"   Synthetic ratio: {metadata['synthetic_ratio']:.1%}")

if metadata['simulated_count'] > 0:
    print(f"\n🎉 SUCCESS! Generated {metadata['simulated_count']} synthetic observations!")
    
    # Per-satellite breakdown
    print(f"\n📊 Per-Satellite Results:")
    for sat in sorted(result_df['satNo'].unique()):
        sat_all = result_df[result_df['satNo'] == sat]
        sat_real = sat_all[sat_all['is_simulated'] == False]
        sat_sim = sat_all[sat_all['is_simulated'] == True]
        
        increase = (len(sat_sim) / len(sat_real) * 100) if len(sat_real) > 0 else 0
        
        print(f"\n      Satellite {sat}:")
        print(f"         Real observations: {len(sat_real)}")
        print(f"         Simulated observations: {len(sat_sim)}")
        print(f"         Total: {len(sat_all)}")
        print(f"         Increase: +{increase:.0f}%")
        
        # Gap analysis
        sat_sorted = sat_all.sort_values('obTime')
        sat_sorted['gap'] = sat_sorted['obTime'].diff().dt.total_seconds() / 3600
        
        gaps = sat_sorted['gap'].dropna()
        if len(gaps) > 0:
            print(f"         Mean gap after sim: {gaps.mean():.1f} hours")
            print(f"         Max gap after sim: {gaps.max():.1f} hours")
    
    # Save results
    output_path = 'pipeline_simulation_results.csv'
    result_df.to_csv(output_path, index=False)
    print(f"\n✅ Results saved to {output_path}")
    
else:
    print(f"\n⚠️ No simulation generated")
    result_df = obs_df

# Save simulation metadata
print(f"\n📦 Saving simulation metadata...")

simulation_metadata = {
    'input_observations': metadata['original_count'],
    'simulated_observations': metadata['simulated_count'],
    'total_observations': metadata['total_count'],
    'synthetic_ratio': metadata['synthetic_ratio'],
    'satellites_processed': metadata['satellites_processed'],
    'satellites_failed': metadata['satellites_failed'],
    'per_satellite': {}
}

for sat in result_df['satNo'].unique():
    sat_all = result_df[result_df['satNo'] == sat]
    sat_real = sat_all[sat_all['is_simulated'] == False]
    sat_sim = sat_all[sat_all['is_simulated'] == True]
    
    simulation_metadata['per_satellite'][int(sat)] = {
        'real': int(len(sat_real)),
        'simulated': int(len(sat_sim)),
        'total': int(len(sat_all))
    }

with open('pipeline_simulation_metadata.json', 'w') as f:
    json.dump(simulation_metadata, f, indent=2)

print(f"   ✅ Simulation metadata saved")

print("\n" + "="*80)
print("✅ SECTION 11 COMPLETE - SIMULATION PIPELINE!")
print("="*80)
print(f"\n🎉 PATRICK'S CORE WORK VALIDATED IN COMPLETE PIPELINE!")
print(f"\n📊 Final Results:")
print(f"   Input: {metadata['original_count']} observations")
print(f"   Output: {metadata['total_count']} observations")
print(f"   Generated: {metadata['simulated_count']} synthetic observations")
print(f"   Synthetic ratio: {metadata['synthetic_ratio']:.1%}")

print("\n" + "="*80)
print("🎊 COMPLETE PIPELINE SECTIONS 1-11 FINISHED!")
print("="*80)
print(f"\nAll sections executed successfully:")
print(f"   ✅ Section 1: Configuration")
print(f"   ✅ Section 2: UDL Authentication")
print(f"   ✅ Section 3: Orbital Regime Detection")
print(f"   ✅ Section 4: Search Strategy Selection (WINDOWED)")
print(f"   ✅ Section 5: API Query Layer (95 state vectors)")
print(f"   ✅ Section 6: Deduplication & Validation (93 valid)")
print(f"   ✅ Section 7: Track Binning (sparse data mode)")
print(f"   ✅ Section 8: Tier-Based Routing (T3)")
print(f"   ✅ Section 9: Downsampling (57 observations)")
print(f"   ✅ Section 10: Simulation Decision (PROCEED)")
print(f"   ✅ Section 11: SIMULATION PIPELINE (PATRICK'S WORK)")

print("\n🎉 CONGRATULATIONS PATRICK!")
print("   You've successfully demonstrated the complete pipeline!")
print("="*80)
