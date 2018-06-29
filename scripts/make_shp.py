import os
import pandas as pd
from geopandas import GeoDataFrame
from shapely.geometry import Point, LineString
import argparse

OUTPUT_DIR = 'output/shp/'

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def df_to_gdf(df, lat='Lat', lon='Lon'):
    geometry = [Point(xy) for xy in zip(df[lon], df[lat])]
    crs = {'init': 'epsg:4326'}
    return GeoDataFrame(df, crs=crs, geometry=geometry)

def pts_to_line(gdf, group_by):
    gdf = gdf.groupby(group_by)['geometry'].apply(lambda x: LineString(x.tolist()))
    return GeoDataFrame(gdf.reset_index(), geometry='geometry')

def add_radius(gdf, radius):
    if radius in gdf.columns:
        gdf = gdf.dropna(subset=[radius])
        if gdf.shape[0] > 0:
            geometry = gdf.apply(lambda x: x.geometry.buffer(x[radius]/111.0), axis=1)
            return GeoDataFrame(gdf, geometry=geometry)
    return None

def make_shp(in_file, out_dir=OUTPUT_DIR):
    ensure_dir(out_dir+'jtwc_rad/test')

    df = pd.read_csv(in_file)
    row_to_insert = df[(df['Center']=='JTWC') & (df['PosType']=='c')].copy()
    if row_to_insert.shape[0] == 1:
        row_split_index = df[(df['Center']=='JTWC') & (df['PosType']=='c')].index.values[0]
        row_to_insert['Center'] = 'JTWC_forecast'
        df.loc[(df['Center']=='JTWC') & (df['PosType']=='f'), 'Center'] = 'JTWC_forecast'
        df2 = df.iloc[0:row_split_index+1].append(row_to_insert, ignore_index=True)
        df = df2.append(df.iloc[row_split_index+1:], ignore_index=True)

    gdf_pts = df_to_gdf(df)
    gdf_pts.to_file(out_dir+'track_pts')

    gdf_lns = pts_to_line(gdf_pts, 'Center')
    gdf_lns.to_file(out_dir+'track_line')

    gdf_rad = gdf_pts[gdf_pts['Center']=='JTWC_forecast'].copy()
    for r in ['R34', 'R50', 'R64']:
        s = add_radius(gdf_rad, r)
        if s is not None:
            s.to_file(out_dir+'jtwc_rad/'+r.lower())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create SHP files from CSV')
    parser.add_argument('input', help='Input CSV')
    parser.add_argument('--out-dir', help='Output directory of the shp files', default=OUTPUT_DIR)
    args = parser.parse_args()
    make_shp(args.input, args.out_dir)
