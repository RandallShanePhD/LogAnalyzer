# IGC Flight Log Analyzer — Analysis Pipeline

## Overview

`Bot/decode.py` is the core analysis engine that parses IGC (International Gliding Commission) flight log files, performs a multi-stage analysis of flight performance (climbs, glides, sinks, thermals), and returns a structured results dictionary. The results drive both CLI display (`Bot/display.py`) and KML/KMZ visualization (`Bot/kmzs.py`).

---

## Pipeline Stages

### 1. IGC File Parsing — `load_igc()`

`load_igc()` reads a raw IGC file line-by-line and extracts:

**Header Records (H-Records):**
- `HFPLTPILOTINCHARGE:` / `HFPLT` → Pilot name
- `HFFTYFRTYPE:` / `HFGPS:` → Vario model
- `HFGTYGLIDERTYPE:` → Glider type
- `HFDTEDATE:` / `HFDTE` → Flight date (DDMMYY)

**B-Records (position fixes):** Each B-record contains: time (HHMMSS), latitude (DDMMmmm), N/S hemisphere, longitude (DDDMMmmm), E/W hemisphere, pressure altitude, and GPS altitude.

**Coordinate Conversion (line 273–282):**
```
lat = int(DD) + float(MMmmm) / 60000
lon = int(DDD) + float(MMmmm) / 60000
```
IGC stores coordinates as DDMMmmm (degrees, minutes + thousandths). The conversion divides the fractional minutes by 60000 (the number of thousandths of a minute in a degree) to get decimal degrees. N/S and E/W indicators apply the appropriate sign.

**Per-Record Processing:**
- **Distance** (`haversine`): Great-circle distance from the previous fix. Distances < 0.3 km accumulate toward `total_distance_km`; distances > 25 km are treated as GPS errors and discarded.
- **Bearing**: Initial heading from the first valid coordinate pair becomes `takeoff_heading`.
- **Altitude**: Pressure altitude (`line[25:30]`) is primary; GPS altitude (`line[30:35]`) is fallback if pressure altitude is 0.
- **Flight Area**: Maximum great-circle distance from takeoff, tracked throughout the flight.
- **Lift/Sink Averaging**: Altitude readings accumulate over an `averaging_factor` window (default 10 records). Every `n`th record, `calc_lift_sink()` computes the mean climb/sink rate, filtering outliers beyond ±2σ.
- **Climb/Glide Counters**: Simple comparison of consecutive altitudes increments `climb_readings` or `glide_readings`.
- **Analysis Data**: Each B-record is appended to `analysis_data` as a tuple `(datetime_int, lat, lon, alt_m, heading, distance)`.

**Landing & Duration:**
- `landing_dt` is derived from the last B-record's timestamp.
- Duration = `landing_dt - takeoff_dt` (handles midnight-crossing with +24h adjustment).

**Return Value:** A rich dictionary containing all raw stats, plus the results of `flight_analyzer()`, `analyze_glide_performance()`, and `analyze_thermals()`.

---

### 2. Flight Segmentation — `flight_analyzer()`

This is the main analysis function. It takes the `analysis_data` list and processes it in four steps:

**Step 1 — Chunking (line 446–451):**
The `analysis_data` list (one entry per B-record) is split into fixed-size chunks of `averaging_factor` (10) records each. Each chunk represents ~10 seconds of flight data.

**Step 2 — Classification (line 454–464):**
Each chunk is classified based on its mean vertical speed (`calc_lift_sink()`):
- **Climb ("C")**: mean lift/sink > `climb_ascend_threshold` (+0.5 m/s)
- **Sink ("S")**: mean lift/sink < `sink_descend_threshold` (-2.5 m/s)
- **Glide ("G")**: anything between those thresholds

**Step 3 — Consolidation (line 469–485):**
Adjacent chunks with the same classification are merged into contiguous **blocks**. This loop iterates through `chunk_cat`, merging same-type chunks. The final residual chunk (if any) is appended after the loop. Each block stores its averaged lift/sink value alongside the raw B-record data.

**Step 4 — Grade Calculation (line 487–568):**
- **Global Average Climb**: All climb rates across all climb blocks are aggregated, outliers (±2σ) are filtered, and the mean is computed as `global_avg_climb`.
- **Climb Grades**: For each climb block, `calculate_climb_efficiency()` returns a 0–1 score, multiplied by 100 for the final percentage.
- **Glide Grades**: For each glide block, L/D = `(total_distance_m / altitude_loss)`. The overall `glide_grade` is the mean L/D across all glide blocks.
- **Sink Grades**: For each sink block, the absolute sink rate (m/s) is recorded. The overall `sink_grade` is the mean sink rate.

**Step 5 — Detail Blocks (line 530–552):**
A `details` list is built with one dictionary per block, containing: `number`, `tyype` (Climb/Glide/Sink), `time_secs`, `altitude_start_m`, `altitude_end_m`, `avg_lift_sink_ms`, `l_over_d` (glide blocks only), `loc_start`, `loc_end`, and `total_distance_m`.

**Flight Type Detection (line 571–596):**
Uses `detect_circling()` to find circling blocks. If circling time > 10% of total flight time:
- **xc**: flight area diameter > 8 km
- **thermal**: flight area ≤ 8 km
- **soaring**: circling time ≤ 10% (also applies a separate efficiency formula based on climb/sink time ratios)

---

### 3. Efficiency Scoring — `calculate_climb_efficiency()`

Computes a composite 0–1 score for each climb block from four factors:

