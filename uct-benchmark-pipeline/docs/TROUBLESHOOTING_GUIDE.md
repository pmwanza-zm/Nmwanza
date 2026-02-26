# 🔧 Troubleshooting Guide - UCT Benchmark Pipeline
**Common Errors & Solutions**

## Import Errors

### Error: `ModuleNotFoundError: No module named 'uct_benchmark'`

**Solution:**
```bash
export PYTHONPATH=.
python complete_pipeline_sections_1_to_11_consolidated.py
```

### Error: `ModuleNotFoundError: No module named 'pandas'`

**Solution:**
```bash
pip install pandas numpy matplotlib python-dotenv
```

## Authentication Errors

### Error: `No UDL credentials found!`

**Solution:** Create `.env` file:
```bash
cat > .env << 'ENVFILE'
UDL_USERNAME=your_username
UDL_PASSWORD=your_password
ENVFILE
```

### Error: `401 Unauthorized`

**Solutions:**
1. Check credentials in `.env`
2. Verify account is active
3. Try regenerating token

## API Errors

### Error: `400 Bad Request` on UDL endpoint

**Solution:** Use correct endpoint:
```python
# ❌ OLD:
UDLQuery(token, 'elset/current', {'satNo': '26608'})

# ✅ NEW:
UDLQuery(token, 'elset', {'satNo': '26608'})
```

### Error: `No data retrieved` (0 records)

**Solutions:**
1. Try shorter time range (7 days instead of 30)
2. Check satellite is active
3. Try different satellites: `[26608, 42915]`

## Data Processing Errors

### Error: `KeyError: column not in index`

**Solution:** Check available columns first:
```python
print("Available columns:", list(df.columns))
```

### Error: `'<' not supported between str and int`

**Solution:** Explicit type conversion:
```python
mean_motion = float(tle_row['meanMotion'])
```

## File Errors

### Error: `FileNotFoundError: data/referenceTLEs_.csv`

**Solutions:**
1. Check current directory: `pwd`
2. Verify file exists: `ls data/`
3. Contact team for data files

## Simulation Errors

### Error: `No simulation generated` (0 synthetic)

**Possible causes:**
- Gaps too small (need >6 hours for GEO)
- Insufficient orbital coverage (<1 period)
- No TLE data available

**Check:**
```python
# Check gap sizes
gaps = df.groupby('satNo')['obTime'].diff()
print(f"Mean gap: {gaps.mean()}")
```

---

**Patrick Mwanza** | UCT Benchmark | Feb 2026
