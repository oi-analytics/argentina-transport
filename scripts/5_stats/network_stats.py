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

3. Shapefile of administrative boundaries of Argentina with attributes:
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
    road_edges = pd.read_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8-sig')
    road_nodes = pd.read_csv(os.path.join(data_path,'network','road_nodes.csv'),encoding='utf-8-sig')
    print ('* Number of road edges:',len(road_edges.index))
    print ('* Number of road nodes:',len(road_nodes.index))


    road_quality = road_edges[road_edges['road_type'] == 'national'][['road_quality','length']]
    road_quality['score'] = 0
    mask = (road_quality['road_quality'] > 0) & (road_quality['road_quality'] <= 3)
    road_quality.loc[mask, 'score'] = 1
    mask = (road_quality['road_quality'] > 3) & (road_quality['road_quality'] <= 5)
    road_quality.loc[mask, 'score'] = 2
    mask = (road_quality['road_quality'] > 5) & (road_quality['road_quality'] <= 7)
    road_quality.loc[mask, 'score'] = 3
    mask = (road_quality['road_quality'] > 7)
    road_quality.loc[mask, 'score'] = 4
    road_quality_lengths = road_quality[['score','length']].groupby(['score'])['length'].sum().reset_index().to_csv(os.path.join(output_path,'network_stats','national_road_quality.csv'))

    road_service = road_edges[road_edges['road_type'] == 'national'][['road_service','length']]
    road_service['score'] = 0
    mask = (road_service['road_service'] > 0) & (road_service['road_service'] <= 1)
    road_service.loc[mask, 'score'] = 1
    mask = (road_service['road_service'] > 1) & (road_service['road_service'] <= 2)
    road_service.loc[mask, 'score'] = 2
    mask = (road_service['road_service'] > 2) & (road_service['road_service'] <= 3)
    road_service.loc[mask, 'score'] = 3
    mask = (road_service['road_service'] > 3)
    road_service.loc[mask, 'score'] = 4
    road_service_lengths = road_service[['score','length']].groupby(['score'])['length'].sum().reset_index().to_csv(os.path.join(output_path,'network_stats','national_road_service.csv'))

    road_edge_types = road_edges[['road_type']].groupby(['road_type']).size().reset_index(name='counts').to_csv(os.path.join(output_path,'network_stats','road_numbers.csv'))
    road_edge_lengths = road_edges[['road_type','length']].groupby(['road_type'])['length'].sum().reset_index().to_csv(os.path.join(output_path,'network_stats','road_lengths.csv'))

    road_conditions = road_edges[['road_type',
                                'road_cond','length']].groupby(['road_type',
                                    'road_cond'])['length'].sum().reset_index().to_csv(os.path.join(output_path,'network_stats','road_conditions.csv'))

    road_surface = road_edges[['road_type',
                                'surface','length']].groupby(['road_type',
                                    'surface'])['length'].sum().reset_index().to_csv(os.path.join(output_path,'network_stats','road_surface.csv'))


    '''National bridge stats
    '''
    road_bridges = pd.read_csv(os.path.join(data_path,'network','bridges.csv'),encoding='utf-8-sig')
    print ('* Number of road bridges:',len(road_bridges.index))

    bridge_numbers = road_bridges[['structure_type']].groupby(['structure_type']).size().reset_index(name='counts').to_csv(os.path.join(output_path,'network_stats','bridge_numbers.csv'))


    '''Rail stats
    '''
    rail_edges = pd.read_csv(os.path.join(data_path,'network','rail_edges.csv'),encoding='utf-8-sig')
    rail_nodes = pd.read_csv(os.path.join(data_path,'network','rail_nodes.csv'),encoding='utf-8-sig')
    print ('* Number of rail edges:',len(rail_edges.index))
    print ('* Number of rail nodes:',len(rail_nodes.index))
    print ('* Number of rail stations:',len(rail_nodes[rail_nodes['nombre']!='0'].index))

    '''Port stats
    '''
    port_edges = pd.read_csv(os.path.join(data_path,'network','port_edges.csv'),encoding='utf-8-sig')
    port_nodes = gpd.read_file(os.path.join(data_path,'network','port_nodes.shp'),encoding='utf-8').fillna('none')
    port_nodes.drop('geometry', axis=1, inplace=True)
    port_nodes.to_csv(os.path.join(data_path,'network','port_nodes.csv'),encoding='utf-8-sig',index=False)
    print ('* Number of port edges:',len(port_edges.index))
    print ('* Number of port nodes:',len(port_nodes.index))
    print ('* Number of named ports:',len(port_nodes[port_nodes['name']!='none'].index))


    '''Airline stats
    '''
    air_edges = gpd.read_file(os.path.join(data_path,'network','air_edges.shp'),encoding='utf-8')
    air_nodes = gpd.read_file(os.path.join(data_path,'network','air_nodes.shp'),encoding='utf-8').fillna('none')
    air_nodes.drop('geometry', axis=1, inplace=True)
    air_nodes.to_csv(os.path.join(data_path,'network','air_nodes.csv'),encoding='utf-8-sig',index=False)
    air_edges.drop('geometry', axis=1, inplace=True)
    air_edges.to_csv(os.path.join(data_path,'network','air_edges.csv'),encoding='utf-8-sig',index=False)
    print ('* Number of airline routes:',len(air_edges.index))
    print ('* Number of airports:',len(air_nodes.index))



    # '''Flood stats
    # '''
    # for m in range(len(modes)):
    #     flood_df = pd.read_excel(os.path.join(output_path,'hazard_scenarios','national_scale_hazard_intersections.xlsx'),sheet_name=modes[m])
    #     flood_df = flood_df[['hazard_type','climate_scenario','probability','length']].groupby(['hazard_type','climate_scenario','probability'])['length'].sum().reset_index()
    #     flood_df['length'] = 0.001*flood_df['length']
    #     flood_df['return period'] = 1/flood_df['probability']

    #     if modes[m] == 'road':
    #         total_length = road_edges['length'].values.sum()
    #     elif modes[m] == 'rail':
    #         total_length = rail_edges['length'].values.sum()

    #     flood_df['percentage_exposure'] = 1.0*flood_df['length']/total_length
    #     flood_df.to_csv(os.path.join(output_path,'network_stats','{}_flood_exposure.csv'.format(modes[m])))


if __name__ == "__main__":
    main()
