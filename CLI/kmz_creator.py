import os
from math import radians, cos, sin, sqrt, asin


def haversine(loc1, loc2):
    lat1, lon1, lat2, lon2 = map(radians, [loc1[0], loc1[1], loc2[0], loc2[1]])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6372.8
    return c * r


def create_enhanced_kmz(kmz_data):
    out_file = f"KMZs/{kmz_data['filename']}.kmz"
    if not os.path.exists("KMZs"):
        os.makedirs("KMZs")
    if os.path.exists(out_file):
        os.remove(out_file)

    colors = {
        "climb_yellow": "ff00ffff",
        "climb_orange": "ff0080ff",
        "glide_green": "ff00ff00",
        "sink_red": "ff0000ff",
        "max_alt": "ffff0000"
    }

    lon_lat_alt_list = kmz_data.get("lon_lat_alt_list", [])
    details = kmz_data.get("details", [])
    takeoff_gps = kmz_data.get("takeoff_gps", None)
    landing_gps = kmz_data.get("landing_gps", None)

    altis = [int(x[2]) for x in lon_lat_alt_list if int(x[2]) > 0]
    if not altis:
        return

    sorted_altis = sorted(altis)
    n = len(sorted_altis)
    q1 = sorted_altis[int(n * 0.25)]
    q2 = sorted_altis[int(n * 0.50)]
    q3 = sorted_altis[int(n * 0.75)]

    alt_thresholds = {
        'green': q1,
        'yellow': q2,
        'orange': q3
    }

    colors = {
        "climb_green": "ff00ff00",
        "climb_yellow": "ff00ffff",
        "climb_orange": "ff0080ff",
        "climb_red": "ffff0000",
        "glide_green": "ff00ff00",
        "sink_red": "ffff0000"
    }

    thermals = detect_thermals(details)
    climb_blocks = [b for b in details if b['tyype'] == 'Climb']

    block_index = 0
    coordinates = []
    for i, coord in enumerate(lon_lat_alt_list):
        alti = coord[2]
        block = find_block_for_altitude(coord, climb_blocks)
        if block:
            if alti >= alt_thresholds['orange']:
                color = "climb_red"
            elif alti >= alt_thresholds['yellow']:
                color = "climb_orange"
            elif alti >= alt_thresholds['green']:
                color = "climb_yellow"
            else:
                color = "climb_green"
        else:
            block = find_block_for_altitude(coord, [b for b in details if b['tyype'] == 'Sink'])
            if block:
                color = "sink_red"
            else:
                if alti >= alt_thresholds['orange']:
                    color = "climb_red"
                elif alti >= alt_thresholds['yellow']:
                    color = "climb_orange"
                elif alti >= alt_thresholds['green']:
                    color = "climb_yellow"
                else:
                    color = "glide_green"
        coordinates.append((coord[0], coord[1], coord[2], color))

    f = open(out_file, "a")
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<kml xmlns="http://www.opengis.net/kml/2.2"\n')
    f.write('     xmlns:gx="http://www.google.com/kml/ext/2.2">\n')
    f.write('<Document>\n')
    f.write(f'<name>{kmz_data["pilot"]} - Flight Analysis</name>\n')
    f.write('<description>Flight path colored by phase: Green=Glide, Yellow/Orange=Climb, Red=Sink</description>\n')

    f.write('<Style id="takeoffIcon">\n')
    f.write('<IconStyle><color>ff00ff00</color><scale>1.5</scale>')
    f.write('<Icon><href>http://maps.google.com/mapfiles/kml/paddle/grn-circle.png</href></Icon></IconStyle>\n')
    f.write('</Style>\n')

    f.write('<Style id="landingIcon">\n')
    f.write('<IconStyle><color>ffff0000</color><scale>1.5</scale>')
    f.write('<Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href></Icon></IconStyle>\n')
    f.write('</Style>\n')

    f.write('<Style id="thermalIcon">\n')
    f.write('<IconStyle><color>ff0080ff</color><scale>1.2</scale>')
    f.write('<Icon><href>http://maps.google.com/mapfiles/kml/shapes/circle.png</href></Icon></IconStyle>\n')
    f.write('</Style>\n')

    for i, thermal in enumerate(thermals, 1):
        f.write('<Placemark>\n')
        f.write(f'<name>Thermal #{i}</name>\n')
        f.write(f'<description>Strength: {thermal["strength"]:.1f} m/s, Alt: {thermal["alt_start"]}-{thermal["alt_end"]}m</description>\n')
        f.write('<styleUrl>#thermalIcon</styleUrl>\n')
        f.write('<Point>\n')
        f.write(f'<coordinates>{thermal["lon"]},{thermal["lat"]},0</coordinates>\n')
        f.write('</Point>\n')
        f.write('</Placemark>\n')

    if takeoff_gps:
        f.write('<Placemark>\n')
        f.write('<name>Takeoff</name>\n')
        f.write('<description>Flight departure point</description>\n')
        f.write('<styleUrl>#takeoffIcon</styleUrl>\n')
        f.write('<Point>\n')
        f.write(f'<coordinates>{takeoff_gps[1]},{takeoff_gps[0]},0</coordinates>\n')
        f.write('</Point>\n')
        f.write('</Placemark>\n')

    if landing_gps:
        f.write('<Placemark>\n')
        f.write('<name>Landing</name>\n')
        f.write('<description>Flight arrival point</description>\n')
        f.write('<styleUrl>#landingIcon</styleUrl>\n')
        f.write('<Point>\n')
        f.write(f'<coordinates>{landing_gps[1]},{landing_gps[0]},0</coordinates>\n')
        f.write('</Point>\n')
        f.write('</Placemark>\n')

    segment_count = 0
    block = []
    last_color = coordinates[0][3] if coordinates else "glide_green"
    for i, coord in enumerate(coordinates):
        current_color = coord[3]
        if current_color == last_color:
            block.append(f"{coord[0]},{coord[1]},{coord[2]}")
        else:
            if block:
                segment_count += 1
                color_name = get_color_name(last_color)
                f.write(f'<Placemark id="segment_{segment_count}">\n')
                f.write(f'<name>{color_name}</name>\n')
                f.write('<Snippet maxLines="0"></Snippet>\n')
                f.write('<Style>\n')
                f.write('<LineStyle>\n')
                f.write(f'<color>{colors.get(last_color, "ff00ff00")}</color>\n')
                f.write('<width>4</width>\n')
                f.write('</LineStyle>\n')
                f.write('</Style>\n')
                f.write('<LineString>\n')
                f.write('<extrude>0</extrude>\n')
                f.write('<tessellate>1</tessellate>\n')
                f.write('<altitudeMode>absolute</altitudeMode>\n')
                f.write('<coordinates>\n')
                f.write(' '.join(block) + '\n')
                f.write('</coordinates>\n')
                f.write('</LineString>\n')
                f.write('</Placemark>\n')
            last_color = current_color
            block = [f"{coord[0]},{coord[1]},{coord[2]}"]

    if block:
        segment_count += 1
        color_name = get_color_name(last_color)
        f.write(f'<Placemark id="segment_{segment_count}">\n')
        f.write(f'<name>{color_name}</name>\n')
        f.write('<Snippet maxLines="0"></Snippet>\n')
        f.write('<Style>\n')
        f.write('<LineStyle>\n')
        f.write(f'<color>{colors.get(last_color, "ff00ff00")}</color>\n')
        f.write('<width>4</width>\n')
        f.write('</LineStyle>\n')
        f.write('</Style>\n')
        f.write('<LineString>\n')
        f.write('<extrude>0</extrude>\n')
        f.write('<tessellate>1</tessellate>\n')
        f.write('<altitudeMode>absolute</altitudeMode>\n')
        f.write('<coordinates>\n')
        f.write(' '.join(block) + '\n')
        f.write('</coordinates>\n')
        f.write('</LineString>\n')
        f.write('</Placemark>\n')

    f.write('<Folder>\n')
    f.write('<name>Legend</name>\n')
    f.write('<description>Altitude quantile color legend</description>\n')
    f.write(f'<Placemark><name>Green - Lower 25%</name><description>Altitude below {q1}m (25th percentile)</description></Placemark>\n')
    f.write(f'<Placemark><name>Yellow - 25-50%</name><description>Altitude {q1}-{q2}m (25th-50th percentile)</description></Placemark>\n')
    f.write(f'<Placemark><name>Orange - 50-75%</name><description>Altitude {q2}-{q3}m (50th-75th percentile)</description></Placemark>\n')
    f.write(f'<Placemark><name>Red - Top 25%</name><description>Altitude above {q3}m (75th-100th percentile)</description></Placemark>\n')
    f.write('</Folder>\n')

    f.write('</Document>\n')
    f.write('</kml>\n')
    f.close()
    print(f"  Enhanced KMZ saved to: {out_file}")


