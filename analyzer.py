#!/usr/bin/python3
import datetime as dt
import os
import statistics as stat
import sys

from math import asin, atan2, degrees, cos, radians, sin, sqrt

# Constants -------------------------------------/
settings = {
    "averaging_factor": 5,
    "climb_time_threshold": 10,
    "glide_time_threshold": 30,
    "sink_time_threshold": 7,
    "sink_descend_threshold": 2.5,
    }


# Reference Functions ---------------------------/
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
    except Exception as exc:
        value = 0
    finally:
        return value


def convert_hm_to_dt(raw_date, raw_time):
    dt_string = f"{raw_date} {raw_time}"
    return dt.datetime.strptime(dt_string, '%d%m%y %H%M%S')


def meters_to_feet(meters: int):
    return int(round(float(meters) * 3.28084))


def km_to_miles(km: float):
    return round(km * 0.6213712, 1)


def msToFpm(ms: float):
    return round(ms * 196.8504)


def haversine(loc1, loc2):
    # loc is a (lat, lon) tuple
    lat1, lon1, lat2, lon2 = map(radians, [loc1[0], loc1[1], loc2[0], loc2[1]])
    dlon = (lon2 - lon1)
    dlat = (lat2 - lat1)
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))  # formula 1
    # c = 2 * atan2(sqrt(a), sqrt(1 - a))  # formula 2
    r = 6372.8  # for km. Use 3959.87433 for miles
    rtn_val = (c * r)
    return rtn_val


def bearing(loc1, loc2):
    # loc is a (lat, lon) tuple
    lat1, lon1, lat2, lon2 = loc1[0], loc1[1], loc2[0], loc2[1]
    bearing = atan2(sin(lon2 - lon1) * cos(lat2), cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(lon2 - lon1))
    bearing = degrees(bearing)
    return int((bearing + 360) % 360)


# Operational Functions -----------------------/
def create_kmz(kmz_data):
    out_file = f"{kmz_data['filename']}.kmz"
    if os.path.exists(out_file):
        os.remove(out_file)

    # breakpoints for highlighting in m
    highlight = {}
    colors = {"green" : "ff00ff00",
              "yellow": "ff00ffff",
              "orange": "ff0080ff",
              "red": "ff0000ff"}

    altis = [int(x[2]) for x in kmz_data["lon_lat_alt_list"] if int(x[2]) > 0]
    max_alti = max(altis)
    min_alti = min(altis)
    diff = (max_alti - min_alti) / 4
    highlight[int(min_alti + diff)] = "green"
    highlight[int(min_alti + (diff * 2))] = "yellow"
    highlight[int(min_alti + (diff * 3))] = "orange"
    highlight[int(max_alti * .9)] = "red"

    # Color code the Coordinates
    def color_alti(alti):
        color = "green"
        for h_alti in highlight:
            if alti > h_alti:
                color = highlight[h_alti]
        return color

    coordinates = []
    for coord in kmz_data["lon_lat_alt_list"]:
        alti = coord[2]
        color = color_alti(alti)
        coord = (coord[0], coord[1], coord[2], color)
        coordinates.append(coord)

    # Write File Header
    f = open(out_file, "a")
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('''<kml xmlns="http://www.opengis.net/kml/2.2"
     xmlns:gx="http://www.google.com/kml/ext/2.2">''')
    f.write('<Document>\n')
    f.write(f'<name>{kmz_data["pilot"]}</name>\n')
    f.write(f'<description>{kmz_data["filename"]} IGC file with color coded altitude.</description>\n')

    # Block and write the color coded coordinates for plotting
    block = []
    last_color = coordinates[0][3]
    for i, coord in enumerate(coordinates):
        current_color = coord[3]
        if current_color == last_color:
            block.append(f"{coord[0]},{coord[1]},{coord[2]}")
        else:
            block = []
            last_color = current_color
            # KMZ Data
            f.write(f'<Placemark id = "ID_0{i}">\n')  # ID number
            f.write('<name>Flight Track</name>\n')  # track name
            f.write(f'<description> {last_color} line section </description>\n')  # description
            f.write('<Snippet maxLines="0"></Snippet>\n')
            f.write('<Style>\n')
            f.write('<LineStyle>\n')
            f.write(f'<color>{colors[last_color]}</color>\n')  # color
            f.write('<width>2</width>\n')  # line thickness
            f.write('</LineStyle>\n')
            f.write('</Style>\n')
            f.write('<LineString>\n')
            f.write('<extrude>0</extrude>\n')
            f.write('<tessellate>1</tessellate>\n')
            f.write('<altitudeMode>absolute</altitudeMode>\n')
            f.write('<coordinates>\n')
            writable_block = " ".join(block)
            f.write(f'{writable_block}\n')  # coordinate block
            f.write('</coordinates>\n')
            f.write('</LineString>\n')
            f.write('</Placemark>\n')

    # Write File Tail
    f.write('</Document>\n')
    f.write('</kml>\n')
    f.close()


