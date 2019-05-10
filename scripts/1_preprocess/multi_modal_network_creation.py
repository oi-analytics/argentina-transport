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
from shapely.geometry import Point, LineString
from atra.utils import *
import datetime
from tqdm import tqdm

def network_shapefile_to_network(edges_in, mode_properties_file, mode_name, speed_min, speed_max,utilization_factors):
    """Create igraph network from inputs

    Parameters
        - edges_in - String path to edges file/network Shapefile
        - mode_properties_file - String path to Excel file with mode attributes
        - mode_name - String name of mode
        - speed_min - Float value of minimum assgined speed
        - speed_max - Float value of maximum assgined speed
        - usage_factor - Tuple of 2-float values between 0 and 1

    Returns
        G - Igraph object with network edge topology and attributes
    """
    edges = network_shapefile_to_dataframe(
        edges_in, mode_properties_file, mode_name, speed_min, speed_max,utilization_factors)
    G = ig.Graph.TupleList(edges.itertuples(index=False), edge_attrs=list(edges.columns)[2:])

    # only keep connected network
    return G


def assign_minmax_tariff_costs_multi_modal_apply(x, cost_dataframe):
    """Assign tariff costs on multi-modal network links in Argentina

    Parameters
        - x - Pandas dataframe with values
            - port_type - String name of port type
            - from_mode - String name of mode
            - to_mode - String name of mode
            - other_mode - String name of mode
        - cost_dataframe - Pandas Dataframe with costs

    Returns
        - min_tariff_cost - Float minimum assigned tariff cost in USD/ton
        - max_tariff_cost - Float maximum assigned tariff cost in USD/ton
    """
    min_tariff_cost = 0
    max_tariff_cost = 0
    cost_list = list(cost_dataframe.itertuples(index=False))
    for cost_param in cost_list:
        if cost_param.one_mode == x.port_type and cost_param.other_mode == x.to_mode:
            min_tariff_cost = cost_param.tariff_min_usd
            max_tariff_cost = cost_param.tariff_max_usd
            break
        elif cost_param.one_mode == x.to_mode and cost_param.other_mode == x.from_mode:
            min_tariff_cost = cost_param.tariff_min_usd
            max_tariff_cost = cost_param.tariff_max_usd
            break
        elif cost_param.one_mode == x.to_mode and cost_param.other_mode == x.port_type:
            min_tariff_cost = cost_param.tariff_min_usd
            max_tariff_cost = cost_param.tariff_max_usd
            break
        elif cost_param.one_mode == x.from_mode and cost_param.other_mode == x.to_mode:
            min_tariff_cost = cost_param.tariff_min_usd
            max_tariff_cost = cost_param.tariff_max_usd
            break

    return min_tariff_cost, max_tariff_cost


def multi_modal_shapefile_to_dataframe(edges_in, mode_properties_file, mode_name, length_threshold,usage_factors):
    """Create multi-modal network dataframe from inputs

    Parameters
        - edges_in - String path to edges file/network Shapefile
        - mode_properties_file - String path to Excel file with mode attributes
        - mode_name - String name of mode
        - length_threshold - Float value of threshold in km of length of multi-modal links
        - usage_factor - Tuple of 2-float values between 0 and 1

    Returns
        edges - Geopandas DataFrame with network edge topology and attributes
    """

    edges = gpd.read_file(edges_in,encoding='utf-8')
    edges.columns = map(str.lower, edges.columns)

    # assgin asset terrain

    # get the right linelength
    edges['length'] = edges.geometry.apply(line_length)

    cost_values_df = pd.read_excel(mode_properties_file, sheet_name=mode_name)

    # assign minimum and maximum cost of tonnage in USD/ton to the network
    # the costs of time  = (unit cost of tariff in USD/ton)
    edges['tariff_cost'] = edges.apply(
        lambda x: assign_minmax_tariff_costs_multi_modal_apply(x, cost_values_df), axis=1)
    edges[['min_tariff_cost', 'max_tariff_cost']] = edges['tariff_cost'].apply(pd.Series)
    edges.drop('tariff_cost', axis=1, inplace=True)

    edges['min_time'] = 0
    edges['max_time'] = 0
    edges['min_time_cost'] = 0
    edges['max_time_cost'] = 0

    edges['min_time_cost'] = (1 + usage_factors[0])*edges['min_time_cost']
    edges['max_time_cost'] = (1 + usage_factors[1])*edges['max_time_cost']
    edges['min_tariff_cost'] = (1 + usage_factors[0])*edges['min_tariff_cost']
    edges['max_tariff_cost'] = (1 + usage_factors[1])*edges['max_tariff_cost']
    # make sure that From and To node are the first two columns of the dataframe
    # to make sure the conversion from dataframe to igraph network goes smooth
    edges = edges.reindex(list(edges.columns)[2:]+list(edges.columns)[:2], axis=1)
    edges = edges[edges['length'] < length_threshold]

    return edges


def multi_modal_shapefile_to_network(edges_in, mode_properties_file, mode_name, length_threshold,utilization_factors):
    """Create multi-modal igraph network dataframe from inputs

    Parameters
        - edges_in - String path to edges file/network Shapefile
        - mode_properties_file - String path to Excel file with mode attributes
        - mode_name - String name of mode
        - length_threshold - Float value of threshold in km of length of multi-modal links
        - usage_factor - Tuple of 2-float values between 0 and 1

    Returns
        G - Igraph object with network edge topology and attributes
    """
    edges = multi_modal_shapefile_to_dataframe(
        edges_in, mode_properties_file, mode_name, length_threshold,utilization_factors)
    G = ig.Graph.TupleList(edges.itertuples(index=False), edge_attrs=list(edges.columns)[2:])

    # only keep connected network
    return G

