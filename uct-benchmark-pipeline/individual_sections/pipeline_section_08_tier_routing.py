"""
SECTION 8: TIER-BASED ROUTING
Determines processing path based on quality tier (T1/T2/T3/T4)
"""
import json
import pandas as pd

print("="*80)
print("SECTION 8: TIER-BASED ROUTING")
print("="*80)

# Load configuration and binned data
print("\n📥 Loading previous sections...")
with open('pipeline_config.json', 'r') as f:
    config = json.load(f)

binned_df = pd.read_csv('pipeline_binned_data.csv')
binned_df['epoch'] = pd.to_datetime(binned_df['epoch'])

print(f"   ✅ Configuration loaded: Tier {config['quality_tier']}")
print(f"   ✅ Binned data loaded: {len(binned_df)} observations")

# Define tier configurations
tier_configs = {
    'T1': {
        'name': 'High Fidelity',
        'coverage_range': (0.20, 0.40),
        'gap_target_periods': 1.5,
        'max_obs_per_sat': 200,
        'require_simulation': False,
        'require_downsampling': False,
        'description': 'Real data only, minimal reduction'
    },
    'T2': {
        'name': 'Standard',
        'coverage_range': (0.05, 0.15),
        'gap_target_periods': 2.0,
        'max_obs_per_sat': 50,
        'require_simulation': False,
        'require_downsampling': True,
        'description': 'Real + filtered, moderate reduction'
    },
    'T3': {
        'name': 'Degraded',
        'coverage_range': (0.02, 0.10),
        'gap_target_periods': 3.0,
        'max_obs_per_sat': 30,
        'require_simulation': True,
        'require_downsampling': True,
        'description': 'Real + sparse + simulation, aggressive reduction'
    },
    'T4': {
        'name': 'Lowest Quality',
        'coverage_range': (0.01, 0.05),
        'gap_target_periods': 4.0,
        'max_obs_per_sat': 20,
        'require_simulation': True,
        'require_downsampling': True,
        'description': 'Mostly simulated, extreme reduction'
    }
}

selected_tier = config['quality_tier']
tier_config = tier_configs[selected_tier]

print(f"\n📊 Tier Configuration: {selected_tier} - {tier_config['name']}")
print("="*80)
print(f"   Description: {tier_config['description']}")
print(f"\n   Parameters:")
print(f"      Coverage Target: {tier_config['coverage_range'][0]*100:.0f}%-{tier_config['coverage_range'][1]*100:.0f}% of orbit")
print(f"      Gap Target: {tier_config['gap_target_periods']} orbital periods")
print(f"      Max Observations/Satellite: {tier_config['max_obs_per_sat']}")
print(f"\n   Processing Requirements:")
print(f"      Downsampling Required: {'✅ Yes' if tier_config['require_downsampling'] else '❌ No'}")
print(f"      Simulation Required: {'✅ Yes' if tier_config['require_simulation'] else '❌ No'}")

# Determine routing based on tier
print(f"\n🔀 Routing Decision:")

if selected_tier == 'T1':
    print(f"   ✅ Tier T1: Minimal processing path")
    print(f"      → Skip downsampling (Section 9)")
    print(f"      → Skip simulation (Section 10-11)")
    print(f"      → Proceed directly to output")
    
    proceed_to_downsampling = False
    proceed_to_simulation = False
    
elif selected_tier in ['T2']:
    print(f"   ✅ Tier T2: Moderate processing path")
    print(f"      → Proceed to downsampling (Section 9)")
    print(f"      → Skip simulation (Section 10-11)")
    
    proceed_to_downsampling = True
    proceed_to_simulation = False
    
else:  # T3 or T4
    print(f"   ✅ Tier {selected_tier}: Full processing path")
    print(f"      → Proceed to downsampling (Section 9)")
    print(f"      → Proceed to simulation (Section 10-11)")
    
    proceed_to_downsampling = True
    proceed_to_simulation = True

# Check current data volume against tier limits
print(f"\n📊 Data Volume Check:")
for sat in binned_df['satNo'].unique():
    sat_obs = len(binned_df[binned_df['satNo'] == sat])
    max_allowed = tier_config['max_obs_per_sat']
    
    if sat_obs > max_allowed:
        print(f"   Satellite {sat}: {sat_obs} obs > {max_allowed} limit")
        print(f"      ⚠️ Downsampling REQUIRED")
    else:
        print(f"   Satellite {sat}: {sat_obs} obs ≤ {max_allowed} limit")
        print(f"      ✅ Within tier limit")

# Save routing decision
print(f"\n📦 Saving routing decision...")

routing_data = {
    'tier': selected_tier,
    'tier_name': tier_config['name'],
    'tier_config': tier_config,
    'routing_decision': {
        'proceed_to_downsampling': proceed_to_downsampling,
        'proceed_to_simulation': proceed_to_simulation
    },
    'current_data': {
        'observations': len(binned_df),
        'satellites': binned_df['satNo'].unique().tolist(),
        'per_satellite': {}
    }
}

for sat in binned_df['satNo'].unique():
    sat_obs = len(binned_df[binned_df['satNo'] == sat])
    routing_data['current_data']['per_satellite'][int(sat)] = {
        'observations': int(sat_obs),
        'exceeds_limit': sat_obs > tier_config['max_obs_per_sat']
    }

with open('pipeline_routing.json', 'w') as f:
    json.dump(routing_data, f, indent=2)

print(f"   ✅ Routing data saved to pipeline_routing.json")

print("\n✅ Section 8 Complete!")
print(f"   Tier: {selected_tier} ({tier_config['name']})")
print(f"   Next steps:")
if proceed_to_downsampling:
    print(f"      → Section 9: Downsampling")
    if proceed_to_simulation:
        print(f"      → Section 10-11: Simulation")
else:
    print(f"      → Skip to final output")

print("="*80)
