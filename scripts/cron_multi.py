import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from _const_ import JTWC_BASE_URL, T2K_BASE_URL
from dotenv import dotenv_values
from make_shp import make_shp
from parse_jtwc import proc_tc_data as get_jtwc
from parse_rammb import proc_tc_data as get_rammb
from parse_t2k import proc_tc_data as get_t2k

CONFIG = dotenv_values()


def main():
    # Load TC information
    print("Loading TC information...")
    dt_now = pd.to_datetime(datetime.now())
    tc_info = {
        "name": CONFIG.get("TC_NAME", ""),
        "yr": int(CONFIG.get("TC_YEAR", f"{dt_now:'%Y'}")),
        "cy": int(CONFIG.get("TC_CY", "1")),
        "basin": CONFIG.get("TC_BASIN", "wp").lower(),
    }

    out_dir = Path(CONFIG.get("OUT_DIR", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    out_csv = out_dir / f"csv/{tc_info['name']}_{dt_now:%Y%m%d%H}.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    out_shp_dir = out_dir / f"shp/{tc_info['name']}_{dt_now:%Y%m%d%H}/"
    out_shp_dir.mkdir(parents=True, exist_ok=True)

    out_zip = out_dir / f"{tc_info['name']}_{dt_now:%Y%m%d%H}"
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    out_cols = [
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
    empty_df = pd.DataFrame(columns=out_cols)

    # Initialize the csv
    print("Initializing CSV...")
    init_df = empty_df.copy()
    csvs = sorted(out_csv.parent.glob("*.csv"), key=os.path.getmtime, reverse=True)

    if len(csvs) > 0:  # There is a csv, update it
        init_df = pd.read_csv(csvs[0])
        init_df = init_df.loc[init_df["PosType"] != "f", out_cols[:7]].copy()
        init_df["PosType"] = "h"
    else:
        tc_code = f"{tc_info['basin']}{tc_info['cy']:02}{tc_info['yr']}"
        init_df = get_rammb(tc_code)

    if isinstance(init_df, pd.DataFrame):
        out_df = init_df.copy()
    else:
        out_df = empty_df.copy()

    raw_out_dir = Path(out_dir) / "multi"
    raw_out_dir.mkdir(parents=True, exist_ok=True)

    # Get forecast data from JTWC
    print("Getting forecast from JTWC...")
    tc_code = f"{tc_info['basin']}{tc_info['cy']:02}{tc_info['yr'] % 100}"
    in_file = JTWC_BASE_URL + tc_code + "web.txt"
    jtwc_df = get_jtwc(in_file, tc_code, raw_out_dir=raw_out_dir)
    if isinstance(jtwc_df, pd.DataFrame):
        c_date = jtwc_df.loc[jtwc_df["PosType"] == "c", "Date"].values
        if len(c_date) > 0:
            c_date = c_date[0]
            out_df = out_df.loc[
                ~((out_df["Center"] == "JTWC") & (out_df["Date"] == c_date))
            ].copy()
        out_df = pd.concat([out_df, jtwc_df], ignore_index=True)
    else:
        out_df = pd.concat([out_df, empty_df], ignore_index=True)

    # Get multilog from Typhoon2000
    print("Getting TC data from Typhoon2k...")
    in_file = T2K_BASE_URL + tc_info["name"] + ".TXT"
    t2k_df = get_t2k(in_file, tc_info["name"], exclude="JTWC", raw_out_dir=raw_out_dir)
    if isinstance(t2k_df, pd.DataFrame):
        for center_name in t2k_df["Center"].unique():
            c_date = jtwc_df.loc[t2k_df["PosType"] == "c", "Date"].values
            if len(c_date) > 0:
                c_date = c_date[0]
                out_df = out_df.loc[
                    ~((out_df["Center"] == center_name) & (out_df["Date"] == c_date))
                ].copy()
        out_df = pd.concat([out_df, t2k_df], ignore_index=True)
    else:
        out_df = pd.concat([out_df, empty_df], ignore_index=True)

    # Save CSV
    print("Saving CSV...")
    out_df[out_cols].to_csv(out_csv, index=False)

    # Create SHP
    print("Creating SHPs...")
    make_shp(out_csv, out_shp_dir, main_track=CONFIG["MAIN_TRACK"])
    shutil.make_archive(out_zip, "zip", out_shp_dir)


if __name__ == "__main__":
    main()
