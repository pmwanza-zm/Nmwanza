# ⚡ Quick Start Guide - UCT Benchmark Pipeline
**Get running in 5 minutes**

## Prerequisites (1 minute)
```bash
# Check Python version
python --version  # Need 3.12+

# Install packages
pip install pandas numpy matplotlib python-dotenv
```

## Setup Credentials (1 minute)

Create `.env` file:
```bash
cat > .env << 'ENVFILE'
UDL_USERNAME=your_username
UDL_PASSWORD=your_password
ENVFILE
```

## Run Pipeline (30 seconds)
```bash
# Set Python path
export PYTHONPATH=.

# Run complete pipeline
python complete_pipeline_sections_1_to_11_consolidated.py
```

**That's it!** ✅

## Expected Output (2 minutes)
```
SECTION 1: Configuration ✅
SECTION 2: Authentication ✅
SECTION 3: Regime Detection (GEO) ✅
SECTION 4: Search Strategy (WINDOWED) ✅
SECTION 5: API Query (95 state vectors) ✅
SECTION 6: Deduplication (93 valid) ✅
SECTION 7: Track Binning (sparse mode) ✅
SECTION 8: Tier Routing (T3) ✅
SECTION 9: Downsampling (57 obs) ✅
SECTION 10: Simulation Decision (PROCEED) ✅
SECTION 11: Simulation (30 synthetic) ✅

Final: 57 → 87 observations (34.5% synthetic)
🎉 SUCCESS!
```

## Quick Configuration

Change satellites (line 52):
```python
config = {
    'satellite_ids': [25544, 28654],  # Change to YOUR satellites
}
```

Change tier (line 58):
```python
'quality_tier': 'T2',  # T1/T2/T3/T4
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module 'uct_benchmark'` | Run with `PYTHONPATH=.` |
| `No UDL credentials` | Create `.env` file |
| `FileNotFoundError` | Check you're in correct directory |

**For more help:** See `TROUBLESHOOTING_GUIDE.md`

---

**Patrick Mwanza** | UCT Benchmark | Feb 2026
