import re
import requests
from bs4 import BeautifulSoup
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
    if wind_speed != wind_speed:
        return ''
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

def proc_tc_data(tc_code):
    url = 'http://rammb.cira.colostate.edu/products/tc_realtime/storm.asp?storm_identifier=' + tc_code

    r = requests.get(url)
    if (r.status_code == 200):
        soup = BeautifulSoup(r.text, 'lxml')
        tab = soup.find('h3', text=re.compile('Track History')).find_next_sibling('table')
        df = pd.read_html(str(tab), header=0)[0]
        df.columns = ['Timestamp', 'Lat', 'Lon', 'Vmax']
        df['Center'] = 'JTWC'
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d%H%M', utc=True).dt.tz_convert('Asia/Manila')
        df.sort_values('Timestamp', inplace=True)
        df['Date'] = df['Timestamp'].dt.strftime('%b %-d %-I %P')
        df['Cat'] = df['Vmax'].apply(knots_to_cat)
        df['Vmax'] = df['Vmax'].apply(knots_to_kph)
        return df[['Center', 'Date', 'Lat', 'Lon', 'Vmax', 'Cat']].copy()
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and process data from RAMMB')
    parser.add_argument('tc_code', help='TC Code')
    parser.add_argument('output', help='Output CSV')
    args = parser.parse_args()
    df = proc_tc_data(args.tc_code.upper())
    df.to_csv(args.output, index=False)