import datetime
import sys
from metpy.plots import SkewT
from metpy.units import units
import matplotlib.pyplot as plt
import numpy as np
from siphon.catalog import TDSCatalog
from siphon.ncss import NCSS

# 1. Define your location and time
if len(sys.argv) >= 3:
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
else:
    print("Usage: python idapente.py <latitude> <longitude>")
    print("Example: python idapente.py 45.83 6.22")
    sys.exit(1)
forecast_time = datetime.datetime.utcnow()

# 2. Access NOAA GFS Best Dataset via Siphon
catalog_url = 'https://thredds.ucar.edu/thredds/catalog/grib/NCEP/GFS/Global_0p25deg/catalog.xml'
catalog = TDSCatalog(catalog_url)
dataset_name = sorted(catalog.datasets.keys())[-1]  # Get latest dataset
dataset = catalog.datasets[dataset_name]

# Query the NetCDF Subset Service (NCSS)
ncss = NCSS(dataset.access_urls['NetcdfSubset'])
query = ncss.query()
query.lonlat_point(lon, lat).time(forecast_time)
query.variables('Temperature_isobaric', 'Relative_humidity_isobaric',
                'u-component_of_wind_isobaric', 'v-component_of_wind_isobaric')
query.accept('netcdf4')

data = ncss.get_data(query)

# 3. Extract and parse data arrays
# Extract variables and handle dimensions (removing singleton dimensions)
p_vals = np.asarray(data.variables['altitude'][:])  # Pressure levels in Pa
t_vals = np.asarray(np.squeeze(data.variables['Temperature_isobaric'][:]) - 273.15)  # Convert K to C
rh_vals = np.asarray(np.squeeze(data.variables['Relative_humidity_isobaric'][:]))
u_vals = np.asarray(np.squeeze(data.variables['u-component_of_wind_isobaric'][:])) * 1.94384  # Convert m/s to knots
v_vals = np.asarray(np.squeeze(data.variables['v-component_of_wind_isobaric'][:])) * 1.94384

# Convert pressure to hPa/mb for MetPy compatibility
p = (p_vals / 100.0) * units.hPa
T = t_vals * units.degC

# Calculate Dewpoint from Relative Humidity
rh = (rh_vals / 100.0)
es = 6.112 * np.exp((17.67 * T.m) / (T.m + 243.5))
e = rh * es
Td = ((243.5 * np.log(e / 6.112)) / (17.67 - np.log(e / 6.112))) * units.degC

u = u_vals * units.knots
v = v_vals * units.knots

# 4. Plotting the Skew-T
fig = plt.figure(figsize=(9, 9))
skew = SkewT(fig, rotation=45)

# Plot Temperature (Red) and Dewpoint (Blue)
skew.plot(p, T, 'r', linewidth=2, label='Temperature')
skew.plot(p, Td, 'b', linewidth=2, label='Dewpoint')

# Plot Wind Barbs (subsampled for readability)
skew.plot_barbs(p[::2], u[::2], v[::2])
skew.ax.set_ylim(1000, 300)  # Standard paragliding altitudes (SFC to ~9000m)
skew.ax.set_xlim(-30, 40)

# Add dry adiabats, moist adiabats, and mixing ratio lines
skew.plot_dry_adiabats(colors='orange', alpha=0.4, linewidths=1)
skew.plot_moist_adiabats(colors='green', alpha=0.4, linewidths=1)
skew.plot_mixing_lines(colors='purple', alpha=0.3, linewidths=1)

plt.title(f"Sounding Forecast for Lat: {lat}, Lon: {lon}\nTime: {forecast_time.strftime('%Y-%m-%d %H:%M')} UTC", fontsize=14)
plt.xlabel("Temperature (°C)")
plt.ylabel("Pressure (hPa)")
plt.legend(loc='upper left')

plt.show()