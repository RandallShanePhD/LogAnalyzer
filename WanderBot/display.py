# CLI Display Functions
import datetime as dt
from base import settings
from base import convert_meters_to_feet, convert_km_to_miles, convert_ms_to_fpm, haversine


def efficiency_grade_lookup(grade_num, flight_type='thermal'):
    if flight_type == 'soaring':
        if grade_num >= 90:
            return "Exceptional. Masterful ridge running — you stayed in the lift band\n almost the entire flight with minimal sink."
        elif grade_num >= 75:
            return "Excellent. Strong ridge reading — you found consistent lift and\n maintained altitude well along the terrain."
        elif grade_num >= 64:
            return "Good. Solid soaring — you're staying in lift most of the time,\n but there are stretches where you drift out of the band."
        elif grade_num >= 45:
            return "Average. Functional ridge flight — some time in lift, some time\n sinking. Look for better terrain features to work."
        elif grade_num >= 30:
            return "Below Average. Significant time out of the lift band. Try staying\n tighter to the ridge and reading the wind direction better."
        else:
            return "Poor. Struggling to stay in lift. Focus on identifying where the\n wind hits the ridge and staying in the rising air."
    elif flight_type == 'xc':
        if grade_num >= 90:
            return "Exceptional. Elite cross-country performance — efficient climbs,\n tight glides, and excellent route selection."
        elif grade_num >= 75:
            return "Excellent. Strong XC technique — well-centered climbs and\n efficient glides between thermals."
        elif grade_num >= 64:
            return "Good. Solid XC flying — you're making progress and finding lift\n consistently, but polish your transitions."
        elif grade_num >= 45:
            return "Average. Functional XC flight — managing climbs and glides but\n losing efficiency in transitions or off-core."
        elif grade_num >= 30:
            return "Below Average. Significant time in sink or struggling to connect\n climbs. Work on glide speed and thermal entry."
        else:
            return "Poor. Difficult flight — struggling to stay up or make progress.\n Review weather conditions and route planning."
    else:  # thermal
        if grade_num >= 90:
            return "Exceptional. Near-perfect thermal centering. You're consistently in\n the core, smooth and steady. Rare even for experienced pilots."
        elif grade_num >= 75:
            return "Excellent. Strong thermal technique. Well-centered climbs, minimal\n drift into sink, good reactions to lift changes."
        elif grade_num >= 64:
            return "Good. Solid flying. You're finding lift and making progress, but\n there's room to tighten your circles or react faster."
        elif grade_num >= 45:
            return "Average. Functional but inconsistent. Some time in core, some time\n drifting. Typical for newer pilots or marginal conditions."
        elif grade_num >= 30:
            return "Below Average. Significant time in sink or off-center. Lift is being\n found but not maximized."
        else:
            return "Poor. Struggling to find or stay in lift. Lots of altitude loss within\n climbs, poor centering, or very weak/active conditions."


def display_details(details):
    for detail in details:
        altitude_change = detail['altitude_end_m'] - detail['altitude_start_m']
        print(
            f" Block Number: {detail['number']}   Block Type: {detail['tyype']}   Time in Secs: {detail['time_secs']}")
        print(
            f"  Altitude Start: {detail['altitude_start_m']}m | {convert_meters_to_feet(detail['altitude_start_m'])}ft   End: {detail['altitude_end_m']}m | {convert_meters_to_feet(detail['altitude_end_m'])}ft")
        print(
            f"  Change in Altitude: {altitude_change}m | {convert_meters_to_feet(altitude_change)}ft   µ Lift: {detail['avg_lift_sink_ms']}m/s | {convert_ms_to_fpm(detail['avg_lift_sink_ms'])}ft/min")
        print(f"  Location Start: {detail['loc_start']}   End: {detail['loc_end']}")
        distance = round(haversine(detail['loc_start'], detail['loc_end']) * 1000)
        print(
            f"  Distance Start-End: {distance}m | {convert_meters_to_feet(distance)}ft   Distance Total: {detail['total_distance_m']}m | {convert_meters_to_feet(detail['total_distance_m'])}ft")
        print(" - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -")


