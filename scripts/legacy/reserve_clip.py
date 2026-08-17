import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent
SRC     = DATA_DIR / "combined_fire_with_timestamp.csv"
GEOJSON = DATA_DIR / "east_ural_reserve.geojson"
OUT     = DATA_DIR / "fires_near_reserve.csv"
CHUNK   = 500_000
PAD_DEG = 0.8     # padding around the reserve (see note below for km)

# --- derive the bounding box from the real polygon ---
gj = json.loads(GEOJSON.read_text())
lons, lats = [], []
def walk(c):
    if isinstance(c[0], (int, float)):
        lons.append(c[0]); lats.append(c[1])
    else:
        for x in c: walk(x)
for feat in gj["features"]:
    walk(feat["geometry"]["coordinates"])

min_lon, max_lon = min(lons) - PAD_DEG, max(lons) + PAD_DEG
min_lat, max_lat = min(lats) - PAD_DEG, max(lats) + PAD_DEG
print(f"Reserve bounds: lon {min(lons):.4f}..{max(lons):.4f}, "
      f"lat {min(lats):.4f}..{max(lats):.4f}")
print(f"Padded bbox   : lon {min_lon:.4f}..{max_lon:.4f}, "
      f"lat {min_lat:.4f}..{max_lat:.4f}  (pad {PAD_DEG}°)")

# --- stream the combined file, keep only rows inside the bbox ---
if OUT.exists():
    OUT.unlink()
total_in = total_kept = 0
first = True
for chunk in pd.read_csv(SRC, chunksize=CHUNK):
    total_in += len(chunk)
    m = (chunk["longitude"].between(min_lon, max_lon) &
         chunk["latitude"].between(min_lat, max_lat))
    kept = chunk[m].copy()
    if len(kept):
        # kepler-friendly time formats: acq_time HH:MM, acq_datetime "YYYY-MM-DD HH:MM:SS"
        t = pd.to_numeric(kept["acq_time"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(4)
        kept["acq_time"] = t.str[:2] + ":" + t.str[2:]
        kept["acq_datetime"] = kept["acq_datetime"].astype(str).str.replace("T", " ", n=1)
        kept.to_csv(OUT, mode="a", index=False, header=first)
        first = False
        total_kept += len(kept)

print(f"\nScanned {total_in:,} rows -> kept {total_kept:,} inside the box")
print(f"Saved -> {OUT.name}")