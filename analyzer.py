#!/usr/bin/python3
import datetime as dt
import sys

from math import radians, cos, sin, asin, sqrt

# Helper Functions ---------------------------/
def calc_lift_sink(altitudes: [float]) -> float:
    meters_per_second = 0.00
    last_altitude = float(altitudes[0])
    total_altitude = 0.00
    factors = 0.00
    for altitude in altitudes:
        if altitude != last_altitude:
            factors += 1
            total_altitude += altitude
            meters_per_second += (altitude - last_altitude)
            last_altitude = altitude

    alt_average = meters_per_second / factors
    return alt_average


def convert_hm_to_dt(raw_date, raw_time):
    dt_string = f"{raw_date} {raw_time}"
    return dt.datetime.strptime(dt_string, '%d%m%y %H%M%S')


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r


# Operational Functions -----------------------/
def instructions():
    # Optional
    # file = sys.argv[1]
    # print(f"File: {file}")
    print("-------------------------------------")
    print("--   IGC Log File Analyzer         --")
    print("--   Wander Expeditions LLC        --")
    print("--   v2023-03                      --")
    print("--   Randall Shane PhD             --")
    print("--   Randall@WanderExpeditions.com --")
    print("--   ENJOY, THIS IS FREE SOFTWARE! --")
    print("-------------------------------------\n")
    print("Instructions:")
    print("1) Place your IGC file in this directory")
    print("2) Type the filename in exactly as you see it")
    filename = input(">")
    return filename


def load_igc(in_igc_file):
    f = open(in_igc_file, "r")
    lines = f.readlines()

    for line in lines:
        print(line, end="")
        raw_utc_date = None
        raw_time: None
        last_lat: float = 0.00
        last_lon: float = 0.00
        takeoff_dt: float = 0.00
        takeoff_lat: float = 0.00
        takeoff_lon: float = 0.00
        takeoff_alt_m: float = 0.00  # meters
        alt_readings: float = []
        high_alt_m: int = 0
        high_lift_m: float = 0.00
        high_sink_m: float = 0.00
        dist_total: float = 0.00

        if line[:5] ==  "HFDTE":
            raw_utc_date = line[5:]

        elif line[0] == "B":

            raw_time = line[1:7]
            lat = float(line[7:14]) / 100000.00
            ns = line[14]
            if ns == "S":
                lat = lat * -1

            lon = float(line[15:22]) / 100000.00
            ew = line[23]
            if ew == "W":
                lon = lon * -1

        # 0 123456 78901234 567890123 4 56789 01234 5678901234567890
        # R TTTTTT DDMMMMMC DDDMMMMMC V PPPPP GGGGG AAA SS NNN CR LF
        # B 063038 2801415N 08344016E A 01625 01625 001100001205050

            # altitude, lift & sink
            alt_m = int(line[25:30])  # pressure altitude
            if alt_m == 0:
                alt_m = int(line[30:35])  # gps altitude

            averaging_factor = 5

            if int(raw_time) % averaging_factor == 0:
                if len(alt_readings) > averaging_factor:
                    climb_sink = calc_lift_sink(alt_readings)
                    if climb_sink > high_lift_m:
                        high_lift_m = climb_sink
                    elif climb_sink < high_sink_m:
                        high_sink_m = climb_sink
                    alt_readings =[]
                else:
                    alt_readings.append(float(alt_m))

                # distance & times
                if last_lat == 0.00 and lat > 0.00:
                    takeoff_lat = lat
                    takeoff_lon = lon
                    takeoff_dt = convert_hm_to_dt(raw_utc_date, raw_time)
                    takeoff_alt_m = alt_m
                elif last_lat > 0:
                    dist_km = haversine(last_lon, last_lat, lon, lat)
                    dist_total += abs(dist_km)

                # set values
                last_lat = lat
                last_lon = lon
                if alt_m > high_alt_m:
                    high_alt_m = alt_m

    distFromTakeoff = haversine(takeoff_lon, takeoff_lat, last_lon, last_lat)

    # duration
    landing_dt = convert_hm_to_dt(raw_utc_date, raw_time)
    # flight_duration = landingDT.timeIntervalSince(takeoffDT)
    #if flightDuration < 0  {
    #flightDuration = flightDuration + (24 * 60 * 60)


def write_file(outfile):
    text = ['Welcome to datagy.io!', "Let's learn some Python!"]

    with open('/Users/nikpi/Desktop/textfile.txt', 'w') as f:
        for line in text:
            f.write(line)
            f.write('\n')


if __name__ == '__main__':
    in_file = instructions()
    in_file = "2023-02-27-XFH-000-01.IGC"
    load_igc(in_file)