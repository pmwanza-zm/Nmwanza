"""
SECTION 5: API QUERY LAYER
Executes the selected search strategy to retrieve data from UDL
"""
import json
import pandas as pd
from datetime import datetime, timedelta

print("="*80)
print("SECTION 5: API QUERY LAYER")
print("="*80)

# Load previous sections
print("\n📥 Loading previous sections...")
with open('pipeline_config.json', 'r') as f:
    config = json.load(f)
    
with open('pipeline_auth.json', 'r') as f:
    auth = json.load(f)
    
with open('pipeline_strategy.json', 'r') as f:
    strategy = json.load(f)

token = auth['token']
satellite_ids = config['satellite_ids']
start_time = datetime.fromisoformat(config['start_time'])
end_time = datetime.fromisoformat(config['end_time'])

print(f"   ✅ Configuration: {len(satellite_ids)} satellites")
print(f"   ✅ Authentication: Token ready")
print(f"   ✅ Strategy: {strategy['selected_strategy']}")

# Import API functions
from uct_benchmark.api.apiIntegration import asyncUDLBatchQuery, datetimeToUDL

print(f"\n🚀 Executing {strategy['selected_strategy']} Strategy")
print(f"   {strategy['strategy_params']['description']}")
print("="*80)

# Execute selected strategy
if strategy['selected_strategy'] == 'FAST':
    # FAST Strategy: Single query per satellite
    print(f"\n📡 FAST Strategy Execution:")
    print(f"   Querying {len(satellite_ids)} satellites over full time range...")
    
    sv_params = []
    for sat in satellite_ids:
        sv_params.append({
            'satNo': str(sat),
            'epoch': f"{datetimeToUDL(start_time)}..{datetimeToUDL(end_time)}"
        })
    
    print(f"   Making {len(sv_params)} API calls...")
    sv_df = asyncUDLBatchQuery(token, 'statevector', sv_params, dt=0.5)
    print(f"   ✅ Retrieved {len(sv_df)} state vectors")

elif strategy['selected_strategy'] == 'WINDOWED':
    # WINDOWED Strategy: Time-chunked queries
    window_hours = strategy['strategy_params']['window_size_hours']
    
    print(f"\n📡 WINDOWED Strategy Execution:")
    print(f"   Window size: {window_hours} hours")
    print(f"   Time range: {start_time.date()} to {end_time.date()}")
    
    # Create time windows
    windows = []
    current = start_time
    while current < end_time:
        window_end = min(current + timedelta(hours=window_hours), end_time)
        windows.append((current, window_end))
        current = window_end
    
    print(f"   Created {len(windows)} time windows")
    print(f"   Expected API calls: {len(windows) * len(satellite_ids)}")
    
    # Query each window
    all_sv_data = []
    
    for i, (win_start, win_end) in enumerate(windows, 1):
        # Show progress every 5 windows
        if i % 5 == 1 or i == len(windows):
            print(f"\n   Window {i}/{len(windows)}: {win_start.date()} to {win_end.date()}")
        
        sv_params = []
        for sat in satellite_ids:
            sv_params.append({
                'satNo': str(sat),
                'epoch': f"{datetimeToUDL(win_start)}..{datetimeToUDL(win_end)}"
            })
        
        try:
            window_data = asyncUDLBatchQuery(token, 'statevector', sv_params, dt=0.5)
            all_sv_data.append(window_data)
            
            if i % 5 == 1 or i == len(windows):
                print(f"      Retrieved {len(window_data)} records")
        except Exception as e:
            print(f"      ⚠️ Window {i} failed: {e}")
            continue
    
    # Combine all windows
    if all_sv_data:
        sv_df = pd.concat(all_sv_data, ignore_index=True)
        print(f"\n   ✅ Total retrieved: {len(sv_df)} state vectors across {len(windows)} windows")
    else:
        sv_df = pd.DataFrame()
        print(f"\n   ❌ No data retrieved")

