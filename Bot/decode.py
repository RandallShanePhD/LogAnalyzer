#!/usr/bin/python3
import statistics as stat

from base import settings
from base import convert_hm_to_dt, convert_meters_to_feet, convert_km_to_miles, convert_ms_to_fpm, format_timestamp, \
    haversine, bearing


MAX_GLIDE_RATIO = 20


# Reference Functions ---------------------------------------------------------------------------|
def calc_lift_sink(altitudes: [float]) -> float:
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


def calculate_climb_efficiency(altis, global_avg_climb, averaging_factor):
    if len(altis) < 2:
        return 0.0

    climb_rates = [float(t - s) for s, t in zip(altis, altis[1:])]

    net_gain = altis[-1] - altis[0]
    expected_gain = len(climb_rates) * global_avg_climb if global_avg_climb > 0 else 1

    net_efficiency = min(net_gain / expected_gain, 1.0) if expected_gain > 0 else 0.0

    try:
        rate_sd = stat.stdev(climb_rates)
        consistency_score = max(0, 1 - (rate_sd / (global_avg_climb * 2))) if global_avg_climb > 0 else 0.5
    except:
        consistency_score = 0.5

    threshold = global_avg_climb * 0.5
    sustained_count = sum(1 for r in climb_rates if r >= threshold)
    sustained_ratio = sustained_count / len(climb_rates) if climb_rates else 0

    positive_steps = sum(1 for r in climb_rates if r > 0)
    positive_ratio = positive_steps / len(climb_rates) if climb_rates else 0

    efficiency = (
            net_efficiency * 0.35 +
            consistency_score * 0.25 +
            sustained_ratio * 0.25 +
            positive_ratio * 0.15
    )

    return round(min(efficiency, 1.0), 2)


# Detection & specific analysis mechanisms  --------------------------------------------------------------------|
def detect_circling(blocks, min_turns=2, min_duration=20, min_alt_gain=50, max_drift_m=1000):
    circling_blocks = []
    for block in blocks:
        if block['tyype'] == 'Climb' and block['time_secs'] >= min_duration:
            alt_gain = block['altitude_end_m'] - block['altitude_start_m']
            if alt_gain >= min_alt_gain:
                start_loc = block['loc_start']
                end_loc = block['loc_end']
                distance = haversine(start_loc, end_loc) * 1000
                if distance < max_drift_m:
                    circling_blocks.append(block)
    return circling_blocks


def calculate_thermal_stats(thermal_blocks, all_blocks):
    if not thermal_blocks:
        return {
            'thermal_count': 0,
            'avg_thermal_strength': 0,
            'max_thermal_strength': 0,
            'min_thermal_strength': 0,
            'avg_thermal_duration': 0,
            'total_thermal_time': 0,
            'avg_alt_gain': 0,
            'total_alt_gain': 0,
            'thermal_locations': [],
            'thermal_strengths': []
        }

    strengths = [b['avg_lift_sink_ms'] for b in thermal_blocks]
    durations = [b['time_secs'] for b in thermal_blocks]
    alt_gains = [b['altitude_end_m'] - b['altitude_start_m'] for b in thermal_blocks]
    locations = [b['loc_start'] for b in thermal_blocks]

    total_flight_time = sum(b['time_secs'] for b in all_blocks)
    total_thermal_time = sum(durations)

    return {
        'thermal_count': len(thermal_blocks),
        'avg_thermal_strength': round(stat.mean(strengths), 2),
        'max_thermal_strength': max(strengths),
        'min_thermal_strength': min(strengths),
        'avg_thermal_duration': round(stat.mean(durations), 1),
        'total_thermal_time': total_thermal_time,
        'thermal_time_pct': round(total_thermal_time / total_flight_time * 100, 1) if total_flight_time > 0 else 0,
        'avg_alt_gain': round(stat.mean(alt_gains), 1),
        'total_alt_gain': sum(alt_gains),
        'thermal_locations': locations,
        'thermal_strengths': strengths
    }


def analyze_thermals(all_blocks):
    circling_blocks = detect_circling(all_blocks)
    stats = calculate_thermal_stats(circling_blocks, all_blocks)
    stats['circling_blocks'] = circling_blocks
    return stats


