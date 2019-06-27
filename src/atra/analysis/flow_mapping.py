"""Map flows on national networks

Purpose
-------

Mapping the OD node level matrix values to network paths

For all transport modes at national scale: ['road', 'rail', 'port']

The code estimates 2 values - A MIN and a MAX value of flows between each selected OD node pair
    - Based on MIN-MAX generalised costs estimates

Input data requirements
-----------------------
1. Correct paths to all files and correct input parameters
2. Excel file with mode sheets containing network graph structure and attributes
    - edge_id - String Edge ID
    - from_node - String node ID that should be present in node_id column
    - to_node - String node ID that should be present in node_id column
    - length - Float length of edge in km
    - min_time - Float minimum time of travel in hours on edge
    - max_time - Float maximum time of travel in hours on edge
    - min_time_cost - Float minimum cost of time in USD on edge
    - max_time_cost - Float maximum cost of time in USD on edge
    - min_tariff_cost - Float minimum tariff cost in USD on edge
    - max_tariff_cost - Float maximum tariff cost in USD on edge

3. Edge shapefiles for all national-scale networks with attributes:
    - edge_id - String Edge ID
    - geometry - Shapely LineString geometry of edges

4. Excel file with mode sheets containing node-level OD values with attributes:
    - origin - String node ID of Origin
    - destination - String node ID of Destination
    - min_tons -  Float values of minimum daily OD in tons
    - max_tons - Float values of maximum daily OD in tons
    - Names of the industry columns specified in the inputs

Results
-------
1. Excel sheets with results of flow mapping based on MIN-MAX generalised costs estimates:
    - origin - String node ID of Origin
    - destination - String node ID of Destination
    - origin_province - String name of Province of Origin node ID
    - destination_province - String name of Province of Destination node ID
    - min_edge_path - List of string of edge ID's for paths with minimum generalised cost flows
    - max_edge_path - List of string of edge ID's for paths with maximum generalised cost flows
    - min_distance - Float values of estimated distance for paths with minimum generalised cost flows
    - max_distance - Float values of estimated distance for paths with maximum generalised cost flows
    - min_time - Float values of estimated time for paths with minimum generalised cost flows
    - max_time - Float values of estimated time for paths with maximum generalised cost flows
    - min_gcost - Float values of estimated generalised cost for paths with minimum generalised cost flows
    - max_gcost - Float values of estimated generalised cost for paths with maximum generalised cost flows
    - industry_columns - All daily tonnages of industry columns given in the OD matrix data

2. Shapefiles
    - edge_id - String/Integer/Float Edge ID
    - geometry - Shapely LineString geomtry of edges
    - min_{industry} - Float values of estimated minimum daily industries/commodities/total volumes in tons on edges
    - max_{industry} - Float values of estimated maximum daily industries/commodities/total volumes in tons on edges

References
----------
1. Pant, R., Koks, E.E., Paltan, H., Russell, T. & Hall, J.W. (2019).
   Transport risk analysis in Argentina.
   Final Report, Oxford Infrastructure Analytics Ltd., Oxford, UK.
2. All input data folders and files referred to in the code below.

"""
import os
import subprocess
import sys
import copy

import ast
import geopandas as gpd
import igraph as ig
import numpy as np
import pandas as pd
from tqdm import tqdm
from atra.transport_flow_and_failure_functions import *
from atra.utils import *

