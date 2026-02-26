# 🆕 Setup Guide for New Users
**Anyone with UDL credentials can use this pipeline**

## What You Need

1. **UDL Account** - Contact UCT Benchmark team for:
   - UDL Username
   - UDL Password

2. **Python 3.12+**
```bash
   python --version
```

3. **Git** (for cloning)

## Step 1: Clone Repository
```bash
git clone https://github.com/pmwanza-zm/Nmwanza.git
cd Nmwanza/uct-benchmark-pipeline
```

## Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 3: Set Up YOUR Credentials
```bash
cp .env.example .env
# Edit .env with YOUR credentials
```

Edit `.env`:
```
UDL_USERNAME=YOUR_USERNAME_HERE
UDL_PASSWORD=YOUR_PASSWORD_HERE
```

**⚠️ NEVER commit .env to Git!**

## Step 4: (Optional) Customize Satellites

Edit `complete_pipeline_sections_1_to_11_consolidated.py` (line 52):
```python
config = {
    'satellite_ids': [25544, 28654],  # Change to YOUR satellites
}
```

## Step 5: Run Pipeline
```bash
export PYTHONPATH=.
python complete_pipeline_sections_1_to_11_consolidated.py
```

**Expected output:**
```
✅ Section 1-11 complete
Input: XX state vectors
Output: XX observations (XX real + XX simulated)
```

## Customize for Your Use Case

### Change Time Range
```python
config = {
    'start_time': datetime.now() - timedelta(days=7),  # Last 7 days
}
```

### Change Quality Tier
```python
config = {
    'quality_tier': 'T2',  # T1/T2/T3/T4
}
```

## Troubleshooting

- **"No credentials"** → Check `.env` file exists
- **"Authentication failed"** → Verify username/password
- **"No data"** → Try different satellites or shorter time range

**For more help:** See `TROUBLESHOOTING_GUIDE.md`

## Your Privacy

- Credentials stored ONLY in YOUR local `.env` file
- Never shared or committed to Git
- Works the same for every user

---

**Patrick Mwanza** | UCT Benchmark | Feb 2026