def instructions():
    print("\n")
    print("-----------------------------------------------------")
    print("--   IGC Log File Analyzer  (v2023-06)             --")
    print("--   Wander Expeditions LLC                        --")
    print("--   Randall Shane PhD                             --")
    print("--   Randall@WanderExpeditions.com                 --")
    print("--   https:/github.com/RandallShanePhD/LogAnalyzer --")
    print("-----------------------------------------------------\n")
    print("Instructions:")
    print("- Place your IGC file in this directory")
    print("- Select the file number from this list:")

    files = [x for x in os.listdir(".") if x.split(".")[-1] in ["IGC", "igc"]]
    files = [x for x in files if os.path.isfile(x)]
    files = dict({(str(i + 1), x) for i, x in enumerate(files)})
    files = dict(sorted(files.items(), key=lambda x: x[0]))
    files["r"] = "Re-scan Directory"
    files["s"] = "Settings & Analysis Notes"
    files["x"] = "Exit"
    for file_num in files:
        print(f"\t{file_num} - {files[file_num]}")

    while True:
        number = input()
        try:
            if number == "x":
                sys.exit()
            elif number == "r":
                return
            elif number == "s":
                display_settings()
            else:
                return files[number]
        except KeyError:
            print(f"\t ERROR: Please choose the correct file number")


def display_settings():
    selection = "x"
    print("\n Settings & Analysis Notes:")
    print("--------------------------------------------------------------------------------")
    print("  NOTE: Analysis of the flight log looks for climbs, glides and sinks. The")
    print("  goal is to determine the consistency of climbing by evaluating the changes in ")
    print("  the rate of climb. It also seeks to determine how efficiently a pilot is ")
    print("  gliding by averaging the L/D for the glides and deriving a deviation rating ")
    print("  per glide. These are subsequently evaluated with a weighted average where ")
    print("  climbing is worth 2x and gliding is worth 1x. The final number is a 0-100% ")
    print("  flight efficiency rating.\n")
    print("--------------------------------------------------------------------------------")
    print(f"  A: Lift/Sink Averaging Factor == {settings['averaging_factor']}")
    print("     - Number of seconds used to average lift & sink.")
    print(f"  C: Climb Time Threshold == {settings['climb_time_threshold']}")
    print("     - Number of seconds of continuing climb to be labeled a climb.")
    print(f"  G: Glide Time Threshold == {settings['glide_time_threshold']}")
    print("     - Number of seconds of continuing glide to be labeled a glide.")
    print(f"  S: Sink Time Threshold == {settings['sink_time_threshold']}")
    print("     - Number of seconds of continuing sink to be labeled sinking.")
    print(f"  D: Sink Descend Threshold == {settings['sink_descend_threshold']}")
    print("     - Meters/second threshold to be considered sinking.")
    print("\n Select letter to edit, x to return")
    selection = input()
    try:
        if selection == "x":
            pass
        elif selection == 'A':
            param = input("Input new number of Averaging seconds: ")
            if param.isnumeric():
                settings['averaging_factor'] = int(param)
        elif selection == "C":
            param = input("Input new number of Climbing seconds: ")
            if param.isnumeric():
                settings['climb_time_threshold'] = int(param)
        elif selection == "G":
            param = input("Input new number of Gliding seconds: ")
            if param.isnumeric():
                settings['glide_time_threshold'] = int(param)
        elif selection == "S":
            param = input("Input new number of Sinking seconds: ")
            if param.isnumeric():
                settings['sink_time_threshold'] = int(param)
        elif selection == "D":
            param = input("Input new Sink Descent threshold as a decimal (ex: 3.1): ")
            if param.replace(".", "").isnumeric():
                settings['climb_time_threshold'] = float(param)
        else:
            print(f"\t** Unknown selection - returning to main menu! **")
    except Exception as exc:
        print(f"\t** ERROR: {exc} **")
    finally:
        instructions()


