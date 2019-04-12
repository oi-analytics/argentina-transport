"""Generate darthmouth events
"""
import csv
import os
import types
import fiona
import pandas as pd
import geopandas as gpd
import numpy as np
import igraph as ig
import copy
import unidecode
from scipy.spatial import Voronoi
from oia.utils import *
import datetime
from tqdm import tqdm



def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']

    events_df = gpd.read_file(os.path.join(incoming_data_path,'FloodsArchived_shp','FloodsArchived_shape.shp'))
    events_df = events_df.to_crs({'init': 'epsg:4326'})
    events_df.columns = map(str.lower, events_df.columns)
    sindex_events_df = events_df.sindex
    print (events_df.columns.values.tolist())

    boundary_df = gpd.read_file(os.path.join(data_path,'boundaries','admin_0_boundaries.shp'),encoding='utf-8')
    boundary_df = boundary_df.to_crs({'init': 'epsg:4326'})
    boundary_df.columns = map(str.lower, boundary_df.columns)
    countries = boundary_df['name'].values.tolist()
    boundary_df = boundary_df[boundary_df['name'] == 'Argentina']

    intersected_events = events_df.iloc[list(sindex_events_df.intersection(boundary_df['geometry'].values[0].bounds))]
    for idx,val in intersected_events.iterrows():
        country_match = [c for c in countries
                        if (unidecode.unidecode(str(val.country)).lower().strip() in unidecode.unidecode(c).lower().strip()) 
                        or (unidecode.unidecode(c).lower().strip() in unidecode.unidecode(str(val.country)).lower().strip())]

        if not country_match:
            intersected_events = intersected_events[intersected_events['country'] != val.country]

    reference_date = pd.Timestamp('2000-01-01')
    intersected_events['time_diff'] = intersected_events.progress_apply(lambda x:(datetime.datetime.strptime(x.began,"%Y-%m-%d") - reference_date).days*24.0,axis=1)
    intersected_events = intersected_events[intersected_events['time_diff'] > 0]
    intersected_events = gpd.GeoDataFrame(intersected_events,geometry='geometry',crs={'init' :'epsg:4326'}).reset_index()
    intersected_events.drop('time_diff',axis=1,inplace=True)
    print (intersected_events.dtypes)
    
    intersected_events.to_file(os.path.join(data_path,'flood_data','Darthmouth_events','darthmouth_event_set.shp'),encoding='utf-8')
    intersected_events.drop(['geometry'],axis=1,inplace=True)
    intersected_events.to_csv(os.path.join(data_path,'flood_data','Darthmouth_events','darthmouth_event_set.csv'),index=False,encoding='utf-8-sig')


if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
