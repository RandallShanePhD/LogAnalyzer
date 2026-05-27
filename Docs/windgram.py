import argparse
import datetime
import matplotlib.pyplot as plt
import numpy as np

import matplotlib.patches as patches
from siphon.catalog import TDSCatalog
from siphon.ncss import NCSS

# 1. Define location and model from command line arguments
MODELS = {
    'gfs': {
        'catalog': 'https://thredds.ucar.edu/thredds/catalog/grib/NCEP/GFS/Global_0p25deg/catalog.xml',
        'desc': 'GFS 0.25° Global',
        'vars': ('u-component_of_wind_isobaric', 'v-component_of_wind_isobaric',
                 'Temperature_isobaric', 'Relative_humidity_isobaric'),
    },
    'hrrr': {
        'catalog': 'https://thredds.ucar.edu/thredds/catalog/grib/NCEP/HRRR/CONUS_2p5km/catalog.xml',
        'desc': 'HRRR 2.5km CONUS',
        'vars': ('u-component_of_wind_isobaric', 'v-component_of_wind_isobaric', 'Temperature_isobaric'),
    },
    'nam': {
        'catalog': 'https://thredds.ucar.edu/thredds/catalog/grib/NCEP/NAM/CONUS_12km/catalog.xml',
        'desc': 'NAM 12km CONUS',
        'vars': ('u-component_of_wind_isobaric', 'v-component_of_wind_isobaric',
                 'Temperature_isobaric', 'Relative_humidity_isobaric'),
    },
}

parser = argparse.ArgumentParser(description='Generate a windgram for a given location.')
parser.add_argument('lat', type=float, help='Latitude')
parser.add_argument('lon', type=float, help='Longitude')
parser.add_argument('ground_ft', nargs='?', type=float, default=0, help='Ground elevation in feet')
parser.add_argument('--model', '-m', choices=list(MODELS.keys()), default='gfs',
                    help=f"Weather model ({', '.join(MODELS.keys())})")
args = parser.parse_args()

lat = args.lat
lon = args.lon
ground_ft = args.ground_ft
model_name = args.model
ground_m = ground_ft * 0.3048

start_time = datetime.datetime.utcnow()
end_time = start_time + datetime.timedelta(hours=18)

print(f"Model: {MODELS[model_name]['desc']}")
print(f"Fetching 18-hour forecast for Lat: {lat}, Lon: {lon}...")

# 2. Access dataset via Siphon
catalog_url = MODELS[model_name]['catalog']
catalog = TDSCatalog(catalog_url)
dataset_name = sorted(catalog.datasets.keys())[-1]
dataset = catalog.datasets[dataset_name]

ncss = NCSS(dataset.access_urls['NetcdfSubset'])
query = ncss.query()
query.lonlat_point(lon, lat).time_range(start_time, end_time)
query.variables(*MODELS[model_name]['vars'])
query.accept('netcdf4')

has_rh = 'Relative_humidity_isobaric' in MODELS[model_name]['vars']
if not has_rh:
    print("Note: this model lacks relative humidity — will use default 50% for cloud base")

data = ncss.get_data(query)

# 3. Data comes in profile/obs format (1D concatenated profiles)
nobs = np.asarray(data.variables['nobs'][:])
profile_time_raw = np.asarray(data.variables['profileTime'][:])

u_raw = np.asarray(data.variables['u-component_of_wind_isobaric'][:])
v_raw = np.asarray(data.variables['v-component_of_wind_isobaric'][:])
t_raw = np.asarray(data.variables['Temperature_isobaric'][:])  # Kelvin
p_raw = np.asarray(data.variables['altitude'][:])  # Pressure in Pa

# Parse time units to get base reference time
time_units = data.variables['profileTime'].units
base_time_str = time_units.split(" since ")[1]
base_time = datetime.datetime.strptime(base_time_str, "%Y-%m-%dT%H:%M:%SZ")

num_profiles = len(nobs)
num_levels = nobs[0]

