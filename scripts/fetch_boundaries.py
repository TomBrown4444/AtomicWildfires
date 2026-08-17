"""Download the site boundary polygons from OpenStreetMap.

Every boundary file in data/boundaries/ can be regenerated with this script.
Sources are OpenStreetMap features, fetched through two public APIs:

  - Overpass API (https://overpass-api.de) for plain ways (closed outlines)
  - Nominatim (https://nominatim.openstreetmap.org) for the Chernobyl
    Exclusion Zone, which is a multi-member relation

OpenStreetMap data is (c) OpenStreetMap contributors, licensed ODbL:
https://www.openstreetmap.org/copyright

Usage:
    uv run scripts/fetch_boundaries.py
"""
import json
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "boundaries"
HEADERS = {"User-Agent": "AtomicWildfires/1.0 (journalism research)"}
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
NOMINATIM_LOOKUP = "https://nominatim.openstreetmap.org/lookup"

# output name -> OSM way ids (each way is one closed polygon)
WAY_SITES = {
    # East Ural Nature Reserve, the closed zone on the Kyshtym fallout trace
    "east_ural_reserve": [256825533],
    # Mayak Production Association site, Ozyorsk
    "mayak_pa": [109744083],
    # Mining and Chemical Combine, Zheleznogorsk
    "mcc_zheleznogorsk": [197752192],
    # Siberian Chemical Combine plants, Seversk: isotope separation plant,
    # repair-mechanical plant, sublimate plant, chemical-metallurgical plant,
    # radiochemical plant, special storage site
    "scc_seversk": [19792255, 23597948, 23597957, 23597969, 220753186, 220753189],
}

# Chernobyl NPP Exclusion Zone (OSM relation)
CHERNOBYL_RELATION = 3311547


def overpass_query(q):
    # public Overpass servers rate-limit and time out under load;
    # retry with backoff, alternating between servers
    last = None
    for attempt, wait in enumerate((0, 15, 45, 90)):
        if wait:
            print(f"  server busy, retrying in {wait}s...")
            time.sleep(wait)
        server = OVERPASS_SERVERS[attempt % len(OVERPASS_SERVERS)]
        try:
            r = requests.post(server, data={"data": q}, headers=HEADERS, timeout=90)
            last = r
            if r.status_code == 200:
                return r
        except requests.RequestException as e:
            print(f"  {server}: {e}")
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("all Overpass servers failed")


def fetch_ways(name, way_ids):
    ids = "".join(f"way({w});" for w in way_ids)
    q = f"[out:json][timeout:60];({ids});out geom tags;"
    r = overpass_query(q)
    feats = []
    for el in r.json()["elements"]:
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        feats.append({"type": "Feature",
                      "properties": {**el.get("tags", {}), "osm": f"way/{el['id']}"},
                      "geometry": {"type": "Polygon", "coordinates": [coords]}})
    path = OUT / f"{name}.geojson"
    json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"))
    print(f"{name}: {len(feats)} polygon(s) -> {path.relative_to(ROOT)}")


def fetch_chernobyl():
    r = requests.get(NOMINATIM_LOOKUP,
                     params={"osm_ids": f"R{CHERNOBYL_RELATION}",
                             "polygon_geojson": 1, "format": "json"},
                     headers=HEADERS, timeout=90)
    r.raise_for_status()
    result = r.json()[0]
    feat = {"type": "Feature",
            "properties": {"name": "Chernobyl Exclusion Zone",
                           "osm": f"relation/{CHERNOBYL_RELATION}"},
            "geometry": result["geojson"]}
    path = OUT / "chernobyl_exclusion_zone.geojson"
    json.dump({"type": "FeatureCollection", "features": [feat]}, open(path, "w"))
    print(f"chernobyl_exclusion_zone: 1 polygon -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, way_ids in WAY_SITES.items():
        fetch_ways(name, way_ids)
        time.sleep(5)          # be polite to the public API
    fetch_chernobyl()
