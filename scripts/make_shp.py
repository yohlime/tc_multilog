from pathlib import Path
import numpy as np
import pandas as pd
from geopandas import GeoDataFrame, points_from_xy
from shapely.geometry import LineString, Polygon
from scipy.optimize import curve_fit
import argparse


OUTPUT_DIR = Path("output/shp")

PROJ_CRS = 4326


def generate_envelope(pts_gdf, main_track="JTWC"):
    gdf = pts_gdf.loc[pts_gdf["Center"].str.contains("forecast")].copy()
    gdf["ts"] = pd.to_datetime(gdf["Date"], format="%b %d %I %p")
    gdf.sort_values(["Center", "ts"], inplace=True)
    gdf.drop(columns="ts", inplace=True)

    main_pts = gdf.loc[gdf["Center"].str.contains(main_track)].reset_index(drop=True).copy()

    bnd_pts1 = []
    bnd_pts2 = []
    for i, r in main_pts.iterrows():
        if i == 0:
            u = np.array(r.geometry.coords[0])
            bnd_pts1.append(u)
            bnd_pts2.append(u)
            continue

        # slope m of tangent line at current point
        X = np.array([pt.coords[0][0] for pt in main_pts.iloc[i - 1 : i + 2].geometry])
        Y = np.array([pt.coords[0][1] for pt in main_pts.iloc[i - 1 : i + 2].geometry])
        u = np.array(r.geometry.coords[0])
        (m,), pcov = curve_fit(lambda x, m: m * (x - u[0]) + u[1], X, Y)
        m = np.abs(m)

        # unit vector normal to the current point
        n = np.array((1, -1 / m))
        n_hat = n / np.linalg.norm(n)

        pts = gdf.loc[gdf["Date"] == r["Date"]].copy()
        X = np.array([pt.coords[0][0] for pt in pts.geometry])
        Y = np.array([pt.coords[0][1] for pt in pts.geometry])
        if len(X) == 1:
            continue
        # projection to the normal line
        d = np.array([np.dot(pt - u, n_hat) for pt in zip(X, Y)])

        # keep only the edges
        bnd_pts1.append(u + d.min() * n_hat)
        bnd_pts2.append(u + d.max() * n_hat)

    return GeoDataFrame(
        [
            {"name": main_track, "geometry": LineString(main_pts.geometry)},
            {"name": "bndln1", "geometry": LineString(bnd_pts1)},
            {"name": "bndln2", "geometry": LineString(bnd_pts2)},
            {"name": "bnd", "geometry": Polygon(bnd_pts1 + bnd_pts2[::-1])},
        ]
    )


def add_radius(gdf, radius):
    if radius in gdf.columns:
        gdf = gdf.dropna(subset=[radius])
        if gdf.shape[0] > 0:
            geometry = gdf.apply(lambda x: x.geometry.buffer(x[radius] / 111.0), axis=1)
            return GeoDataFrame(gdf, geometry=geometry, crs=PROJ_CRS)
    return None


def make_shp(in_file, out_dir=OUTPUT_DIR, main_track="JTWC"):
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
    pts_gdf = GeoDataFrame(df.copy(), crs=PROJ_CRS, geometry=geom)
    _out_dir = out_dir / "track_pts"
    _out_dir.mkdir(parents=True, exist_ok=True)
    pts_gdf.to_file(_out_dir)

    # connect the dots
    lns_gdf = pts_gdf.copy().groupby("Center").filter(lambda x: len(x) > 1)
    lns_gdf = lns_gdf.groupby("Center")["geometry"].apply(lambda x: LineString(x.tolist()))
    lns_gdf = GeoDataFrame(lns_gdf.reset_index(), geometry="geometry", crs=PROJ_CRS)
    _out_dir = out_dir / "track_line"
    _out_dir.mkdir(parents=True, exist_ok=True)
    lns_gdf.to_file(_out_dir)

    bnds_gdf = generate_envelope(pts_gdf, main_track=main_track)
    _out_dir = out_dir / "track_bnds"
    _out_dir.mkdir(parents=True, exist_ok=True)
    bnds_gdf.to_file(_out_dir)

    gdf_rad = pts_gdf[pts_gdf["Center"] == "JTWC_forecast"].copy()
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
