"""
SECTION 2: UDL AUTHENTICATION
Establishes authentication with the UDL API
"""
import json
import os
from dotenv import load_dotenv

print("="*80)
print("SECTION 2: UDL AUTHENTICATION")
print("="*80)

# Load configuration from Section 1
print("\n📥 Loading configuration from Section 1...")
with open('pipeline_config.json', 'r') as f:
    config = json.load(f)
print(f"   ✅ Configuration loaded")

# Load environment variables
load_dotenv()

print("\n🔑 Checking UDL credentials...")

# Check for existing token or credentials
token = os.getenv('UDL_TOKEN')
username = os.getenv('UDL_USERNAME')
password = os.getenv('UDL_PASSWORD')

if token:
    print(f"   ✅ Existing UDL_TOKEN found")
    print(f"   Token preview: {token[:20]}...")
    token_source = "existing"
    
elif username and password:
    print(f"   ✅ UDL_USERNAME and UDL_PASSWORD found")
    print(f"   Username: {username}")
    print(f"   Generating new token...")
    
    from uct_benchmark.api.apiIntegration import UDLTokenGen
    
    try:
        token = UDLTokenGen(username, password)
        print(f"   ✅ Token generated successfully!")
        print(f"   Token preview: {token[:20]}...")
        token_source = "generated"
        
        # Optionally save to .env
        print(f"\n💡 Tip: Add this to your .env file to avoid regenerating:")
        print(f"   UDL_TOKEN={token}")
        
    except Exception as e:
        print(f"   ❌ Token generation failed: {e}")
        exit(1)
        
else:
    print(f"   ❌ No UDL credentials found!")
    print(f"\n📝 Please add to your .env file:")
    print(f"   UDL_TOKEN=your_token_here")
    print(f"   OR")
    print(f"   UDL_USERNAME=your_username")
    print(f"   UDL_PASSWORD=your_password")
    exit(1)

# Test the token with a simple query
print(f"\n🧪 Testing authentication...")
from uct_benchmark.api.apiIntegration import UDLQuery

try:
    # Simple test query - get count of ISS state vectors from last day
    test_result = UDLQuery(
        token, 
        'statevector', 
        {'satNo': '25544', 'epoch': '>now-1 days'},
        count=True
    )
    
    print(f"   ✅ Authentication successful!")
    print(f"   Test query returned: {test_result} records for ISS")
    auth_status = "valid"
    
except Exception as e:
    print(f"   ⚠️ Authentication test failed: {e}")
    print(f"   Token may be invalid or expired")
    auth_status = "failed"
    # Continue anyway for demonstration

# Save authentication data for next section
print(f"\n📦 Saving authentication data...")

auth_data = {
    'token': token,
    'token_source': token_source,
    'auth_status': auth_status,
    'test_query_count': test_result if auth_status == "valid" else 0
}

with open('pipeline_auth.json', 'w') as f:
    json.dump(auth_data, f, indent=2)

print(f"   ✅ Authentication data saved to pipeline_auth.json")

print("\n✅ Section 2 Complete!")
print(f"   Ready to proceed to Section 3 (Orbital Regime Detection)")
print("="*80)
