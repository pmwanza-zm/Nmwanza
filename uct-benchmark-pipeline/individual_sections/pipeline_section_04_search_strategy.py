"""
SECTION 4: SEARCH STRATEGY SELECTION
Selects optimal API query strategy (FAST/WINDOWED/HYBRID)
"""
import json
from datetime import datetime

print("="*80)
print("SECTION 4: SEARCH STRATEGY SELECTION")
print("="*80)

# Load configuration and regime data
print("\n📥 Loading previous sections...")
with open('pipeline_config.json', 'r') as f:
    config = json.load(f)
    
with open('pipeline_regimes.json', 'r') as f:
    regime_data = json.load(f)

# Parse time range
start_time = datetime.fromisoformat(config['start_time'])
end_time = datetime.fromisoformat(config['end_time'])

print(f"   ✅ Configuration loaded")
print(f"   ✅ Regime data loaded")

# Extract decision criteria
num_satellites = len(config['satellite_ids'])
time_span_days = (end_time - start_time).days
primary_regime = regime_data['primary_regime']
user_strategy = config['search_strategy']

print(f"\n📊 Strategy Selection Criteria:")
print(f"   Number of Satellites: {num_satellites}")
print(f"   Time Span: {time_span_days} days")
print(f"   Primary Orbital Regime: {primary_regime}")
print(f"   User Preference: {user_strategy}")

# Define strategy selection logic
print(f"\n🤔 Evaluating Strategy Options...")

strategies_evaluated = {
    'FAST': {
        'suitable': False,
        'reason': '',
        'score': 0
    },
    'WINDOWED': {
        'suitable': False,
        'reason': '',
        'score': 0
    },
    'HYBRID': {
        'suitable': True,  # Always suitable as fallback
        'reason': 'Count-first optimization (default)',
        'score': 50
    }
}

# FAST Strategy evaluation
if num_satellites <= 5 and time_span_days <= 7:
    strategies_evaluated['FAST']['suitable'] = True
    strategies_evaluated['FAST']['reason'] = f'Small window ({time_span_days} days) + few satellites ({num_satellites})'
    strategies_evaluated['FAST']['score'] = 90
    print(f"   ✅ FAST: Suitable - {strategies_evaluated['FAST']['reason']}")
else:
    strategies_evaluated['FAST']['reason'] = f'Too many satellites ({num_satellites}) or long window ({time_span_days} days)'
    print(f"   ❌ FAST: Not suitable - {strategies_evaluated['FAST']['reason']}")

# WINDOWED Strategy evaluation
if num_satellites >= 10 or time_span_days >= 30:
    strategies_evaluated['WINDOWED']['suitable'] = True
    strategies_evaluated['WINDOWED']['reason'] = f'Large window ({time_span_days} days) or many satellites ({num_satellites})'
    strategies_evaluated['WINDOWED']['score'] = 85
    print(f"   ✅ WINDOWED: Suitable - {strategies_evaluated['WINDOWED']['reason']}")
else:
    strategies_evaluated['WINDOWED']['reason'] = f'Small scale ({num_satellites} sats, {time_span_days} days)'
    print(f"   ⚠️ WINDOWED: Possible but not optimal - {strategies_evaluated['WINDOWED']['reason']}")

# HYBRID is always suitable
print(f"   ✅ HYBRID: Always suitable - {strategies_evaluated['HYBRID']['reason']}")

# Select strategy based on user preference or automatic selection
print(f"\n🎯 Strategy Selection Decision:")

if user_strategy.lower() == 'auto':
    # Automatic selection - pick highest score
    selected = max(strategies_evaluated.items(), key=lambda x: x[1]['score'])
    selected_strategy = selected[0]
    selection_reason = f"Auto-selected based on criteria (score: {selected[1]['score']})"
    
elif user_strategy.upper() in ['FAST', 'WINDOWED', 'HYBRID']:
    selected_strategy = user_strategy.upper()
    if strategies_evaluated[selected_strategy]['suitable']:
        selection_reason = f"User override (suitable: {strategies_evaluated[selected_strategy]['reason']})"
    else:
        selection_reason = f"User override (warning: {strategies_evaluated[selected_strategy]['reason']})"
else:
    # Invalid preference, fallback to HYBRID
    selected_strategy = 'HYBRID'
    selection_reason = f"Invalid user preference '{user_strategy}', defaulting to HYBRID"

print(f"   Selected: {selected_strategy}")
print(f"   Reason: {selection_reason}")

# Define strategy-specific parameters
if selected_strategy == 'FAST':
    strategy_params = {
        'method': 'single_query_per_satellite',
        'description': 'Single query per satellite over full time range',
        'window_size_hours': None,
        'expected_api_calls': num_satellites
    }
    
elif selected_strategy == 'WINDOWED':
    # Window size based on orbital regime
    window_hours = {
        'LEO': 6,
        'MEO': 12,
        'GEO': 24,
        'HEO': 8
    }.get(primary_regime, 12)
    
    num_windows = max(1, int(time_span_days * 24 / window_hours))
    
    strategy_params = {
        'method': 'time_chunked_queries',
        'description': f'Split into {window_hours}-hour windows based on {primary_regime} regime',
        'window_size_hours': window_hours,
        'expected_windows': num_windows,
        'expected_api_calls': num_satellites * num_windows
    }
    
else:  # HYBRID
    strategy_params = {
        'method': 'count_first_optimization',
        'description': 'Query count first, then decide: direct if ≤10k, chunked if >10k',
        'threshold': 10000,
        'expected_api_calls': 'variable (1-N)'
    }

print(f"\n📋 Strategy Configuration:")
print(f"   Method: {strategy_params['method']}")
print(f"   Description: {strategy_params['description']}")
for key, value in strategy_params.items():
    if key not in ['method', 'description']:
        print(f"   {key.replace('_', ' ').title()}: {value}")

# Save strategy selection for next section
print(f"\n📦 Saving strategy selection...")

strategy_data = {
    'selected_strategy': selected_strategy,
    'selection_reason': selection_reason,
    'strategy_params': strategy_params,
    'criteria': {
        'num_satellites': num_satellites,
        'time_span_days': time_span_days,
        'primary_regime': primary_regime
    },
    'evaluated_strategies': strategies_evaluated
}

with open('pipeline_strategy.json', 'w') as f:
    json.dump(strategy_data, f, indent=2)

print(f"   ✅ Strategy data saved to pipeline_strategy.json")

print("\n✅ Section 4 Complete!")
print(f"   Selected Strategy: {selected_strategy}")
print(f"   Ready to proceed to Section 5 (API Query Layer)")
print("="*80)