def display_glide_analysis(s):
    stats = s["glide_perf"]
    print(f"  Segments Analyzed: {stats['glide_count']}")
    if stats['glide_count'] == 0:
        print("  No glide segments found for analysis")
        print("\n  return to continue")
        input()
        return

    print(f"\n  BEST GLIDE:")
    print(f"    Glide Ratio: {stats['best_glide_ratio']}:1")
    print(f"    Altitude: {stats['best_glide_alt']} m || {convert_meters_to_feet(stats['best_glide_alt'])} ft")
    print(f"    Sink Rate: {stats['best_glide_sink']} m/s")

    print(f"\n  AVERAGE GLIDE:")
    print(f"    Glide Ratio: {stats['avg_glide_ratio']}:1")
    print(
        f"    Average Altitude: {stats['avg_glide_ratio_alt']} m || {convert_meters_to_feet(stats['avg_glide_ratio_alt'])} ft")
    print(f"    Average Sink Rate: {stats['avg_sink_rate']} m/s || {convert_ms_to_fpm(stats['avg_sink_rate'])} fpm")
    print(f"    Overall Glide Ratio: {stats['overall_glide_ratio']}:1")

    print(f"\n  SPEED-TO-FLY (MacReady):")
    print(f"    Optimal MacReady Setting: {stats['macready_optimal']} m/s || {convert_ms_to_fpm(stats['macready_optimal'])} fpm")

    if s['duration'] > 3600:
        hours = s['duration'] / 3600
        avg_kph = round(s['total_distance'] / hours, 1)
        avg_mph = round(convert_km_to_miles(avg_kph), 1)
        print(f"    Average Speed: {avg_kph} km/h || {avg_mph} mph")

    print(f"    Average Climb Rate: {stats['avg_climb_rate']} m/s || {convert_ms_to_fpm(stats['avg_climb_rate'])} fpm")
    print(f"    Cruise Efficiency: {stats['cruise_efficiency']}%")

    print(f"\n  INTERPRETATION:")
    if stats['cruise_efficiency'] > 90:
        print(f"    Excellent cruise efficiency - consistent glide performance")
    elif stats['cruise_efficiency'] > 75:
        print(f"    Good cruise efficiency")
    else:
        print(f"    Consider optimizing cruise speed for conditions")

    print("\n" + "-" * 60)
    print("Top 5 Glides by L/D:")
    print("-" * 60)
    for i, g in enumerate(stats['glide_blocks'][:5], 1):
        print(
            f"  #{i}: L/D {g['l_d']}:1 | Alt {int(g['altitude'])}m | Sink {g['sink_rate']} m/s | Dist {int(g['distance'])}m")

    print("\nPolar Glide Curve (sink rate vs glide ratio):")
    print("-" * 40)
    print(f"  {'Sink (m/s)':<12} {'L/D':<8} {'Alt (m)':<10}")
    print("-" * 40)
    shown = set()
    for target in range(5, 16):
        best = min(stats['glide_polar'], key=lambda g: abs(g['l_d'] - target))
        key = (best['sink_rate'], best['l_d'], best['altitude'])
        if key not in shown:
            shown.add(key)
            print(f"  {best['sink_rate']:<12.2f} {best['l_d']:<8.2f} {int(best['altitude']):<10}")
        if len(shown) >= 10:
            break


def display_thermal_analysis(s):
    thermals = s["thermals"]
    print(f"\n  Thermal Count: {thermals['thermal_count']}")
    if thermals['thermal_count'] == 0:
        print("  No thermals detected (no circling behavior found)")
        print("\n  return to continue")
        input()
        return

    print(f"  Average Thermal Strength: {thermals['avg_thermal_strength']} m/s || {convert_ms_to_fpm(thermals['avg_thermal_strength'])} fpm")
    print(f"  Max Thermal Strength: {thermals['max_thermal_strength']} m/s || {convert_ms_to_fpm(thermals['max_thermal_strength'])} fpm")
    print(f"  Min Thermal Strength: {thermals['min_thermal_strength']} m/s || {convert_ms_to_fpm(thermals['min_thermal_strength'])} fpm")
    print(f"  Average Thermal Duration: {thermals['avg_thermal_duration']} seconds")
    print(f"  Total Time in Thermals: {thermals['total_thermal_time']} seconds ({thermals['thermal_time_pct']}% of flight)")
    print(f"  Average Altitude Gain per Thermal: {thermals['avg_alt_gain']} m || {convert_meters_to_feet(thermals['avg_alt_gain'])} ft")
    print(f"  Total Altitude Gained in Thermals: {thermals['total_alt_gain']} m || {convert_meters_to_feet(thermals['total_alt_gain'])} ft")

    for i, thermal in enumerate(thermals['circling_blocks'], 1):
        alt_gain = thermal['altitude_end_m'] - thermal['altitude_start_m']
        print(f"\n  Thermal #{i}:")
        print(f"    Duration: {thermal['time_secs']}s | Strength: {thermal['avg_lift_sink_ms']} m/s ({convert_ms_to_fpm(thermal['avg_lift_sink_ms'])} fpm)")
        print(f"    Altitude: {thermal['altitude_start_m']} m -> {thermal['altitude_end_m']} m (gain: {alt_gain}m)")
        print(f"              {convert_meters_to_feet(thermal['altitude_start_m'])} ft -> {convert_meters_to_feet(thermal['altitude_end_m'])} ft (gain: {convert_meters_to_feet(alt_gain)} ft)")
        print(f"    Location: {thermal['loc_start']}")