else:  # HYBRID
    # HYBRID Strategy: Count-first optimization
    print(f"\n📡 HYBRID Strategy Execution:")
    print(f"   Step 1: Checking expected record count...")
    
    from uct_benchmark.api.apiIntegration import UDLQuery
    
    # Query count for first satellite to estimate
    test_params = {
        'satNo': str(satellite_ids[0]),
        'epoch': f"{datetimeToUDL(start_time)}..{datetimeToUDL(end_time)}"
    }
    
    try:
        test_count = UDLQuery(token, 'statevector', test_params, count=True)
        estimated_total = test_count * len(satellite_ids)
        print(f"      Sample count: {test_count} (satellite {satellite_ids[0]})")
        print(f"      Estimated total: ~{estimated_total}")
    except Exception as e:
        print(f"      ⚠️ Count query failed: {e}, defaulting to direct query")
        estimated_total = 0
    
    threshold = strategy['strategy_params']['threshold']
    
    if estimated_total > threshold:
        print(f"\n   Step 2: Count > {threshold} → Using chunked approach")
        
        # Use 24-hour windows for GEO
        window_hours = 24
        windows = []
        current = start_time
        while current < end_time:
            window_end = min(current + timedelta(hours=window_hours), end_time)
            windows.append((current, window_end))
            current = window_end
        
        all_sv_data = []
        for win_start, win_end in windows:
            sv_params = []
            for sat in satellite_ids:
                sv_params.append({
                    'satNo': str(sat),
                    'epoch': f"{datetimeToUDL(win_start)}..{datetimeToUDL(win_end)}"
                })
            window_data = asyncUDLBatchQuery(token, 'statevector', sv_params, dt=0.5)
            all_sv_data.append(window_data)
        
        sv_df = pd.concat(all_sv_data, ignore_index=True)
    else:
        print(f"\n   Step 2: Count ≤ {threshold} → Using direct query")
        
        sv_params = []
        for sat in satellite_ids:
            sv_params.append({
                'satNo': str(sat),
                'epoch': f"{datetimeToUDL(start_time)}..{datetimeToUDL(end_time)}"
            })
        
        sv_df = asyncUDLBatchQuery(token, 'statevector', sv_params, dt=0.5)
    
    print(f"   ✅ Retrieved {len(sv_df)} state vectors")

# Data summary
print(f"\n📊 Retrieved Data Summary:")
print(f"   Total records: {len(sv_df)}")

if len(sv_df) > 0:
    print(f"   Satellites in data: {sorted(sv_df['satNo'].unique())}")
    print(f"   Time range: {sv_df['epoch'].min()} to {sv_df['epoch'].max()}")
    
    # Per-satellite breakdown
    print(f"\n   Per-Satellite Breakdown:")
    for sat in satellite_ids:
        sat_data = sv_df[sv_df['satNo'] == sat]
        if len(sat_data) > 0:
            print(f"      Satellite {sat}: {len(sat_data)} records")
        else:
            print(f"      Satellite {sat}: 0 records (no data)")

# Save retrieved data
print(f"\n📦 Saving retrieved data...")

# Save DataFrame
sv_df.to_csv('pipeline_state_vectors.csv', index=False)
print(f"   ✅ State vectors saved to pipeline_state_vectors.csv")

# Save metadata
query_metadata = {
    'strategy_used': strategy['selected_strategy'],
    'total_records': len(sv_df),
    'satellites_queried': satellite_ids,
    'satellites_with_data': sv_df['satNo'].unique().tolist() if len(sv_df) > 0 else [],
    'time_range_start': start_time.isoformat(),
    'time_range_end': end_time.isoformat(),
    'columns': sv_df.columns.tolist() if len(sv_df) > 0 else []
}

with open('pipeline_query_metadata.json', 'w') as f:
    json.dump(query_metadata, f, indent=2)

print(f"   ✅ Query metadata saved to pipeline_query_metadata.json")

print("\n✅ Section 5 Complete!")
print(f"   Retrieved {len(sv_df)} state vectors using {strategy['selected_strategy']} strategy")
print(f"   Ready to proceed to Section 6 (Deduplication & Validation)")
print("="*80)
