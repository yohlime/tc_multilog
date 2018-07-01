#!/home/miniconda3/envs/toolbox/bin/python

import os
import shutil
import json
from glob import glob
import pandas as pd

from parse_rammb import proc_tc_data as get_rammb, BASE_URL as rammb_burl
from parse_jtwc import proc_tc_data as get_jtwc, BASE_URL as jtwc_burl
from parse_t2k import proc_tc_data as get_t2k, BASE_URL as t2k_burl
from make_shp import make_shp

QGIS_DATA_DIR = '/home/modelgal/data/tc/ty_multilog/input'
IS_TEST=False

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
            except Exception as e:
                print e
                os.unlink(d)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)
    #shutil.rmtree(src)

def main(is_test=IS_TEST):
    # Load TC information
    print('Loading TC information...')
    TC_INFO = json.load(open('tc_info.txt'))
    DATETIME_NOW = pd.to_datetime(pd.datetime.now())
    OUT_CSV = 'output/csv/{}_{:%Y%m%d%H}.csv'.format(TC_INFO['name'], DATETIME_NOW)
    OUT_SHP_DIR = 'output/shp/{}_{:%Y%m%d%H}/'.format(TC_INFO['name'], DATETIME_NOW)
    OUT_ZIP_FILE = 'output/{}_{:%Y%m%d%H}'.format(TC_INFO['name'], DATETIME_NOW)

    OUT_COLUMNS = ['Center', 'Date', 'Lat', 'Lon', 'PosType', 'Vmax', 'Cat', 'R34', 'R50', 'R64']
    empty_df = pd.DataFrame(columns=OUT_COLUMNS)

    # Initialize the csv
    print('Initializing CSV...')
    csvs = sorted(glob('output/csv/*.csv'), key=os.path.getmtime, reverse=True)
    if len(csvs) > 0: # There is a csv, update it
        init_df = pd.read_csv(csvs[0])
        init_df = init_df.loc[(init_df['Center']=='JTWC') & (init_df['PosType']!='f'), OUT_COLUMNS[:7]]
        init_df['PosType'] = 'h'
    else: # No csv, fetch data from http://rammb.cira.colostate.edu/products/tc_realtime/storm.asp
        init_df = get_rammb('{basin}{cy:02}{year}'.format(**TC_INFO).upper())

    if isinstance(init_df, pd.DataFrame):
        out_df = init_df.copy()
    else:
        out_df = empty_df.copy()

    # Get forecast data from JTWC
    print('Getting forecast from JTWC...')
    tc_code = '{basin}{cy:02}{yy}'.format(yy=str(TC_INFO['year'])[2:], **TC_INFO)
    if is_test:
        jtwc_df = get_jtwc(tc_code, base_url='http://localhost:8000/', timestamp=DATETIME_NOW)
    else:
        jtwc_df = get_jtwc(tc_code)
    if isinstance(jtwc_df, pd.DataFrame):
        c_date = jtwc_df.loc[jtwc_df['PosType']=='c','Date'].values
        if len(c_date) > 0:
            c_date = c_date[0]
            drop_index = out_df[out_df['Date']==c_date].index
            if len(drop_index) > 0:
                out_df.drop(out_df.iloc[drop_index[0]:].index, inplace=True)
        out_df = out_df.append(jtwc_df, ignore_index=True)
    else:
        out_df = out_df.append(empty_df, ignore_index=True)


    # Get multilog from Typhoon2000
    print('Getting TC data from Typhoon2k...')
    tc_name = TC_INFO['name']
    if is_test:
        t2k_df = get_t2k(tc_name, base_url='http://localhost:8000/', exclude='JTWC', timestamp=DATETIME_NOW)
    else:
        t2k_df = get_t2k(tc_name, exclude='JTWC')
    if isinstance(t2k_df, pd.DataFrame):
        out_df = out_df.append(t2k_df, ignore_index=True)
    else:
        out_df = out_df.append(empty_df, ignore_index=True)

    # Save CSV
    print('Saving CSV...')
    out_df[OUT_COLUMNS].to_csv(OUT_CSV, index=False)

    # Create SHP
    print('Creating SHPs...')
    make_shp(OUT_CSV, OUT_SHP_DIR)
    shutil.make_archive(OUT_ZIP_FILE, 'zip', OUT_SHP_DIR)

    # Copy to QGIS directory
    print('Copying files to QGIS directory...')
    copytree(OUT_SHP_DIR, QGIS_DATA_DIR)
    print('Done!!!')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
    
