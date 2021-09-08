import re


def knots_to_cat(wind_speed):
    """Converts wind speed in knots to equivalent tropical cyclone category
    based on Saffir-Simpson scale

    Input:
    wind_speed (int) -- wind speed in knots

    Output:
    cat (str) -- TC category
    """
    if wind_speed != wind_speed:
        return ""
    cat = ""
    if wind_speed < 15:
        cat = ""
    elif wind_speed <= 33:
        cat = "TD"
    elif wind_speed <= 63:
        cat = "TS"
    elif wind_speed <= 82:
        cat = "1"
    elif wind_speed <= 95:
        cat = "2"
    elif wind_speed <= 112:
        cat = "3"
    elif wind_speed <= 136:
        cat = "4"
    else:
        cat = "5"
    return cat


def knots_to_kph(wind_speed):
    """Converts wind speed in knots to kph

    Input:
    wind_speed (int) -- wind speed in knots

    Output:
    kph (float) -- wind speed in kph
    """
    return wind_speed * 1.852


def nm_to_km(dist):
    """Converts nautical mile to kilometer

    Input:
    dist (int) -- distance in nm

    Output:
    km (float) -- distance in km
    """
    if dist is not None:
        return dist * 1.852


def vmax_10min_to_1min(wind_speed_10):
    """Convert 10 min average wind speed to 1 min average

    Input:
    wind_speed_10 (float) -- 10-min average wind

    Output:
    wind_speed_1 (float) -- 1-min average wind
    """
    return wind_speed_10 * 1.14


def parse_lat(str):
    """Extract latitude information from the string

    Input:
    str (str) -- the string input

    Output:
    lat (float) -- latitude in degrees
    """
    res = re.search("([0-9]+\.[0-9]+)[NS]", str)
    if res is not None:
        return float(res.group(1))


def parse_lon(str):
    """Extract longitude information from the string

    Input:
    str (str) -- the string input

    Output:
    lon (float) -- longitude in degrees
    """
    res = re.search("([0-9]+\.[0-9]+)[WE]", str)
    if res is not None:
        return float(res.group(1))
