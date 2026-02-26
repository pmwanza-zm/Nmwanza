# 🔧 Pipeline Setup Instructions
**Comprehensive Installation & Configuration Guide**

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Data Files](#data-files)
5. [Testing Installation](#testing)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements {#system-requirements}

### Python Version
- **Required:** Python 3.12 or higher
- **Recommended:** Python 3.12.1+

**Check your version:**
```bash
python --version
# or
python3 --version
```

**If you need to install/upgrade Python:**
- **macOS:** `brew install python@3.12`
- **Ubuntu:** `sudo apt install python3.12`
- **Windows:** Download from python.org

### Operating System
**Tested on:**
- macOS 14+ (Apple Silicon & Intel)
- Ubuntu 22.04+
- Windows 11

### Disk Space
- **Minimum:** 500 MB
- **Recommended:** 1 GB (for data files)

### Network
- Internet connection required for:
  - UDL API access
  - Package installation
  - Initial setup

---

## Installation {#installation}

### Step 1: Clone Repository
```bash
# Navigate to where you want the project
cd ~/Documents

# Clone the repository
git clone https://github.com/pmwanza-zm/Nmwanza.git

# Navigate to pipeline directory
cd Nmwanza/uct-benchmark-pipeline

# Verify you're in the right place
pwd
# Should show: .../Nmwanza/uct-benchmark-pipeline
```

### Step 2: Create Virtual Environment (Recommended)

**Why use a virtual environment?**
- Isolates project dependencies
- Prevents package conflicts
- Easy to reset if something breaks
```bash
# Create virtual environment
python -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# You should see (.venv) in your prompt
```

### Step 3: Install Dependencies
```bash
# Upgrade pip first
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# Verify installation
pip list
```

**Required packages:**
- pandas >= 2.0.0
- numpy >= 1.24.0
- matplotlib >= 3.7.0
- python-dotenv >= 1.0.0
- requests >= 2.31.0
- aiohttp >= 3.9.0

### Step 4: Verify UCT Benchmark Modules
```bash
# Set Python path
export PYTHONPATH=.

# Test import
python -c "from uct_benchmark.api import apiIntegration; print('✅ Modules found')"
```

**If you get `ModuleNotFoundError`:**
- Make sure you're in the correct directory
- Verify PYTHONPATH is set: `echo $PYTHONPATH`
- Check the parent directory structure

---

## Configuration {#configuration}

### Step 1: UDL API Credentials

**Get credentials from:**
- UCT Benchmark team lead (Kelvin)
- UDL administrator
- Your organization's API manager

### Step 2: Create .env File
```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env
# or
vim .env
# or use any text editor
```

**Required format:**
```
UDL_USERNAME=your_actual_username
UDL_PASSWORD=your_actual_password
```

**Important notes:**
- ✅ No quotes around values
- ✅ No spaces around `=`
- ✅ One credential per line
- ❌ Never commit .env to Git

**Example of CORRECT format:**
```
UDL_USERNAME=patrick.mwanza
UDL_PASSWORD=SecurePass123!
```

**Example of WRONG format:**
```
UDL_USERNAME = "patrick.mwanza"  # ❌ Has spaces and quotes
UDL_PASSWORD='SecurePass123!'    # ❌ Has quotes
```

### Step 3: Verify Credentials
```bash
# Test authentication
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('Username:', os.getenv('UDL_USERNAME'))
print('Password:', '***' if os.getenv('UDL_PASSWORD') else 'NOT SET')
"
```

**Expected output:**
```
Username: your_username
Password: ***
```

### Step 4: Configure Pipeline Parameters (Optional)

Edit `complete_pipeline_sections_1_to_11_consolidated.py`:

**Line 52 - Satellites:**
```python
'satellite_ids': [26608, 42915],  # Change to your satellites
```

**Line 58 - Quality Tier:**
```python
'quality_tier': 'T3',  # Options: T1, T2, T3, T4
```

**Line 55 - Time Range:**
```python
'start_time': datetime.now() - timedelta(days=30),  # Change days
```

---

## Data Files {#data-files}

### Required Files

The pipeline needs these data files in the `data/` directory:

**1. referenceTLEs_.csv**
- Contains TLE orbital elements
- Used for satellite propagation
- Contact team if missing

**2. sensorCounts.csv**
- Ground sensor configurations
- Used for visibility calculations
- Contact team if missing

### Verify Data Files
```bash
# Check if data files exist
ls -lh data/referenceTLEs_.csv
ls -lh data/sensorCounts.csv

# Check number of satellites in TLE file
wc -l data/referenceTLEs_.csv
```

### Getting Data Files

**If files are missing:**
1. Contact UCT Benchmark team
2. Check team shared drive
3. Download from Space-Track.org (for TLEs)

---

## Testing Installation {#testing}

### Test 1: Python Environment
```bash
python --version
# Should be 3.12+
```

### Test 2: Package Installation
```bash
python -c "import pandas, numpy, matplotlib; print('✅ Packages OK')"
```

### Test 3: UCT Benchmark Modules
```bash
export PYTHONPATH=.
python -c "from uct_benchmark.api.apiIntegration import UDLTokenGen; print('✅ Modules OK')"
```

### Test 4: UDL Authentication
```bash
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
from uct_benchmark.api.apiIntegration import UDLTokenGen

username = os.getenv('UDL_USERNAME')
password = os.getenv('UDL_PASSWORD')

if username and password:
    token = UDLTokenGen(username, password)
    print('✅ Authentication successful')
else:
    print('❌ No credentials found')
"
```

### Test 5: Data Files
```bash
python -c "
import pandas as pd
tle = pd.read_csv('data/referenceTLEs_.csv')
sensors = pd.read_csv('data/sensorCounts.csv')
print(f'✅ TLEs: {len(tle)} satellites')
print(f'✅ Sensors: {len(sensors)} sensors')
"
```

### Test 6: Full Pipeline (Quick Test)
```bash
# Run with default configuration
export PYTHONPATH=.
python complete_pipeline_sections_1_to_11_consolidated.py
```

**Expected runtime:** 3-5 minutes

**Expected output:**
```
SECTION 1: Configuration ✅
SECTION 2: Authentication ✅
...
SECTION 11: Simulation ✅
Final: XX → YY observations
```

---

## Troubleshooting {#troubleshooting}

### Issue: "command not found: python"

**Solution:**
```bash
# Try python3 instead
python3 --version

# Or create alias
alias python=python3
```

### Issue: "No module named 'uct_benchmark'"

**Solutions:**
```bash
# 1. Set PYTHONPATH
export PYTHONPATH=.

# 2. Verify you're in correct directory
pwd  # Should end with /uct-benchmark-pipeline

# 3. Check directory structure
ls -la  # Should see complete_pipeline_sections_1_to_11_consolidated.py
```

### Issue: "No UDL credentials found"

**Solutions:**
```bash
# 1. Check .env exists
ls -la .env

# 2. Check .env format
cat .env

# 3. Verify load_dotenv() is working
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('UDL_USERNAME'))"
```

### Issue: "FileNotFoundError: data/referenceTLEs_.csv"

**Solutions:**
```bash
# 1. Check if data directory exists
ls -la data/

# 2. Contact team for data files

# 3. Verify file paths in code match actual structure
```

### Issue: Virtual environment not activating

**Solutions:**
```bash
# macOS/Linux:
source .venv/bin/activate

# Windows (Command Prompt):
.venv\Scripts\activate.bat

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# If PowerShell gives error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Advanced Configuration

### Custom Data Locations

Edit paths in the script if your data is elsewhere:
```python
# Line ~2300
tle_df = pd.read_csv('/path/to/your/TLEs.csv')
sensor_df = pd.read_csv('/path/to/your/sensors.csv')
```

### Performance Tuning

**For faster execution:**
```python
# Reduce time range
'start_time': datetime.now() - timedelta(days=7),  # Instead of 30

# Reduce satellites
'satellite_ids': [26608],  # Test with one satellite first
```

### Logging

**Enable detailed logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Next Steps

After successful installation:

1. ✅ Read `QUICK_START_GUIDE.md` for basic usage
2. ✅ Review `COMPLETE_PIPELINE_TUTORIAL.md` for detailed walkthrough
3. ✅ Explore individual section scripts in `individual_sections/`
4. ✅ Run your own satellites and configurations

---

**Installation complete!** 🎉

**Patrick Mwanza** | UCT Benchmark | Feb 2026
