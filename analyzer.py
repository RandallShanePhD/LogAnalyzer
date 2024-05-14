#!/usr/bin/python3
import datetime as dt
import numpy as np
import os
import statistics as stat
import sys

from math import asin, atan2, degrees, cos, radians, sin, sqrt

# Constants -------------------------------------/
settings = {
    "averaging_factor": 5,
    "climb_time_threshold": 10,
    "climb_ascend_threshold": 0.5,
    "glide_time_threshold": 15,
    "sink_time_threshold": 7,
    "sink_descend_threshold": 2.5,
    "kmz_speed_units": "kmh"
    }


# Reference Functions ---------------------------/
def calc_lift_sink(altitudes: [float]) -> float:
    # Remove any outliers over 2 sd
    value = 0
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
    raw_date = raw_date.replace("DATE:", "")  # flymaster encoding
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


def create_kmz(kmz_data):
    # kmz_data = {"pilot": pilot,
    #             "filename": in_igc_file[:-4]}
    infile = f"Logs/{kmz_data['filename']}"
    outfile = f"KMZs/{kmz_data['filename'][:-4]}.kmz"
    if os.path.exists(outfile):
        os.remove(outfile)

    from igc2kml import parse_igc, process_data, write_kml
    data, meta_data = parse_igc(infile)
    data, meta_data = process_data(data, meta_data, speed_unit=settings['kmz_speed_units'])
    meta_data["pilot"] = kmz_data["pilot"]
    write_kml(outfile, data, meta_data)


# Operational Functions -----------------------/
def instructions():
    print("\n")
    print("-----------------------------------------------------")
    print("--   IGC Log File Analyzer  (v2024-05)             --")
    print("--   Wander Expeditions LLC                        --")
    print("--   Randall Shane PhD                             --")
    print("--   Randall@WanderExpeditions.com                 --")
    print("--   https:/github.com/RandallShanePhD/LogAnalyzer --")
    print("-----------------------------------------------------\n")
    print("Instructions:")
    print("- Place your IGC file in this directory")
    print("- Select the file number from this list:")
    print("(r = Re-scan Directory / s = Settings / x = Exit)")

    files = []
    for file_name in os.listdir("Logs"):
        if file_name.split(".")[-1] in ["IGC", "igc"]:
            file_path = f"Logs/{file_name}"
            if os.path.isfile(file_path):
                files.append(file_name)
    files = dict({(str(i + 1), x) for i, x in enumerate(files)})
    files = dict(sorted(files.items(), key=lambda x: x[0]))
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
    print("  per glide. These are subsequently graded; climb, glide and # sink events provided.\n")
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
    print(f"  E: KMZ File Speed Units == {settings['kmz_speed_units']}")
    print("     - Units of measure for speed in KMZ file. Options: m/s, kmh, mph, kts")

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
        elif selection == "M":
            param = input("Input new m/s Climbing thresholh as a decimal (ex: 2.5): ")
            if param.isnumeric():
                settings['climb_ascend_threshold'] = float(param)
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
                settings['sink_descend_threshold'] = float(param)
        elif selection == "E":
            param = input("Input new KMZ units: m/s, kmh, mph, kts ")
            if param in ['m/s', 'kmh', 'mph', 'kts']:
                settings['kmz_speed_units'] = param
            else:
                print(f"\t** Unknown units selection - try again! **")
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
    global alt_m
    in_file = f"Logs/{in_igc_file}"
    f = open(in_file, "r")
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
    climb_sink: float = 0.00
    heading: float = 0.00
    takeoff_heading: int = 0
    alt_readings: [float] = []
    travelled: float = 0.00
    high_alt_m: int = 0
    high_lift_m: float = 0.00
    high_sink_m: float = 0.00
    last_lat: float = 0.00
    last_lon: float = 0.00
    last_alt: int = 0
    landing_alt_m: float = 0.00
    landing_heading: int = 0
    total_distance_km = 0.00
    lon_lat_alt_list = []

    takeoff_flag = True
    analysis_data = []
    climb_readings = 0
    glide_readings = 0

    for i, line in enumerate(lines):
        if line[:5] ==  "HFPLT":  # xc tracer pilot data
            offset =11
            if line[:19] == "HFPLTPILOTINCHARGE:":  # flymaster pilot data
                offset = 19

            pilot = line[offset:].replace("\n", "")

        if line[:5] ==  "HFDTE":  # date info
            raw_utc_date = line[5:].replace("\n", "")

        elif line[0] == "B":  # data lines start with 'B'
            raw_time = line[1:7]

            lat = float(line[7:14]) / 100000
            ns = line[14]
            if ns == "S":
                lat = lat * -1

            lon = float(line[15:23]) / 100000
            ew = line[23]
            if ew == "W":
                lon = lon * -1

            # GPS & Decimal places
            # 100s = non zero = longitude
            # 10s = 1000km
            # 1s = 111km
            # 1 decimal = 11.1km
            # 2 decimals = 1.1km
            # 3 decimals = 110m
            # 4 decimals = 11m
            # 5 decimals = 1.1m
            # 6 decimals = 11cm
            # 7 decimals = 1.1cm (surveying, limit of GPS tech)


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
            a_data = (int(raw_time), lat, lon, alt_m, heading, climb_sink)
            analysis_data.append(a_data)

            # Count climbs and glides
            if alt_m > last_alt:
                climb_readings += 1
            elif alt_m <= last_alt:
                glide_readings += 1

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

    analysis = flight_analyzer(analysis_data)

    kmz_data = {"pilot": pilot,
                "filename": in_igc_file}
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
               "duration": duration,
               "climbs_num": analysis["climbs_num"],
               "glides_num": analysis["glides_num"],
               "sinks_num": analysis["sinks_num"],
               "climb_grade": analysis["climb_grade"],
               "glide_grade": analysis["glide_grade"]}

    return summary


