# AtomicWildfires

Twenty-five years of satellite fire detections around four nuclear sites in Russia and Ukraine, prepared for animated mapping in [kepler.gl](https://kepler.gl/).

The question behind the project: how often does wildfire come close Soviet and Russian nuclear complexes? Fires have been measured repeatedly around Chernobyl, most recently during the April 2020 fires inside the Exclusion Zone (see [Why fires matter here](#why-fires-matter-at-these-sites)). But more radioactive sites exist within Russia which have not been thoroughly investigated. This repo tracks fires approaching those areas.

The repository contains the raw satellite data, the boundary outlines of each site, and maps fire detections to each location.

## The sites

| Site | What it is | Centre of the clip | Fire detections (2000–2026) |
|---|---|---|---|
| Chernobyl Exclusion Zone, Ukraine | The 2,600 km² area evacuated after the 1986 reactor explosion. Heavily contaminated forest and abandoned farmland | 51.31 N, 29.91 E | 113,046 |
| Mayak / Ozyorsk, Russia | The Mayak Production Association, Russia's main plutonium and spent-fuel reprocessing plant, site of the 1957 Kyshtym disaster | 55.69 N, 60.76 E | 98,578 |
| East Ural Nature Reserve, Russia | The closed reserve created in 1966 on the most contaminated part of the Kyshtym fallout trace, just north of Mayak | 55.85 N, 60.94 E | 105,221 |
| Seversk (Tomsk-7), Russia | The Siberian Chemical Combine, a closed city 15 km northwest of Tomsk: uranium enrichment, plutonium production reactors, reprocessing | 56.64 N, 84.88 E | 31,921 |
| Zheleznogorsk (Krasnoyarsk-26), Russia | The Mining and Chemical Combine on the Yenisei river: underground plutonium reactors, spent-fuel storage, reprocessing | 56.35 N, 93.65 E | 47,671 |

## What is in this repository

```
AtomicWildfires/
├── README.md                      this file
├── pyproject.toml, uv.lock        Python project files, managed with uv
├── scripts/
│   ├── concat_firms.py            merge the raw FIRMS files, build timestamps
│   ├── clip_sites.py              cut the detections to a box around each site
│   ├── cluster_events.py          group detections into fire events (DBSCAN)
│   ├── fetch_boundaries.py        re-download the site outlines from OpenStreetMap
│   └── legacy/                    earlier one-off scripts, kept for the record
├── data/
│   ├── raw/                       FIRMS downloads as received (kept out of git)
│   │   ├── firms_russia/          all of Russia, Nov 2000 – Jun 2026
│   │   └── firms_ukraine/         all of Ukraine, Nov 2000 – Aug 2026
│   ├── processed/                 merged, timestamped tables (kept out of git)
│   │   ├── combined_fire_russia.csv    36,466,438 detections
│   │   └── combined_fire_ukraine.csv    2,821,200 detections
│   ├── boundaries/                site outlines as GeoJSON, from OpenStreetMap
│   └── clips/                     the working data, one set of files per site:
│       ├── fires_near_<site>.csv           detections inside the site's box
│       ├── fires_near_<site>_events.csv    the same rows plus an event_id column
│       └── events_summary.csv              one row per fire event, all sites
└── reference/
    ├── papers/                    academic papers on Mayak, Kyshtym and the EURT (PDF)
    ├── articles/                  press coverage and NGO reporting (PDF)
    └── mayak_snf_inventory.csv.rtf
```

## Data sources

### Fire detections: NASA FIRMS

All fire data come from NASA's [Fire Information for Resource Management System (FIRMS)](https://firms.modaps.eosdis.nasa.gov/), which distributes "active fire" detections from two instrument families:

- **MODIS** on the Terra and Aqua satellites, from November 2000, 1 km pixels (Collection 6.1; Giglio, Schroeder and Justice 2016, ref. 1)
- **VIIRS** on the Suomi NPP, NOAA-20 and NOAA-21 satellites, from 2012, sharper 375 m pixels (Schroeder et al. 2014, ref. 2)

Each row in the data is one satellite pixel that was flagged as burning during one overpass: a time, a location, a fire radiative power (FRP, in megawatts), and a confidence value. A single wildfire produces anywhere from a handful to thousands of these rows.

Two country archives were ordered through the [FIRMS archive download tool](https://firms.modaps.eosdis.nasa.gov/download/):

- **Russia**, request IDs 767687–767690, downloaded 28 June 2026, covering 1 November 2000 to 28 June 2026
- **Ukraine**, request IDs 787742–787746, downloaded 17 August 2026, covering 1 November 2000 to 17 August 2026

Both archives are country-clipped: the Russia files contain no detections inside Ukraine, which is why the Chernobyl clip is built from its own Ukraine download. The most recent weeks in each archive come from FIRMS's near-real-time stream.

### Site boundaries: OpenStreetMap

The outlines in `data/boundaries/` were extracted from OpenStreetMap on 17 August 2026, through the public [Overpass](https://overpass-api.de) and [Nominatim](https://nominatim.openstreetmap.org) APIs. `scripts/fetch_boundaries.py` re-downloads all of them, and every file records its source feature in an `osm` property. The exact OpenStreetMap features used:

| File | OpenStreetMap feature(s) |
|---|---|
| `chernobyl_exclusion_zone.geojson` | [relation 3311547](https://www.openstreetmap.org/relation/3311547) — "Зона відчуження Чорнобильської АЕС" |
| `east_ural_reserve.geojson` | [way 256825533](https://www.openstreetmap.org/way/256825533) — East Ural Nature Reserve |
| `mayak_pa.geojson` | [way 109744083](https://www.openstreetmap.org/way/109744083) — Mayak Production Association site |
| `mcc_zheleznogorsk.geojson` | [way 197752192](https://www.openstreetmap.org/way/197752192) — Mining and Chemical Combine site |
| `scc_seversk.geojson` | Six plant sites of the Siberian Chemical Combine: [19792255](https://www.openstreetmap.org/way/19792255) (isotope separation), [23597948](https://www.openstreetmap.org/way/23597948) (repair-mechanical), [23597957](https://www.openstreetmap.org/way/23597957) (sublimate), [23597969](https://www.openstreetmap.org/way/23597969) (chemical-metallurgical), [220753186](https://www.openstreetmap.org/way/220753186) (radiochemical), [220753189](https://www.openstreetmap.org/way/220753189) (special storage) |

OpenStreetMap data is © OpenStreetMap contributors and licensed under the [Open Database License](https://www.openstreetmap.org/copyright). No official shapefiles exist for most of these facilities — they are closed sites in closed cities — so community-mapped outlines are the most practical option.

## How the data was built

Before running the script, you have to download data for all of Russia from NASA FIRMS, ticking the archive box: https://firms.modaps.eosdis.nasa.gov/

With [uv](https://docs.astral.sh/uv/) installed, `uv sync` sets up the environment and the whole chain reproduces from the raw files:

```bash
uv sync
uv run scripts/fetch_boundaries.py
uv run scripts/concat_firms.py data/raw/firms_russia  data/processed/combined_fire_russia.csv
uv run scripts/concat_firms.py data/raw/firms_ukraine data/processed/combined_fire_ukraine.csv
uv run scripts/clip_sites.py
uv run scripts/cluster_events.py
```

**Step 1 — merge (`concat_firms.py`).** FIRMS ships separate files per sensor and per processing level. The script merges them, reconciles the differing column layouts, and combines FIRMS's separate date and time fields into one `acq_datetime` timestamp. Rows are written out in chronological order.

**Step 2 — clip (`clip_sites.py`).** Each site's detections are cut out of the country table with a rectangular box:

- For the two areas whose outline is itself the point (the Chernobyl Exclusion Zone, the East Ural reserve), the box is the outline's bounding rectangle plus 0.8 degrees on every side.
- For the three production plants, whose fenced sites are tiny compared to the landscape, the box is a fixed 1.87° × 1.84° rectangle centred on the plant — the same footprint as the East Ural clip, roughly 115–120 km east–west by 205 km north–south at these latitudes.

The exact boxes:

| Clip | Longitude | Latitude |
|---|---|---|
| chernobyl | 28.4675 – 31.3613 | 50.2834 – 52.3316 |
| east_ural_reserve | 60.0080 – 61.8735 | 54.9355 – 56.7739 |
| mayak_ozyorsk | 59.8242 – 61.6897 | 54.7757 – 56.6141 |
| scc_seversk | 83.9492 – 85.8147 | 55.7233 – 57.5617 |
| mcc_zheleznogorsk | 92.7141 – 94.5797 | 55.4343 – 57.2727 |

**Step 3 — group detections into fire events (`cluster_events.py`).** Individual detections answer "was something burning in this pixel at this moment". To ask "how many fires were there, how big, how long", detections have to be grouped into events. This project uses DBSCAN, a standard clustering algorithm (Ester et al. 1996, ref. 3) that links detections which sit within 2 km and 3 days of one another and follows those links transitively, so a spreading fire front stays one event. Groups smaller than 5 detections are set aside as noise (`event_id` = −1) rather than counted as events.

Grouping satellite fire pixels into events with a space–time neighbourhood rule is the established way to build fire histories from this kind of data. The main global fire-event datasets are all built on some version of it: the Global Fire Atlas (Andela et al. 2019, ref. 5), GlobFire (Artés et al. 2019, ref. 6) and FIRED (Balch et al. 2020, ref. 7) cluster daily burned-area pixels with space–time windows of similar size, and NASA JPL's California fire-tracking system (Chen et al. 2022, ref. 8) clusters the same VIIRS active-fire detections used here by spatial proximity at each time step. The space–time extension of DBSCAN itself is described in Birant and Kut 2007 (ref. 4).

**Step 4 — map (kepler.gl).** The clip files are formatted so kepler.gl recognises the timestamps (`acq_datetime` as `YYYY-MM-DD HH:MM:SS`). To animate: load a `fires_near_<site>_events.csv` and the matching boundary GeoJSON at [kepler.gl/demo](https://kepler.gl/demo), add a filter on `acq_datetime`, and a playback timeline appears. Colour points by `frp` (fire intensity) or `event_id` (one colour per fire). The animation can be screen-recorded or exported to make a GIF.

## Caveats

**A detection is a hot pixel, not a confirmed wildfire.** The satellites flag anything hot enough: wildfires, but also agricultural burning, gas flares, smokestacks, and smouldering waste. Around industrial cities this matters. The most extreme example in this dataset: the longest "events" in the Mayak/East Ural files — one runs 200 days at a fixed spot near 55.28 N, 61.45 E — are the Chelyabinsk city landfill smouldering through the warm season, not a spreading forest fire. Fixed-location, months-long events in `events_summary.csv` should be treated as industrial or waste heat unless verified otherwise.

**Detection counts are not comparable across the full 25 years.** Until 2012 only the two 1 km MODIS instruments were watching; the 375 m VIIRS instruments joined in 2012 (Suomi NPP), 2018 (NOAA-20) and 2023 (NOAA-21). Later years see more, smaller fires simply because more and sharper eyes are looking. Compare like with like: MODIS-only counts across years, or VIIRS counts from 2012 onwards.

**Gaps do not mean no fire.** Cloud, heavy smoke and the timing of satellite overpasses all hide fires. Each satellite passes a given point roughly twice a day.

**Positions are approximate.** A detection is placed at the centre of its pixel; the fire can be anywhere inside it (up to ~1 km for MODIS, ~375 m for VIIRS).

**Confidence fields differ by sensor.** MODIS reports 0–100; VIIRS reports `l`/`n`/`h` (low, nominal, high). Filtering out low-confidence detections removes many false alarms and some real fires.

**The fire location does not suggest that radioactive material was necessarily released.** A detection in `fires_near_mayak_ozyorsk.csv` means a fire within roughly 60 km of the plant, not a fire on the plant site. Cross-check any specific claims of radioactive release.

**Recent months are near-real-time data.** FIRMS may revise or remove detections when the science-quality processing catches up.

## Why fires matter at these sites

Wildfires in radioactively contaminated land re-mobilise fallout. The peer-reviewed record on the Chernobyl zone is direct on this point: the 2015 fires measurably redistributed caesium-137 (ref. 9), and the April 2020 fires — the largest in the zone's history, clearly visible in this dataset — produced radionuclide plumes detected by monitoring stations across Europe (refs. 10, 11), at concentrations far below health thresholds but unmistakable in origin. A 2021 review treats fire in the zone as a recurring multi-hazard threat rather than a one-off (ref. 12).

The Urals sites carry the same logic. Mayak's surroundings hold the fallout of the 1957 Kyshtym explosion (the East Urals Radioactive Trace), decades of authorised and unauthorised discharges into the Techa river system, and the dust-prone bed of Lake Karachay. The East Ural Nature Reserve exists because that land is too contaminated to use; when it burns, the same resuspension question applies. Background on all of this is collected in `reference/papers/` and `reference/articles/` (Bellona's Mayak reporting, the IPFM blog's reprocessing coverage, and reporting on the 2010 fires that came close to the plant, among others).

## References

Method papers — satellite fire products:

1. Giglio, L., Schroeder, W., Justice, C.O. (2016). The Collection 6 MODIS active fire detection algorithm and fire products. *Remote Sensing of Environment*. [doi:10.1016/j.rse.2016.02.054](https://doi.org/10.1016/j.rse.2016.02.054)
2. Schroeder, W., Oliva, P., Giglio, L., Csiszar, I.A. (2014). The New VIIRS 375 m active fire detection data product: Algorithm description and initial assessment. *Remote Sensing of Environment*. [doi:10.1016/j.rse.2013.12.008](https://doi.org/10.1016/j.rse.2013.12.008)

Method papers — clustering detections into fire events:

3. Ester, M., Kriegel, H.-P., Sander, J., Xu, X. (1996). A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases with Noise. *Proceedings of KDD-96*. [PDF](https://cdn.aaai.org/KDD/1996/KDD96-037.pdf)
4. Birant, D., Kut, A. (2007). ST-DBSCAN: An algorithm for clustering spatial–temporal data. *Data & Knowledge Engineering*. [doi:10.1016/j.datak.2006.01.013](https://doi.org/10.1016/j.datak.2006.01.013)
5. Andela, N., et al. (2019). The Global Fire Atlas of individual fire size, duration, speed and direction. *Earth System Science Data*. [doi:10.5194/essd-11-529-2019](https://doi.org/10.5194/essd-11-529-2019)
6. Artés, T., et al. (2019). A global wildfire dataset for the analysis of fire regimes and fire behaviour. *Scientific Data*. [doi:10.1038/s41597-019-0312-2](https://doi.org/10.1038/s41597-019-0312-2)
7. Balch, J.K., et al. (2020). FIRED (Fire Events Delineation): An Open, Flexible Algorithm and Database of US Fire Events Derived from the MODIS Burned Area Product (2001–2019). *Remote Sensing*. [doi:10.3390/rs12213498](https://doi.org/10.3390/rs12213498)
8. Chen, Y., Hantson, S., Andela, N., et al. (2022). California wildfire spread derived using VIIRS satellite observations and an object-based tracking system. *Scientific Data*. [doi:10.1038/s41597-022-01343-0](https://www.nature.com/articles/s41597-022-01343-0)

Fires and radioactivity at these sites:

9. Evangeliou, N., Zibtsev, S., Myroniuk, V., et al. (2016). Resuspension and atmospheric transport of radionuclides due to wildfires near the Chernobyl Nuclear Power Plant in 2015: An impact assessment. *Scientific Reports*. [doi:10.1038/srep26062](https://www.nature.com/articles/srep26062)
10. Evangeliou, N., Eckhardt, S. (2020). Uncovering transport, deposition and impact of radionuclides released after the early spring 2020 wildfires in the Chernobyl Exclusion Zone. *Scientific Reports*. [doi:10.1038/s41598-020-67620-3](https://www.nature.com/articles/s41598-020-67620-3)
11. Masson, O., et al. (2021). Europe-Wide Atmospheric Radionuclide Dispersion by Unprecedented Wildfires in the Chernobyl Exclusion Zone, April 2020. *Environmental Science & Technology*. [doi:10.1021/acs.est.1c03314](https://pubs.acs.org/doi/10.1021/acs.est.1c03314)
12. The Environmental Effects of the April 2020 Wildfires and the Cs-137 Re-Suspension in the Chernobyl Exclusion Zone: A Multi-Hazard Threat (2021). *Atmosphere*. [mdpi.com/2073-4433/12/4/467](https://www.mdpi.com/2073-4433/12/4/467)

Additional monitoring study: [The assessment of the April 2020 Chernobyl wildfires and their impact on Cs-137 levels in Belgium and The Netherlands](https://www.sciencedirect.com/science/article/pii/S0265931X21001600), *Journal of Environmental Radioactivity* (2021).

## Licences and credits

- Fire data: NASA FIRMS / LANCE, NASA Earth Science Data and Information System. Free to use; acknowledge NASA FIRMS ([earthdata.nasa.gov/firms](https://www.earthdata.nasa.gov/firms)).
- Boundaries: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, ODbL.
- Everything in `reference/` belongs to its original publishers and is stored here for research convenience only.
