import argparse
import datetime
import json
import urllib.request
import urllib.error
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

import matplotlib.patches as patches
from siphon.catalog import TDSCatalog
from siphon.ncss import NCSS


def lookup_elevation(lat, lon):
    """Look up ground elevation (meters) using Open-Elevation API."""
    try:
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return float(data['results'][0]['elevation'])
    except Exception as e:
        print(f"Warning: could not auto-detect elevation ({e})")
        return None

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
parser.add_argument('--name', '-n', type=str, default=None,
                    help='Site name to display in chart title')
args = parser.parse_args()

lat = args.lat
lon = args.lon
ground_ft = args.ground_ft
model_name = args.model
site_name = args.name
ground_m = ground_ft * 0.3048

if ground_ft == 0:
    auto_m = lookup_elevation(lat, lon)
    if auto_m is not None:
        ground_m = float(auto_m)
        ground_ft = ground_m / 0.3048
        print(f"Ground elevation: {ground_m:.0f}m ({ground_ft:.0f}ft)")
    else:
        print("Assuming sea level")

start_time = datetime.datetime.utcnow()
end_time = start_time + datetime.timedelta(hours=18)

print(f"Model: {MODELS[model_name]['desc']}")
print(f"Fetching forecast for Lat: {lat}, Lon: {lon}...")

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

# Filter levels from ground up to 4500m
valid_idx = np.where((altitudes >= ground_m) & (altitudes <= 4500))[0]
# Ensure ascending altitude order (NCSS may return levels high-to-low)
if len(valid_idx) > 1 and altitudes[valid_idx[0]] > altitudes[valid_idx[-1]]:
    valid_idx = valid_idx[::-1]
altitudes = altitudes[valid_idx]
wind_speed = wind_speed[:, valid_idx]
u_mph = u_mph[:, valid_idx]
v_mph = v_mph[:, valid_idx]
y_top = min(altitudes[-1] + 300, 4500)

# Use the lowest above-ground model level as the surface for ceiling calc
if len(valid_idx) > 0:
    surface_level_idx = valid_idx[0]

# Build hour positions and labels from profile timestamps
# Build model hour positions from timestamps
model_hours = []
for pt in profile_time_raw:
    dt = base_time + datetime.timedelta(hours=float(pt))
    model_hours.append(dt.hour + dt.minute / 60.0)
model_hours = np.array(model_hours)

# Target columns: every hour 10 AM to 10 PM
target_hours = np.arange(10, 23)  # 10..22
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
    cell_half[i] = min(above, below) * 0.5

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

# Lapse ratio → color: custom colormap
# Ratio > 0 means unstable (good for thermals), higher = stronger lift
# Ratio <= 0 (inversion) = no lift (light grey)
LR_MAX = 6.0

# Clean NaN / inf from weather data
lapse_ratio = np.nan_to_num(lapse_ratio, nan=0.0, posinf=0.0, neginf=0.0)

# Debug: report lapse ratio stats
all_lr = lapse_ratio.ravel()
print(f"Lapse ratio stats: min={all_lr.min():.3f}, max={all_lr.max():.3f}, "
      f"mean={all_lr.mean():.3f}, positive={(all_lr > 0).sum()}/{all_lr.size} cells")
print(f"  Sample values: {lapse_ratio[0, :5]}")
print(f"  Ceilings (m MSL): {[int(c) for c in ceiling_per_hour]}")
print(f"  Min altitude in plot: {altitudes[0]:.0f}m, Max: {altitudes[-1]:.0f}m")

# Custom colormap: cream → yellow → orange → deep red
THERMAL_CMAP = mcolors.LinearSegmentedColormap.from_list(
    'thermal', ['#fdf5e6', '#ffff00', '#ff8c00', '#dc143c', '#8b0000'], N=256)

# 5. Plotting the Windgram Grid
fig, ax = plt.subplots(figsize=(11, 9))

cell_width = np.median(np.diff(hour_positions))  # uniform spacing
cell_hw = cell_width * 0.4  # half-width for cell rectangle