# Reshape flat arrays into (profile, level)
u_2d = u_raw.reshape(num_profiles, num_levels)
v_2d = v_raw.reshape(num_profiles, num_levels)
t_2d = t_raw.reshape(num_profiles, num_levels)
rh_2d = np.full((num_profiles, num_levels), 50.0)  # default 50% RH
if has_rh:
    rh_raw = np.asarray(data.variables['Relative_humidity_isobaric'][:])
    rh_2d = rh_raw.reshape(num_profiles, num_levels)
p_2d = p_raw.reshape(num_profiles, num_levels)

# Pressure levels are same for all profiles; take first
p_vals = p_2d[0] / 100.0  # Convert Pa to hPa

# Convert m/s to mph
u_mph = u_2d * 2.23694
v_mph = v_2d * 2.23694
wind_speed = np.sqrt(u_mph ** 2 + v_mph ** 2)

# Convert Pressure levels (hPa) to approximate Altitude (m) using barometric formula
altitudes = 44330.0 * (1.0 - (p_vals / 1013.25) ** (1.0 / 5.255))

# Find the model level closest to ground elevation (before filtering)
full_altitudes = altitudes.copy()
surface_level_idx = np.argmin(np.abs(full_altitudes - ground_m)) if ground_m > 0 else 0

# Filter levels from ground to ~4000m
valid_idx = np.where((altitudes >= ground_m) & (altitudes <= 4200))[0]
altitudes = altitudes[valid_idx]
wind_speed = wind_speed[:, valid_idx]
u_mph = u_mph[:, valid_idx]
v_mph = v_mph[:, valid_idx]

# Build hour positions and labels from profile timestamps
# Build model hour positions from timestamps
model_hours = []
for pt in profile_time_raw:
    dt = base_time + datetime.timedelta(hours=float(pt))
    model_hours.append(dt.hour + dt.minute / 60.0)
model_hours = np.array(model_hours)

# Target columns: every hour 8 AM to 9 PM
target_hours = np.arange(8, 22)  # 8..21
time_idx = np.array([np.argmin(np.abs(model_hours - h)) for h in target_hours])
hour_positions = target_hours.tolist()

# Compute per-hour thermal ceiling (cloud base) from T and RH at ground level
ceiling_per_hour = []
for ti in range(num_profiles):
    t_sfc_k = t_2d[ti, surface_level_idx]
    rh_sfc = rh_2d[ti, surface_level_idx]
    t_sfc_c = t_sfc_k - 273.15
    rh_sfc = max(rh_sfc, 1.0)
    es = 6.112 * np.exp((17.67 * t_sfc_c) / (t_sfc_c + 243.5))
    e = (rh_sfc / 100.0) * es
    e_ratio = max(e / 6.112, 0.001)
    log_ratio = np.log(e_ratio)
    denom = 17.67 - log_ratio
    td = (243.5 * log_ratio) / denom if abs(denom) > 0.01 else -20
    cb_agl = max((t_sfc_c - td) * 125, 100)
    cb_msl = cb_agl + ground_m
    ceiling_per_hour.append(cb_msl)

print(f"Per-hour ceilings (m MSL): {[int(c) for c in ceiling_per_hour]}")
num_alts = len(altitudes)

# Compute per-level cell heights from altitude spacing for seamless tiling
cell_half = np.zeros(num_alts)
for i in range(num_alts):
    above = altitudes[i + 1] - altitudes[i] if i < num_alts - 1 else altitudes[i] - altitudes[i - 1]
    below = altitudes[i] - altitudes[i - 1] if i > 0 else altitudes[i + 1] - altitudes[i]
    cell_half[i] = min(above, below) * 0.45

# 4. Compute thermal strength (lapse rate ratio) for each cell
# Dry adiabatic lapse rate = 9.8°C/km; ratio = actual / dry adiabatic
# Ratio > 0 means unstable (good for thermals), higher = stronger lift
# Ratio <= 0 (inversion) = no lift (white)
DRY_ADIABATIC = 9.8  # °C/km
alt_sfc = full_altitudes[surface_level_idx]
t_sfc_k = t_2d[:, surface_level_idx]  # surface T for all profiles