def get_color_name(color_key):
    names = {
        "climb_green": "Green - Lower 25%",
        "climb_yellow": "Yellow - 25-50%",
        "climb_orange": "Orange - 50-75%",
        "climb_red": "Red - Top 25%",
        "glide_green": "Green - Glide",
        "sink_red": "Red - Sink"
    }
    return names.get(color_key, "Track")


def find_block_for_altitude(coord, blocks):
    for block in blocks:
        loc = block.get('loc_start', (0, 0))
        loc_end = block.get('loc_end', (0, 0))
        lat, lon = coord[1], coord[0]
        if (min(loc[0], loc_end[0]) <= lat <= max(loc[0], loc_end[0]) and
            min(loc[1], loc_end[1]) <= lon <= max(loc[1], loc_end[1])):
            return block
    return None


def detect_thermals(details, min_alt_gain=50):
    thermals = []
    for block in details:
        if block['tyype'] == 'Climb' and block['time_secs'] >= 20:
            alt_gain = block['altitude_end_m'] - block['altitude_start_m']
            if alt_gain >= min_alt_gain:
                start_loc = block['loc_start']
                end_loc = block['loc_end']
                distance = haversine(start_loc, end_loc) * 1000
                if distance < 500:
                    thermals.append({
                        'lat': start_loc[0],
                        'lon': start_loc[1],
                        'strength': block['avg_lift_sink_ms'],
                        'alt_start': block['altitude_start_m'],
                        'alt_end': block['altitude_end_m'],
                        'duration': block['time_secs']
                    })
    return thermals


def detect_turnpoints(details):
    turnpoints = []
    for i, block in enumerate(details):
        if i > 0 and i < len(details) - 1:
            prev = details[i - 1]
            next_block = details[i + 1]
            if (prev['tyype'] == 'Glide' and block['tyype'] == 'Climb' and next_block['tyype'] == 'Glide'):
                if abs(block['avg_lift_sink_ms'] - max(d['avg_lift_sink_ms'] for d in details if d['tyype'] == 'Climb')) < 0.5:
                    turnpoints.append({
                        'lat': block['loc_start'][0],
                        'lon': block['loc_start'][1],
                        'strength': block['avg_lift_sink_ms']
                    })
    return turnpoints