| Factor | Weight | Calculation |
|--------|--------|-------------|
| Net Efficiency | 35% | `net_gain / expected_gain` (capped at 1.0). Expected gain = number of readings × global average climb. |
| Consistency Score | 25% | `max(0, 1 - (rate_stdev / (global × 2)))`. Lower variance = higher score. |
| Sustained Ratio | 25% | Fraction of climb readings ≥ 50% of global average climb. |
| Positive Steps | 15% | Fraction of readings showing any altitude gain. |

The weighted sum is capped at 1.0 and returned as a float.

---

### 4. Thermal Detection — `detect_circling()`, `analyze_thermals()`, `calculate_thermal_stats()`

**`detect_circling()`** filters climb blocks for true thermalling:
- Block type must be "Climb"
- Duration ≥ 20 seconds
- Altitude gain ≥ 50 meters
- Horizontal drift ≤ 1000 meters (great-circle distance between start/end)

**`analyze_thermals()`** — wrapper that calls `detect_circling()` followed by `calculate_thermal_stats()`.

**`calculate_thermal_stats()`** — aggregates:
- Count, average/max/min strength (m/s)
- Average/total duration, total thermal time
- % of flight in thermals
- Average/total altitude gain
- Locations and strength values for each thermal

---

### 5. Glide Performance — `analyze_glide_performance()`

Takes all "Glide" detail blocks and computes:
- **Best glide ratio** (max L/D) and its altitude/sink rate
- **Average glide ratio** and average altitude
- **Overall glide ratio** (total distance / total altitude loss across all glides)
- **Average sink rate** (m/s)
- **MacReady setting**: average climb rate across all thermal blocks (recommended speed-to-fly setting)
- **Cruise efficiency**: `overall_ld / best_ld × 100` (%)
- **Glide polar**: sorted list of (L/D, altitude, sink_rate) for each glide segment

---

### 6. KMZ Data Generation — `Bot/kmzs.py`

`create_enhanced_kmz()` takes the `kmz_data` dict from `load_igc()` and produces a KML file:

- **Altitude Quantiles**: All altitudes are sorted and split at 25th/50th/75th percentiles for color coding.
- **Color Coding** by block type:
  - Climb blocks: green → yellow → orange → red (ascending altitude quartiles)
  - Sink blocks: red
  - Glide blocks: fallback to climb color scheme
- **Thermal Markers**: `detect_thermals()` (same criteria as `detect_circling()` + duration ≥ 20s) places orange circle icons at thermal locations with strength labels.
- **Takeoff/Landing Markers**: Green/red paddle icons at the start/end GPS coordinates.
- **Segments**: The full GPS track is split into same-color segments, each rendered as a `<LineString>` with `<altitudeMode>absolute</altitudeMode>` for true 3D terrain display.

---

## Supporting Modules

### `Bot/base.py`
- **`haversine(loc1, loc2)`**: Great-circle distance in km between two (lat, lon) tuples. Earth radius = 6372.8 km.
- **`bearing(loc1, loc2)`**: Initial bearing in degrees (0–360).
- **`convert_hm_to_dt(raw_date, raw_time)`**: Parses DDMMYY + HHMMSS to a datetime object.
- **`settings` dictionary**: `averaging_factor` (10), `climb_ascend_threshold` (0.5 m/s), `sink_descend_threshold` (2.5 m/s), `kmz_speed_units` ("kmh").
- **Unit conversions**: meters↔feet, km↔miles, m/s↔ft/min.

### `Bot/display.py`
- **`display_summary_stats()`**: Prints formatted flight summary, overview (climbs/glides/sinks counts, rates, ratios), efficiency grade with natural-language interpretation, detailed block inspection (blocks > 90s), glide performance analysis, and thermal analysis.
- **`efficiency_grade_lookup()`**: Maps score to human-readable critique based on flight type.
- **`display_glide_analysis()`**: Best/average glide, MacReady setting, cruise efficiency, top 5 glides, polar curve table.
- **`display_thermal_analysis()`**: Per-thermal breakdown (duration, strength, altitude gain, location).

---

## Output Data Structure

`load_igc()` returns a dictionary with the following top-level keys:

| Key | Description |
|-----|-------------|
| `filename` | Input IGC file path |
| `pilot`, `vario`, `glider` | Header metadata |
| `flight_date` | Takeoff datetime |
| `max_alt` | Maximum altitude (m) |
| `max_lift`, `max_sink` | Peak lift/sink rates (m/s) |
| `takeoff_datetime`, `landing_datetime` | Formatted timestamps |
| `takeoff_alt`, `landing_alt` | Altitudes (m) |
| `takeoff_gps`, `landing_gps` | (lat, lon) tuples |
| `takeoff_heading`, `landing_heading` | Degrees |
| `total_distance` | km |
| `takeoff_to_land_dist` | Straight-line distance (km) |
| `flight_area_diameter` | km |
| `duration` | Seconds |
| `flight_type` | "soaring" / "thermal" / "xc" |
| `climbs_num`, `glides_num`, `sinks_num` | Block counts |
| `climb_grade` | Efficiency % (0–100) |
| `glide_grade` | Mean L/D ratio |
| `sink_grade` | Mean sink rate (m/s) |
| `max_sustained_climb` | Best climb block avg (m/s) |
| `µ_sustained_climb`, `µ_sustained_glide` | Mean climb/glide rates |
| `details` | List of per-block analysis dicts |
| `glide_perf` | Glide analysis sub-dict |
| `thermals` | Thermal analysis sub-dict (None if soaring) |
| `model_data` | Sub-dict for weather model integration |
| `kmz_data` | Sub-dict for KMZ generation |
| `lon_lat_alt_list` | Full raw track (lon, lat, alt) tuples |