def load_igc(in_igc_file):
    # File Parse Data
    # 0 123456 78901234 567890123 4 56789 01234 5678901234567890
    # R TTTTTT DDMMSSSC DDDMMSSSC V PPPPP GGGGG AAA SS NNN CRLF
    # B 050818 2801340N 08344054E A 01638 01639 001 10 002 3130139

    f = open(in_igc_file, "r")
    lines = f.readlines()

    pilot: str = ""
    raw_utc_date = None
    takeoff_dt: None
    landing_dt: None
    duration: int = 0
    raw_time = 0
    takeoff_lat: float = 0.00
    takeoff_lon: float = 0.00
    takeoff_alt_m: float = 0.00  # meters
    takeoff_heading: int = 0
    alt_readings: float = []
    travelled: float = 0.00
    high_alt_m: int = 0
    high_lift_m: float = 0.00
    high_sink_m: float = 0.00
    last_lat: float = 0.00
    last_lon: float = 0.00
    last_alt: int = 0.00
    landing_alt_m: float = 0.00
    landing_heading: int = 0
    total_distance_km = 0.00
    lon_lat_alt_list = []

    takeoff_flag = True
    analysis_data = []
    climbs = []
    climb_readings = 0
    glides = []
    glide_readings = 0

    for i, line in enumerate(lines):
        if line[:5] ==  "HFPLT":
            pilot = line[11:].replace("\n", "")

        if line[:5] ==  "HFDTE":
            raw_utc_date = line[5:].replace("\n", "")

        elif line[0] == "B":
            raw_time = line[1:7]

            lat = float(line[7:14]) / 100000
            ns = line[14]
            if ns == "S":
                lat = lat * -1

            lon = float(line[15:23]) / 100000
            ew = line[23]
            if ew == "W":
                lon = lon * -1

            # total distance
            travelled = haversine((last_lat, last_lon), (lat, lon))
            # print(f"GPS: ({last_lat}, {last_lon}), ({lat}, {lon})\tTravelled: {travelled}")
            if travelled < .3:
                total_distance_km += travelled

            # get bearing
            if last_lat != 0.00 and last_lon != 0.00 and \
                (last_lat, last_lon) != (lat, lon):
                heading = bearing((last_lat, last_lon), (lat, lon))
                # print(f"GPS: {(last_lat, last_lon), (lat, lon)}\tHeading {heading}")

                if takeoff_flag:  # set takeoff data
                    takeoff_dt = convert_hm_to_dt(raw_utc_date, raw_time)
                    takeoff_lat = lat
                    takeoff_lon = lon
                    takeoff_alt_m = alt_m
                    takeoff_heading = heading
                    takeoff_flag = False

            # set last lat, lon
            last_lat = lat
            last_lon = lon

            # altitude, lift & sink
            alt_m = int(line[25:30])  # pressure altitude
            if alt_m == 0:
                alt_m = int(line[30:35])  # gps altitude
            landing_alt_m = alt_m

            # List for kmz path
            lon_lat_alt_list.append((lon, lat, alt_m))

            # Climb & Sink with averaging
            if int(raw_time[-2:]) % settings["averaging_factor"] == 0:
                if len(alt_readings) >= settings["averaging_factor"]:
                    climb_sink = calc_lift_sink(alt_readings)
                    if climb_sink > high_lift_m:
                        high_lift_m = climb_sink
                    elif climb_sink < high_sink_m:
                        high_sink_m = climb_sink
                    alt_readings =[]
            else:
                alt_readings.append(float(alt_m))

            # Analysis - Climbs & Glides
            a_data = (raw_time, lat, lon, alt_m)
            analysis_data.append(a_data)

            # count climbs and glides
            # if alt_m > last_alt:
            #     climb_readings += 1
            # elif alt_m == last_alt:
            #     glide_readings += 1
            # elif alt_m < last_alt:
            #     if calc_lift_sink([last_alt, alt_m]) > settings["sink_descend_threshold"]:
            #         glide_readings += 1
            #         climb_readings = 0
            #
            #
            # if climb_readings > settings["climb_time_threshold"]
            #     glide_readings = 0

            # "climb_time_threshold": 10,
            # "glide_time_threshold": 30,
            # "sink_time_threshold": 7,
            # : 2.5,


            # set values
            if alt_m > high_alt_m:
                high_alt_m = alt_m
            last_alt = alt_m

    takeoff_to_land_dist = haversine((takeoff_lat, takeoff_lon), (last_lat, last_lon))

    # Landing Determination
    landing_dt = convert_hm_to_dt(raw_utc_date, raw_time)
    landing_heading = heading
    duration = (landing_dt - takeoff_dt).total_seconds()
    if duration < 0:
        duration = duration + (24 * 60 * 60)

    kmz_data = {"pilot": pilot,
                "filename": in_igc_file[:-4],
                "lon_lat_alt_list": lon_lat_alt_list}
    create_kmz(kmz_data)

    summary = {"filename": in_igc_file,
               "pilot": pilot,
               "flight_date": takeoff_dt,
               "max_alt": high_alt_m,
               "max_lift": high_lift_m,
               "max_sink" : high_sink_m,
               "takeoff_alt": takeoff_alt_m,
               "takeoff_gps": (round(takeoff_lat, 6), round(takeoff_lon, 6)),
               "takeoff_heading": takeoff_heading,
               "landing_alt": landing_alt_m,
               "landing_gps": (round(last_lat, 6), round(last_lon, 6)),
               "landing_heading": landing_heading,
               "total_distance": round(total_distance_km, 1),
               "takeoff_to_land_dist": round(takeoff_to_land_dist, 1),
               "duration": duration}

    return summary


