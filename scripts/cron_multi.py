import os
import shutil
from datetime import datetime
from pathlib import Path
import pandas as pd
from dotenv import dotenv_values

from parse_rammb import proc_tc_data as get_rammb
from parse_jtwc import proc_tc_data as get_jtwc
from parse_t2k import proc_tc_data as get_t2k
from make_shp import make_shp


IS_TEST = False
CONFIG = dotenv_values()


def main(is_test=IS_TEST):
    # Load TC information
    print("Loading TC information...")
    DATETIME_NOW = pd.to_datetime(datetime.now())
    OUT_CSV = (
        Path(CONFIG["OUT_DIR"]) / f"csv/{CONFIG['TC_NAME']}_{DATETIME_NOW:%Y%m%d%H}.csv"
    )
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_SHP_DIR = (
        Path(CONFIG["OUT_DIR"]) / f"shp/{CONFIG['TC_NAME']}_{DATETIME_NOW:%Y%m%d%H}/"
    )
    OUT_SHP_DIR.mkdir(parents=True, exist_ok=True)
    OUT_ZIP_FILE = (
        Path(CONFIG["OUT_DIR"]) / f"{CONFIG['TC_NAME']}_{DATETIME_NOW:%Y%m%d%H}"
    )
    OUT_ZIP_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUT_COLUMNS = [
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
    empty_df = pd.DataFrame(columns=OUT_COLUMNS)

    # Initialize the csv
    print("Initializing CSV...")
    # fetch data from http://rammb.cira.colostate.edu/products/tc_realtime/storm.asp
    init_df = get_rammb(
        f"{CONFIG['TC_BASIN'].lower()}{CONFIG['TC_CY'].rjust(2, '0')}{CONFIG['TC_YEAR']}"
    )
    if not isinstance(init_df, pd.DataFrame):
        csvs = sorted(OUT_CSV.parent.glob("*.csv"), key=os.path.getmtime, reverse=True)
        if len(csvs) > 0:  # There is a csv, update it
            init_df = pd.read_csv(csvs[0])
            init_df = init_df.loc[
                (init_df["Center"] == "JTWC") & (init_df["PosType"] != "f"),
                OUT_COLUMNS[:7],
            ]
            init_df["PosType"] = "h"

    if isinstance(init_df, pd.DataFrame):
        out_df = init_df.copy()
    else:
        out_df = empty_df.copy()

    raw_out_dir = Path(CONFIG["OUT_DIR"]) / "multi"

    # Get forecast data from JTWC
    print("Getting forecast from JTWC...")
    tc_code = (
        f"{CONFIG['TC_BASIN']}{CONFIG['TC_CY'].rjust(2, '0')}{CONFIG['TC_YEAR'][2:]}"
    )
    if is_test:
        jtwc_df = get_jtwc(
            tc_code,
            base_url="http://localhost:8000/",
            timestamp=DATETIME_NOW,
        )
    else:
        jtwc_df = get_jtwc(
            tc_code,
            raw_out_dir=raw_out_dir,
        )
    if isinstance(jtwc_df, pd.DataFrame):
        c_date = jtwc_df.loc[jtwc_df["PosType"] == "c", "Date"].values
        if len(c_date) > 0:
            c_date = c_date[0]
            drop_index = out_df[out_df["Date"] == c_date].index
            if len(drop_index) > 0:
                out_df.drop(out_df.iloc[drop_index[0] :].index, inplace=True)
        out_df = out_df.append(jtwc_df, ignore_index=True)
    else:
        out_df = out_df.append(empty_df, ignore_index=True)

    # Get multilog from Typhoon2000
    print("Getting TC data from Typhoon2k...")
    tc_name = CONFIG["TC_NAME"]
    if is_test:
        t2k_df = get_t2k(
            tc_name,
            base_url="http://localhost:8000/",
            exclude="JTWC",
            timestamp=DATETIME_NOW,
        )
    else:
        t2k_df = get_t2k(tc_name, exclude="JTWC", raw_out_dir=raw_out_dir)
    if isinstance(t2k_df, pd.DataFrame):
        out_df = out_df.append(t2k_df, ignore_index=True)
    else:
        out_df = out_df.append(empty_df, ignore_index=True)

    # Save CSV
    print("Saving CSV...")
    out_df[OUT_COLUMNS].to_csv(OUT_CSV, index=False)

    # Create SHP
    print("Creating SHPs...")
    make_shp(OUT_CSV, OUT_SHP_DIR)
    shutil.make_archive(OUT_ZIP_FILE, "zip", OUT_SHP_DIR)


if __name__ == "__main__":
    main()
