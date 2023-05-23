import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from geopandas import GeoDataFrame, points_from_xy
from scipy.optimize import curve_fit
from shapely.geometry import LineString, Polygon

OUTPUT_DIR = Path("output/shp")

PROJ_CRS = 4326


def generate_track_envelope(pts_gdf, main_track="JTWC"):
    gdf = pts_gdf.loc[pts_gdf["Center"].str.contains("forecast")].copy()
    gdf["ts"] = pd.to_datetime(gdf["Date"], format="%b %d %I %p")
    gdf.sort_values(["Center", "ts"], inplace=True)
    gdf.drop(columns="ts", inplace=True)

    main_pts = gdf.loc[gdf["Center"].str.contains(main_track)].reset_index(drop=True).copy()
    bnd_pts1 = [[], []]
    bnd_pts2 = [[], []]
    for i, r in main_pts.iterrows():
        if i == 0:
            u = np.array(r.geometry.coords[0])
            bnd_pts1[0].append(u)
            bnd_pts1[1].append(u)
            bnd_pts2[0].append(u)
            bnd_pts2[1].append(u)
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
        d_proj = np.array([np.dot(pt - u, n_hat) for pt in zip(X, Y)])

        # keep only the edges
        bnd_pts1[0].append(next(pt.coords[0] for i, pt in enumerate(pts.geometry) if d_proj[i] == d_proj.min()))
        bnd_pts1[1].append(next(pt.coords[0] for i, pt in enumerate(pts.geometry) if d_proj[i] == d_proj.max()))
        bnd_pts2[0].append(u + d_proj.min() * n_hat)
        bnd_pts2[1].append(u + d_proj.max() * n_hat)

    return (
        GeoDataFrame(
            [
                {"name": "bndln1", "geometry": LineString(bnd_pts1[0])},
                {"name": "bndln2", "geometry": LineString(bnd_pts1[1])},
            ],
            crs=PROJ_CRS,
        ),
        GeoDataFrame(
            [
                {"name": "bnd", "geometry": Polygon(bnd_pts1[0] + bnd_pts1[1][::-1])},
            ],
            crs=PROJ_CRS,
        ),
        GeoDataFrame(
            [
                {"name": "bndln1", "geometry": LineString(bnd_pts2[0])},
                {"name": "bndln2", "geometry": LineString(bnd_pts2[1])},
            ],
            crs=PROJ_CRS,
        ),
        GeoDataFrame(
            [
                {"name": "bnd", "geometry": Polygon(bnd_pts2[0] + bnd_pts2[1][::-1])},
            ],
            crs=PROJ_CRS,
        ),
    )


def generate_radius_envelope(pts_gdf, main_track="JTWC"):
    gdf = pts_gdf.loc[pts_gdf["Center"].str.contains("forecast")].copy()
    gdf["ts"] = pd.to_datetime(gdf["Date"], format="%b %d %I %p")
    gdf.sort_values(["Center", "ts"], inplace=True)
    gdf.drop(columns="ts", inplace=True)

    main_pts = gdf.loc[gdf["Center"].str.contains(main_track)].reset_index(drop=True).copy()
    bnd_r = {k: [[], []] for k in ["R34", "R50", "R64"]}
    for i, r in main_pts.iterrows():
        i_min = i - 1
        if i == 0:
            i_min = i
        i_max = i + 2
        # slope m of tangent line at current point
        X = np.array([pt.coords[0][0] for pt in main_pts.iloc[i_min:i_max].geometry])
        Y = np.array([pt.coords[0][1] for pt in main_pts.iloc[i_min:i_max].geometry])
        u = np.array(r.geometry.coords[0])
        (m,), pcov = curve_fit(lambda x, m: m * (x - u[0]) + u[1], X, Y)
        m = np.abs(m)

        # unit vector normal to the current point
        n = np.array((1, -1 / m))
        n_hat = n / np.linalg.norm(n)

        for k in bnd_r.keys():
            if not np.isnan(r[k]):
                d_r = r[k] / 111
                bnd_r[k][0].append(u + d_r * n_hat)
                bnd_r[k][1].append(u - d_r * n_hat)

    bnd_r = [{"name": k, "geometry": Polygon(v[0] + v[1][::-1])} for k, v in bnd_r.items() if len(v[0]) > 0]
    if len(bnd_r) > 0:
        return GeoDataFrame(
            bnd_r,
            crs=PROJ_CRS,
        )

    return None


def generate_radius(gdf, radius):
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
            df2 = pd.concat([df.iloc[0 : row_split_index + 1], row_to_insert], ignore_index=True)
            df = pd.concat([df2, df.iloc[row_split_index + 1 :]], ignore_index=True)

    # generate spatial points from dataframe
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

    # generate envelope from multitrack
    track_bnds = generate_track_envelope(pts_gdf, main_track)
    for i, track_bnd in enumerate(track_bnds):
        if (i % 2) == 0:
            _out_dir = out_dir / f"track_bnds/line{int(i/2)+1}"
        else:
            _out_dir = out_dir / f"track_bnds/poly{int(i/2)+1}"
        _out_dir.mkdir(parents=True, exist_ok=True)
        track_bnd.to_file(_out_dir)

    # generate concentric circles from wind radii
    rad_gdf = pts_gdf[pts_gdf["Center"] == "JTWC_forecast"].copy()
    for r in ["R34", "R50", "R64"]:
        s = generate_radius(rad_gdf, r)
        if s is not None:
            _out_dir = out_dir / f"jtwc_rad/{r.lower()}"
            _out_dir.mkdir(parents=True, exist_ok=True)
            s.to_file(_out_dir)
            _s = s.dissolve("Center")
            _out_dir = out_dir / f"jtwc_rad2/{r.lower()}"
            _out_dir.mkdir(parents=True, exist_ok=True)
            _s.to_file(_out_dir)

    # generate envelope from wind radii
    rad_bnds = generate_radius_envelope(pts_gdf, main_track)
    if rad_bnds is not None:
        _out_dir = out_dir / "track_bnds/wind_radii"
        _out_dir.mkdir(parents=True, exist_ok=True)
        rad_bnds.to_file(_out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create SHP files from CSV")
    parser.add_argument("input", help="Input CSV")
    parser.add_argument("--out-dir", help="Output directory of the shp files", default=OUTPUT_DIR)
    args = parser.parse_args()
    make_shp(args.input, args.out_dir)