for ti, hr in enumerate(hour_positions):
    mi = time_idx[ti]  # nearest model timestep
    thermal_ceiling = ceiling_per_hour[mi]
    for a_idx in range(1, num_alts):  # skip surface level (a_idx=0, no valid lapse rate)
        speed = wind_speed[mi, a_idx]
        u = u_mph[mi, a_idx]
        v = v_mph[mi, a_idx]
        alt = altitudes[a_idx]

        lr = lapse_ratio[mi, a_idx]
        half = cell_half[a_idx]
        above_ceiling = alt > thermal_ceiling
        cell_top = alt + half

        if a_idx == 1:
            cell_bottom = altitudes[0]  # first cell extends to surface level
        else:
            cell_bottom = alt - half

        if above_ceiling:
            cell_color = '#c8cdd6'
            edge, lw = '#888888', 0.3
        elif lr <= 0:
            cell_color = '#b0b8c4'
            edge, lw = '#888888', 0.3
        else:
            t = min(float(lr) / LR_MAX, 1.0)
            cell_color = THERMAL_CMAP(t)
            edge, lw = '#555555', 0.3

        rect = patches.Rectangle((hr - cell_hw, cell_bottom), cell_hw * 2, cell_top - cell_bottom,
                                 facecolor=cell_color, edgecolor=edge, linewidth=lw)
        ax.add_patch(rect)

        if speed > 0.5:
            angle = np.arctan2(v, u)
            arrow_size = min(10 + speed * 0.5, 18)

            ax.text(hr, alt, "\u2192", fontsize=arrow_size,
                    ha='center', va='center', fontweight='bold',
                    rotation=np.degrees(angle), rotation_mode='anchor',
                    color='#222222')

            ax.text(hr, alt - half * 0.6, f"{int(round(speed))}",
                    fontsize=6, color='#111111', ha='center', va='top')

ax.set_xlim(9.5, 22.5)
ax.set_xticks(range(10, 23))
ax.set_xticklabels([f"{h:02d}:00" for h in range(10, 23)], fontsize=8, fontweight='bold')

ax.set_ylim(ground_m, y_top)
y_ticks = list(range(int(ground_m), int(y_top), 500))
if ground_m > 0 and int(ground_m) not in y_ticks:
    y_ticks.insert(0, int(ground_m))
ax.set_yticks(y_ticks)
ax.set_ylabel(f"Altitude (m) — ground: {int(ground_ft)}ft", fontsize=12, fontweight='bold')

# Secondary y-axis for feet
ax2 = ax.twinx()
ax2.set_ylim(ground_m, y_top)
ft_min = int(ground_ft / 500) * 500 + 500
ft_ticks = range(ft_min, int(y_top * 3.28084), 500)
ax2.set_yticks([t / 3.28084 for t in ft_ticks])
ax2.set_yticklabels(ft_ticks, fontsize=10)
ax2.set_ylabel("Altitude (ft)", fontsize=12, fontweight='bold')

ax.set_facecolor('white')
for spine in ax.spines.values():
    spine.set_linewidth(2)
ax.grid(False)

# Draw cloud-base ceiling line for each hour column
for ti, hr in enumerate(hour_positions):
    mi = time_idx[ti]
    cb = ceiling_per_hour[mi]
    if cb < y_top:
        ax.plot([hr - 0.45, hr + 0.45], [cb, cb],
                color='#4a6a9a', linewidth=1.5, linestyle='--', zorder=5)
        ax.plot([hr, hr], [cb, cb + 60],
                color='#4a6a9a', linewidth=1.0, linestyle=':', zorder=5)

# Colorbar — horizontal below title/subtitle
fig.subplots_adjust(top=0.75)
cbar_ax = fig.add_axes([0.12, 0.85, 0.76, 0.03])
sm = plt.cm.ScalarMappable(cmap=THERMAL_CMAP, norm=mcolors.Normalize(vmin=0, vmax=LR_MAX))
sm.set_array([])
cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal')
cbar.set_label('Thermal Lift Strength (lapse rate ratio)', fontsize=9, fontweight='bold', labelpad=3)
cbar.set_ticks([0, 1, 2, 3, 4, 5, 6])
cbar.ax.tick_params(labelsize=7)

title_site = f"{site_name} " if site_name else ""
fig.suptitle(f"{title_site}Windgram | {MODELS[model_name]['desc']} | Lat: {lat}, Lon: {lon}",
             fontsize=14, y=0.97)
fig.text(0.5, 0.92, "Colored cells = thermal lift strength, dashed line = cloud base",
         ha='center', fontsize=9, fontweight='normal')
file_suffix = f"_{site_name}" if site_name else ""
plt.savefig(f"windgram_{model_name}_{lat}_{lon}{file_suffix}.png", dpi=150, bbox_inches='tight')
print(f"Saved: windgram_{model_name}_{lat}_{lon}{file_suffix}.png")
