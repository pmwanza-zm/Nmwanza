"""
SECTION 1: PIPELINE CONFIGURATION
Defines input parameters for the UCT Benchmark pipeline
"""
from datetime import datetime, timedelta

print("="*80)
print("SECTION 1: PIPELINE CONFIGURATION")
print("="*80)

# Pipeline configuration
config = {
    # Satellite Selection
    'satellite_ids': [26608, 42915],  # 2 GEO satellites with known TLE data
    
    # Time Range
    'start_time': datetime.now() - timedelta(days=30),
    'end_time': datetime.now(),
    
    # Quality Settings
    'quality_tier': 'T3',  # T1=High fidelity, T2=Standard, T3=Degraded, T4=Lowest
    
    # API Settings
    'search_strategy': 'auto',  # auto, fast, windowed, hybrid
    'max_datapoints': 1000,
    
    # Processing Options
    'enable_simulation': True,
    'enable_downsampling': True
}

print(f"\n📊 Configuration Summary:")
print(f"   Satellites: {config['satellite_ids']}")
print(f"   Number of satellites: {len(config['satellite_ids'])}")
print(f"   ")
print(f"   Time Range:")
print(f"      Start: {config['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
print(f"      End: {config['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
print(f"      Duration: {(config['end_time'] - config['start_time']).days} days")
print(f"   ")
print(f"   Quality Settings:")
print(f"      Tier: {config['quality_tier']}")
print(f"      Search Strategy: {config['search_strategy']}")
print(f"      Max Datapoints: {config['max_datapoints']}")
print(f"   ")
print(f"   Processing Options:")
print(f"      Enable Simulation: {config['enable_simulation']}")
print(f"      Enable Downsampling: {config['enable_downsampling']}")

print(f"\n✅ Configuration Complete!")
print(f"   Ready to proceed to Section 2 (UDL Authentication)")

# Return config for next section
print(f"\n📦 Exporting configuration...")
import json
with open('pipeline_config.json', 'w') as f:
    json.dump({
        'satellite_ids': config['satellite_ids'],
        'start_time': config['start_time'].isoformat(),
        'end_time': config['end_time'].isoformat(),
        'quality_tier': config['quality_tier'],
        'search_strategy': config['search_strategy'],
        'max_datapoints': config['max_datapoints'],
        'enable_simulation': config['enable_simulation'],
        'enable_downsampling': config['enable_downsampling']
    }, f, indent=2)

print(f"   ✅ Configuration saved to pipeline_config.json")
print("="*80)