def display_summary_stats(s):
    """
        The efficiency score (0-100%) is a weighted composite of four factors:
        - Net Efficiency (35%): Actual altitude gain vs. expected gain based on global average climb rate
        - Consistency Score (25%): Lower variance in climb rates scores higher (penalizes bobbing)
        - Sustained Ratio (25%): Percentage of readings maintaining ≥50% of average climb rate
        - Positive Steps (15%): Percentage of readings showing any altitude gain
        This rewards smooth, consistent climbs with minimal altitude loss, sustained lift rather than
        intermittent bobbing, and optimal thermal centering.
        """

    formatted_date = dt.datetime.strftime(s['flight_date'], "%d %b %Y")
    formatted_duration = str(dt.timedelta(seconds=s["duration"]))

    print("\nFLIGHT:")
    print(f"  File: {s['filename']}")
    print(f"  Pilot: {s['pilot']}")
    print(f"  Glider: {s['glider']}")
    print(f"  Vario: {s['vario']}")
    print("\n========================================================================")
    print("STATISTICS:")
    print(f"  Date: {formatted_date}")
    print(f"  Duration: {formatted_duration}")
    print(f"  Flight Type: {s['flight_type']}")
    print(f"  Takeoff GPS: {s['takeoff_gps']}")
    print(f"  Takeoff DateTime: {s['takeoff_datetime']}")
    print(f"  Takeoff Altitude: {s['takeoff_alt']} m || {convert_meters_to_feet(s['takeoff_alt'])} ft")
    print(f"  Takeoff Heading: {s['takeoff_heading']}°")
    print(f"  Landing GPS: {s['landing_gps']}")
    print(f"  Landing DateTime: {s['landing_datetime']}")
    print(f"  Landing Altitude: {s['landing_alt']} m || {convert_meters_to_feet(s['landing_alt'])} ft")
    print(f"  Landing Heading: {s['landing_heading']}°")
    print(f"  Distance Total: {s['total_distance']} km || {convert_km_to_miles(s['total_distance'])} mi")
    print(f"  Flight Area Diameter: {s['flight_area_diameter']} km || {convert_km_to_miles(s['flight_area_diameter'])} mi")
    print(f"  Takeoff to Landing: {s['takeoff_to_land_dist']} km || {convert_km_to_miles(s['takeoff_to_land_dist'])} mi")
    print(f"  Max Altitude: {s['max_alt']} m || {convert_meters_to_feet(s['max_alt'])} ft")
    print(f"  Max Lift: {s['max_lift']} m/s || {convert_ms_to_fpm(s['max_lift'])} ft/min")
    print(f"  Max Sink: {s['max_sink']} m/s || {convert_ms_to_fpm(s['max_sink'])} ft/min")
    print("\n========================================================================")
    print("OVERVIEW:")
    print(f"  Climbs - Number of Climbs: {s['climbs_num']}")
    print(f"  Climbs - Max Sustained m/s: {s['max_sustained_climb']} || {convert_ms_to_fpm(s['max_sustained_climb'])} fpm")
    print(f"  Climbs - µ Sustained: {s['µ_sustained_climb']} m/s || {convert_ms_to_fpm(s['µ_sustained_climb'])} fpm")
    print(f"  Glides - Number of Glides: {s['glides_num']}")
    print(f"  Glides - µ Sustained: {s['µ_sustained_glide']} m/s || {convert_ms_to_fpm(s['µ_sustained_glide'])} fpm")
    print(f"  Glides - µ L/D on Glide: {s['glide_grade']}:1")
    print(f"  Sinks - Number of Sinks (> {settings['sink_descend_threshold']} m/s | 500fpm): {s['sinks_num']}")
    print(f"  Sinks - µ Sink Rate: {s['sink_grade']} m/s || {convert_ms_to_fpm(s['sink_grade'])} fpm")
    climb_ratio = round(
        s['climbs_num'] / (s['climbs_num'] + s['glides_num'] + s['sinks_num']) * 100, 2)
    print(f"  You are climbing {climb_ratio}% of the flight")
    glide_ratio = round(
        s['glides_num'] / (s['climbs_num'] + s['glides_num'] + s['sinks_num']) * 100, 2)
    print(f"  You are gliding {glide_ratio}% of the flight")
    sink_ratio = round(
        s['sinks_num'] / (s['climbs_num'] + s['glides_num'] + s['sinks_num']) * 100, 2)
    print(f"  You are sinking {sink_ratio}% of the flight")
    print("\n========================================================================\nFLIGHT TYPE: " + s.get('flight_type', 'thermal').upper())
    print(f"EFFICIENCY GRADE ({s.get('flight_type', 'thermal').upper()}): {s['climb_grade']}%")
    narative = efficiency_grade_lookup(s['climb_grade'], s.get('flight_type', 'thermal'))
    print(f"\t{narative}")
    print("\n========================================================================")
    print("DETAILED FLIGHT INSPECTION OF BLOCKS OVER 90 SECONDS LONG")
    print("  (all blocks zipped and attached)\n")
    large_blocks = [x for x in s["details"] if x['time_secs'] > 90]
    display_details(large_blocks)

    print("\n========================================================================")
    print("GLIDE PERFORMANCE ANALYSIS")
    display_glide_analysis(s)

    if s['flight_type'] != 'soaring':
        print("\n========================================================================")
        print("THERMAL ANALYSIS")
        display_thermal_analysis(s)

    # TODO: validate kmz file creator
    kmz_data = {
        "pilot": s['pilot'],
        "filename": s['filename'][:-4],
        "takeoff_gps": s['takeoff_gps'],
        "landing_gps": s['landing_gps'],
        "lon_lat_alt_list": s.get('lon_lat_alt_list', []),
        "details": s['details']
    }
    # create_kmz(kmz_data)