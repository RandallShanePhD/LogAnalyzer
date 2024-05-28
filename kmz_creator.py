import os

def create_kmz(kmz_data):
    out_file = f"KMZs/{kmz_data['filename']}.kmz"
    if os.path.exists(out_file):
        os.remove(out_file)

    # breakpoints for highlighting in m
    highlight = {}
    colors = {"yellow": "ff00ffff",
              "orange": "ff0080ff",
              "red": "ff0000ff"}

    names = {"yellow": "Low",
              "orange": "Medium",
              "red": "High"}

    altis = [int(x[2]) for x in kmz_data["lon_lat_alt_list"] if int(x[2]) > 0]

    # GEarth Relativity Correction
    start_alti = altis[0]
    altis = [x - start_alti for x in altis]

    max_alti = max(altis)
    min_alti = min(altis)
    diff = (max_alti - min_alti) / 4
    highlight[int(min_alti + (diff * 2))] = "yellow"
    highlight[int(min_alti + (diff * 3))] = "orange"
    highlight[int(min_alti + (diff * 4)) - 10] = "red"

    # Color code the Coordinates
    def color_alti(alti):
        color = "yellow"
        for h_alti in highlight:
            if alti > h_alti:
                color = highlight[h_alti]
        return color

    coordinates = []
    for coord in kmz_data["lon_lat_alt_list"]:
        alti = coord[2] - start_alti  # alti correction added
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
            # KMZ Data
            f.write(f'<Placemark id = "ID_0{i}">\n')  # ID number
            f.write(f'<name>{names[current_color]} Track</name>\n')  # track name
            f.write(f'<description> {current_color} line section </description>\n')  # description
            f.write('<Snippet maxLines="0"></Snippet>\n')
            f.write('<Style>\n')
            f.write('<LineStyle>\n')
            f.write(f'<color>{colors[current_color]}</color>\n')  # color
            f.write('<width>3</width>\n')  # line thickness
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
            last_color = current_color
            block = []

    # Write File Tail
    f.write('</Document>\n')
    f.write('</kml>\n')
    f.close()