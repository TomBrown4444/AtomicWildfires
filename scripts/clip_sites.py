"""Clip the combined FIRMS fire detections to boxes around each nuclear site.

Two box modes:
  "pad"      : bounding box of the site polygon, plus PAD_DEG on every side.
               Used where the polygon itself is the area of interest
               (Chernobyl Exclusion Zone, East Ural Nature Reserve).
  "ref-size" : a fixed-size box centred on the facility, matching the total
               size of the East Ural reserve clip (about 117 x 205 km).
               Used for the three production plants, whose fenced sites are
               small compared to the landscape around them.

Output CSVs are formatted for kepler.gl time-series playback:
acq_datetime as "YYYY-MM-DD HH:MM:SS" and acq_time as "HH:MM".

Usage:
    uv run scripts/clip_sites.py                 # all sites
    uv run scripts/clip_sites.py chernobyl       # one or more named sites
"""
import sys
import pandas as pd
import json
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
BOUNDARIES = ROOT / "data" / "boundaries"
CLIPS      = ROOT / "data" / "clips"
SRC_RUSSIA  = ROOT / "data" / "processed" / "combined_fire_russia.csv"
SRC_UKRAINE = ROOT / "data" / "processed" / "combined_fire_ukraine.csv"
CHUNK    = 500_000
PAD_DEG  = 0.8

# Total box size of the East Ural reserve clip (its polygon bbox + 2*PAD_DEG),
# reused as the reference clip size for the facility-centred boxes.
REF_LON_SPAN = 0.2655275 + 2 * PAD_DEG   # 1.8655 degrees
REF_LAT_SPAN = 0.2383984 + 2 * PAD_DEG   # 1.8384 degrees


def geojson_bounds(path):
    gj = json.loads(path.read_text())
    lons, lats = [], []
    def walk(c):
        if isinstance(c[0], (int, float)):
            lons.append(c[0]); lats.append(c[1])
        else:
            for x in c: walk(x)
    for feat in gj["features"]:
        walk(feat["geometry"]["coordinates"])
    return min(lons), max(lons), min(lats), max(lats)


# name -> (boundary geojson, clip mode, source csv)
SITES = {
    "chernobyl": ("chernobyl_exclusion_zone.geojson", "pad", SRC_UKRAINE),
    "east_ural_reserve": ("east_ural_reserve.geojson", "pad", SRC_RUSSIA),
    "scc_seversk": ("scc_seversk.geojson", "ref-size", SRC_RUSSIA),
    "mcc_zheleznogorsk": ("mcc_zheleznogorsk.geojson", "ref-size", SRC_RUSSIA),
    "mayak_ozyorsk": ("mayak_pa.geojson", "ref-size", SRC_RUSSIA),
}

selected = sys.argv[1:] or list(SITES)
unknown = [s for s in selected if s not in SITES]
if unknown:
    sys.exit(f"Unknown site(s) {unknown}; choose from {list(SITES)}")

boxes, sources = {}, {}
for name in selected:
    gj_file, mode, src = SITES[name]
    lo, hi, la, ha = geojson_bounds(BOUNDARIES / gj_file)
    if mode == "pad":
        box = (lo - PAD_DEG, hi + PAD_DEG, la - PAD_DEG, ha + PAD_DEG)
    else:
        cx, cy = (lo + hi) / 2, (la + ha) / 2
        box = (cx - REF_LON_SPAN / 2, cx + REF_LON_SPAN / 2,
               cy - REF_LAT_SPAN / 2, cy + REF_LAT_SPAN / 2)
    boxes[name] = box
    sources.setdefault(src, []).append(name)
    print(f"{name:18s} box: lon {box[0]:.4f}..{box[1]:.4f}  lat {box[2]:.4f}..{box[3]:.4f}")

CLIPS.mkdir(parents=True, exist_ok=True)
outs = {name: CLIPS / f"fires_near_{name}.csv" for name in boxes}
for p in outs.values():
    if p.exists():
        p.unlink()

kept = {name: 0 for name in boxes}
first = {name: True for name in boxes}
for src, site_names in sources.items():
    total_in = 0
    for chunk in pd.read_csv(src, chunksize=CHUNK):
        total_in += len(chunk)
        for name in site_names:
            lo, hi, la, ha = boxes[name]
            m = (chunk["longitude"].between(lo, hi) &
                 chunk["latitude"].between(la, ha))
            rows = chunk[m].copy()
            if len(rows):
                # kepler-friendly time formats: acq_time HH:MM, acq_datetime "YYYY-MM-DD HH:MM:SS"
                t = pd.to_numeric(rows["acq_time"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(4)
                rows["acq_time"] = t.str[:2] + ":" + t.str[2:]
                rows["acq_datetime"] = rows["acq_datetime"].astype(str).str.replace("T", " ", n=1)
                rows.to_csv(outs[name], mode="a", index=False, header=first[name])
                first[name] = False
                kept[name] += len(rows)
    print(f"\nScanned {total_in:,} rows from {src.relative_to(ROOT)}")
    for name in site_names:
        print(f"  {name:18s} -> {kept[name]:,} rows  ({outs[name].name})")