def network_od_paths_assembly(points_dataframe, graph, transport_mode,
                                min_tons_column,max_tons_column,csv_output_path=''):
    """Assemble estimates of OD paths, distances, times, costs and tonnages on networks

    Parameters
    ----------
    points_dataframe : pandas.DataFrame
        OD nodes and their tonnages
    graph
        igraph network structure
    region_name : str
        name of Province
    excel_writer
        Name of the excel writer to save Pandas dataframe to Excel file

    Returns
    -------
    save_paths_df : pandas.DataFrame
        - origin - String node ID of Origin
        - destination - String node ID of Destination
        - min_edge_path - List of string of edge ID's for paths with minimum generalised cost flows
        - max_edge_path - List of string of edge ID's for paths with maximum generalised cost flows
        - min_netrev - Float values of estimated netrevenue for paths with minimum generalised cost flows
        - max_netrev - Float values of estimated netrevenue for paths with maximum generalised cost flows
        - min_croptons - Float values of estimated crop tons for paths with minimum generalised cost flows
        - max_croptons - Float values of estimated crop tons for paths with maximum generalised cost flows
        - min_distance - Float values of estimated distance for paths with minimum generalised cost flows
        - max_distance - Float values of estimated distance for paths with maximum generalised cost flows
        - min_time - Float values of estimated time for paths with minimum generalised cost flows
        - max_time - Float values of estimated time for paths with maximum generalised cost flows
        - min_gcost - Float values of estimated generalised cost for paths with minimum generalised cost flows
        - max_gcost - Float values of estimated generalised cost for paths with maximum generalised cost flows

    """
    save_paths = []
    points_dataframe = points_dataframe.set_index('origin_id')
    origins = list(set(points_dataframe.index.values.tolist()))
    for origin in origins:
        try:
            destinations = points_dataframe.loc[[origin], 'destination_id'].values.tolist()

            get_min_path, get_min_dist, get_min_time, get_min_gcost = network_od_path_estimations(
                graph, origin, destinations, 'min_gcost', 'min_time')
            get_max_path, get_max_dist, get_max_time, get_max_gcost = network_od_path_estimations(
                graph, origin, destinations,'max_gcost', 'max_time')

            if min_tons_column == max_tons_column:
                tons = points_dataframe.loc[[origin], max_tons_column].values
                save_paths += list(zip([origin]*len(destinations), destinations, get_min_path, get_max_path,
                                       get_min_dist, get_max_dist, get_min_time, get_max_time, list(tons*np.array(get_min_gcost)), list(tons*np.array(get_max_gcost))))
            else:
                min_tons = points_dataframe.loc[[origin], min_tons_column].values
                max_tons = points_dataframe.loc[[origin], max_tons_column].values
                save_paths += list(zip([origin]*len(destinations), destinations, get_min_path, get_max_path,
                                       get_min_dist, get_max_dist, get_min_time, get_max_time, list(min_tons*np.array(get_min_gcost)), list(max_tons*np.array(get_max_gcost))))


            print("done with {0}".format(origin))
        except:
            print('* no path between {}-{}'.format(origin,destinations))

    cols = [
        'origin_id', 'destination_id', 'min_edge_path', 'max_edge_path','min_distance', 'max_distance', 'min_time', 'max_time',
        'min_gcost', 'max_gcost'
    ]
    save_paths_df = pd.DataFrame(save_paths, columns=cols)
    points_dataframe = points_dataframe.reset_index()
    save_paths_df = pd.merge(save_paths_df, points_dataframe, how='left', on=[
                             'origin_id', 'destination_id']).fillna(0)

    save_paths_df = save_paths_df[(save_paths_df[max_tons_column] > 0)
                                  & (save_paths_df['origin_id'] != 0)]
    if csv_output_path:
        save_paths_df.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
    del save_paths

    return save_paths_df


