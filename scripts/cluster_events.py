"""Group individual satellite fire detections into fire events with DBSCAN.

A FIRMS detection is one satellite pixel flagged as burning during one
overpass. A single wildfire therefore shows up as dozens to thousands of
detections spread over hours or days. This script groups detections into
events: two detections belong to the same event when they are within EPS_KM
kilometres and EPS_DAYS days of each other, chained transitively through
their neighbours (density-based clustering).

Method: DBSCAN (Ester et al. 1996) on three coordinates - east-west km,
north-south km, and time rescaled so that EPS_DAYS maps onto EPS_KM. This
follows the spatiotemporal-clustering approach used to build global fire
event datasets from the same satellite products; see the References section
of README.md (Birant & Kut 2007; Andela et al. 2019; Artes et al. 2019;
Balch et al. 2020; Chen et al. 2022).

Parameters (defaults chosen to sit inside the range used by those datasets):
  EPS_KM      = 2.0   neighbour distance in km (MODIS pixels are 1 km,
                      VIIRS pixels 375 m; 2 km bridges adjacent pixels
                      without merging distant fires)
  EPS_DAYS    = 3.0   neighbour distance in time (global fire-event datasets
                      use 5-11 day windows on daily burned-area grids; active
                      fire detections arrive several times a day, so a
                      shorter window holds events together without chaining
                      separate burns)
  MIN_SAMPLES = 5     smaller groups are labelled noise (event_id = -1)

Outputs, per input clip:
  data/clips/fires_near_<site>_events.csv   input rows + event_id column
  data/clips/events_summary.csv             one row per event, all sites

Usage:
    uv run scripts/cluster_events.py                 # all clips
    uv run scripts/cluster_events.py chernobyl       # one or more named sites
"""
import sys
import math
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import DBSCAN

EPS_KM = 2.0
EPS_DAYS = 3.0
MIN_SAMPLES = 5

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "data" / "clips"

SITES = ["chernobyl", "east_ural_reserve", "scc_seversk",
         "mcc_zheleznogorsk", "mayak_ozyorsk"]


def cluster(df):
    t = pd.to_datetime(df["acq_datetime"])
    days = (t - t.min()).dt.total_seconds() / 86400.0
    lat0 = math.radians(df["latitude"].mean())
    x = df["longitude"].to_numpy() * 111.320 * math.cos(lat0)
    y = df["latitude"].to_numpy() * 110.574
    z = days.to_numpy() * (EPS_KM / EPS_DAYS)
    coords = np.column_stack([x, y, z])
    return DBSCAN(eps=EPS_KM, min_samples=MIN_SAMPLES).fit_predict(coords)


def summarise(df, site):
    ev = df[df["event_id"] >= 0]
    g = ev.groupby("event_id")
    t = g["acq_datetime"].agg(["min", "max"])
    out = pd.DataFrame({
        "site": site,
        "event_id": t.index,
        "start": t["min"],
        "end": t["max"],
        "duration_days": ((pd.to_datetime(t["max"]) - pd.to_datetime(t["min"]))
                          .dt.total_seconds() / 86400.0).round(2),
        "detections": g.size(),
        "total_frp_mw": g["frp"].sum().round(1),
        "centroid_lat": g["latitude"].mean().round(4),
        "centroid_lon": g["longitude"].mean().round(4),
    })
    return out.reset_index(drop=True)


if __name__ == "__main__":
    selected = sys.argv[1:] or SITES
    unknown = [s for s in selected if s not in SITES]
    if unknown:
        sys.exit(f"Unknown site(s) {unknown}; choose from {SITES}")

    summaries = []
    for site in selected:
        src = CLIPS / f"fires_near_{site}.csv"
        df = pd.read_csv(src)
        df["event_id"] = cluster(df)
        n_events = df.loc[df["event_id"] >= 0, "event_id"].nunique()
        n_noise = int((df["event_id"] < 0).sum())
        out = CLIPS / f"fires_near_{site}_events.csv"
        df.to_csv(out, index=False)
        summaries.append(summarise(df, site))
        print(f"{site:18s} {len(df):,} detections -> {n_events:,} events "
              f"({n_noise:,} noise points)  -> {out.name}")

    # merge with any previously written summaries for sites not in this run
    summary_path = CLIPS / "events_summary.csv"
    all_sum = pd.concat(summaries, ignore_index=True)
    if summary_path.exists() and set(selected) != set(SITES):
        prev = pd.read_csv(summary_path)
        all_sum = pd.concat([prev[~prev["site"].isin(selected)], all_sum],
                            ignore_index=True)
    all_sum = all_sum.sort_values("detections", ascending=False)
    all_sum.to_csv(summary_path, index=False)
    print(f"\nEvent table -> {summary_path.relative_to(ROOT)} "
          f"({len(all_sum):,} events)")