def display_summary_stats(summary):
    formatted_date = dt.datetime.strftime(summary['flight_date'], "%d %b %Y")
    formatted_duration = str(dt.timedelta(seconds=summary["duration"]))

    print("\nSummary Statistics:")
    print(f" File: {summary['filename']}")
    print(f" Pilot: {summary['pilot']}")
    print(f" Date: {formatted_date}")
    print(f" Duration: {formatted_duration}")
    print(f" Takeoff GPS: {summary['takeoff_gps']}")
    print(f" Takeoff Altitude: {summary['takeoff_alt']} m || {meters_to_feet(summary['takeoff_alt'])} ft")
    print(f" Takeoff Heading: {summary['takeoff_heading']}°")
    print(f" Landing GPS: {summary['landing_gps']}")
    print(f" Landing Altitude: {summary['landing_alt']} m || {meters_to_feet(summary['landing_alt'])} ft")
    print(f" Landing Heading: {summary['landing_heading']}°")
    print(f" Distance Total: {summary['total_distance']} km || {km_to_miles(summary['total_distance'])} mi")
    print(f" Takeoff to Landing: {summary['takeoff_to_land_dist']} km || {km_to_miles(summary['takeoff_to_land_dist'])} mi")
    print(f" Max Altitude: {summary['max_alt']} m || {meters_to_feet(summary['max_alt'])} ft")
    print(f" Max Lift: {summary['max_lift']} m/s || {msToFpm(summary['max_lift'])} ft/min")
    print(f" Max Sink: {summary['max_sink']} m/s || {msToFpm(summary['max_sink'])} ft/min")
    print("---------------------------------------------------\n")
    print("[return] to continue")
    input()


if __name__ == '__main__':
    while True:
        in_file = instructions()
        if in_file is not None:
            summary = load_igc(in_file)
            display_summary_stats(summary)



# Test File - Slovenia
# 2 June 2023 - 11:46am
# duration 50min
# takeoff 4058'
# land 853'
# horiz distance 3.4mile
# distance covered 18.9mile / 30.42km
# max alti 4144'
# max lift 866fpm
# max sink -753fpm

# max ground speed 34.2mph
# flat triangle 8.2mile
# open distance 5.5mile
# free dist (5 point) 10.1mile
# FAI triangle 7.8mile
