"""
SECTION 10: SIMULATION DECISION
Determines if simulation should run based on data characteristics
"""
import json
import pandas as pd

print("="*80)
print("SECTION 10: SIMULATION DECISION")
print("="*80)

# Load previous sections
print("\n📥 Loading previous sections...")
downsampled_df = pd.read_csv('pipeline_downsampled_data.csv')
downsampled_df['epoch'] = pd.to_datetime(downsampled_df['epoch'])

with open('pipeline_routing.json', 'r') as f:
    routing = json.load(f)

with open('pipeline_regimes.json', 'r') as f:
    regimes = json.load(f)

# Load TLE data for period calculation
tle_df = pd.read_csv('data/referenceTLEs_.csv')

print(f"   ✅ Loaded {len(downsampled_df)} downsampled observations")
print(f"   Tier: {routing['tier']} ({routing['tier_name']})")
print(f"   Simulation required by tier: {routing['tier_config']['require_simulation']}")

# Check simulation requirements
print(f"\n📊 Simulation Requirements Check:")

tier_requires_sim = routing['tier_config']['require_simulation']
print(f"   1. Tier requirement: {'✅ Yes' if tier_requires_sim else '❌ No'} (Tier {routing['tier']})")

# Check minimum observations
min_obs_required = 3
has_min_obs = len(downsampled_df) >= min_obs_required

print(f"   2. Minimum observations: {'✅ Pass' if has_min_obs else '❌ Fail'} ({len(downsampled_df)} ≥ {min_obs_required})")

# Check orbital period coverage for each satellite
print(f"\n   3. Orbital Period Coverage Check:")

period_coverage_ok = True
for sat in downsampled_df['satNo'].unique():
    sat_data = downsampled_df[downsampled_df['satNo'] == sat]
    
    # Get orbital period from TLE
    sat_tle = tle_df[tle_df['satNo'] == sat]
    if len(sat_tle) > 0:
        mean_motion = sat_tle.iloc[0]['meanMotion']  # rev/day
        period_hours = 24 / mean_motion
        
        # Calculate time span of observations
        time_span = sat_data['epoch'].max() - sat_data['epoch'].min()
        time_span_hours = time_span.total_seconds() / 3600
        
        periods_covered = time_span_hours / period_hours
        
        print(f"      Satellite {sat}:")
        print(f"         Orbital period: {period_hours:.2f} hours")
        print(f"         Time span: {time_span_hours:.1f} hours")
        print(f"         Periods covered: {periods_covered:.2f}")
        
        if periods_covered >= 1.0:
            print(f"         ✅ Sufficient coverage (≥1.0 period)")
        else:
            print(f"         ❌ Insufficient coverage (<1.0 period)")
            period_coverage_ok = False
    else:
        print(f"      Satellite {sat}: ❌ No TLE data")
        period_coverage_ok = False

# Overall decision
print(f"\n🎯 SIMULATION DECISION:")
print("="*80)

if tier_requires_sim and has_min_obs and period_coverage_ok:
    proceed_to_simulation = True
    decision = "PROCEED TO SIMULATION"
    reason = "All requirements met"
    print(f"   ✅ {decision}")
    print(f"   Reason: {reason}")
    print(f"      • Tier {routing['tier']} requires simulation")
    print(f"      • Minimum observations present ({len(downsampled_df)} ≥ 3)")
    print(f"      • All satellites have ≥1 orbital period coverage")
    
elif not tier_requires_sim:
    proceed_to_simulation = False
    decision = "SKIP SIMULATION"
    reason = f"Tier {routing['tier']} does not require simulation"
    print(f"   ℹ️ {decision}")
    print(f"   Reason: {reason}")
    
elif not has_min_obs:
    proceed_to_simulation = False
    decision = "SKIP SIMULATION"
    reason = f"Insufficient observations ({len(downsampled_df)} < 3)"
    print(f"   ⚠️ {decision}")
    print(f"   Reason: {reason}")
    
else:  # not period_coverage_ok
    proceed_to_simulation = False
    decision = "SKIP SIMULATION"
    reason = "Insufficient orbital period coverage (<1.0 period)"
    print(f"   ⚠️ {decision}")
    print(f"   Reason: {reason}")
    print(f"   Status: window_too_short")

# Save decision
print(f"\n📦 Saving simulation decision...")

decision_data = {
    'proceed_to_simulation': proceed_to_simulation,
    'decision': decision,
    'reason': reason,
    'checks': {
        'tier_requires_simulation': tier_requires_sim,
        'has_minimum_observations': has_min_obs,
        'period_coverage_ok': period_coverage_ok
    },
    'input_observations': len(downsampled_df),
    'satellites': downsampled_df['satNo'].unique().tolist()
}

with open('pipeline_simulation_decision.json', 'w') as f:
    json.dump(decision_data, f, indent=2)

print(f"   ✅ Decision saved to pipeline_simulation_decision.json")

print("\n✅ Section 10 Complete!")
print(f"   Decision: {decision}")
if proceed_to_simulation:
    print(f"   Ready to proceed to Section 11 (SIMULATION PIPELINE - PATRICK'S WORK)")
else:
    print(f"   Skipping to final output")
print("="*80)
