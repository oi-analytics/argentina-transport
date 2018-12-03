"""Map flows on national networks

Purpose
-------

Mapping the OD node level matrix values to network paths

For all transport modes at national scale: ['road', 'rail', 'air', 'inland', 'coastal']

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
    - o_region - String name of Province of Origin node ID
    - d_region - String name of Province of Destination node ID
    - min_edge_path - List of string of edge ID's for paths with minimum generalised cost flows
    - max_edge_path - List of string of edge ID's for paths with maximum generalised cost flows
    - min_distance - Float values of estimated distance for paths with minimum generalised cost flows
    - max_distance - Float values of estimated distance for paths with maximum generalised cost flows
    - min_time - Float values of estimated time for paths with minimum generalised cost flows
    - max_time - Float values of estimated time for paths with maximum generalised cost flows
    - min_gcost - Float values of estimated generalised cost for paths with minimum generalised cost flows
    - max_gcost - Float values of estimated generalised cost for paths with maximum generalised cost flows
    - min_vehicle_nums - Float values of estimated vehicle numbers for paths with minimum generalised cost flows
    - max_vehicle_nums - Float values of estimated vehicle numbers for paths with maximum generalised cost flows
    - industry_columns - All daily tonnages of industry columns given in the OD matrix data

2. Shapefiles
    - edge_id - String/Integer/Float Edge ID
    - geometry - Shapely LineString geomtry of edges
    - min_{industry} - Float values of estimated minimum daily industries/commodities/total volumes in tons on edges
    - max_{industry} - Float values of estimated maximum daily industries/commodities/total volumes in tons on edges

References
----------
1. Pant, R., Koks, E.E., Russell, T., Schoenmakers, R. & Hall, J.W. (2018).
   Analysis and development of model for addressing climate change/disaster risks in multi-modal transport networks in Vietnam.
   Final Report, Oxford Infrastructure Analytics Ltd., Oxford, UK.
2. All input data folders and files referred to in the code below.

"""
import os
import subprocess
import sys
import copy

import geopandas as gpd
import igraph as ig
import numpy as np
import pandas as pd
from oia.transport_flow_and_failure_functions import *
from oia.utils import *

