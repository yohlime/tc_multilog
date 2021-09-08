from datetime import datetime
import re
import requests
import pandas as pd
import argparse

try:
    from StringIO import StringIO  # for Python 2
except ImportError:
    from io import StringIO  # for Python 3

from _const_ import T2K_BASE_URL, REQ_HEADER
from _helper_ import (
    knots_to_cat,
    knots_to_kph,
    vmax_10min_to_1min,
    parse_lat,
    parse_lon,
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
    tc_name,
    base_url=T2K_BASE_URL,
    dload_url=None,
    exclude=[],
    timestamp=pd.to_datetime(datetime.now()),
    raw_out_dir=None,
):
    if dload_url is None:
        url = base_url + tc_name + ".TXT"
    else:
        url = dload_url

    if isinstance(exclude, str):
        exclude = [exclude]
    elif exclude is None:
        exclude = []

    r = requests.get(url, headers=REQ_HEADER)
    if r.status_code == 200:
        if raw_out_dir is not None:
            out_file_name = raw_out_dir / f"{tc_name.upper()}_{timestamp:%Y%m%d%H}.TXT"
            out_file = open(out_file_name, "w")
            out_file.write(r.text)
            out_file.close()

        res = re.sub("\s+", " ", r.text).strip()

        update_time = pd.to_datetime(re.search("\((.*UTC)\)", res).group(1))

        res1 = re.search("=+(.*)", res).group(1).strip().split(":")
        centers = [
            re.search("[A-Z]{3,}", s).group(0)
            for s in res1
            if re.match(".*[A-Z]{3,}", s)
        ]
        info = [
            re.search(".*KT", s).group(0).strip() for s in res1 if re.match(".*KT", s)
        ]

        out_df = pd.DataFrame(
            columns=["Center", "Date", "Lat", "Lon", "PosType", "Vmax", "Cat"]
        )
        for i, f in enumerate(info):
            if centers[i] not in exclude:
                df = pd.read_csv(
                    StringIO(re.sub("KT\ ?", "\n", f)),
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
                    df.loc[1:, "Timestamp"].apply(parse_forecast_time), unit="H"
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
                out_df = out_df.append(df, ignore_index=True)
        return out_df[["Center", "Date", "Lat", "Lon", "PosType", "Vmax", "Cat"]]
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and process data from Typhoon2000"
    )
    parser.add_argument("tc_name", help="TC international name")
    parser.add_argument("output", help="Output CSV")
    parser.add_argument("--base-url", help="Base URL", default=T2K_BASE_URL)
    parser.add_argument("--dload-url", help="Download URL", default=None)
    parser.add_argument("--exclude", help="Center to exclude", nargs="*")
    args = parser.parse_args()
    df = proc_tc_data(args.tc_name.upper())
    df.to_csv(args.output, index=False)
