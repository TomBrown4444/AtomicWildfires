"""Combine raw NASA FIRMS CSV exports into one chronologically sorted file.

FIRMS ships separate files per sensor (MODIS, VIIRS on three satellites) and
per processing level (archive vs near-real-time). This script merges them,
reconciles the differing column sets, and builds a proper timestamp column
(acq_datetime) from FIRMS's separate acq_date and acq_time fields.

Usage:
    uv run scripts/concat_firms.py data/raw/firms_russia  data/processed/combined_fire_russia.csv
    uv run scripts/concat_firms.py data/raw/firms_ukraine data/processed/combined_fire_ukraine.csv
"""
import sys
import pandas as pd
from pathlib import Path
import tempfile, shutil

CHUNK = 500_000


def main(in_dir, out_csv):
    in_dir, out_csv = Path(in_dir), Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(in_dir.glob("fire_*.csv"))
    if not files:
        sys.exit(f"No fire_*.csv files found in {in_dir}")
    print(f"Found {len(files)} files:")
    for f in files:
        print(f"  {f.name}")

    # union of columns (MODIS vs VIIRS schemas differ)
    all_cols = []
    for f in files:
        for c in pd.read_csv(f, nrows=0).columns:
            if c not in all_cols:
                all_cols.append(c)
    out_cols = all_cols + ["source", "product", "acq_datetime"]

    # --- Pass 1: stream rows into monthly buckets on disk ---
    tmp = Path(tempfile.mkdtemp(prefix="fire_buckets_", dir=out_csv.parent))
    seen_months = set()
    total = 0
    for f in files:
        product, sensor = f.stem.split("_")[1], f.stem.split("_")[2]
        n = 0
        for chunk in pd.read_csv(f, chunksize=CHUNK):
            chunk["source"] = sensor
            chunk["product"] = product
            t = (pd.to_numeric(chunk["acq_time"], errors="coerce")
                   .fillna(0).astype(int).astype(str).str.zfill(4))
            chunk["acq_datetime"] = (
                chunk["acq_date"].astype(str) + "T" + t.str[:2] + ":" + t.str[2:] + ":00"
            )
            chunk = chunk.reindex(columns=out_cols)
            month = chunk["acq_date"].astype(str).str.slice(0, 7)   # YYYY-MM
            for m, grp in chunk.groupby(month):
                grp.to_csv(tmp / f"{m}.csv", mode="a", index=False,
                           header=(m not in seen_months))
                seen_months.add(m)
            n += len(chunk)
        total += n
        print(f"  {f.name}: {n:,} rows  (running total {total:,})")

    # --- Pass 2: sort each bucket, write out in chronological order ---
    if out_csv.exists():
        out_csv.unlink()
    first, min_date, max_date = True, None, None
    for bf in sorted(tmp.glob("*.csv")):          # filenames sort chronologically
        df = pd.read_csv(bf).sort_values("acq_datetime", kind="mergesort")
        df.to_csv(out_csv, mode="a", index=False, header=first)
        first = False
        cmin, cmax = df["acq_date"].min(), df["acq_date"].max()
        min_date = cmin if min_date is None else min(min_date, cmin)
        max_date = cmax if max_date is None else max(max_date, cmax)

    shutil.rmtree(tmp)
    print(f"\nSaved -> {out_csv}  ({total:,} rows, sorted by acq_datetime)")
    print(f"Date range: {min_date} to {max_date}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: concat_firms.py <input_dir_with_fire_csvs> <output_csv>")
    main(sys.argv[1], sys.argv[2])