def flight_analyzer(analysis_data):
    # from settings
    # "climb_time_threshold": 10,
    # "climb_ascend_threshold": 0.5, (0.5 m/s + or you're not really climbing)
    # "glide_time_threshold": 15,
    # "sink_time_threshold": 7,
    # "sink_descend_threshold": 2.5,
    climbs_temp = []
    glides_temp = []
    sinks_temp = []

    for i, line in enumerate(analysis_data):
        alt_m = line[3]

        # analyze for climbs
        if i > settings["climb_time_threshold"]:
            compared_to_entry = i - settings["climb_time_threshold"]
            if alt_m > analysis_data[compared_to_entry][3]:
                climb_sink = [x[5] for x in analysis_data[compared_to_entry:i]]
                # you must climb more than 1/3rd of the time over the ascending threshold else it's not a climb
                if len([x for x in climb_sink if x > settings["climb_ascend_threshold"]]) > (len(climb_sink) / 3):
                    climbs_temp.extend(analysis_data[compared_to_entry:i])

        if i > settings["glide_time_threshold"]:
            compared_to_entry = i - settings["glide_time_threshold"]
            # everything that is not a climb is a glide including sinks which will be later ruled out
            if alt_m <= analysis_data[compared_to_entry][3]:
                glides_temp.extend(analysis_data[compared_to_entry:i])

        if i > settings["sink_time_threshold"]:
            compared_to_entry = i - settings["sink_time_threshold"]
            if alt_m < analysis_data[compared_to_entry][3]:
                climb_sink = [x[5] for x in analysis_data[compared_to_entry:i]]
                # you need 1 sink reading in excess of the sink descending threshold for it to be analyzed as a sink
                if len([x for x in climb_sink if x > settings["sink_descend_threshold"]]) > 1:
                    sinks_temp.extend(analysis_data[compared_to_entry:i])

    # Create unique c,g & s
    def chunker(array, tyype):
        # tyype: climbs, glides, sinks
        temp = list(set(array))
        temp.sort(key=lambda row: row[0])
        bulk, block = [], []

        for i, entry in enumerate(temp):
            if i > 0:
                if entry[0] - temp[i - 1][0] == 1:
                    block.append(entry)
                else:
                    if tyype == "climbs":
                        if len(block) > settings["climb_time_threshold"]:
                            actual_climbs = [x[5] for x in block if x[5] > settings["climb_ascend_threshold"]]
                            if len(actual_climbs) > len(block) / 3:
                                bulk.append(block)
                    elif tyype == "glides":
                        if len(block) > settings["glide_time_threshold"]:
                            bulk.append(block)
                    elif tyype == "sinks":
                        if len(block) > settings["sink_time_threshold"]:
                            actual_sinks = [x[5] for x in block if x[5] > settings["sink_descend_threshold"]]
                            # must be sinking half the time to be an actual sink event
                            if len(actual_sinks) > len(block) / 2:
                                bulk.append(block)
                    block = []

        return bulk

    all_climbs = chunker(climbs_temp, "climbs")
    all_glides = chunker(glides_temp, "glides")
    all_sinks = chunker(sinks_temp, "sinks")

    # climbs analysis
    climbing_grades = []
    for single_climb in all_climbs:
        altis = [x[3] for x in single_climb]
        climbing = 0
        for i in range(len(altis)):
            if i > 0 and altis[i] >= altis[i - 1]:
                climbing += 1
        climbing_grades.append(round(float(climbing / i), 2))
    climb_grade = 0.0
    try:
        climb_grade = round(stat.mean(climbing_grades) * 100, 1)
    except Exception:
        pass

    # glides analysis
    gliding_grades = []
    for single_glide in all_glides:
        altis = [x[3] for x in single_glide]
        gliding = 0
        for i in range(len(altis)):
            if i > 0 and altis[i] - altis[i - 1] < settings["sink_descend_threshold"]:
                gliding += 1
        gliding_grades.append(round(float(gliding / i), 2))
    glide_grade = 0.0
    try:
        glide_grade = round(stat.mean(gliding_grades) * 100, 1)
    except Exception:
        pass

    analysis_data = {"climbs_num": len(all_climbs),
                     "glides_num": len(all_glides),
                     "sinks_num": len(all_sinks),
                     "climb_grade": climb_grade,
                     "glide_grade": glide_grade}

    return analysis_data


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
    print("Analysis:")
    print(f" Number of Climbs: {summary['climbs_num']}")
    print(f" Climb Efficiency: {summary['climb_grade']}%")
    print(f" Number of Glides: {summary['glides_num']}")
    print(f" Glide Efficiency: {summary['glide_grade']}%")
    print(f" Number of Sinks: {summary['sinks_num']}")
    ratio = round(summary['climbs_num'] / (summary['climbs_num'] + summary['glides_num'] + summary['sinks_num']) * 100, 2)
    print(f" You are climbing {ratio}% of the flight")
    print("------------------------------------------\n")
    print("[return] to continue")
    input()


if __name__ == '__main__':
    while True:
        in_file = instructions()
        if in_file is not None:
            summary = load_igc(in_file)
            display_summary_stats(summary)
