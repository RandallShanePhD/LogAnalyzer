# LogAnalyzer

IGC flight log file analyzer for paragliding and soaring sports. Analyzes thermal soaring performance, glide efficiency, and generates visualization files for Google Earth.

## Quick Start

1. Place IGC files in the `Logs` directory
2. Run: `python3 analyzer.py` or `./analyzer.py`
3. Select a file from the menu
4. Results print to terminal; KMZ files save to `KMZs` directory

## Menu Options

| Key | Action |
|-----|--------|
| `D` | Display blocks longer than 90 seconds |
| `A` | Display ALL flight blocks |
| `C` | Display climb blocks only |
| `S` | Display sink blocks only |
| `g` | Display glide blocks only |
| `G` | **Glide Performance Analysis** - best glide ratio, MacReady speed-to-fly |
| `T` | **Thermal Analysis** - circling detection, thermal statistics |
| `K` | **Export Enhanced KMZ** - flight visualization for Google Earth |
| `s` | Settings menu |
| `r` | Rescan Logs directory |
| `x` | Exit |

## Analysis Methodology

### Data Processing Pipeline

1. **IGC Parsing**: Extracts GPS coordinates, timestamps, pressure/GPS altitude from B-records
2. **Flight Phase Detection**: Classifies each reading as Climb, Glide, or Sink based on altitude rate
3. **Block Consolidation**: Groups consecutive readings of the same type into flight phases
4. **Statistical Analysis**: Computes grades and metrics for each phase type

### Phase Classification

| Phase | Detection Criteria |
|-------|-------------------|
| **Climb** | Average altitude rate > 0.5 m/s |
| **Sink** | Average altitude rate < -2.5 m/s |
| **Glide** | Everything in between |

### Climb Efficiency Calculation

The efficiency grade (0-100%) uses a weighted composite of four factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| **Net Efficiency** | 35% | Actual altitude gain vs. expected gain based on global average climb rate |
| **Consistency Score** | 25% | Lower variance in climb rates scores higher (penalizes bobbing) |
| **Sustained Ratio** | 25% | Percentage of readings maintaining ≥50% of average climb rate |
| **Positive Steps** | 15% | Percentage of readings showing any altitude gain |

This approach rewards:
- Smooth, consistent climbs with minimal altitude loss between readings
- Sustained lift rather than intermittent bobbing
- Optimal thermal centering

### Glide Analysis

- **L/D Ratio**: Distance traveled divided by altitude lost for each glide segment
- **Best Glide**: Highest L/D achieved and the altitude at which it was flown
- **Average Glide**: Mean L/D across all glide segments
- **Speed-to-Fly (MacReady)**: Optimal circling speed based on average climb and sink rates

### Thermal Analysis

Detects thermals by identifying circling behavior:
- Minimum 20 seconds duration
- Minimum 50 meters altitude gain
- Start-to-end distance < 500 meters (indicates circling)

**Thermal Statistics:**
- Count, average strength, max/min strength
- Duration statistics
- Altitude gain per thermal
- Centering score (based on climb rate consistency)

## Enhanced KMZ Output

Press `K` to generate an enhanced KML file for Google Earth with:

- **Color-coded flight path** by altitude quantile:
  - Green: Lower 25% (below 25th percentile)
  - Yellow: 25-50% (25th-50th percentile)
  - Orange: 50-75% (50th-75th percentile)
  - Red: Top 25% (above 75th percentile)
- **Takeoff marker** (green circle)
- **Landing marker** (red circle)
- **Thermal locations** (orange circles with strength/altitude labels)
- **Legend** explaining color coding

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Averaging Factor | 10 | Seconds used to average lift/sink rate |
| Sink Threshold | 2.5 m/s | Minimum descent rate to classify as sink |
| KMZ Speed Units | kmh | Units for speed in KMZ visualization |

Access settings menu by pressing `s` from the main menu.

## File Structure

```
LogAnalyzer/
├── analyzer.py          # Main analysis engine
├── kmz_creator.py       # Enhanced KMZ generation
├── igc2kml.py           # Alternative KML library
├── prototype.py          # Experimental code
├── Logs/                # Place IGC files here
│   └── *.igc
└── KMZs/                # Generated visualization files
    └── *.kmz
```

## IGC File Format

The analyzer parses standard IGC files from variometer devices. Supported headers include:
- `HFPLT` / `HFPLTPILOTINCHARGE` - Pilot name
- `HFFTYFRTYPE` - Device type
- `HFGPS` - GPS info
- `HFGTYGLIDERTYPE` - Glider type
- `HFDTE` / `HFDTEDATE` - Flight date
- `B` - GPS data records (lat, lon, altitude)

## Credits

- IGC2KML library: https://github.com/MScherbela/igc2kml
- Created by Randall Shane PhD
- Wander Expeditions LLC
