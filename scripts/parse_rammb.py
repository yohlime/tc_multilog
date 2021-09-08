import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import argparse

from _const_ import RAMMB_BASE_URL, REQ_HEADER


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


def proc_tc_data(tc_code, base_url=RAMMB_BASE_URL, dload_url=None):
    if dload_url is None:
        url = base_url + tc_code
    else:
        url = dload_url

    r = requests.get(url, headers=REQ_HEADER)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "lxml")
        tab = soup.find("h3", text=re.compile("Track History")).find_next_sibling(
            "table"
        )
        if tab is None:
            return None
        df = pd.read_html(str(tab), header=0)[0]
        df.columns = ["Timestamp", "Lat", "Lon", "Vmax"]
        df["Center"] = "JTWC"
        # df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d%H%M', utc=True).dt.tz_convert('Asia/Manila')
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], utc=True).dt.tz_convert(
            "Asia/Manila"
        )
        df.sort_values("Timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df["Date"] = df["Timestamp"].dt.strftime("%b %-d %-I %P")
        df["Cat"] = df["Vmax"].apply(knots_to_cat)
        df["Vmax"] = df["Vmax"].apply(knots_to_kph)
        df["PosType"] = "h"
        df.loc[df.shape[0] - 1, "PosType"] = "c"
        return df[["Center", "Date", "Lat", "Lon", "PosType", "Vmax", "Cat"]].copy()
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and process data from RAMMB")
    parser.add_argument("tc_code", help="TC Code")
    parser.add_argument("output", help="Output CSV")
    parser.add_argument("--base-url", help="Base URL", default=RAMMB_BASE_URL)
    parser.add_argument("--dload-url", help="Download URL", default=None)
    args = parser.parse_args()
    df = proc_tc_data(args.tc_code.upper(), args.base_url, args.dload_url)
    df.to_csv(args.output, index=False)
