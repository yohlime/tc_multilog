import re
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
from _const_ import REQ_HEADER
from _helper_ import (
    knots_to_cat,
    knots_to_kph,
    parse_lat,
    parse_lon,
    vmax_10min_to_1min,
)


def parse_forecast_time(str):
    """Extract forecast time from the string

    Input:
    str (str) -- the string input

    Output:
    toff (int) -- forecast time in hr
    """
    res = re.search("([0-9]+)H", str)
    if res is not None:
        return int(res.group(1))


def proc_tc_data(
    in_file,
    tc_name,
    exclude=[],
    timestamp=None,
    mode="download",
    raw_out_dir=None,
):
    if isinstance(exclude, str):
        exclude = [exclude]
    elif exclude is None:
        exclude = []

    if timestamp is None:
        if mode == "local":
            raise ValueError("'timestamp' should be supplied for 'local' mode")
        else:
            timestamp = pd.to_datetime(datetime.now())

    data = ""
    if mode == "download":
        r = requests.get(in_file, headers=REQ_HEADER)
        if r.status_code != 200:
            return None
        data = r.text
        if raw_out_dir is not None:
            out_file_name = raw_out_dir / f"{tc_name.upper()}_{timestamp:%Y%m%d%H}.TXT"
            out_file = open(out_file_name, "w")
            out_file.write(data)
            out_file.close()
    elif mode == "local":
        text_file = open(in_file, "r")
        data = text_file.read()
        text_file.close()
    else:
        return None

    res = re.sub(r"\s+", " ", data).strip()

    update_time = pd.to_datetime(re.search(r"\((.*UTC)\)", res).group(1))

    res1 = re.search(r"=+(.*)", res).group(1).strip().split(":")
    centers = [
        re.search(r"[A-Z]{3,}", s).group(0) for s in res1 if re.match(r".*[A-Z]{3,}", s)
    ]
    info = [
        re.search(r".*KT", s).group(0).strip() for s in res1 if re.match(r".*KT", s)
    ]

    out_df = pd.DataFrame(
        columns=["Center", "Date", "Lat", "Lon", "PosType", "Vmax", "Cat"]
    )
    for i, f in enumerate(info):
        if centers[i] not in exclude:
            df = pd.read_csv(
                StringIO(re.sub(r"KT\ ?", "\n", f)),
                sep=" ",
                header=None,
                na_values="---",
            )
            df.columns = ["Timestamp", "Lat", "Lon", "Vmax"]
            df["Lat"] = df["Lat"].apply(parse_lat)
            df["Lon"] = df["Lon"].apply(parse_lon)
            df.loc[0, "Timestamp"] = pd.to_datetime(
                update_time.strftime("%Y%m") + df.loc[0, "Timestamp"][:4],
                format="%Y%m%d%H",
                utc=True,
            )
            df.loc[1:, "Timestamp"] = df.loc[0, "Timestamp"] + pd.to_timedelta(
                df.loc[1:, "Timestamp"].apply(parse_forecast_time), unit="h"
            )
            df.sort_values("Timestamp", inplace=True)
            df.reset_index(drop=True, inplace=True)
            df["Date"] = (
                pd.to_datetime(df["Timestamp"])
                .dt.tz_convert("Asia/Manila")
                .dt.strftime("%b %-d %-I %P")
            )
            df["Vmax"] = df["Vmax"].apply(vmax_10min_to_1min)
            df["Cat"] = df["Vmax"].apply(knots_to_cat)
            df["Vmax"] = df["Vmax"].apply(knots_to_kph)
            df["Center"] = centers[i]
            df["PosType"] = "f"
            df.loc[0, "PosType"] = "c"
            out_df = pd.concat([out_df, df], ignore_index=True)
    return out_df[["Center", "Date", "Lat", "Lon", "PosType", "Vmax", "Cat"]]