def analyze_glide_performance(blocks, glider_type=None):
    glide_blocks = [b for b in blocks if b['tyype'] == 'Glide']
    if not glide_blocks:
        return {
            'glide_count': 0,
            'best_glide_ratio': 0,
            'best_glide_alt': 0,
            'avg_glide_ratio': 0,
            'avg_glide_ratio_alt': 0,
            'avg_sink_rate': 0,
            'macready_optimal': 0,
            'cruise_efficiency': 0,
            'glide_polar': []
        }

    glide_data = []
    for block in glide_blocks:
        alt_loss = block['altitude_start_m'] - block['altitude_end_m']
        distance = block['total_distance_m']
        if alt_loss > 10 and distance > 50:
            l_d = round(distance / alt_loss, 2) if alt_loss > 0 else 0  # L/D Calc Here
            if l_d > MAX_GLIDE_RATIO:
                continue
            avg_alt = (block['altitude_start_m'] + block['altitude_end_m']) / 2
            sink_rate = abs(block['avg_lift_sink_ms'])
            glide_data.append({
                'l_d': l_d,
                'altitude': avg_alt,
                'sink_rate': sink_rate,
                'distance': distance,
                'alt_loss': alt_loss,
                'duration': block['time_secs']
            })

    if not glide_data:
        return {
            'glide_count': 0,
            'best_glide_ratio': 0,
            'best_glide_alt': 0,
            'avg_glide_ratio': 0,
            'avg_glide_ratio_alt': 0,
            'avg_sink_rate': 0,
            'macready_optimal': 0,
            'cruise_efficiency': 0,
            'glide_polar': []
        }

    glide_data.sort(key=lambda x: x['l_d'], reverse=True)
    best = glide_data[0]

    avg_ld = round(stat.mean([g['l_d'] for g in glide_data]), 2)
    avg_alt = round(stat.mean([g['altitude'] for g in glide_data]), 1)
    avg_sink = round(stat.mean([g['sink_rate'] for g in glide_data]), 2)

    total_glide_dist = sum(g['distance'] for g in glide_data)
    total_glide_alt = sum(g['alt_loss'] for g in glide_data)
    overall_ld = round(total_glide_dist / total_glide_alt, 2) if total_glide_alt > 0 else 0

    thermals = [b for b in blocks if b['tyype'] == 'Climb']
    if thermals:
        avg_climb = stat.mean([t['avg_lift_sink_ms'] for t in thermals])
    else:
        avg_climb = 1.0

    macready = round(avg_climb, 2)

    glide_polar = sorted(glide_data, key=lambda x: x['sink_rate'])

    return {
        'glide_count': len(glide_data),
        'best_glide_ratio': best['l_d'],
        'best_glide_alt': int(best['altitude']),
        'best_glide_sink': best['sink_rate'],
        'avg_glide_ratio': avg_ld,
        'avg_glide_ratio_alt': avg_alt,
        'overall_glide_ratio': overall_ld,
        'avg_sink_rate': avg_sink,
        'macready_optimal': macready,
        'avg_climb_rate': round(avg_climb, 2),
        'cruise_efficiency': round(overall_ld / best['l_d'] * 100, 1) if best['l_d'] > 0 else 0,
        'glide_polar': glide_polar,
        'glide_blocks': glide_data
    }


