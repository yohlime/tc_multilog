import re
import requests
import pandas as pd
import argparse

def knots_to_cat(wind_speed):
    """Converts wind speed in knots to equivalent tropical cyclone category
    based on Saffir-Simpson scale

    Input:
    wind_speed (int) -- wind speed in knots

    Output:
    cat (str) -- TC category
    """
    cat = ''
    if wind_speed < 15:
        cat = ''
    elif wind_speed <= 33:
        cat = 'TD'
    elif wind_speed <= 63:
        cat = 'TS'
    elif wind_speed <= 82:
        cat = '1'
    elif wind_speed <= 95:
        cat = '2'
    elif wind_speed <= 112:
        cat = '3'
    elif wind_speed <= 136:
        cat = '4'
    else:
        cat = '5'
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

def parse_lat(str):
    """Extract latitude information from the string

    Input:
    str (str) -- the string input

    Output:
    lat (float) -- latitude in degrees
    """
    res = re.search('([0-9]+\.[0-9]+)[NS]', str)
    if res is not None:
        return float(res.group(1))

def parse_lon(str):
    """Extract longitude information from the string

    Input:
    str (str) -- the string input

    Output:
    lon (float) -- longitude in degrees
    """
    res = re.search('([0-9]+\.[0-9]+)[WE]', str)
    if res is not None:
        return float(res.group(1))

def parse_vmax(str):
    """Extract maximum sustained wind speed from the string

    Input:
    str (str) -- the string input

    Output:
    vmax (int) -- maximum sustained winds in knots
    """
    res = re.search('MAX\ SUSTAINED\ WINDS\ - ([0-9]*)\ KT', str)
    if res is not None:
        return int(res.group(1))

def parse_wind_rad(str):
    """Extract wind radius from the string

    Input:
    str (str) -- the string input

    Output:
    rad_wind (pandas.core.series.Series) -- series containing wind information
    """
    wind_df = pd.DataFrame(columns=['WRAD', 'NORTHEAST', 'SOUTHEAST', 'SOUTHWEST', 'NORTHWEST'])
    for m in re.finditer('RADIUS OF ([0-9]*) KT WINDS - ([0-9]* NM [A-Z]{9} QUADRANT ){1,4}', str):
        d = {'WRAD': int(m.group(1))}
        str2 = str[m.start():m.end()]
        for n in re.finditer('([0-9]*) NM ([A-Z]{9}) QUADRANT', str2):
            d[n.group(2)] = int(n.group(1))
        wind_df = wind_df.append(d, ignore_index=True)
    wind_df.set_index('WRAD', inplace=True)
    return wind_df.max(axis=1)

def parse_forecast_time(str):
    """Extract forecast time from the string

    Input:
    str (str) -- the string input

    Output:
    toff (int) -- forecast time in hr
    """
    res = re.search('([0-9]{2}) HRS', str)
    if res is not None:
        return int(res.group(1))

def proc_tc_data(tc_code):
    url = 'https://metoc.ndbc.noaa.gov/ProductFeeds-portlet/img/jtwc/products/' + tc_code + 'web.txt'

    r = requests.get(url)
    if (r.status_code == 200):
        forecast_df = pd.DataFrame(columns=['Center', 'Date', 'Lat', 'Lon', 'Vmax', 'Cat', 'R34', 'R50', 'R64'])
        res = re.sub('\s+', ' ', r.text).strip()
        res1 = re.search('WARNING\ POSITION(.*)FORECASTS', res).group(1)
        wind_df = parse_wind_rad(res1)
        forecast_df = forecast_df.append({
            'Center': 'JTWC',
            'Date': 0,
            'Lat': parse_lat(res1),
            'Lon': parse_lon(res1),
            'Vmax': parse_vmax(res1),
            'R34': wind_df.loc[34],
            'R50': wind_df.loc[50],
            'R64': wind_df.loc[64]
        }, ignore_index=True)

        res2 = re.search('FORECASTS(.*)---', res).group(1).split('---')
        res3 = [s for s in res2 if re.search('HRS', s)]
        res4 = [s for s in res2 if re.search('WIND', s)]
        for i, s in enumerate(res4):
            wind_df = parse_wind_rad(s)
            forecast_df = forecast_df.append({
                'Center': 'JTWC',
                'Date': parse_forecast_time(res3[i]),
                'Lat': parse_lat(s),
                'Lon': parse_lon(s),
                'Vmax': parse_vmax(s),
                'R34': wind_df.loc[34] if wind_df.index.contains(34) else None,
                'R50': wind_df.loc[50] if wind_df.index.contains(50) else None,
                'R64': wind_df.loc[64] if wind_df.index.contains(64) else None
            }, ignore_index=True)
        forecast_df['Cat'] = forecast_df['Vmax'].apply(knots_to_cat)
        forecast_df['Vmax'] = forecast_df['Vmax'].apply(knots_to_kph)
        forecast_df['R34'] = forecast_df['R34'].apply(nm_to_km)
        forecast_df['R50'] = forecast_df['R50'].apply(nm_to_km)
        forecast_df['R64'] = forecast_df['R64'].apply(nm_to_km)
        return forecast_df
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and process data from JTWC')
    parser.add_argument('tc_code', help='TC Code')
    parser.add_argument('output', help='Output CSV')
    args = parser.parse_args()
    df = proc_tc_data(args.tc_code.lower())
    df.to_csv(args.output, index=False)