def network_od_paths_assembly(points_dataframe, graph, vehicle_wt, transport_mode,
                                         csv_output_path=''):
    """Assemble estimates of OD paths, distances, times, costs and tonnages on networks

    Parameters
    ----------
    points_dataframe : pandas.DataFrame
        OD nodes and their tonnages
    graph
        igraph network structure
    vehicle_wt : float
        unit weight of vehicle
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
        - min_vehicle_nums - Float values of estimated vehicle numbers for paths with minimum generalised cost flows
        - max_vehicle_nums - Float values of estimated vehicle numbers for paths with maximum generalised cost flows

    """
    save_paths = []
    points_dataframe = points_dataframe.set_index('origin_id')
    origins = list(set(points_dataframe.index.values.tolist()))
    for origin in origins:
        try:
            destinations = points_dataframe.loc[[origin], 'destination_id'].values.tolist()

            tons = points_dataframe.loc[[origin], 'total_tons'].values

            get_min_path, get_min_dist, get_min_time, get_min_gcost = network_od_path_estimations(
                graph, origin, destinations, 'min_gcost', 'min_time')
            get_max_path, get_max_dist, get_max_time, get_max_gcost = network_od_path_estimations(
                graph, origin, destinations,'max_gcost', 'max_time')


            save_paths += list(zip([origin]*len(destinations), destinations, get_min_path, get_max_path,
                                   get_min_dist, get_max_dist, get_min_time, get_max_time, list(tons*np.array(get_min_gcost)), list(tons*np.array(get_max_gcost))))
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

    save_paths_df = save_paths_df[(save_paths_df['total_tons'] > 0)
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
        - Names of modes: List of strings
        - Unit weight of vehicle assumed for each mode: List of float types
        - Names of all industry sector and crops in VITRANSS2 and IFPRI datasets: List of string types
        - Names of commodity/industry columns for which min-max tonnage column names already exist: List of string types
        - Percentage of OD flow we want to send along path: FLoat type

    3. Give the paths to the input data files:
        - Network edges Excel file
        - OD flows Excel file
        - Costs of modes Excel file
        - Road properties Excel file

    4. Specify the output files and paths to be created
    """
    incoming_data_path, data_path, calc_path, output_path = load_config()['paths']['incoming_data'],load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    # modes = ['road', 'rail', 'air', 'inland', 'coastal']
    modes = ['road']
    veh_wt = [25, 800, 0, 800, 1200]
    # percentage = [10,90,100]
    percentage = [100]
    total_tons = 'total_tons'
    index_cols = ['origin_id','destination_id','destination_province', 'destination_zone_id', 'origin_province', 'origin_zone_id']

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
            print ('* Loading {} igraph network and GeoDataFrame'.format(modes[m]))
            edges_in = pd.read_csv(os.path.join(network_data_path,'{}_edges.csv'.format(modes[m])),encoding='utf-8')
            G = ig.Graph.TupleList(edges_in.itertuples(index=False), edge_attrs=list(edges_in.columns)[2:])
            G = add_igraph_generalised_costs(G, 1.0/veh_wt[m], 1)
            del edges_in
            gdf_edges = gpd.read_file(os.path.join(network_data_path,'{}_edges.shp'.format(modes[m])),encoding='utf-8')
            gdf_edges = gdf_edges[['edge_id','geometry']]

            # Load mode OD nodes pairs and tonnages
            print ('* Loading {} OD nodes pairs and tonnages'.format(modes[m]))
            ods = pd.read_csv(os.path.join(incoming_data_path,'road_ods','road_ods.csv'),encoding='utf-8-sig')
            print ('Number of unique OD pairs',len(ods.index))
            if modes[m] == 'road':
                ods = ods[1.0*ods[total_tons]/365.0 > 0.5]

            print ('Number of unique OD pairs',len(ods.index))
            all_ods = copy.deepcopy(ods)
            # all_ods_tons_cols = [col for col in all_ods.columns.values.tolist() if col not in ['origin','o_region','destination','d_region']]
            all_ods_tons_cols = [col for col in all_ods.columns.values.tolist() if col not in index_cols]
            print (all_ods_tons_cols)
            if modes[m] == 'road':
                all_ods[all_ods_tons_cols] = 0.01*perct*all_ods[all_ods_tons_cols]/365.0
                all_ods['vehicle_nums'] = np.maximum(1, np.ceil(all_ods['total_tons']/veh_wt[m]))
            # Calculate mode OD paths
            print ('* Calculating {} OD paths'.format(modes[m]))
            csv_output_path = os.path.join(flow_paths_dir,'flow_paths_{}_{}_percent_assignment.csv'.format(modes[m],int(perct)))
            all_paths = network_od_paths_assembly(
                all_ods, G, veh_wt[m], modes[m],csv_output_path=csv_output_path)

            del all_ods
            # Create network shapefiles with flows
            print ('* Creating {} network shapefiles and csv files with flows'.format(modes[m]))

            # all_paths = pd.read_csv(os.path.join(flow_paths_dir,'flow_paths_{}_{}_percent_assignment.csv'.format(modes[m],int(perct))),encoding='utf-8-sig')
            shp_output_path = os.path.join(flow_shp_dir,'weighted_flows_{}_{}_percent.shp'.format(modes[m],int(perct)))
            csv_output_path = os.path.join(flow_csv_dir,'weighted_flows_{}_{}_percent.csv'.format(modes[m],int(perct)))

            min_max_exist = []
            write_flow_paths_to_network_files(all_paths,
                all_ods_tons_cols,min_max_exist,gdf_edges,
                save_csv=True, save_shapes=False, shape_output_path=shp_output_path,csv_output_path=csv_output_path)


if __name__ == '__main__':
    main()