def main():
    """Estimate flows

    1. Specify the paths from where you want to read and write:
        - Input data
        - Intermediate calcuations data
        - Output results

    2. Supply input data and parameters
        - Percentage of OD flow we want to send along path: FLoat type
        - Names of modes: List of dictionaries
        - Names of min-max tonnage column names in OD data

    3. Give the paths to the input data files:
        - Network edges csv files
        - OD daily flows csv file

    4. Specify the output files and paths to be created
    """
    tqdm.pandas()
    incoming_data_path, data_path, calc_path, output_path = load_config()['paths']['incoming_data'],load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    percentage = [100]
    index_cols = ['origin_id','destination_id','destination_province', 'destination_zone_id', 'origin_province', 'origin_zone_id']
    modes = [
                {
                'sector':'road',
                'min_tons_column':'total_tons',
                'max_tons_column':'total_tons',
                },
                {
                'sector':'rail',
                'min_tons_column':'min_total_tons',
                'max_tons_column':'max_total_tons',
                },
                {
                'sector':'port',
                'min_tons_column':'min_total_tons',
                'max_tons_column':'max_total_tons',
                }
    ]

    # Give the paths to the input data files
    network_data_path = os.path.join(data_path,'network')

    # Specify the output files and paths to be created
    flow_shp_dir = os.path.join(output_path, 'flow_mapping_shapefiles')
    if os.path.exists(flow_shp_dir) == False:
        os.mkdir(flow_shp_dir)

    flow_csv_dir = os.path.join(output_path, 'flow_mapping_combined')
    if os.path.exists(flow_csv_dir) == False:
        os.mkdir(flow_csv_dir)

    flow_paths_dir = os.path.join(output_path, 'flow_mapping_paths')
    if os.path.exists(flow_paths_dir) == False:
        os.mkdir(flow_paths_dir)

    for perct in percentage:
        # Start the OD flow mapping process
        for m in range(len(modes)):
            # Load mode igraph network and GeoDataFrame
            print ('* Loading {} igraph network and GeoDataFrame'.format(modes[m]['sector']))
            edges_in = pd.read_csv(os.path.join(network_data_path,'{}_edges.csv'.format(modes[m]['sector'])),encoding='utf-8-sig')
            G = ig.Graph.TupleList(edges_in.itertuples(index=False), edge_attrs=list(edges_in.columns)[2:])
            del edges_in
            gdf_edges = gpd.read_file(os.path.join(network_data_path,'{}_edges.shp'.format(modes[m]['sector'])),encoding='utf-8')
            gdf_edges = gdf_edges[['edge_id','geometry']]

            # Load mode OD nodes pairs and tonnages
            print ('* Loading {} OD nodes pairs and tonnages'.format(modes[m]['sector']))
            ods = pd.read_csv(os.path.join(data_path,'OD_data','{}_nodes_daily_ods.csv'.format(modes[m]['sector'])),encoding='utf-8-sig')
            print ('Number of unique OD pairs',len(ods.index))
            
            all_ods = copy.deepcopy(ods)
            all_ods_tons_cols = [col for col in all_ods.columns.values.tolist() if col not in index_cols]

            min_ind_cols = [m for m in all_ods_tons_cols if 'min_' == m[:4]]
            max_ind_cols = [m for m in all_ods_tons_cols if 'max_' == m[:4]]
            if len(min_ind_cols) == 0 or len(max_ind_cols) == 0:
                min_ind_cols = all_ods_tons_cols
                max_ind_cols = all_ods_tons_cols
            
            all_ods[all_ods_tons_cols] = 0.01*perct*all_ods[all_ods_tons_cols]
            # Calculate mode OD paths
            print ('* Calculating {} OD paths'.format(modes[m]))
            csv_output_path = os.path.join(flow_paths_dir,'flow_paths_{}_{}_percent_assignment.csv'.format(modes[m]['sector'],int(perct)))
            all_paths = network_od_paths_assembly(
                all_ods, G, modes[m]['sector'],modes[m]['min_tons_column'],modes[m]['max_tons_column'],csv_output_path=csv_output_path)

            del all_ods
            # Create network shapefiles with flows
            print ('* Creating {} network shapefiles and csv files with flows'.format(modes[m]['sector']))

            all_paths = pd.read_csv(os.path.join(flow_paths_dir,'flow_paths_{}_{}_percent_assignment.csv'.format(modes[m]['sector'],int(perct))),encoding='utf-8-sig')
            all_paths['min_edge_path'] = all_paths.progress_apply(lambda x:ast.literal_eval(x['min_edge_path']),axis=1)
            all_paths['max_edge_path'] = all_paths.progress_apply(lambda x:ast.literal_eval(x['max_edge_path']),axis=1)

            shp_output_path = os.path.join(flow_shp_dir,'weighted_flows_{}_{}_percent.shp'.format(modes[m]['sector'],int(perct)))
            csv_output_path = os.path.join(flow_csv_dir,'weighted_flows_{}_{}_percent.csv'.format(modes[m]['sector'],int(perct)))

            write_flow_paths_to_network_files(all_paths,
                min_ind_cols,max_ind_cols,gdf_edges,
                save_csv=True, save_shapes=True, shape_output_path=shp_output_path,csv_output_path=csv_output_path)


if __name__ == '__main__':
    main()