# Core Functions ---------------------------------------------------------------------------|
def load_igc(in_igc_file):
    # File Parse Data
    # 0 123456 78901234 567890123 4 56789 01234 5678901234567890
    # R TTTTTT DDMMSSSC DDDMMSSSC V PPPPP GGGGG AAA SS NNN CRLF
    # B 050818 2801340N 08344054E A 01638 01639 001 10 002 3130139
    global alt_m
    f = open(in_igc_file, "r")
    lines = f.readlines()

    pilot: str = ""
    vario: str = ""
    glider: str = ""
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

    model_data = {}

    for i, line in enumerate(lines):
        if line[:5] == "HFPLT":  # xc tracer pilot data
            offset = 11
            if line[:19] == "HFPLTPILOTINCHARGE:":  # flymaster pilot data
                offset = 19
            pilot = line[offset:].replace("\n", "")

        if line[:12] == "HFFTYFRTYPE:":
            vario = line[12:].replace("\n", "").replace(",", " ")

        if line.startswith("HFGPS:"):
            vario += f", {line[6:]}".replace("\n", "")

        if line.startswith("HFGTYGLIDERTYPE:"):
            glider = line[16:].replace("\n", "")

        if line.startswith("HFDTEDATE:"):  # SeeYou Navigator
            raw_utc_date = line[10:].replace("\n", "").split(",")[0]
        elif line.startswith("HFDTE"):  # date info
            raw_utc_date = line[5:].replace("\n", "")

        elif line[0] == "B":  # data lines start with 'B'
            raw_time = line[1:7]

            lat_raw = line[7:14]
            lat = int(lat_raw[:2]) + float(lat_raw[2:]) / 60000
            ns = line[14]
            if ns == "S":
                lat = lat * -1

            lon_raw = line[15:23]
            lon = int(lon_raw[:3]) + float(lon_raw[3:]) / 60000
            ew = line[23]
            if ew == "W":
                lon = lon * -1

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

            # flight area calculation (only after takeoff is established, skip zero coords)
            if not takeoff_flag and lat != 0.0 and lon != 0.0:
                fa_dist = haversine((takeoff_lat, takeoff_lon), (lat, lon))
                if fa_dist > flight_area_km:
                    flight_area_km = fa_dist

            # List for kml path
            lon_lat_alt_list.append((lon, lat, alt_m))

            # Climb & Sink with averaging
            if int(raw_time[-2:]) % settings["averaging_factor"] == 0:
                if len(alt_readings) >= settings["averaging_factor"]:
                    climb_sink = calc_lift_sink(alt_readings)
                    if climb_sink > high_lift_m:
                        high_lift_m = climb_sink
                    elif climb_sink < high_sink_m:
                        high_sink_m = climb_sink
                    alt_readings = []
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

    # Final calcs & vars
    takeoff_to_land_dist = haversine((takeoff_lat, takeoff_lon), (last_lat, last_lon))
    takeoff_gps = (round(takeoff_lat, 5), round(takeoff_lon, 5))
    landing_gps = (round(last_lat, 5), round(last_lon, 5))

    # Landing Determination
    landing_dt = convert_hm_to_dt(raw_utc_date, raw_time)
    landing_heading = heading
    duration = (landing_dt - takeoff_dt).total_seconds()
    if duration < 0:
        duration = duration + (24 * 60 * 60)

    # ANALYSIS SECTION
    analysis = flight_analyzer(analysis_data, flight_area_km)
    glide_perf = analyze_glide_performance(analysis['details'], glider)
    thermals = None
    if analysis['flight_type'] != 'soaring':
        thermals = analyze_thermals(analysis['details'])

    # Weather Model Data
    model_data["takeoff_datetime"] = takeoff_dt
    model_data["landing_datetime"] = landing_dt
    model_data["duration"] = duration
    model_data["takeoff_gps"] = (takeoff_lat, takeoff_lon)
    model_data["landing_gps"] = (last_lat, last_lon)
    model_data["max_altitude"] = high_alt_m
    model_data["distance_total"] = total_distance_km
    model_data["takeoff_to_landing"] = takeoff_to_land_dist
    model_data["flight_area"] = flight_area_km

    # kml File Data
    kml_data = {"pilot": pilot,
                "filename": in_igc_file,
                "takeoff_gps": takeoff_gps,
                "landing_gps": landing_gps,
                "lon_lat_alt_list": lon_lat_alt_list,
                "details": analysis['details']}

    return {"filename": in_igc_file,
            "pilot": pilot,
            "vario": vario,
            "glider": glider,
            "flight_date": takeoff_dt,
            "max_alt": high_alt_m,
            "max_lift": high_lift_m,
            "max_sink": high_sink_m,
            "takeoff_datetime": format_timestamp(takeoff_dt),
            "takeoff_alt": takeoff_alt_m,
            "takeoff_gps": takeoff_gps,
            "takeoff_heading": takeoff_heading,
            "landing_datetime": format_timestamp(landing_dt),
            "landing_alt": landing_alt_m,
            "landing_gps": landing_gps,
            "landing_heading": landing_heading,
            "total_distance": round(total_distance_km, 1),
            "takeoff_to_land_dist": round(takeoff_to_land_dist, 1),
            "flight_area_diameter": round(flight_area_km, 2),
            "duration": duration,
            # Analysis Data
            "flight_type": analysis["flight_type"],
            "climbs_num": analysis["climbs_num"],
            "glides_num": analysis["glides_num"],
            "sinks_num": analysis["sinks_num"],
            "climb_grade": analysis["climb_grade"],
            "max_sustained_climb": analysis["max_sustained_climb"],
            "glide_grade": analysis["glide_grade"],
            "sink_grade": analysis["sink_grade"],
            "details": analysis["details"],
            "µ_sustained_climb": analysis["µ_sustained_climb"],
            "µ_sustained_glide": analysis["µ_sustained_glide"],
            "model_data": model_data,
            "lon_lat_alt_list": lon_lat_alt_list,
            # Glide, Thermal & kml Data
            "glide_perf": glide_perf,
            "thermals": thermals,
            "kml_data": kml_data}