lapse_ratio = np.zeros((num_profiles, num_alts))
for a_idx in range(num_alts):
    full_idx = valid_idx[a_idx]
    alt_k = altitudes[a_idx]
    t_alt_k = t_2d[:, full_idx]
    dalt = (alt_k - alt_sfc) / 1000.0
    if abs(dalt) > 0.01:
        lapse = (t_sfc_k - t_alt_k) / dalt
        lapse_ratio[:, a_idx] = lapse / DRY_ADIABATIC

# Lapse ratio → color: yellow → orange gradient
# Yellow at lr=0, deep orange at lr=LR_MAX
LR_MAX = 1.5

# Debug: report lapse ratio stats
all_lr = lapse_ratio.ravel()
print(f"Lapse ratio stats: min={all_lr.min():.3f}, max={all_lr.max():.3f}, "
      f"mean={all_lr.mean():.3f}, positive={(all_lr > 0).sum()}/{all_lr.size} cells")
print(f"  Sample values: {lapse_ratio[0, :5]}")
print(f"  Ceilings (m MSL): {[int(c) for c in ceiling_per_hour]}")
print(f"  Min altitude in plot: {altitudes[0]:.0f}m, Max: {altitudes[-1]:.0f}m")

# 5. Plotting the Windgram Grid
fig, ax = plt.subplots(figsize=(11, 9))

cell_width = np.median(np.diff(hour_positions))  # uniform spacing
cell_hw = cell_width * 0.4  # half-width for cell rectangle

for ti, hr in enumerate(hour_positions):
    mi = time_idx[ti]  # nearest model timestep
    thermal_ceiling = ceiling_per_hour[mi]
    for a_idx in range(num_alts):
        speed = wind_speed[mi, a_idx]
        u = u_mph[mi, a_idx]
        v = v_mph[mi, a_idx]
        alt = altitudes[a_idx]

        lr = lapse_ratio[mi, a_idx]
        if lr <= 0 or alt > thermal_ceiling:
            cell_color = 'white'
        else:
            t = min(float(lr) / LR_MAX, 1.0)
            cell_color = plt.cm.YlOrRd(t)

        half = cell_half[a_idx]
        rect = patches.Rectangle((hr - cell_hw, alt - half), cell_hw * 2, half * 2,
                                 facecolor=cell_color, edgecolor='#cccccc', linewidth=0.5)
        ax.add_patch(rect)

        if speed > 0.5:
            angle = np.arctan2(v, u)
            arrow_size = min(10 + speed * 0.5, 18)

            ax.text(hr, alt, "\u2192", fontsize=arrow_size,
                    ha='center', va='center', fontweight='bold',
                    rotation=np.degrees(angle), rotation_mode='anchor',
                    color='#222222')

            ax.text(hr + 0.3, alt - half * 0.35, f"{int(round(speed))}",
                    fontsize=6, color='#111111', ha='left', va='center')

ax.set_xlim(7.5, 21.5)
ax.set_xticks(range(8, 22))
ax.set_xticklabels([f"{h:02d}:00" for h in range(8, 22)], fontsize=8, fontweight='bold')

ax.set_ylim(ground_m, 4100)
ax.set_yticks(range(int(ground_m), 4100, 500))
ax.set_ylabel(f"Altitude (m) — ground: {int(ground_ft)}ft", fontsize=12, fontweight='bold')

# Secondary y-axis for feet
ax2 = ax.twinx()
ax2.set_ylim(ground_m, 4100)
ft_min = int(ground_ft / 500) * 500 + 500
ft_ticks = range(ft_min, int(4100 * 3.28084), 500)
ax2.set_yticks([t / 3.28084 for t in ft_ticks])
ax2.set_yticklabels(ft_ticks, fontsize=10)
ax2.set_ylabel("Altitude (ft)", fontsize=12, fontweight='bold')

ax.set_facecolor('#e0e0e0')
ax.grid(False)

plt.title(f"Windgram | {MODELS[model_name]['desc']} | Lat: {lat}, Lon: {lon}\nLapse Rate Ratio — Yellow/Orange = stronger thermal lift", fontsize=14, pad=15)
plt.tight_layout()
out_file = f"windgram_{model_name}_{lat}_{lon}.png"
plt.savefig(out_file, dpi=150)
print(f"Saved: {out_file}")
