from pathlib import Path
import pandas as pd
from geopandas import GeoDataFrame, points_from_xy
from shapely.geometry import LineString
import argparse

OUTPUT_DIR = Path("output/shp")

PROJ_CRS = 4326


def add_radius(gdf, radius):
    if radius in gdf.columns:
        gdf = gdf.dropna(subset=[radius])
        if gdf.shape[0] > 0:
            geometry = gdf.apply(lambda x: x.geometry.buffer(x[radius] / 111.0), axis=1)
            return GeoDataFrame(gdf, geometry=geometry, crs=PROJ_CRS)
    return None


def make_shp(in_file, out_dir=OUTPUT_DIR):
    df = pd.read_csv(in_file)
    for center_name in df["Center"].unique():
        row_to_insert = df[(df["Center"] == center_name) & (df["PosType"] == "c")].copy()
        if row_to_insert.shape[0] == 1:
            row_split_index = df[(df["Center"] == center_name) & (df["PosType"] == "c")].index.values[0]
            row_to_insert["Center"] = f"{center_name}_forecast"
            df.loc[(df["Center"] == center_name) & (df["PosType"] == "f"), "Center"] = f"{center_name}_forecast"
            df2 = df.iloc[0 : row_split_index + 1].append(row_to_insert, ignore_index=True)
            df = df2.append(df.iloc[row_split_index + 1 :], ignore_index=True)

    # df to gdf pts
    geom = points_from_xy(df["Lon"], df["Lat"], crs=PROJ_CRS)
    gdf_pts = GeoDataFrame(df.copy(), crs=PROJ_CRS, geometry=geom)
    _out_dir = out_dir / "track_pts"
    _out_dir.mkdir(parents=True, exist_ok=True)
    gdf_pts.to_file(_out_dir)

    # connect the dots
    gdf_lns = gdf_pts.copy().groupby("Center").filter(lambda x: len(x) > 1)
    gdf_lns = gdf_lns.groupby("Center")["geometry"].apply(lambda x: LineString(x.tolist()))
    gdf_lns = GeoDataFrame(gdf_lns.reset_index(), geometry="geometry", crs=PROJ_CRS)
    _out_dir = out_dir / "track_line"
    _out_dir.mkdir(parents=True, exist_ok=True)
    gdf_lns.to_file(_out_dir)

    gdf_rad = gdf_pts[gdf_pts["Center"] == "JTWC_forecast"].copy()
    for r in ["R34", "R50", "R64"]:
        s = add_radius(gdf_rad, r)
        if s is not None:
            _out_dir = out_dir / f"jtwc_rad/{r.lower()}"
            _out_dir.mkdir(parents=True, exist_ok=True)
            s.to_file(_out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create SHP files from CSV")
    parser.add_argument("input", help="Input CSV")
    parser.add_argument("--out-dir", help="Output directory of the shp files", default=OUTPUT_DIR)
    args = parser.parse_args()
    make_shp(args.input, args.out_dir)
