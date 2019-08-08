"""Failure analysis of national-scale networks
For transport modes at national scale:

    - road
    - rail

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters
2. Excel sheets with results of flow mapping based on MIN-MAX generalised costs estimates:

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

3. Shapefiles

    - edge_id - String/Integer/Float Edge ID
    - geometry - Shapely LineString geomtry of edges

Results
-------
Csv sheets with results of failure analysis:

1. All failure scenarios

    - edge_id - String name or list of failed edges
    - origin - String node ID of Origin of disrupted OD flow
    - destination - String node ID of Destination of disrupted OD flow
    - o_region - String name of Province of Origin node ID of disrupted OD flow
    - d_region - String name of Province of Destination node ID of disrupted OD flow
    - no_access - Boolean 1 (no reroutng) or 0 (rerouting)
    - min/max_distance - Float value of estimated distance of OD journey before disruption
    - min/max_time - Float value of estimated time of OD journey before disruption
    - min/max_gcost - Float value of estimated travel cost of OD journey before disruption
    - min/max_vehicle_nums - Float value of estimated vehicles of OD journey before disruption
    - new_cost - Float value of estimated cost of OD journey after disruption
    - new_distance - Float value of estimated distance of OD journey after disruption
    - new_path - List of string edge ID's of estimated new route of OD journey after disruption
    - new_time - Float value of estimated time of OD journey after disruption
    - dist_diff - Float value of Post disruption minus per-disruption distance
    - time_diff - Float value Post disruption minus per-disruption timee
    - min/max_tr_loss - Float value of estimated change in rerouting cost
    - industry_columns - Float values of all daily tonnages of industry columns along disrupted OD pairs
    - min/max_tons - Float values of total daily tonnages along disrupted OD pairs

2. Isolated OD scenarios - OD flows with no rerouting options

    - edge_id - String name or list of failed edges
    - o_region - String name of Province of Origin node ID of disrupted OD flow
    - d_region - String name of Province of Destination node ID of disrupted OD flow
    - industry_columns - Float values of all daily tonnages of industry columns along disrupted OD pairs
    - min/max_tons - Float values of total daily tonnages along disrupted OD pairs

3. Rerouting scenarios - OD flows with rerouting options

    - edge_id - String name or list of failed edges
    - o_region - String name of Province of Origin node ID of disrupted OD flow
    - d_region - String name of Province of Destination node ID of disrupted OD flow
    - min/max_tr_loss - Float value of change in rerouting cost
    - min/max_tons - Float values of total daily tonnages along disrupted OD pairs

4. Min-max combined scenarios - Combined min-max results along each edge

    - edge_id - String name or list of failed edges
    - no_access - Boolean 1 (no reroutng) or 0 (rerouting)
    - min/max_tr_loss - Float values of change in rerouting cost
    - min/max_tons - Float values of total daily tonnages affted by disrupted edge

5. Shapefile Min-max combined scenarios - Combined min-max reults along each edge
    - edge_id - String name or list of failed edges
    - no_access - Boolean 1 (no reroutng) or 0 (rerouting)
    - min/max_tr_loss - Float values of change in rerouting cost
    - min/max_tons - Float values of total daily tonnages affted by disrupted edge
    - geometry - Shapely LineString geomtry of edges

"""
import ast
import copy
import csv
import itertools
import math
import operator
import os
import sys

import igraph as ig
import networkx as nx
import numpy as np
import pandas as pd
from atra.utils import *
from atra.transport_flow_and_failure_functions import *


def main():
    """Estimate failures

    Specify the paths from where you want to read and write:

    1. Input data
    2. Intermediate calcuations data
    3. Output results

    Supply input data and parameters

    1. Names of modes
        List of strings
    2. Unit weight of vehicle assumed for each mode
        List of float types
    3. Range of usage factors for each mode to represent uncertainty in cost estimations
        List of tuples of float types
    4. Min-max names of names of different types of attributes - paths, distance, time, cost, vehicles, tons
        List of string types
    5. Names of commodity/industry columns for which min-max tonnage column names already exist
        List of string types
    6. Percentage of OD flows that are assumed disrupted
        List of float type
    7. Condition on whether analysis is single failure or multiple failure
        Boolean condition True or False

    Give the paths to the input data files:

    1. Network edges Excel and shapefiles
    2. OD flows Excel file
    3. Costs of modes Excel file
    4. Road properties Excel file
    5. Failure scenarios Excel file

    Specify the output files and paths to be created
    """
    data_path, calc_path, output_path = load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    percentage = [100.0]
    single_edge = True

    # Give the paths to the input data files
    network_data_path = os.path.join(data_path,'network')
    fail_scenarios_data = os.path.join(
        output_path, 'hazard_scenarios', 'bridge_hazard_intersections.csv')

    # Specify the output files and paths to be created
    fail_output_path = os.path.join(output_path, 'failure_results')
    if os.path.exists(fail_output_path) == False:
        os.mkdir(fail_output_path)

    minmax_combine = os.path.join(fail_output_path,'minmax_combined_scenarios')
    if os.path.exists(minmax_combine) == False:
        os.mkdir(minmax_combine)


    # Load mode igraph network and GeoDataFrame
    print ('* Loading bridge DataFrame')
    G_df = pd.read_csv(os.path.join(network_data_path,'bridges.csv'),encoding='utf-8').fillna(0)
    G_df = G_df[['bridge_id','edge_id']]

    # Create failure scenarios
    print ('* Creating bridge failure scenarios')
    fail_df = pd.read_csv(fail_scenarios_data)
    ef_sc_list = edge_failure_sampling(fail_df,'bridge_id')
    print ('Number of failure scenarios',len(ef_sc_list))

    for perct in percentage:
        # Load flow paths
        flow_file_path = os.path.join(output_path, 'flow_mapping_combined',
                                           'weighted_flows_road_{}_percent.csv'.format(int(perct)))
        flow_file = pd.read_csv(flow_file_path,encoding='utf-8-sig').fillna(0)
        df = pd.merge(G_df,flow_file,how='left',on=['edge_id']).fillna(0)
        df.drop('edge_id',axis=1,inplace=True)
        df.to_csv(os.path.join(output_path,
                'flow_mapping_combined',
                'weighted_flows_bridge_{}_percent.csv'.format(int(perct))),
                index=False,encoding='utf-8-sig')

        del df

        print ('* Loading road failure results')
        if single_edge == True:
            file_name = 'single_edge_failures_minmax_road_{}_percent_disrupt'.format(int(perct))
        else:
            file_name = 'multiple_edge_failures_minmax_road_{1}_percent_disrupt'.format(int(perct))

        df_path = os.path.join(minmax_combine,file_name + '.csv')
        edge_impact = pd.read_csv(df_path,encoding='utf-8-sig')

        print ('* Merging road and bridge files')
        G_df = G_df[G_df['bridge_id'].isin(ef_sc_list)]
        G_df = pd.merge(G_df,edge_impact,how='left',on=['edge_id']).fillna(0)
        G_df.drop('edge_id',axis=1,inplace=True)
        G_df = G_df[G_df['max_econ_impact'] > 0]

        if single_edge == True:
            file_name = 'single_edge_failures_minmax_bridge_{}_percent_disrupt'.format(int(perct))
        else:
            file_name = 'multiple_edge_failures_minmax_bridge_{}_percent_disrupt'.format(int(perct))

        print ('* Write min-max bridge results')
        df_path = os.path.join(minmax_combine,file_name + '.csv')
        G_df.to_csv(df_path, index = False,encoding='utf-8-sig')


if __name__ == "__main__":
    main()