def create_from_to_mode_mapping(from_mode_df,to_mode_df,from_mode,to_mode):
    edge_df = copy.deepcopy(from_mode_df)
    edge_df.rename(columns={'node_id':'from_node'},inplace=True)
    edge_df['from_mode'] = from_mode
    sindex_nodes = to_mode_df.sindex
    edge_df['to_node'] = edge_df.geometry.progress_apply(lambda x: get_nearest_node(x, sindex_nodes, to_mode_df, 'node_id'))
    edge_df['to_mode'] = to_mode
    edge_df['to_geometry'] = edge_df.geometry.progress_apply(lambda x: get_nearest_node(x, sindex_nodes, to_mode_df, 'geometry'))
    edge_df.rename(columns={'geometry':'from_geometry'},inplace=True)

    return edge_df

def get_operational_state(x,operational_nodes):
    state = 'operational'
    if ('rail' in x.from_node) or ('rail' in x.to_node):
        if (x.from_node in operational_nodes) or (x.to_node in operational_nodes):
            state = 'operational'
        else:
            state = 'non operational'

    return state

def main(config):
    tqdm.pandas()
    incoming_data_path = config['paths']['incoming_data']
    data_path = config['paths']['data']
    output_path = config['paths']['output']

    road_nodes_path = os.path.join(data_path,'network','road_nodes.shp')
    road_nodes = gpd.read_file(road_nodes_path,encoding='utf-8').fillna(0)
    road_nodes = road_nodes.to_crs({'init': 'epsg:4326'})
    road_nodes.columns = map(str.lower, road_nodes.columns)
    road_nodes.rename(columns={'id':'node_id'},inplace=True)
    road_nodes = road_nodes[['node_id','geometry']]

    rail_nodes_path = os.path.join(data_path,'network','rail_nodes.shp')
    rail_nodes = gpd.read_file(rail_nodes_path,encoding='utf-8').fillna(0)
    rail_nodes = rail_nodes.to_crs({'init': 'epsg:4326'})
    rail_nodes.columns = map(str.lower, rail_nodes.columns)
    rail_nodes = rail_nodes[['node_id','geometry']]

    port_nodes_path = os.path.join(data_path,'network','port_nodes.shp')
    port_nodes = gpd.read_file(port_nodes_path,encoding='utf-8').fillna('none')
    port_nodes = port_nodes.to_crs({'init': 'epsg:4326'})
    port_nodes.columns = map(str.lower, port_nodes.columns)
    port_nodes.rename(columns={'id':'node_id'},inplace=True)
    port_nodes = port_nodes[port_nodes['name'] != 'none']
    port_nodes = port_nodes[['node_id','geometry']]


    '''
    Find closest rail, port and road points
    '''
    multi_edge_df = []

    multi_edge_df.append(create_from_to_mode_mapping(rail_nodes,road_nodes,'rail','road'))
    multi_edge_df.append(create_from_to_mode_mapping(rail_nodes,port_nodes,'rail','port'))
    multi_edge_df.append(create_from_to_mode_mapping(port_nodes,road_nodes,'port','road'))

    multi_edge_df = pd.concat(multi_edge_df,axis=0,sort='False', ignore_index=True)
    multi_edge_df['geometry'] = multi_edge_df.progress_apply(lambda x: LineString([x.from_geometry,x.to_geometry]),axis = 1)
    multi_edge_df['length'] = multi_edge_df.geometry.progress_apply(line_length)
    multi_edge_df.drop(['from_geometry','to_geometry'],axis=1,inplace=True)
    multi_edge_df = multi_edge_df[multi_edge_df['length'] < 2]

    '''Add costs to multi-modal edges
    '''
    multi_edge_df['min_time'] = 0
    multi_edge_df['max_time'] = 0
    multi_edge_df['min_gcost'] = 0
    multi_edge_df['max_gcost'] = 0

    '''Find the non-operational rail links
    '''
    G_df = pd.read_csv(os.path.join(data_path,'network','rail_edges.csv'),encoding='utf-8').fillna(0)
    e_flow = pd.read_csv(os.path.join(output_path,'flow_mapping_combined','weighted_flows_rail_100_percent.csv'))[['edge_id','max_total_tons']]
    G_df = pd.merge(G_df,e_flow[['edge_id','max_total_tons']],how='left',on=['edge_id'])
    G_nodes = list(set(G_df[G_df['max_total_tons'] > 0]['from_node'].values.tolist() + G_df[G_df['max_total_tons'] > 0]['to_node'].values.tolist()))
    multi_edge_df['operation_state'] = multi_edge_df.progress_apply(lambda x: get_operational_state(x,G_nodes),axis = 1)

    '''Create edges and arrange columns
    '''
    multi_edge_df['edge_id'] = ['{}_{}'.format('multie', i) for i in range(len(multi_edge_df.index))]
    cols = [c for c in multi_edge_df.columns.values.tolist() if c not in ['from_node','to_node']]
    multi_edge_df = multi_edge_df[['from_node','to_node'] + cols]

    '''Write the output to files
    '''
    multi_edge_df = gpd.GeoDataFrame(multi_edge_df,geometry='geometry',crs={'init' :'epsg:4326'})
    multi_edge_df.to_file(os.path.join(data_path,'network','multi_edges.shp'),encoding='utf-8')
    multi_edge_df.drop('geometry',axis=1,inplace=True)
    multi_edge_df.to_csv(os.path.join(data_path,'network','multi_edges.csv'),index=False,encoding='utf-8-sig')







if __name__ == '__main__':
    CONFIG = load_config()
    main(CONFIG)
