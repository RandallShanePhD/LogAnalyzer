#!/usr/bin/python3
import datetime as dt
import os
import statistics as stat

from math import radians, cos, sin, asin, sqrt

# Constants ----------------------------------/
# breakpoints for highlighting in m
highlight = {"green": 0,  # below 5k
             "yellow": 1500,  # 4921ft
             "orange": 2300,  # 7545ft
             "red": 3000}  # 9842ft

# Helper Functions ---------------------------/
def calc_lift_sink(altitudes: [float]) -> float:
    # Remove any outliers over 2 sd
    try:
        meters_per_second = [float(t - s) for s, t in zip(altitudes, altitudes[1:])]
        sd = stat.stdev(meters_per_second)
        mn = stat.mean(meters_per_second)
        high = mn + 2.0 * sd
        low = mn - 2.0 * sd
        calc_list = [float(x) for x in meters_per_second if low < x < high]
        value = round(stat.mean(calc_list), 1)
    except Exception:
        value = 0
    finally:
        return value


def dms_to_dec(d, m, s):
    return float(d + (m / 60.0) + (s / 3600.0))


def convert_hm_to_dt(raw_date, raw_time):
    dt_string = f"{raw_date} {raw_time}"
    return dt.datetime.strptime(dt_string, '%d%m%y %H%M%S')


def meters_to_feet(meters: int):
    return int(round(float(meters) * 3.28084))


def km_to_miles(km: float):
    return round(km * 0.6213712, 1)


def msToFpm(ms: float):
    return round(ms * 196.8504)


def haversine(lon1, lat1, lon2, lat2, no_round=False):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # 3956 for miles
    rtn_val = round(c * r, 1)
    if no_round:
        rtn_val = (c * r)
    return rtn_val  # in km


def create_kmz(kmz_data):
    out_file = f"{kmz_data['filename']}.kmz"
    coordinates = " ".join([str(x).replace("(", "").replace(")", "").replace(" ", "") for x in kmz_data["lon_lat_alt_list"]])

    f = open(out_file, "a")
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<kml xmlns="http://www.opengis.net/kml/2.2\n')
    f.write('     xmlns:gx="http://www.google.com/kml/ext/2.2">\n')
    f.write('<Document>\n')
    f.write(f'<name>{kmz_data["pilot"]}</name>\n')
    f.write(f'<description>{kmz_data["filename"]} IGC file with color coded altitude.</description>\n')
    f.write('<Placemark id = "ID_00000">\n')  # ID number
    f.write('<name> Flight Track - B </name>\n')  # track name
    f.write('<description> Red line section </description>\n')  # description
    f.write('<Snippet maxLines="0"></Snippet>\n')
    f.write('<Style>\n')
    f.write('<LineStyle>\n')
    f.write('<color>ff0000ff</color>\n')  # color
    f.write('<width>2</width>\n')  # line thickness
    f.write('</LineStyle>\n')
    f.write('</Style>\n')
    f.write('<LineString>\n')
    f.write('<extrude>1</extrude>\n')
    f.write('<tessellate>1</tessellate>\n')
    f.write('<altitudeMode>absolute</altitudeMode>\n')
    f.write('<coordinates>\n')
    f.write(f'{coordinates}\n')  # add coordinated here
    f.write('</coordinates>\n')
    f.write('</LineString>\n')
    f.write('</Placemark>\n')
    f.write('</Document>\n')
    f.write('</kml>\n')

    f.close()


# Operational Functions -----------------------/
def instructions():
    # Optional
    # file = sys.argv[1]
    # print(f"File: {file}")
    print("-----------------------------------------------------")
    print("--   IGC Log File Analyzer  (v2023-04)             --")
    print("--   Wander Expeditions LLC                        --")
    print("--   Randall Shane PhD                             --")
    print("--   Randall@WanderExpeditions.com                 --")
    print("--   https:/github.com/RandallShanePhD/LogAnalyzer --")
    print("---------------------------------------------------\n")
    print("Instructions:")
    print("1) Place your IGC file in this directory")
    print("2) Type the filename in exactly as you see it")

    while True:
        filename = input("> ")
        if os.path.isfile(filename):
            print(f" {filename}")
            return filename


def display(summary):
    formatted_date = dt.datetime.strftime(summary['flight_date'], "%d %b %Y")
    formatted_duration = str(dt.timedelta(seconds=summary["duration"]))

    print("Summary Statistics:")
    print(f" Pilot: {summary['pilot']}")
    print(f" Date: {formatted_date}")
    print(f" Duration: {formatted_duration}")
    print(f" Takeoff Altitude: {summary['takeoff_alt']} m || {meters_to_feet(summary['takeoff_alt'])} ft")
    print(f" Landing Altitude: {summary['landing_alt']} m || {meters_to_feet(summary['landing_alt'])} ft")
    # print(f" Distance Total: {summary['total_distance']} km || {km_to_miles(summary['total_distance'])} mi")
    print(f" Distance from Takeoff: {summary['takeoff_distance']} km || {km_to_miles(summary['takeoff_distance'])} mi")
    print(f" Max Altitude: {summary['max_alt']} m || {meters_to_feet(summary['max_alt'])} ft")
    print(f" Max Lift: {summary['max_lift']} m/s || {msToFpm(summary['max_lift'])} ft/min")
    print(f" Max Sink: {summary['max_sink']} m/s || {msToFpm(summary['max_sink'])} ft/min")
    print("---------------------------------------------------\n")


