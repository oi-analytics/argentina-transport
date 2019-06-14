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

    # Supply input data and parameters
    modes = [
                {
                'sector':'road',
                'vehicle_wt':15,
                'min_tons_column':'total_tons',
                'max_tons_column':'total_tons',
                'min_ind_cols':['total_tons','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'Carnes','Combustibles',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS','Granos',
                    'INDUSTRIA MANUFACTURERA','Industrializados',
                    'Mineria','PESCA','Regionales','Semiterminados'],
                'max_ind_cols':['total_tons','AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                    'Carnes','Combustibles',
                    'EXPLOTACIÓN DE MINAS Y CANTERAS','Granos',
                    'INDUSTRIA MANUFACTURERA','Industrializados',
                    'Mineria','PESCA','Regionales','Semiterminados']},
                {
                'sector':'rail',
                'vehicle_wt':1,
                'min_tons_column':'min_total_tons',
                'max_tons_column':'max_total_tons',
                'min_ind_cols':['min_AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                                'min_COMERCIO','min_EXPLOTACIÓN DE MINAS Y CANTERAS',
                                'min_INDUSTRIA MANUFACTURERA','min_TRANSPORTE Y COMUNICACIONES',
                                'min_total_tons'],
                'max_ind_cols':['max_AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
                                'max_COMERCIO', 'max_EXPLOTACIÓN DE MINAS Y CANTERAS',
                                'max_INDUSTRIA MANUFACTURERA', 'max_TRANSPORTE Y COMUNICACIONES',
                                'max_total_tons']
                }
    ]

    # modes = [
    #             {
    #             'sector':'rail',
    #             'vehicle_wt':1,
    #             'min_tons_column':'min_total_tons',
    #             'max_tons_column':'max_total_tons',
    #             'min_ind_cols':['min_AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
    #                             'min_COMERCIO','min_EXPLOTACIÓN DE MINAS Y CANTERAS',
    #                             'min_INDUSTRIA MANUFACTURERA','min_TRANSPORTE Y COMUNICACIONES',
    #                             'min_total_tons'],
    #             'max_ind_cols':['max_AGRICULTURA, GANADERÍA, CAZA Y SILVICULTURA',
    #                             'max_COMERCIO', 'max_EXPLOTACIÓN DE MINAS Y CANTERAS',
    #                             'max_INDUSTRIA MANUFACTURERA', 'max_TRANSPORTE Y COMUNICACIONES',
    #                             'max_total_tons']
    #             }
    # ]


    types = ['min', 'max']
    path_types = ['min_edge_path', 'max_edge_path']
    dist_types = ['min_distance', 'max_distance']
    time_types = ['min_time', 'max_time']
    cost_types = ['min_gcost', 'max_gcost']
    percentage = [100.0]
    single_edge = True

    # Give the paths to the input data files
    network_data_path = os.path.join(data_path,'network')
    flow_paths_data = os.path.join(output_path, 'flow_mapping_paths')
    fail_scenarios_data = os.path.join(
        output_path, 'hazard_scenarios', 'national_scale_hazard_intersections.xlsx')

    # Specify the output files and paths to be created
    shp_output_path = os.path.join(output_path, 'failure_shapefiles')
    if os.path.exists(shp_output_path) == False:
        os.mkdir(shp_output_path)

    fail_output_path = os.path.join(output_path, 'failure_results')
    if os.path.exists(fail_output_path) == False:
        os.mkdir(fail_output_path)

    all_fail_scenarios = os.path.join(fail_output_path,'all_fail_scenarios')
    if os.path.exists(all_fail_scenarios) == False:
        os.mkdir(all_fail_scenarios)

    isolated_ods = os.path.join(fail_output_path,'isolated_od_scenarios')
    if os.path.exists(isolated_ods) == False:
        os.mkdir(isolated_ods)

    isolated_ods = os.path.join(fail_output_path,'isolated_od_scenarios','single_mode')
    if os.path.exists(isolated_ods) == False:
        os.mkdir(isolated_ods)

    rerouting = os.path.join(fail_output_path,'rerouting_scenarios')
    if os.path.exists(rerouting) == False:
        os.mkdir(rerouting)

    minmax_combine = os.path.join(fail_output_path,'minmax_combined_scenarios')
    if os.path.exists(minmax_combine) == False:
        os.mkdir(minmax_combine)


    for m in range(len(modes)):
        # Load mode igraph network and GeoDataFrame
        print ('* Loading {} igraph network and GeoDataFrame'.format(modes[m]['sector']))
        G_df = pd.read_csv(os.path.join(network_data_path,'{}_edges.csv'.format(modes[m]['sector'])),encoding='utf-8').fillna(0)
        gdf_edges = gpd.read_file(os.path.join(network_data_path,'{}_edges.shp'.format(modes[m]['sector'])),encoding='utf-8')
        gdf_edges = gdf_edges[['edge_id','geometry']]

        # Create failure scenarios
        print ('* Creating {} failure scenarios'.format(modes[m]['sector']))
        # fail_df = pd.read_excel(fail_scenarios_data, sheet_name=modes[m]['sector'])
        fail_df = pd.read_csv(os.path.join(
                        output_path, 
                        'hazard_scenarios', 
                        '{}_hazard_intersections.csv'.format(modes[m]['sector'])))
        ef_sc_list = edge_failure_sampling(fail_df,'edge_id')
        print ('Number of failure scenarios',len(ef_sc_list))


        # ef_sc_list = ef_sc_list[0:10]

        for perct in percentage:
            # Load flow paths
            print ('* Loading {} flow paths'.format(modes[m]['sector']))
            flow_df = pd.read_csv(os.path.join(flow_paths_data,'flow_paths_{}_{}_percent_assignment.csv'.format(modes[m]['sector'],int(perct))),encoding='utf-8')

            if modes[m]['sector'] == 'road':
                G_df = add_dataframe_generalised_costs(G_df, 1.0/modes[m]['vehicle_wt'], 1)
                e_flow = pd.read_csv(os.path.join(output_path,'flow_mapping_combined','weighted_flows_{}_{}_percent.csv'.format(modes[m]['sector'],int(perct))))[['edge_id','max_total_tons']]
                ef_df = pd.DataFrame(ef_sc_list,columns=['edge_id'])
                ef_df = pd.merge(ef_df,G_df[['edge_id','road_type']],how='left',on=['edge_id'])
                ef_df = pd.merge(ef_df,e_flow,how='left',on=['edge_id']).fillna(0)
                ef_sc_list = ef_df[(ef_df['road_type'] != '0') & (ef_df['max_total_tons'] > 0)]['edge_id'].values.tolist()
            elif modes[m]['sector'] == 'rail':
                e_flow = pd.read_csv(os.path.join(output_path,'flow_mapping_combined','weighted_flows_{}_{}_percent.csv'.format(modes[m]['sector'],int(perct))))[['edge_id','max_total_tons']]
                ef_df = pd.DataFrame(ef_sc_list,columns=['edge_id'])
                G_df = pd.merge(G_df,e_flow[['edge_id','max_total_tons']],how='left',on=['edge_id'])
                G_df = G_df[G_df['max_total_tons'] > 0]
                ef_df = pd.merge(ef_df,e_flow,how='left',on=['edge_id'])
                ef_sc_list = ef_df[ef_df['max_total_tons'] > 0]['edge_id'].values.tolist()

            print ('Number of failure scenarios',len(ef_sc_list))

            # Perform failure analysis
            edge_fail_ranges = []
            for t in range(len(types)):
                edge_path_idx = get_flow_paths_indexes_of_edges(flow_df,path_types[t])
                print ('* Performing {} {} failure analysis'.format(types[t],modes[m]['sector']))
                ef_list = []
                for f_edge in range(len(ef_sc_list)):
                    fail_edge = ef_sc_list[f_edge]
                    if isinstance(fail_edge,list) == False:
                        fail_edge = [fail_edge]
                    # ef_dict = igraph_scenario_edge_failures(
                    #         G_df, fail_edge, flow_df, modes[m]['vehicle_wt'],path_types[t],modes[m]['{}_tons_column'.format(types[t])], cost_types[t], time_types[t],modes[m]['sector'])
                    ef_dict = igraph_scenario_edge_failures_new(
                            G_df, fail_edge, flow_df,edge_path_idx, modes[m]['vehicle_wt'],path_types[t],modes[m]['{}_tons_column'.format(types[t])], cost_types[t], time_types[t],modes[m]['sector'])

                    if ef_dict:
                        ef_list += ef_dict

                    print('Done with mode {0} edge {1} out of {2} type {3}'.format(modes[m]['sector'], f_edge, len(ef_sc_list),types[t]))

                df = pd.DataFrame(ef_list)

                print ('* Assembling {} {} failure results'.format(types[t],modes[m]['sector']))
                ic_cols = modes[m]['{}_ind_cols'.format(types[t])]


                select_cols = ['origin_id', 'destination_id', 'origin_province', 'destination_province', dist_types[t], time_types[t],
                               cost_types[t]] + ic_cols
                flow_df_select = flow_df[select_cols]
                flow_df_select = merge_failure_results(flow_df_select,df,'edge_id',modes[m]['{}_tons_column'.format(types[t])],
                    dist_types[t],time_types[t],cost_types[t])

                del df

                tr_loss = '{}_tr_loss'.format(types[t])
                flow_df_select.rename(columns={'tr_loss': tr_loss}, inplace=True)

                if single_edge == True:
                    file_name = 'single_edge_failures_all_{0}_{1}_{2}_percent_disrupt.csv'.format(modes[m]['sector'], types[t],int(perct))
                else:
                    file_name = 'multiple_edge_failures_all_{0}_{1}_{2}_percent_disrupt.csv'.format(modes[m]['sector'], types[t],int(perct))

                df_path = os.path.join(all_fail_scenarios,file_name)
                flow_df_select.drop('new_path',axis=1,inplace=True)
                flow_df_select.to_csv(df_path, index=False,encoding='utf-8-sig')

                print ('* Assembling {} {} failure isolation results'.format(types[t],modes[m]['sector']))
                select_cols = ['edge_id','origin_province', 'destination_province','no_access'] + ic_cols
                edge_impact = flow_df_select[select_cols]
                edge_impact = edge_impact[edge_impact['no_access'] == 1]
                edge_impact = edge_impact.groupby(['edge_id', 'origin_province', 'destination_province'])[ic_cols].sum().reset_index()

                if single_edge == True:
                    file_name = 'single_edge_failures_od_losses_{0}_{1}_{2}_percent_disrupt.csv'.format(modes[m]['sector'], types[t],int(perct))
                else:
                    file_name = 'multiple_edge_failures_od_losses_{0}_{1}_{2}_percent_disrupt.csv'.format(modes[m]['sector'], types[t],int(perct))

                df_path = os.path.join(isolated_ods,file_name)
                edge_impact.to_csv(df_path, index = False,encoding='utf-8-sig')

                print ('* Assembling {} {} failure rerouting results'.format(types[t],modes[m]['sector']))
                edge_impact = flow_df_select[select_cols+[tr_loss]]
                edge_impact = edge_impact[edge_impact['no_access'] == 0]
                edge_impact = edge_impact.groupby(['edge_id', 'origin_province', 'destination_province'])[tr_loss,modes[m]['{}_tons_column'.format(types[t])]].sum().reset_index()

                if single_edge == True:
                    file_name = 'single_edge_failures_rerout_losses_{0}_{1}_{2}_percent_disrupt.csv'.format(modes[m]['sector'], types[t],int(perct))
                else:
                    file_name = 'multiple_edge_failures_rerout_losses_{0}_{1}_{2}_percent_disrupt.csv'.format(modes[m]['sector'], types[t],int(perct))

                df_path = os.path.join(rerouting,file_name)
                edge_impact.to_csv(df_path, index = False,encoding='utf-8-sig')

                select_cols = ['edge_id','no_access',tr_loss,modes[m]['{}_tons_column'.format(types[t])]]
                edge_impact = flow_df_select[select_cols]
                edge_impact = edge_impact.groupby(['edge_id', 'no_access'])[
                    select_cols[2:]].sum().reset_index()

                if modes[m]['min_tons_column'] == modes[m]['max_tons_column']:
                    edge_impact.rename(columns={modes[m]['{}_tons_column'.format(types[t])]:'{}_{}'.format(types[t],modes[m]['{}_tons_column'.format(types[t])])},inplace=True)
                edge_fail_ranges.append(edge_impact)
                del edge_impact

            print ('* Assembling {} min-max failure results'.format(modes[m]['sector']))
            edge_impact = edge_fail_ranges[0]
            edge_impact = pd.merge(edge_impact, edge_fail_ranges[1], how='left', on=[
                                   'edge_id', 'no_access']).fillna(0)

            del edge_fail_ranges
            if single_edge == True:
                file_name = 'single_edge_failures_minmax_{0}_{1}_percent_disrupt'.format(modes[m]['sector'],int(perct))
            else:
                file_name = 'multiple_edge_failures_minmax_{0}_{1}_percent_disrupt'.format(modes[m]['sector'],int(perct))

            df_path = os.path.join(minmax_combine,file_name + '.csv')
            edge_impact.to_csv(df_path, index = False,encoding='utf-8-sig')

            # # Create network shapefiles with flows
            # print ('* Creating {} network shapefiles with failure results'.format(modes[m]))
            # shp_path = os.path.join(
            #     shp_output_path,file_name + '.shp')
            # network_failure_assembly_shapefiles(edge_impact,gdf_edges, save_edges=True, shape_output_path=shp_path)


if __name__ == "__main__":
    main()
