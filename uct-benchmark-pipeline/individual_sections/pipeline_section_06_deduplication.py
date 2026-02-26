"""
SECTION 6: DEDUPLICATION & VALIDATION
Removes duplicates and validates data quality
"""
import json
import pandas as pd

print("="*80)
print("SECTION 6: DEDUPLICATION & VALIDATION")
print("="*80)

# Load retrieved data
print("\n📥 Loading retrieved data from Section 5...")
sv_df = pd.read_csv('pipeline_state_vectors.csv')
sv_df['epoch'] = pd.to_datetime(sv_df['epoch'])

with open('pipeline_query_metadata.json', 'r') as f:
    query_meta = json.load(f)

print(f"   ✅ Loaded {len(sv_df)} state vectors")
print(f"   Strategy used: {query_meta['strategy_used']}")

original_count = len(sv_df)

# Step 1: Deduplication
print(f"\n📊 STEP 1: Deduplication")
print(f"   Before deduplication: {len(sv_df)} records")

# Natural key: satellite + epoch (unique identifier)
print(f"   Deduplication key: satNo + epoch")

# Check for duplicates
duplicates = sv_df.duplicated(subset=['satNo', 'epoch'], keep='first')
num_duplicates = duplicates.sum()

print(f"   Found {num_duplicates} duplicate records")

if num_duplicates > 0:
    # Show example duplicates
    dup_rows = sv_df[duplicates].head(3)
    print(f"\n   Example duplicates:")
    for _, row in dup_rows.iterrows():
        print(f"      Satellite {row['satNo']}, Epoch {row['epoch']}")
    
    # Remove duplicates
    sv_df = sv_df.drop_duplicates(subset=['satNo', 'epoch'], keep='first')
    print(f"\n   ✅ Removed {num_duplicates} duplicates")
else:
    print(f"   ✅ No duplicates found")

print(f"   After deduplication: {len(sv_df)} records")

# Step 2: Validate Required Fields
print(f"\n📊 STEP 2: Field Validation")

required_fields = ['satNo', 'epoch', 'xpos', 'ypos', 'zpos', 'xvel', 'yvel', 'zvel']
missing_fields = [f for f in required_fields if f not in sv_df.columns]

if missing_fields:
    print(f"   ❌ Missing required fields: {missing_fields}")
else:
    print(f"   ✅ All required fields present: {required_fields}")

# Check for null values in critical fields
print(f"\n   Checking for null values in critical fields...")
null_counts = {}
for field in required_fields:
    if field in sv_df.columns:
        null_count = sv_df[field].isna().sum()
        null_counts[field] = null_count
        if null_count > 0:
            print(f"      ⚠️ {field}: {null_count} null values")

total_nulls = sum(null_counts.values())
if total_nulls == 0:
    print(f"   ✅ No null values in critical fields")
else:
    print(f"\n   Removing records with null critical values...")
    sv_df_clean = sv_df.dropna(subset=required_fields)
    removed = len(sv_df) - len(sv_df_clean)
    print(f"   ✅ Removed {removed} records with null values")
    sv_df = sv_df_clean

# Step 3: Range Validation
print(f"\n📊 STEP 3: Range Validation")

# Validate position vectors (should be reasonable Earth orbit distances)
print(f"   Validating position vectors...")

# Calculate distance from Earth center
sv_df['distance_km'] = (sv_df['xpos']**2 + sv_df['ypos']**2 + sv_df['zpos']**2)**0.5

# Reasonable ranges:
# LEO: 6,378 - 8,378 km
# MEO: 8,378 - 35,786 km  
# GEO: 35,786 - 45,000 km
# HEO: can vary widely

min_distance = sv_df['distance_km'].min()
max_distance = sv_df['distance_km'].max()
mean_distance = sv_df['distance_km'].mean()

print(f"   Distance from Earth center:")
print(f"      Min: {min_distance:,.1f} km")
print(f"      Max: {max_distance:,.1f} km")
print(f"      Mean: {mean_distance:,.1f} km")

# Flag suspicious distances (too close to Earth or too far)
suspicious_low = sv_df[sv_df['distance_km'] < 6378]  # Below Earth surface
suspicious_high = sv_df[sv_df['distance_km'] > 100000]  # Beyond typical orbits

if len(suspicious_low) > 0:
    print(f"   ⚠️ Warning: {len(suspicious_low)} records below Earth surface!")
    
