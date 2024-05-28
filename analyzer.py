#!/usr/bin/python3
import datetime as dt
import numpy as np
import os
import statistics as stat
import sys

from math import asin, atan2, degrees, cos, radians, sin, sqrt

# Constants -------------------------------------/
settings = {
    "averaging_factor": 10,
    "climb_ascend_threshold": 0.5,
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

    # Native KMZ Creator
    # from kmz_creator import create_kmz
    # create_kmz(kmz_data)

    # for IGC2KML Library
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
    vario: str = ""
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
    flight_area_km = 0.00

    takeoff_flag = True
    analysis_data = []
    climb_readings = 0
    glide_readings = 0

    model_data = []

    for i, line in enumerate(lines):
        if line[:5] ==  "HFPLT":  # xc tracer pilot data
            offset =11
            if line[:19] == "HFPLTPILOTINCHARGE:":  # flymaster pilot data
                offset = 19

            pilot = line[offset:].replace("\n", "")

        if line[:12] == "HFFTYFRTYPE:":
            vario = line[12:].replace("\n", "").replace(",", " ")
        if line.startswith("HFGPS:"):
            vario += f", {line[6:]}".replace("\n", "")

        if line[:9] == "HFDTEDATE":  # SeeYou Navigator
            raw_utc_date = line[10:].replace("\n", "").split(",")[0]

        elif line[:5] ==  "HFDTE":  # date info
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
            if i == 0:
                travelled = 0
            elif travelled < .3:
                total_distance_km += travelled
            elif travelled > 25:
                travelled = 0

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

            # flight area calculation
            fa_dist = haversine((takeoff_lat, takeoff_lon), (lat, lon))
            if fa_dist > flight_area_km:
                flight_area_km = fa_dist

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
            a_data = (int(f"{raw_utc_date}{raw_time}"), lat, lon, alt_m, heading, travelled)
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

            # model data preparation
            # date, time, latitude, longitude, altitude (m), heading
            # model_line = [int(raw_utc_date), int(raw_time), lat, lon, alt_m, heading]  # try 1
            # model_line = [int(f"{raw_utc_date}{raw_time}"), alt_m, climb_sink]  # try 2
            # model_data.append(model_line)

    takeoff_to_land_dist = haversine((takeoff_lat, takeoff_lon), (last_lat, last_lon))

    # Landing Determination
    landing_dt = convert_hm_to_dt(raw_utc_date, raw_time)
    landing_heading = heading
    duration = (landing_dt - takeoff_dt).total_seconds()
    if duration < 0:
        duration = duration + (24 * 60 * 60)

    analysis = flight_analyzer(analysis_data)

    # Native
    # kmz_data = {"pilot": pilot,
    #             "filename": in_igc_file[:-4],
    #             "lon_lat_alt_list": lon_lat_alt_list}
    # create_kmz(kmz_data)

    # IGC2KML Library
    kmz_data = {"pilot": pilot,
                "filename": in_igc_file}

    try:
        create_kmz(kmz_data)
    except Exception as exc:
        print("ERROR: KMZ file not created!")

    summary = {"filename": in_igc_file,
               "pilot": pilot,
               "vario": vario,
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
               "flight_area_diameter": round(flight_area_km / 1000, 2),
               "duration": duration,
               # Analysis Data
               "climbs_num": analysis["climbs_num"],
               "glides_num": analysis["glides_num"],
               "sinks_num": analysis["sinks_num"],
               "climb_grade": analysis["climb_grade"],
               "max_sustained_climb": analysis["max_sustained_climb"],
               "glide_grade": analysis["glide_grade"],
               "sink_grade": analysis["sink_grade"],
               "details": analysis["details"],
               "µ_sustained_climb": analysis["µ_sustained_climb"],
               "µ_sustained_glide": analysis["µ_sustained_glide"]}
               # "model_data": model_data}

    return summary


def flight_analyzer(analysis_data):
    # from settings
    # "averaging_factor": 10,
    # "climb_ascend_threshold": 0.5,
    # "sink_descend_threshold": 2.5,
    analysis_data.sort(key=lambda row: row[0])
    chunks = []
    chunk_cat = []
    blocks = []  # (datetime, lat, lon, alt_m, heading, distance, climb_sink, category)
    blocks_cat = []

    # Step 1: Chunk into 'averaging_factor' Chunks
    temp = []
    for i, line in enumerate(analysis_data):
        # (datetime, lat, lon, alt_m, heading, distance)
        if i > 0:
            if i % settings["averaging_factor"] == 0 and i > 0:
                chunks.append(temp)
                temp = []
                temp.append(line)
            else:
                temp.append(line)

    # Step 2: Analyze for Climb, GLide or Sink
    for chunk in chunks:
        altitudes = [x[3] for x in chunk]
        avg_ls = calc_lift_sink(altitudes)

        # Determine Category: Climb, Glide, Sink
        if avg_ls > settings["climb_ascend_threshold"]:
            chunk_cat.append("C")  # ("C", alt_diff, avg_ls, distance_diff))
        elif avg_ls < (settings["sink_descend_threshold"] * -1):
            chunk_cat.append("S")  # ("S", alt_diff, avg_ls, distance_diff))
        else:
            chunk_cat.append("G")  # ("G", alt_diff, avg_ls, distance_diff))

    # Step 3: Consolidate contiguous types
    # chunks[i]: (datetime, lat, lon, alt_m, heading, distance)
    # chunk_cat[i]: (category, avg_ls)
    temp = []
    for i in range(len(chunk_cat)):
        if i > 0:
            if chunk_cat[i] == chunk_cat[i - 1]:
                temp = temp + chunks[i]
            else:
                # temp.sort(key=lambda x: x[0])
                blocks.append(temp)
                avg_ls = calc_lift_sink([x[3] for x in temp])
                blocks_cat.append((chunk_cat[i - 1], avg_ls))
                temp = chunks[i]

    # Step 4: Analysis
    climbing_grades = []
    gliding_grades = []
    sinking_grades = []
    for i, block in enumerate(blocks):
        if block != []:
            tyype = blocks_cat[i][0]
            altis = [x[3] for x in block]
            if tyype == "C":  # climbs analysis - graded on percent of time altitude increases continuously in climbing block
                total_climb = altis[-1] - altis[0]
                climbing = 0
                for i, alti in enumerate(altis):
                    if i > 0:
                        if alti > altis[i - 1]:
                            climbing += 1
                climbing_grades.append(round(float(climbing / len(altis)), 2))
            elif tyype == "G":  # glides analysis - Calc L/D & aggregate (somehow)
                lift = block[-1][3] - block[0][3]
                if lift == 0:
                    lift = 1
                distance = round(sum(x[5] for x in block) * 100)
                l_over_d = round(distance / lift, 2)
                gliding_grades.append(l_over_d)
            elif tyype == "S":  # record abs of sink rate
                sink_rate = abs(blocks_cat[i][1])
                sinking_grades.append(sink_rate)

    # Step 5: Detail Data
    details = []
    tyype_lookup = {"G": "Glide", "C": "Climb", "S": "Sink"}
    for i, block in enumerate(blocks):
        if block != []:
            altis = [x[3] for x in block]
            block_detail = {}
            block_detail["number"] = i
            block_detail["tyype"] = tyype_lookup[blocks_cat[i][0]]
            block_detail["time_secs"] = len(block)
            block_detail["altitude_start_m"] = block[0][3]
            block_detail["altitude_end_m"] = block[-1][3]
            block_detail["avg_lift_sink_ms"] = blocks_cat[i][1]
            block_detail["loc_start"] = (block[0][1], block[0][2])
            block_detail["loc_end"] = (block[-1][1], block[-1][2])
            block_detail["total_distance_m"] = round(sum(x[5] for x in block) * 100)

            details.append(block_detail)

    # Total Grades
    climb_grade = 0.00
    if len(climbing_grades) > 0:
        climb_grade = round(stat.mean(climbing_grades) * 100, 2)

    glide_grade = 0.00
    if len(gliding_grades) > 0:
        glide_grade = round(stat.mean(gliding_grades), 2)

    sink_grade = 0.00
    if len(sinking_grades) > 0:
        sink_grade = round(stat.mean(sinking_grades), 2)

    avg_sustained_climb = round(stat.mean([x['avg_lift_sink_ms'] for x in details if x["tyype"] == "Climb"]), 2)
    max_sustained_climb = max([x['avg_lift_sink_ms'] for x in details if x["tyype"] == "Climb"])
    avg_sustained_glide = round(stat.mean([x['avg_lift_sink_ms'] for x in details if x["tyype"] == "Glide"]), 2)

    analysis_data = {"climbs_num": len(climbing_grades),
                     "glides_num": len(gliding_grades),
                     "sinks_num": len(sinking_grades),
                     "climb_grade": climb_grade,
                     "glide_grade": glide_grade,
                     "sink_grade": sink_grade,
                     "µ_sustained_climb": avg_sustained_climb,
                     "µ_sustained_glide": avg_sustained_glide,
                     "max_sustained_climb": max_sustained_climb,
                     "details": details}

    return analysis_data


def display_summary_stats(summary):
    formatted_date = dt.datetime.strftime(summary['flight_date'], "%d %b %Y")
    formatted_duration = str(dt.timedelta(seconds=summary["duration"]))

    print("\nSummary Statistics:")
    print(f" File: {summary['filename']}")
    print(f" Pilot: {summary['pilot']}")
    print(f" Vario: {summary['vario']}")
    print(f" Date: {formatted_date}")
    print(f" Duration: {formatted_duration}")
    print(f" Takeoff GPS: {summary['takeoff_gps']}")
    print(f" Takeoff Altitude: {summary['takeoff_alt']} m || {meters_to_feet(summary['takeoff_alt'])} ft")
    print(f" Takeoff Heading: {summary['takeoff_heading']}°")
    print(f" Landing GPS: {summary['landing_gps']}")
    print(f" Landing Altitude: {summary['landing_alt']} m || {meters_to_feet(summary['landing_alt'])} ft")
    print(f" Landing Heading: {summary['landing_heading']}°")
    print(f" Distance Total: {summary['total_distance']} km || {km_to_miles(summary['total_distance'])} mi")
    print(f" Flight Area Diameter: {summary['flight_area_diameter']} km || {km_to_miles(summary['flight_area_diameter'])} mi")
    print(f" Takeoff to Landing: {summary['takeoff_to_land_dist']} km || {km_to_miles(summary['takeoff_to_land_dist'])} mi")
    print(f" Max Altitude: {summary['max_alt']} m || {meters_to_feet(summary['max_alt'])} ft")
    print(f" Max Lift: {summary['max_lift']} m/s || {msToFpm(summary['max_lift'])} ft/min")
    print(f" Max Sink: {summary['max_sink']} m/s || {msToFpm(summary['max_sink'])} ft/min")
    print("Analysis:")
    print(f" Climb - Number of Climbs: {summary['climbs_num']}")
    print(f" Climb - Max Sustained m/s: {summary['max_sustained_climb']} || {msToFpm(summary['max_sustained_climb'])} fpm")
    print(f" Climb - µ Sustained: {summary['µ_sustained_climb']} m/s || {msToFpm(summary['µ_sustained_climb'])} fpm")
    print(f" Climb - Efficiency %age: {summary['climb_grade']}%")
    print(f" Glides - Number of Glides: {summary['glides_num']}")
    print(f" Glides - µ Sustained: {summary['µ_sustained_glide']} m/s || {msToFpm(summary['µ_sustained_glide'])} fpm")
    print(f" Glides - µ L/D on Glide: {summary['glide_grade']}:1")
    print(f" Sinks - Number of Sinks (descents over {settings['sink_descend_threshold']}): {summary['sinks_num']}")
    print(f" Sinks - µ Sink Rate: {summary['sink_grade']} m/s || {msToFpm(summary['sink_grade'])} fpm")
    climb_ratio = round(summary['climbs_num'] / (summary['climbs_num'] + summary['glides_num'] + summary['sinks_num']) * 100, 2)
    print(f" You are climbing {climb_ratio}% of the flight")
    glide_ratio = round(
        summary['glides_num'] / (summary['climbs_num'] + summary['glides_num'] + summary['sinks_num']) * 100, 2)
    print(f" You are gliding {glide_ratio}% of the flight")
    sink_ratio = round(
        summary['sinks_num'] / (summary['climbs_num'] + summary['glides_num'] + summary['sinks_num']) * 100, 2)
    print(f" You are sinking {sink_ratio}% of the flight")
    print("------------------------------------------\n")
    print("'D' for Detailed flight inspection of blocks over 90 seconds long")
    print("'A' for ALL flight blocks")
    print("'C' for CLIMBS only")
    print("'G' for GLIDES only")
    print("'S' for SINKS only")
    print("[return] to continue")
    inp = input()
    if inp == "D":
        large_blocks = [x for x in summary["details"] if x['time_secs'] > 90]
        display_details(large_blocks)
    elif inp == "A":
        display_details(summary["details"])
    elif inp == "C":
        climb_blocks = [x for x in summary["details"] if x['tyype'] == 'Climb']
        display_details(climb_blocks)
    elif inp == "G":
        glide_blocks = [x for x in summary["details"] if x['tyype'] == 'Glide']
        display_details(glide_blocks)
    elif inp == "S":
        sink_blocks = [x for x in summary["details"] if x['tyype'] == 'Sink']
        display_details(sink_blocks)
    else:
        pass


def display_details(details):
    print("\nDetailed Blocks:")
    for detail in details:
        altitude_change = detail['altitude_end_m'] - detail['altitude_start_m']
        print(f" Block Number: {detail['number']}   Block Type: {detail['tyype']}   Time in Secs: {detail['time_secs']}")
        print(f"  Altitude Start: {detail['altitude_start_m']}m | {meters_to_feet(detail['altitude_start_m'])}ft   End: {detail['altitude_end_m']}m | {meters_to_feet(detail['altitude_end_m'])}ft")
        print(f"  Change in Altitude: {altitude_change}   µ Lift: {detail['avg_lift_sink_ms']}m/s | {msToFpm(detail['avg_lift_sink_ms'])}ft/min")
        print(f"  Location Start: {detail['loc_start']}   End: {detail['loc_end']}")
        distance = round(haversine(detail['loc_start'], detail['loc_end']) * 1000)
        print(f"  Distance Start-End: {distance}m | {meters_to_feet(distance)}ft   Distance Total: {detail['total_distance_m']}m | {meters_to_feet(detail['total_distance_m'])}ft")
        print("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")
    print("return to continue")
    input()


if __name__ == '__main__':
    while True:
        in_file = instructions()
        if in_file is not None:
            summary = load_igc(in_file)
            display_summary_stats(summary)