def flight_analyzer(analysis_data, flight_area_km=0.0):
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
        if i > 0 and i % settings["averaging_factor"] == 0:
            chunks.append(temp)
            temp = []
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
    if not chunks:
        chunks = []
    temp = chunks[0] if chunks else []
    for i in range(1, len(chunk_cat)):
        if chunk_cat[i] == chunk_cat[i - 1]:
            temp = temp + chunks[i]
        else:
            # temp.sort(key=lambda x: x[0])
            blocks.append(temp)
            avg_ls = calc_lift_sink([x[3] for x in temp])
            blocks_cat.append((chunk_cat[i - 1], avg_ls))
            temp = chunks[i]

    if temp:
        blocks.append(temp)
        avg_ls = calc_lift_sink([x[3] for x in temp])
        blocks_cat.append((chunk_cat[-1], avg_ls))

    # Step 4: Analysis
    climbing_grades = []
    gliding_grades = []
    sinking_grades = []
    all_climb_rates = []

    for i, block in enumerate(blocks):
        if block != []:
            tyype = blocks_cat[i][0]
            altis = [x[3] for x in block]
            if tyype == "C":
                climb_rates = [float(t - s) for s, t in zip(altis, altis[1:])]
                all_climb_rates.extend(climb_rates)

    global_avg_climb = 0.0
    if all_climb_rates:
        try:
            sd_all = stat.stdev(all_climb_rates)
            mn_all = stat.mean(all_climb_rates)
            filtered_rates = [r for r in all_climb_rates if mn_all - 2 * sd_all <= r <= mn_all + 2 * sd_all]
            global_avg_climb = stat.mean(filtered_rates) if filtered_rates else stat.mean(all_climb_rates)
        except:
            global_avg_climb = stat.mean(all_climb_rates) if all_climb_rates else 0

    for i, block in enumerate(blocks):
        if block != []:
            tyype = blocks_cat[i][0]
            altis = [x[3] for x in block]
            if tyype == "C":
                efficiency = calculate_climb_efficiency(altis, global_avg_climb, settings["averaging_factor"])
                climbing_grades.append(efficiency)
            elif tyype == "G":  # glides analysis - Calc L/D & aggregate
                lift = abs(block[-1][3] - block[0][3])
                if lift == 0:
                    lift = 1
                distance = round(sum(x[5] for x in block) * 1000)
                l_over_d = round(distance / lift, 2)
                if l_over_d <= MAX_GLIDE_RATIO:
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
            if blocks_cat[i][0] == "G":
                lift = abs(block[-1][3] - block[0][3])
                if lift == 0:
                    lift = 1
                distance = round(sum(x[5] for x in block) * 1000)
                l_over_d = round(distance / lift, 2)
                block_detail["l_over_d"] = l_over_d if l_over_d <= MAX_GLIDE_RATIO else 0
            block_detail["loc_start"] = (block[0][1], block[0][2])
            block_detail["loc_end"] = (block[-1][1], block[-1][2])
            block_detail["total_distance_m"] = round(sum(x[5] for x in block) * 1000)

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

    circling_blocks = detect_circling(details)
    flight_type = 'soaring'  # default type
    if circling_blocks:
        total_circling_time = sum(b['time_secs'] for b in circling_blocks)
        total_time = sum(b['time_secs'] for b in details)
        if total_time > 0 and (total_circling_time / total_time) > 0.10:
            flight_type = 'xc' if flight_area_km > 8 else 'thermal'  # 8k/5mi between thermal and XC types

    if flight_type == 'soaring':
        total_time = sum(b['time_secs'] for b in details)
        climb_time = sum(b['time_secs'] for b in details if b['tyype'] == 'Climb')
        climb_ratio = climb_time / total_time if total_time > 0 else 0

        climb_rates = [b['avg_lift_sink_ms'] for b in details if b['tyype'] == 'Climb']
        avg_climb = stat.mean(climb_rates) if climb_rates else 0

        sink_time = sum(b['time_secs'] for b in details if b['tyype'] == 'Sink')
        sink_ratio = sink_time / total_time if total_time > 0 else 0

        time_score = min(climb_ratio / 0.5, 1.0)
        strength_score = min(avg_climb / 2.0, 1.0)
        sink_score = max(1.0 - sink_ratio * 2, 0.0)

        efficiency = time_score * 0.35 + strength_score * 0.35 + sink_score * 0.30
        climb_grade = round(efficiency * 100, 2)

    analysis_data = {"climbs_num": len(climbing_grades),
                     "glides_num": len(gliding_grades),
                     "sinks_num": len(sinking_grades),
                     "climb_grade": climb_grade,
                     "glide_grade": glide_grade,
                     "sink_grade": sink_grade,
                     "µ_sustained_climb": avg_sustained_climb,
                     "µ_sustained_glide": avg_sustained_glide,
                     "max_sustained_climb": max_sustained_climb,
                     "flight_type": flight_type,
                     "details": details}

    return analysis_data


def analyze_file(igc_file):
    # Load & Analyze the file
    results = load_igc(igc_file)

    # OPTION: CLI Display
    from display import display_summary_stats
    display_summary_stats(results)

    # OPTION: Create kml File
    from kmls import create_enhanced_kml
    kml_result = create_enhanced_kml(results['kml_data'])

    # End Email/Analysis Text
    print("\n\nAnalysis Complete - KML file for Google Earth attached.")
    print("Thanks for using the WanderBot IGC analyzer.")
    print("\n\tBlue skies!!\n\tWander Expeditions LLC")


# if __name__ == '__main__':
#     # Specify the file
#     igc_file = 'SB-HSB.igc'
#     analyze_file(igc_file)
