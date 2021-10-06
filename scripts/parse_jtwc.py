from datetime import datetime
import re
import requests
import pandas as pd

from _const_ import REQ_HEADER
from _helper_ import knots_to_cat, knots_to_kph, nm_to_km, parse_lat, parse_lon


def parse_time(str):
    """Extract Timestamp information from the string

    Input:
    str (str) -- the string input

    Output:
    timestamp (str) -- timestamp
    """
    res = re.search(r"([0-9]{6})Z", str)
    if res is not None:
        return res.group(1)


def parse_vmax(str):
    """Extract maximum sustained wind speed from the string

    Input:
    str (str) -- the string input

    Output:
    vmax (int) -- maximum sustained winds in knots
    """
    res = re.search(r"MAX\ SUSTAINED\ WINDS\ - ([0-9]*)\ KT", str)
    if res is not None:
        return int(res.group(1))


def parse_wind_rad(str):
    """Extract wind radius from the string

    Input:
    str (str) -- the string input

    Output:
    rad_wind (pandas.core.series.Series) -- series containing wind information
    """
    wind_df = pd.DataFrame(columns=["WRAD", "NORTHEAST", "SOUTHEAST", "SOUTHWEST", "NORTHWEST"])
    for m in re.finditer(r"RADIUS OF ([0-9]*) KT WINDS - ([0-9]* NM [A-Z]{9} QUADRANT ){1,4}", str):
        d = {"WRAD": int(m.group(1))}
        str2 = str[m.start() : m.end()]
        for n in re.finditer(r"([0-9]*) NM ([A-Z]{9}) QUADRANT", str2):
            d[n.group(2)] = int(n.group(1))
        wind_df = wind_df.append(d, ignore_index=True)
    wind_df.set_index("WRAD", inplace=True)
    return wind_df.max(axis=1)


def parse_forecast_time(str):
    """Extract forecast time from the string

    Input:
    str (str) -- the string input

    Output:
    toff (int) -- forecast time in hr
    """
    res = re.search(r"([0-9]{2,}) HRS", str)
    if res is not None:
        return int(res.group(1))


def proc_tc_data(
    in_file,
    tc_code,
    timestamp=None,
    mode="download",
    raw_out_dir=None,
):
    """Parse tropical cyclone data from JTWC warning

    Args:
        in_file (str): Valid download url or local file path
        tc_code (str): TC code '{BASIN}{CY}{yy}'
        timestamp (pandas.Timestamp, optional): Required if mode is 'local'. Defaults to None.
        mode (str, optional): 'download' or 'local'. Defaults to "download".
        raw_out_dir (str, optional): Directory where the downloaded raw txt will be stored.
            Ignored in 'local' mode. Defaults to None.

    Returns:
        pandas.Dataframe
    """
    if timestamp is None:
        if mode == "local":
            raise ValueError("'timestamp' should be supplied for 'local' mode")
        else:
            timestamp = pd.to_datetime(datetime.now())

    timestamp_utc = timestamp.tz_localize("Asia/Manila").tz_convert("UTC")

    data = ""
    if mode == "download":
        r = requests.get(in_file, headers=REQ_HEADER)
        if r.status_code != 200:
            return None
        data = r.text
        if raw_out_dir is not None:
            out_file_name = raw_out_dir / f"{tc_code}web_{timestamp:%Y%m%d%H}.txt"
            out_file = open(out_file_name, "w")
            out_file.write(data)
            out_file.close()
    elif mode == "local":
        text_file = open(in_file, "r")
        data = text_file.read()
        text_file.close()
    else:
        return None

    forecast_df = pd.DataFrame(
        columns=[
            "Center",
            "Date",
            "Lat",
            "Lon",
            "PosType",
            "Vmax",
            "Cat",
            "R34",
            "R50",
            "R64",
        ]
    )
    res = re.sub(r"\s+", " ", data).strip()
    res1 = re.search(r"WARNING\ POSITION(.*)FORECASTS", res).group(1)
    date0 = pd.to_datetime(timestamp_utc.strftime("%Y%m") + parse_time(res1), format="%Y%m%d%H%M")
    wind_df = parse_wind_rad(res1)
    forecast_df = forecast_df.append(
        {
            "Center": "JTWC",
            "Date": date0,
            "Lat": parse_lat(res1),
            "Lon": parse_lon(res1),
            "PosType": "c",
            "Vmax": parse_vmax(res1),
            "R34": wind_df.loc[34] if 34 in wind_df.index else None,
            "R50": wind_df.loc[50] if 50 in wind_df.index else None,
            "R64": wind_df.loc[64] if 64 in wind_df.index else None,
        },
        ignore_index=True,
    )

    res2 = re.search(r"FORECASTS(.*)---", res).group(1).split("---")
    res3 = [s for s in res2 if re.search(r"HRS", s)]
    res4 = [s for s in res2 if re.search(r"WIND", s)]
    for i, s in enumerate(res4):
        wind_df = parse_wind_rad(s)
        forecast_df = forecast_df.append(
            {
                "Center": "JTWC",
                "Date": date0 + pd.to_timedelta(parse_forecast_time(res3[i]), unit="H"),
                "Lat": parse_lat(s),
                "Lon": parse_lon(s),
                "PosType": "f",
                "Vmax": parse_vmax(s),
                "R34": wind_df.loc[34] if 34 in wind_df.index else None,
                "R50": wind_df.loc[50] if 50 in wind_df.index else None,
                "R64": wind_df.loc[64] if 64 in wind_df.index else None,
            },
            ignore_index=True,
        )
    forecast_df["Date"] = (
        forecast_df["Date"].dt.tz_localize("UTC").dt.tz_convert("Asia/Manila").dt.strftime("%b %-d %-I %P")
    )
    forecast_df["Cat"] = forecast_df["Vmax"].apply(knots_to_cat)
    forecast_df["Vmax"] = forecast_df["Vmax"].apply(knots_to_kph)
    forecast_df["R34"] = forecast_df["R34"].apply(nm_to_km)
    forecast_df["R50"] = forecast_df["R50"].apply(nm_to_km)
    forecast_df["R64"] = forecast_df["R64"].apply(nm_to_km)
    return forecast_df[
        [
            "Center",
            "Date",
            "Lat",
            "Lon",
            "PosType",
            "Vmax",
            "Cat",
            "R34",
            "R50",
            "R64",
        ]
    ]
