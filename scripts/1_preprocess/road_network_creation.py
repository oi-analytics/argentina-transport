"""Copy water network from `C Incoming Data` to `D Work Processes`
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

def assign_road_conditions(x):
    """Assign road conditions as paved or unpaved to Province roads

    Parameters
        x - Pandas DataFrame of values
            - code - Numeric code for type of asset
            - level - Numeric code for level of asset

    Returns
        String value as paved or unpaved
    """
    asset_type = str(x.road_type).lower().strip()
    asset_surface = str(x.surface).lower().strip()

    # This is an national and provincial roads with paved surfaces
    if asset_type == 'national' or asset_surface in ('paved','pavimentado'):
        return 'paved'
    else:
        # Anything else not included above
        return 'unpaved'

def assign_road_terrain_and_width(x,width_terrain_list):
    """Assign terrain as flat or mountain to national roads

    Parameters
        x - Pandas DataFrame of values
            - dia_hinh__ - String value of type of terrain

    Returns
        String value of terrain as flat or mountain
    """
    road_no = x.road_no
    if str(road_no).isdigit():
        road_no = int(road_no)
    terrain = 'flat'
    assumed_width = 0
    if x.road_type == 'national':
        for vals in width_terrain_list:
            rn = vals.road_no
            if str(vals.road_no).isdigit():
                rn = int(rn)
            if road_no == rn and x.inicio_km >= vals.inital_km and x.fin_km <= vals.final_km:
                assumed_width = vals.left_width + vals.right_width
                terrain = vals.terrain
                break

    if assumed_width == 0 and x.road_type in ('national','province'):
        assumed_width = 7.30
    elif assumed_width == 0 and x.road_type == 'rural':
        assumed_width = 3.65

    if unidecode.unidecode(str(terrain).lower().strip()) in ('llano','ondulado'):
        terrain = 'flat'
    elif unidecode.unidecode(str(terrain).lower().strip()) == 'montana':
        terrain = 'mountain'
    else:
        terrain = 'flat'

    return assumed_width, terrain

def assign_min_max_speeds_to_roads(x,speeds_list):
    """Assign terrain as flat or mountain to national roads

    Parameters
        x - Pandas DataFrame of values
            - dia_hinh__ - String value of type of terrain

    Returns
        String value of terrain as flat or mountain
    """
    road_no = x.road_no
    if str(road_no).isdigit():
        road_no = int(road_no)

    min_speed = 0
    max_speed = 0
    for vals in speeds_list:
        rn = vals.ruta
        if str(rn).isdigit():
            rn = int(rn)

        if road_no == rn and x.inicio_km >= vals.inicio and x.fin_km <= vals.fin:
            min_speed = vals.vmpes
            max_speed = vals.percentilpes
            break

    if (min_speed == 0 or isinstance(min_speed,str)) and x.road_type == 'national':
        min_speed = 70
        max_speed = 100
    elif (min_speed == 0 or isinstance(min_speed,str)) and x.road_type == 'province':
        min_speed = 60
        max_speed = 40
    elif (min_speed == 0 or isinstance(min_speed,str)):
        min_speed = 40
        max_speed = 20

    return min_speed, max_speed

def assign_minmax_time_costs_roads(x, road_costs,exchange_rate):
    design_speeds = road_costs['speed'].values.tolist()
    if x.min_speed == 0 and x.max_speed == 0:
        min_cost = 0
        max_cost = 0
    elif x.min_speed in design_speeds and x.max_speed in design_speeds:
        min_speed = x.min_speed
        max_speed = x.max_speed
    else:
        min_speed = [design_speeds[d] for d in range(len(design_speeds)-1) if design_speeds[d] <= x.min_speed < design_speeds[d+1]][0]
        max_speed = [design_speeds[d] for d in range(len(design_speeds)-1) if design_speeds[d] <= x.max_speed < design_speeds[d+1]][0]
    
    if x.road_cond == 'paved':
        min_cost = road_costs.loc[road_costs['speed'] == min_speed,'paved_cost_total'].values[0]
        max_cost = road_costs.loc[road_costs['speed'] == max_speed,'paved_cost_total'].values[0]
    elif x.road_cond == 'unpaved':
        min_cost = road_costs.loc[road_costs['speed'] == min_speed,'tierra_cost_total'].values[0]
        max_cost = road_costs.loc[road_costs['speed'] == max_speed,'tierra_cost_total'].values[0]
    else:
        min_cost = road_costs.loc[road_costs['speed'] == min_speed,'ripio_cost_total'].values[0]
        max_cost = road_costs.loc[road_costs['speed'] == max_speed,'ripio_cost_total'].values[0]

    
    return exchange_rate*min_cost*x.length, exchange_rate*max_cost*x.length

def assign_minmax_tariff_costs_roads_apply(x,tariff_costs_dataframe,exchange_rate):
    min_cost = tariff_costs_dataframe['min_tariff_cost'].values[0]*x.length*exchange_rate
    max_cost = tariff_costs_dataframe['max_tariff_cost'].values[0]*x.length*exchange_rate

    return min_cost,max_cost


def road_shapefile_to_dataframe(edges_in,road_properties_dataframe,
    road_speeds_dataframe,time_costs_dataframe,tariff_costs_dataframe,exchange_rate):
    """Create national network dataframe from inputs

    Parameters
        - edges_in - String path to edges file/network Shapefile
        - road_properties_file - String path to Excel file with road attributes
        - usage_factor - Tuple of 2-float values between 0 and 1

    Returns
        edges: Geopandas DataFrame with network edge topology and attributes
    """
    tqdm.pandas()
    add_columns = ['road_no','terrain','road_type','surface',
        'road_cond','width','length','min_speed','max_speed',
        'min_time','max_time','min_time_cost','max_time_cost','min_tariff_cost',
        'max_tariff_cost','tmda']

    edges = gpd.read_file(edges_in,encoding='utf-8').fillna(0)
    edges.columns = map(str.lower, edges.columns)
    edges.rename(columns={'id':'edge_id','from_id':'from_node','to_id':'to_node'},inplace=True)
    # edges = edges[edges['road_type'] == 'national']

    # assgin asset terrain
    road_properties_dataframe = list(road_properties_dataframe.itertuples(index=False))
    edges['width_terrain'] = edges.progress_apply(lambda x: assign_road_terrain_and_width(x,road_properties_dataframe), axis=1)
    edges[['width', 'terrain']] = edges['width_terrain'].apply(pd.Series)
    edges.drop('width_terrain', axis=1, inplace=True)

    # assign road conditon
    edges['road_cond'] = edges.progress_apply(assign_road_conditions, axis=1)

    # get the right linelength
    edges['length'] = edges.geometry.progress_apply(line_length)

    # assign minimum and maximum speed to network
    road_speeds_dataframe = list(road_speeds_dataframe.itertuples(index=False))
    edges['speed'] = edges.progress_apply(lambda x: assign_min_max_speeds_to_roads(
        x, road_speeds_dataframe), axis=1)
    edges[['min_speed', 'max_speed']] = edges['speed'].apply(pd.Series)
    edges.drop('speed', axis=1, inplace=True)

    # assign minimum and maximum travel time to network
    edges['min_time'] = edges['length']/edges['max_speed']
    edges['max_time'] = edges['length']/edges['min_speed']

    # assign minimum and maximum cost of time in USD to the network
    # the costs of time  = (unit vehicle operating cost depending upon speed in USD/km)*(length of road)
    edges['time_cost'] = edges.progress_apply(
        lambda x: assign_minmax_time_costs_roads(x, time_costs_dataframe,exchange_rate), axis=1)
    edges[['min_time_cost', 'max_time_cost']] = edges['time_cost'].apply(pd.Series)
    edges.drop('time_cost', axis=1, inplace=True)

    # assign minimum and maximum cost of tonnage in USD/ton to the network
    # the costs of time  = (unit cost of tariff in USD/ton-km)*(length in km)
    edges['tariff_cost'] = edges.progress_apply(
        lambda x: assign_minmax_tariff_costs_roads_apply(x, tariff_costs_dataframe,exchange_rate), axis=1)
    edges[['min_tariff_cost', 'max_tariff_cost']] = edges['tariff_cost'].apply(pd.Series)
    edges.drop('tariff_cost', axis=1, inplace=True)

    # make sure that From and To node are the first two columns of the dataframe
    # to make sure the conversion from dataframe to igraph network goes smooth
    edges = edges[['edge_id','from_node','to_node'] + add_columns + ['geometry']]
    edges = edges.reindex(list(edges.columns)[1:]+list(edges.columns)[:1], axis=1)

    return edges

def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    exchange_rate = 0.026

    '''Get road edge network
    '''
    road_edges_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_edges_4326.shp')
    road_nodes_path = os.path.join(incoming_data_path,'pre_processed_network_data','roads','combined_roads','combined_roads_nodes_4326.shp')
    '''Get the road properties, which are mainly the widths of national roads
    '''
    skiprows = 4
    road_properties_df = pd.read_excel(os.path.join(incoming_data_path,'5','DNV_data_recieved_06082018','Tramos por Rutas.xls'),sheet_name='Hoja1',skiprows=skiprows,encoding='utf-8-sig').fillna(0)
    # road_properties_df = road_properties_df.iloc[skiprows:]
    road_properties_df.columns = ['road_no','location','inital_km','final_km',
                                'purpose','description','length_km','left_surface',
                                'left_width','right_surface','right_width','lanes','terrain']


    road_speeds_df = pd.read_excel(os.path.join(incoming_data_path,'5','DNV_data_recieved_06082018','TMDA y Clasificación 2016.xlsx'),sheet_name='Clasificación 2016',skiprows=14,encoding='utf-8-sig').fillna(0)
    road_speeds_df.columns = map(str.lower, road_speeds_df.columns)

    time_costs_df = pd.read_excel(os.path.join(incoming_data_path,'5','Costs','Costos de Operación de Vehículos.xlsx'),sheet_name='Camión Pesado',skiprows=15,encoding='utf-8-sig').fillna(0)
    time_costs_df.columns = ['speed','tierra_cost_A','tierra_cost_B','tierra_cost_total',
                                'ripio_cost_A','ripio_cost_B','ripio_cost_total',
                                'paved_cost_A','paved_cost_B','paved_cost_total','speed_copy']

    time_costs_df = time_costs_df[time_costs_df['speed'] > 0]

    tariff_costs_df = pd.read_excel(os.path.join(incoming_data_path,'5','Costs','tariff_costs.xlsx'),sheet_name='road',encoding='utf-8')

    edges = road_shapefile_to_dataframe(road_edges_path,road_properties_df,road_speeds_df,time_costs_df,tariff_costs_df,exchange_rate)


    edges.to_file(os.path.join(data_path,'network','road_edges.shp'),encoding = 'utf-8')
    edges.drop('geometry', axis=1, inplace=True)
    edges.to_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8',index=False)

    nodes = gpd.read_file(road_nodes_path,encoding='utf-8').fillna(0)
    nodes.columns = map(str.lower, nodes.columns)
    nodes.rename(columns={'id':'node_id'},inplace=True)
    nodes.to_file(os.path.join(data_path,'network', 'road_nodes.shp'),encoding = 'utf-8')
    nodes.drop('geometry', axis=1, inplace=True)
    nodes.to_csv(os.path.join(data_path,'network','road_nodes.csv'),encoding='utf-8',index=False)

if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