if len(suspicious_high) > 0:
    print(f"   ⚠️ Warning: {len(suspicious_high)} records beyond 100,000 km!")

if len(suspicious_low) == 0 and len(suspicious_high) == 0:
    print(f"   ✅ All positions within reasonable orbital ranges")

# Validate velocity vectors (should be reasonable orbital velocities)
print(f"\n   Validating velocity vectors...")

sv_df['velocity_km_s'] = (sv_df['xvel']**2 + sv_df['yvel']**2 + sv_df['zvel']**2)**0.5

min_velocity = sv_df['velocity_km_s'].min()
max_velocity = sv_df['velocity_km_s'].max()
mean_velocity = sv_df['velocity_km_s'].mean()

print(f"   Velocity magnitude:")
print(f"      Min: {min_velocity:.3f} km/s")
print(f"      Max: {max_velocity:.3f} km/s")
print(f"      Mean: {mean_velocity:.3f} km/s")

# Typical orbital velocities: 1-8 km/s
suspicious_velocity = sv_df[(sv_df['velocity_km_s'] < 0.5) | (sv_df['velocity_km_s'] > 12)]

if len(suspicious_velocity) > 0:
    print(f"   ⚠️ Warning: {len(suspicious_velocity)} records with unusual velocities!")
else:
    print(f"   ✅ All velocities within reasonable ranges")

# Step 4: Filter satellites without TLE data
print(f"\n📊 STEP 4: TLE Availability Check")

# Load TLE data
tle_df = pd.read_csv('data/referenceTLEs_.csv')
satellites_with_tle = tle_df['satNo'].unique()

print(f"   Checking TLE availability...")
sv_satellites = sv_df['satNo'].unique()

for sat in sv_satellites:
    if sat in satellites_with_tle:
        print(f"      Satellite {sat}: ✅ TLE available")
    else:
        print(f"      Satellite {sat}: ❌ No TLE data")

sv_df_with_tle = sv_df[sv_df['satNo'].isin(satellites_with_tle)]
removed_no_tle = len(sv_df) - len(sv_df_with_tle)

if removed_no_tle > 0:
    print(f"\n   ⚠️ Removed {removed_no_tle} records without TLE data")
else:
    print(f"\n   ✅ All satellites have TLE data")

sv_df = sv_df_with_tle

# Final Summary
print(f"\n📊 VALIDATION SUMMARY:")
print("="*80)
print(f"   Original records: {original_count}")
print(f"   After deduplication: -{num_duplicates}")
print(f"   After null removal: -{total_nulls}")
print(f"   After TLE filter: -{removed_no_tle}")
print(f"   ─────────────────────────")
print(f"   Final valid records: {len(sv_df)}")
print(f"   Retention rate: {len(sv_df)/original_count*100:.1f}%")

print(f"\n   Final Per-Satellite Breakdown:")
for sat in sorted(sv_df['satNo'].unique()):
    sat_count = len(sv_df[sv_df['satNo'] == sat])
    print(f"      Satellite {sat}: {sat_count} records")

# Save validated data
print(f"\n📦 Saving validated data...")

sv_df.to_csv('pipeline_validated_data.csv', index=False)
print(f"   ✅ Validated data saved to pipeline_validated_data.csv")

validation_metadata = {
    'original_count': original_count,
    'duplicates_removed': int(num_duplicates),
    'nulls_removed': int(total_nulls),
    'no_tle_removed': int(removed_no_tle),
    'final_count': len(sv_df),
    'retention_rate': len(sv_df)/original_count if original_count > 0 else 0,
    'satellites': sv_df['satNo'].unique().tolist(),
    'validation_checks': {
        'required_fields': 'passed' if not missing_fields else 'failed',
        'null_values': 'passed' if total_nulls == 0 else 'warning',
        'position_range': 'passed' if len(suspicious_low) == 0 and len(suspicious_high) == 0 else 'warning',
        'velocity_range': 'passed' if len(suspicious_velocity) == 0 else 'warning',
        'tle_availability': 'passed' if removed_no_tle == 0 else 'warning'
    }
}

with open('pipeline_validation_metadata.json', 'w') as f:
    json.dump(validation_metadata, f, indent=2)

print(f"   ✅ Validation metadata saved to pipeline_validation_metadata.json")

print("\n✅ Section 6 Complete!")
print(f"   Validated {len(sv_df)} records ready for processing")
print(f"   Ready to proceed to Section 7 (Track Binning)")
print("="*80)
