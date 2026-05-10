# Base Functions
import datetime
import datetime as dt

from math import asin, atan2, degrees, cos, radians, sin, sqrt

# Constants -------------------------------------/
settings = {"averaging_factor": 10,
            "climb_ascend_threshold": 0.5,
            "sink_descend_threshold": 2.5,
            "kmz_speed_units": "kmh"}


# Helper & Conversion Functions ---------------------------------------------------|
def convert_hm_to_dt(raw_date, raw_time):
    raw_date = raw_date.replace("DATE:", "")  # flymaster encoding
    dt_string = f"{raw_date} {raw_time}"
    return dt.datetime.strptime(dt_string, '%d%m%y %H%M%S')


def convert_meters_to_feet(meters: int):
    return int(round(float(meters) * 3.28084))


def convert_km_to_miles(km: float):
    return round(km * 0.6213712, 1)


def convert_ms_to_fpm(ms: float):
    return round(ms * 196.8504)


def format_timestamp(ts: datetime):
    formated = f"{ts.date().year}-{ts.date().month}-{ts.date().day} {ts.time().hour}:{ts.time().minute}:{ts.time().second}"
    return formated


def haversine(loc1, loc2):
    """ loc is a (lat, lon) tuple

    REFERENCE: GPS & Decimal places
    100s = non zero = longitude
    10s = 1000km
    1s = 111km/90km (lat 69 miles, lon 56.51 miles)
    1s diagonal = 144km or 89 miles
    1 decimal = 11.1km
    2 decimals = 1.1km
    3 decimals = 110m
    4 decimals = 11m
    5 decimals = 1.1m
    6 decimals = 11cm
    7 decimals = 1.1cm (surveying, limit of GPS tech)
    """
    lat1, lon1, lat2, lon2 = map(radians, [loc1[0], loc1[1], loc2[0], loc2[1]])
    dlon = (lon2 - lon1)
    dlat = (lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
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
