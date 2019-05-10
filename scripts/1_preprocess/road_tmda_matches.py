"""Copy water network from `C Incoming Data` to `D Work Processes`
"""
import csv
import os
import types
import fiona
import numpy as np
import igraph as ig
import copy
import unidecode
from scipy.spatial import Voronoi
from shapely.geometry import Point, LineString
from atra.utils import *
import datetime
from tqdm import tqdm
import pandas as pd
import geopandas as gpd


def get_numeric_attributes(road_gpd,attribute_gpd,attribute_id_column,attribute_value_column,road_column_name):
    epsg_utm_20s = 32720
    road_gpd = road_gpd.to_crs(epsg=epsg_utm_20s)
    attribute_gpd = attribute_gpd.to_crs(epsg=epsg_utm_20s)
    attribute_gpd['geometry'] = attribute_gpd.geometry.progress_apply(lambda x: x.buffer(0.04))
    road_matches = gpd.sjoin(road_gpd,attribute_gpd, how="inner", op='intersects').reset_index()
    road_matches = road_matches[['edge_id',attribute_id_column,attribute_value_column]].set_index(['edge_id'])
    attribute_gpd = attribute_gpd.set_index([attribute_id_column])
    edge_ids = list(set(road_matches.index.values.tolist()))
    edge_vals = []
    for e_id in edge_ids:
        line = road_gpd.loc[road_gpd['edge_id']==e_id,'geometry'].values[0]
        attr_ids = road_matches.loc[[e_id],attribute_id_column].values.tolist()
        attr_vals = road_matches.loc[[e_id],attribute_value_column].values.tolist()
        attr_geom = attribute_gpd.loc[attr_ids,'geometry'].values.tolist()

        poly_list = list(zip(attr_vals,attr_geom))
        attr_tot = 0
        length_tot = 0
        for poly in poly_list:
            length_m = line.intersection(poly[1]).length
            attr_tot += poly[0]*length_m
            length_tot += length_m

        attr_tot = 1.0*attr_tot/length_tot
        edge_vals.append((e_id,attr_tot))

        print ('Done with attribute {} for edge {}'.format(road_column_name,e_id))

    edge_vals = pd.DataFrame(edge_vals,columns=['edge_id',road_column_name])

    del attribute_gpd
    return edge_vals

def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    attributes_desc = [
        {
            'folder_name':'tmda',
            'file_name':'vistagis_selLine.shp',
            'id_column':'nro_regist',
            'attribute':'valor',
            'attribute_rename':'tmda_count'
        },
    ]


    '''Get road edge network
    '''
    edges_geom = gpd.read_file(os.path.join(data_path,'network','road_edges.shp'),encoding='utf-8').fillna(0)
    edges_geom = edges_geom[['edge_id','geometry']]

    edges = pd.read_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8-sig')
    edges = pd.merge(edges,edges_geom,how='left',on=['edge_id'])

    del edges_geom
    '''Add the tmda data
    '''
    for a in attributes_desc:
        road_attr = gpd.read_file(os.path.join(incoming_data_path,
                        'pre_processed_network_data','roads','national_roads',
                        a['folder_name'],a['file_name']),encoding='utf-8').fillna(0)
        road_attr = road_attr[(road_attr['sentido'] == 'A') & (road_attr[a['attribute']] != -1)]
        edge_attr = get_numeric_attributes(edges[edges['road_type']=='national'][['edge_id','length','geometry']],road_attr,a['id_column'],a['attribute'],a['attribute_rename'])

        edges = pd.merge(edges,edge_attr,how='left',on=['edge_id']).fillna(0)

    edges.to_file(os.path.join(data_path,'network','road_edges.shp'),encoding = 'utf-8')
    edges.drop('geometry', axis=1, inplace=True)
    edges.to_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8-sig',index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