def load_igc(in_igc_file):
    # 0 123456 78901234 567890123 4 56789 01234 5678901234567890
    # R TTTTTT DDMMMMMC DDDMMMMMC V PPPPP GGGGG AAA SS NNN CRLF
    # B 050818 2801340N 08344054E A 01638 01639 001 10 002 3130139
    f = open(in_igc_file, "r")
    lines = f.readlines()

    pilot: str = ""
    raw_utc_date = None
    takeoff_dt: None
    landing_dt: None
    raw_time = 0
    takeoff_lat: float = 0.00
    takeoff_lon: float = 0.00
    takeoff_alt_m: float = 0.00  # meters
    alt_readings: float = []
    high_alt_m: int = 0
    high_lift_m: float = 0.00
    high_sink_m: float = 0.00
    last_lat: float = 0.00
    last_lon: float = 0.00
    landing_alt_m: float = 0.00
    total_distance_m = 0.00
    lon_lat_alt_list = []

    first_takeoff_flag = True
    averaging_factor = 5

    for line in lines:
        if line[:5] ==  "HFPLT":
            pilot = line[11:].replace("\n", "")

        if line[:5] ==  "HFDTE":
            raw_utc_date = line[5:].replace("\n", "")

        elif line[0] == "B":
            raw_time = line[1:7]

            lat_d = int(line[7:9])
            lat_m = int(line[9:11])
            lat_s = int(line[11:14])
            lat = dms_to_dec(lat_d, lat_m, lat_s)
            ns = line[14]
            if ns == "S":
                lat = lat * -1

            lon_d = int(line[15:18])
            lon_m = int(line[18:20])
            lon_s = int(line[20:22])
            lon = dms_to_dec(lon_d, lon_m, lon_s)
            ew = line[23]
            if ew == "W":
                lon = lon * -1

            # total distance
            if lon != 0.00 and last_lon != 0.00 \
                and lat != 0.00 and last_lon != 0.00 \
                and lat != last_lat and lon != last_lon:
                travelled = haversine(last_lon, last_lat, lon, lat, no_round=True)
                total_distance_m += travelled

            # set last lat & lon
            last_lat = lat
            last_lon = lon

            # altitude, lift & sink
            alt_m = int(line[25:30])  # pressure altitude
            if alt_m == 0:
                alt_m = int(line[30:35])  # gps altitude
            landing_alt_m = alt_m

            # List for kmz path
            lon_lat_alt_list.append((lon, lat, alt_m))

            if first_takeoff_flag is True:
                takeoff_dt = convert_hm_to_dt(raw_utc_date, raw_time)
                takeoff_lat = lat
                takeoff_lon = lon
                takeoff_alt_m = alt_m
                first_takeoff_flag = False

            if int(raw_time[-2:]) % averaging_factor == 0:
                if len(alt_readings) >= averaging_factor:
                    climb_sink = calc_lift_sink(alt_readings)
                    if climb_sink > high_lift_m:
                        high_lift_m = climb_sink
                    elif climb_sink < high_sink_m:
                        high_sink_m = climb_sink
                    alt_readings =[]
            else:
                alt_readings.append(float(alt_m))

            # set values
            if alt_m > high_alt_m:
                high_alt_m = alt_m

    dist_from_takeoff = haversine(takeoff_lon, takeoff_lat, last_lon, last_lat)

    # duration
    landing_dt = convert_hm_to_dt(raw_utc_date, raw_time)
    duration = (landing_dt - takeoff_dt).total_seconds()
    if duration < 0:
        duration = duration + (24 * 60 * 60)

    kmz_data = {"pilot": pilot,
                "filename": in_igc_file[:-4],
                "lon_lat_alt_list": lon_lat_alt_list}
    create_kmz(kmz_data)

    summary = {"pilot": pilot,
               "flight_date": takeoff_dt,
               "max_alt": high_alt_m,
               "max_lift": high_lift_m,
               "max_sink" : high_sink_m,
               "takeoff_alt": takeoff_alt_m,
               "landing_alt": landing_alt_m,
               # "total_distance": round(total_distance_m, 1),
               "takeoff_distance": dist_from_takeoff,
               "duration": duration}

    return summary


def write_file(outfile):
    text = ['Welcome to datagy.io!', "Let's learn some Python!"]

    with open('/Users/nikpi/Desktop/textfile.txt', 'w') as f:
        for line in text:
            f.write(line)
            f.write('\n')


if __name__ == '__main__':
    in_file = instructions()
    summary = load_igc(in_file)
    display(summary)
