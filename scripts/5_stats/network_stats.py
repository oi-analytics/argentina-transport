"""Summarise length of edges/number of nodes within each boundary (commune, district, province)

Purpose
-------

Collect network attributes
    - Combine with boundary Polygons to collect network-boundary intersection attributes
    - Write final results to an Excel sheet

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters

2. Shapefiles of networks with attributes:
    - edge_id or node_id - String/Integer/Float Edge ID or Node ID of network
    - length - Float length of edge intersecting with hazards
    - geometry - Shapely geometry of edges as LineString or nodes as Points

3. Shapefile of administrative boundaries of Vietnam with attributes:
    - province_i - String/Integer ID of Province
    - pro_name_e - String name of Province in English
    - district_i - String/Integer ID of District
    - dis_name_e - String name of District in English
    - commune_id - String/Integer ID of Commune
    - name_eng - String name of Commune in English
    - geometry - Shapely geometry of boundary Polygon

Results
-------

1. Excel sheet of network-hazard-boundary intersection with attributes:
    - edge_id/node_id - String name of intersecting edge ID or node ID
    - length - Float length of intersection of edge LineString and hazard Polygon: Only for edges
    - province_id - String/Integer ID of Province
    - province_name - String name of Province in English
    - district_id - String/Integer ID of District
    - district_name - String name of District in English
    - commune_id - String/Integer ID of Commune
    - commune_name - String name of Commune in English
"""
import itertools
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from oia.utils import *
from oia.transport_flow_and_failure_functions import *
from tqdm import tqdm

def main():
    """Summarise

    1. Specify the paths from where you to read and write:
        - Input data
        - Intermediate calcuations data
        - Output results

    2. Supply input data and parameters
        - Names of the three Provinces - List of string types
        - Names of modes - List of strings
        - Names of output modes - List of strings
        - Names of hazard bands - List of integers
        - Names of hazard thresholds - List of integers
        - Condition 'Yes' or 'No' is the users wants to process results

    3. Give the paths to the input data files:
        - Commune boundary and stats data shapefile
        - String name of sheet in hazard datasets description Excel file

    4. Specify the output files and paths to be created
    """
    tqdm.pandas()
    incoming_data_path,data_path, calc_path, output_path = load_config()['paths']['incoming_data'],load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    modes = ['road','rail']
    
    '''Road stats
    '''
    road_edges = pd.read_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8')
    road_conditions = road_edges[['road_type',
                                'road_cond','length']].groupby(['road_type',
                                    'road_cond'])['length'].sum().to_csv(os.path.join(output_path,'network_stats','road_conditions.csv'))

    '''Rail stats
    '''
    rail_edges = pd.read_csv(os.path.join(data_path,'network','rail_edges.csv'),encoding='utf-8')
    rail_speeds_min = rail_edges[['linea','min_speed']].groupby(['linea'])['min_speed'].min().reset_index()
    rail_speeds_max = rail_edges[['linea','max_speed']].groupby(['linea'])['max_speed'].max().reset_index()
    rail_speeds = pd.merge(rail_speeds_min,rail_speeds_max,how='left',on=['linea']).to_csv(os.path.join(output_path,'network_stats','rail_speeds.csv'))

    '''Flood stats
    '''
    for m in range(len(modes)):
        flood_df = pd.read_excel(os.path.join(output_path,'hazard_scenarios','national_scale_hazard_intersections.xlsx'),sheet_name=modes[m])
        flood_df = flood_df[['hazard_type','probability','length']].groupby(['hazard_type','probability'])['length'].sum().reset_index()
        flood_df['length'] = 0.001*flood_df['length']
        flood_df['return period'] = 1/flood_df['probability']

        if modes[m] == 'road':
            total_length = road_edges['length'].values.sum()
        elif modes[m] == 'rail':
            total_length = rail_edges['length'].values.sum()

        flood_df['percentage_exposure'] = 1.0*flood_df['length']/total_length
        flood_df.to_csv(os.path.join(output_path,'network_stats','{}_flood_exposure.csv'.format(modes[m])))


if __name__ == "__main__":
    main()
