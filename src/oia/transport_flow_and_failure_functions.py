"""Functions used in the provincial and national-scale network failure analysis
"""
import ast
import copy
import csv
import itertools
import math
import operator
import os
import sys

import json
import igraph as ig
import networkx as nx
import numpy as np
import pandas as pd
from oia.utils import *
from tqdm import tqdm

def spatial_scenario_selection(network_shapefile, polygon_dataframe, hazard_dictionary, data_dictionary, network_type ='nodes'):
    """Intersect network edges/nodes and boundary Polygons to collect boundary and hazard attributes

    Parameters
        - network_shapefile - Shapefile of edge LineStrings or node Points
        - polygon_shapefile - Shapefile of boundary Polygons
        - hazard_dictionary - Dictionary of hazard attributes
        - data_dictionary - Dictionary of network-hazard-boundary intersection attributes
        - network_type - String value -'edges' or 'nodes' - Default = 'nodes'
        - name_province - String name of province if needed - Default = ''

    Outputs
        data_dictionary - Dictionary of network-hazard-boundary intersection attributes:
            - edge_id/node_id - String name of intersecting edge ID or node ID
            - length - Float length of intersection of edge LineString and hazard Polygon: Only for edges
            - province_id - String/Integer ID of Province
            - province_name - String name of Province in English
            - district_id - String/Integer ID of District
            - district_name - String name of District in English
            - commune_id - String/Integer ID of Commune
            - commune_name - String name of Commune in English
            - hazard_attributes - Dictionary of all attributes from hazard dictionary
    """
    line_gpd = gpd.read_file(network_shapefile)
    poly_gpd = polygon_dataframe


    if len(line_gpd.index) > 0 and len(poly_gpd.index) > 0:
        print (network_shapefile,len(line_gpd.index),len(poly_gpd.index))
        line_gpd.columns = map(str.lower, line_gpd.columns)
        poly_gpd.columns = map(str.lower, poly_gpd.columns)

        # create spatial index
        poly_sindex = poly_gpd.sindex

        poly_sindex = poly_gpd.sindex
        for l_index, lines in line_gpd.iterrows():
            intersected_polys = poly_gpd.iloc[list(
                poly_sindex.intersection(lines.geometry.bounds))]
            for p_index, poly in intersected_polys.iterrows():
                if (lines['geometry'].intersects(poly['geometry']) is True) and (poly.geometry.is_valid is True) and (lines.geometry.is_valid is True):
                    if network_type == 'edges':
                        value_dictionary = {'edge_id': lines['edge_id'], 'length': 1000.0*line_length(lines['geometry'].intersection(poly['geometry'])),
                                            'province_id': poly['province_id'], 'province_name': poly['province_name'],
                                            'department_id': poly['department_id'], 'department_name': poly['department_name']}
                    elif network_type == 'nodes':
                        value_dictionary = {'node_id': lines['node_id'],
                                            'province_id': poly['province_id'], 'province_name': poly['province_name'],
                                            'department_id': poly['department_id'], 'department_name': poly['department_name']}

                    data_dictionary.append({**value_dictionary, **hazard_dictionary})

    del line_gpd, poly_gpd
    return data_dictionary

def combine_hazards_and_network_attributes_and_impacts(hazard_dataframe, network_dataframe):
    hazard_dataframe.rename(columns={
        'length': 'exposure_length',
        'min_depth': 'min_flood_depth',
        'max_depth': 'max_flood_depth'
    }, inplace=True)

    network_dataframe.rename(columns={'length': 'edge_length'}, inplace=True)
    network_dataframe['edge_length'] = 1000.0*network_dataframe['edge_length']

    all_edge_fail_scenarios = pd.merge(hazard_dataframe, network_dataframe, on=[
        'edge_id'], how='left').fillna(0)

    all_edge_fail_scenarios['percent_exposure'] = 100.0 * \
        all_edge_fail_scenarios['exposure_length']/all_edge_fail_scenarios['edge_length']

    del hazard_dataframe, network_dataframe

    return all_edge_fail_scenarios


def create_hazard_scenarios_for_adaptation(all_edge_fail_scenarios, index_cols, length_thr):
    all_edge_fail_scenarios = all_edge_fail_scenarios.set_index(index_cols)
    scenarios = list(set(all_edge_fail_scenarios.index.values.tolist()))
    print('Number of failure scenarios', len(scenarios))
    scenarios_list = []
    for sc in scenarios:
        min_height = max(all_edge_fail_scenarios.loc[[sc], 'min_flood_depth'].values.tolist())
        max_height = max(all_edge_fail_scenarios.loc[[sc], 'max_flood_depth'].values.tolist())
        prob = all_edge_fail_scenarios.loc[[sc], 'probability'].values
        if len(list(set(prob))) > 1:
            exposure_len = all_edge_fail_scenarios.loc[[sc], 'exposure_length'].values
            per = all_edge_fail_scenarios.loc[[sc], 'percent_exposure'].values

            prob_tup = list(zip(prob, exposure_len, per))
            u_pr = sorted(list(set(prob.tolist())))
            exposure_len = []
            per = []
            r_wt = []
            for pr in u_pr:
                per_exp = sum([z for (x, y, z) in prob_tup if x == pr])
                exp_len = sum([y for (x, y, z) in prob_tup if x == pr])
                if per_exp > 100.0:
                    exposure_len.append(100.0*exp_len/per_exp)
                    per.append(100.0)
                    r_wt.append(1.0)
                else:
                    exposure_len.append(exp_len)
                    per.append(per_exp)
                    if exp_len < length_thr:
                        r_wt.append(0.01*per_exp)
                    else:
                        r_wt.append(1.0)

            max_exposure_len = max(exposure_len)
            min_exposure_len = min(exposure_len)

            min_per = min(per)
            max_per = max(per)
            min_dur = 0.01*min_per
            max_dur = 0.01*max_per
            risk_wt = 0
            dam_wt = 0
            for p in range(len(u_pr)-1):
                risk_wt += 0.5*(u_pr[p+1]-u_pr[p])*(r_wt[p+1]+r_wt[p])
                dam_wt += 0.5*(u_pr[p+1]-u_pr[p])*(exposure_len[p+1]+exposure_len[p])

        else:
            prob_wt = prob[0]
            min_exposure_len = sum(
                all_edge_fail_scenarios.loc[[sc], 'exposure_length'].values.tolist())
            min_per = sum(all_edge_fail_scenarios.loc[[sc], 'percent_exposure'].values.tolist())
            if min_per > 100.0:
                min_exposure_len = 100.0*min_exposure_len/min_per
                min_per = 100.0

            max_per = min_per
            max_exposure_len = min_exposure_len
            dam_wt = max_exposure_len
            min_dur = 0.01*min_per
            if max_exposure_len < length_thr:
                max_dur = 0.01*max_per
                risk_wt = 0.01*max_per*prob_wt
            else:
                max_dur = 1.0
                risk_wt = prob_wt

        scenarios_list.append(list(sc) + [min_height, max_height,
                                          min_per, max_per, min_dur, max_dur, min_exposure_len,
                                          max_exposure_len, risk_wt, dam_wt])

    new_cols = ['min_flood_depth', 'max_flood_depth', 'min_exposure_percent',
                'max_exposure_percent', 'min_duration_wt', 'max_duration_wt',
                'min_exposure_length', 'max_exposure_length', 'risk_wt', 'dam_wt']
    scenarios_df = pd.DataFrame(scenarios_list, columns=index_cols + new_cols)

    del all_edge_fail_scenarios, scenarios_list
    return scenarios_df

def swap_min_max(x, min_col, max_col):
    """Swap columns if necessary
    """
    if x[min_col] < 0 and x[max_col] < 0:
        if abs(x[min_col]) > abs(x[max_col]):
            return x[max_col], x[min_col]
        else:
            return x[min_col], x[max_col]
    else:
        if x[min_col] > x[max_col]:
            return x[max_col], x[min_col]
        else:
            return x[min_col], x[max_col]

def add_igraph_generalised_costs(G, vehicle_numbers, tonnage):
    # G.es['max_cost'] = list(cost_param*(np.array(G.es['length'])/np.array(G.es['max_speed'])))
    # G.es['min_cost'] = list(cost_param*(np.array(G.es['length'])/np.array(G.es['min_speed'])))
    # print (G.es['max_time'])
    G.es['max_gcost'] = list(

            vehicle_numbers * np.array(G.es['max_time_cost'])
            + tonnage * np.array(G.es['max_tariff_cost'])
    )
    G.es['min_gcost'] = list(
            vehicle_numbers * np.array(G.es['min_time_cost'])
            + tonnage * np.array(G.es['min_tariff_cost'])
    )

    return G

def network_od_path_estimations(graph,
    source, target, cost_criteria, time_criteria):
    """Estimate the paths, distances, times, and costs for given OD pair

    Parameters
    ---------
    graph
        igraph network structure
    source
        String/Float/Integer name of Origin node ID
    source
        String/Float/Integer name of Destination node ID
    tonnage : float
        value of tonnage
    vehicle_weight : float
        unit weight of vehicle
    cost_criteria : str
        name of generalised cost criteria to be used: min_gcost or max_gcost
    time_criteria : str
        name of time criteria to be used: min_time or max_time
    fixed_cost : bool

    Returns
    -------
    edge_path_list : list[list]
        nested lists of Strings/Floats/Integers of edge ID's in routes
    path_dist_list : list[float]
        estimated distances of routes
    path_time_list : list[float]
        estimated times of routes
    path_gcost_list : list[float]
        estimated generalised costs of routes

    """
    # if vehicle_weight == 0 and tonnage == 0:
    #     vehicle_weight = 1
    #     tonnage = 1
    # elif vehicle_weight == 0 and tonnage > 0:
    #     vehicle_weight = tonnage

    # graph = add_igraph_generalised_costs(graph, np.ceil(
    #     tonnage/vehicle_weight), tonnage)

    paths = graph.get_shortest_paths(source, target, weights=cost_criteria, output="epath")

    edge_path_list = []
    path_dist_list = []
    path_time_list = []
    path_gcost_list = []

    for path in paths:
        edge_path = []
        path_dist = 0
        path_time = 0
        path_gcost = 0
        if path:
            for n in path:
                edge_path.append(graph.es[n]['edge_id'])
                path_dist += graph.es[n]['length']
                path_time += graph.es[n][time_criteria]
                path_gcost += graph.es[n][cost_criteria]

        edge_path_list.append(edge_path)
        path_dist_list.append(path_dist)
        path_time_list.append(path_time)
        path_gcost_list.append(path_gcost)

    return edge_path_list, path_dist_list, path_time_list, path_gcost_list

def write_flow_paths_to_network_files(save_paths_df,
    min_industry_columns,max_industry_columns,gdf_edges, save_csv=True, save_shapes=True, shape_output_path='',csv_output_path=''):
    """Write results to Shapefiles

    Outputs ``gdf_edges`` - a shapefile with minimum and maximum tonnage flows of all
    commodities/industries for each edge of network.

    Parameters
    ---------
    save_paths_df
        Pandas DataFrame of OD flow paths and their tonnages
    industry_columns
        List of string names of all OD commodities/industries indentified
    min_max_exist
        List of string names of commodity/industry columns for which min-max tonnage column names already exist
    gdf_edges
        GeoDataFrame of network edge set
    save_csv
        Boolean condition to tell code to save created edge csv file
    save_shapes
        Boolean condition to tell code to save created edge shapefile
    shape_output_path
        Path where the output shapefile will be stored
    csv_output_path
        Path where the output csv file will be stored

    """
    edge_flows_min = []
    edge_flows_max = []
    for iter_, path in save_paths_df.iterrows():
        path_ind_list_min = []
        path_ind_list_max = []

        # min_path = ast.literal_eval(path['min_edge_path'])
        # max_path = ast.literal_eval(path['max_edge_path'])

        min_path = path['min_edge_path']
        max_path = path['max_edge_path']
        path_ind_list_min.append(min_path)
        path_ind_list_max.append(max_path)
        if min_industry_columns == max_industry_columns: 
            for ind in min_industry_columns:
                path_ind_list_min.append([path[ind]]*len(min_path))
                path_ind_list_max.append([path[ind]]*len(max_path))
        else:
            for ind in min_industry_columns:
                path_ind_list_min.append([path[ind]]*len(min_path))
            for ind in max_industry_columns:
                path_ind_list_max.append([path[ind]]*len(max_path))



        # print (path_ind_list)
        path_ind_list_min = list(zip(*path_ind_list_min))
        path_ind_list_max = list(zip(*path_ind_list_max))
        # print (path_ind_list)
        # path_ind_list_df = pd.DataFrame(path_ind_list,columns=['edge_id'] + industry_columns)
        edge_flows_min.append(pd.DataFrame(path_ind_list_min,columns=['edge_id'] + min_industry_columns))
        if len(edge_flows_min) > 1:
            edge_flows_min = [pd.concat(edge_flows_min,axis=0,sort='False', ignore_index=True).groupby('edge_id')[min_industry_columns].sum().reset_index()]

        edge_flows_max.append(pd.DataFrame(path_ind_list_max,columns=['edge_id'] + max_industry_columns))
        if len(edge_flows_max) > 1:
            edge_flows_max = [pd.concat(edge_flows_max,axis=0,sort='False', ignore_index=True).groupby('edge_id')[max_industry_columns].sum().reset_index()]
    

        print ('Done with path',iter_)

        # if iter_ > 1000:
        #     break

    if len(edge_flows_min) == 1:
        edge_flows_min = edge_flows_min[0]
    elif len(edge_flows_min) > 1:
        edge_flows_min = pd.concat(edge_flows_min,axis=0,sort='False', ignore_index=True).groupby('edge_id')[min_industry_columns].sum().reset_index()

    # print (edge_flows_min)

    if len(edge_flows_max) == 1:
        edge_flows_max = edge_flows_max[0]
    elif len(edge_flows_max) > 1:
        edge_flows_max = pd.concat(edge_flows_max,axis=0,sort='False', ignore_index=True).groupby('edge_id')[max_industry_columns].sum().reset_index()

    # print (edge_flows_max)

    if min_industry_columns == max_industry_columns:
        for ind in min_industry_columns:
            edge_flows_min.rename(columns={ind:'min_'+ind},inplace=True)
            edge_flows_max.rename(columns={ind:'max_'+ind},inplace=True) 

    edge_flows = pd.merge(edge_flows_min,edge_flows_max,how='left',on=['edge_id']).fillna(0)
    tqdm.pandas()
    if min_industry_columns == max_industry_columns:
        industry_columns = min_industry_columns
    else:
        industry_columns = [x[4:] for x in min_industry_columns]

    for ind in industry_columns:
        edge_flows['swap'] = edge_flows.progress_apply(lambda x: swap_min_max(x,'min_{}'.format(ind),'max_{}'.format(ind)), axis = 1)
        edge_flows[['min_{}'.format(ind),'max_{}'.format(ind)]] = edge_flows['swap'].apply(pd.Series)
        edge_flows.drop('swap', axis=1, inplace=True)

    gdf_edges = pd.merge(gdf_edges,edge_flows,how='left',on=['edge_id']).fillna(0)

    # gdf_edges = gdf_edges.set_index('edge_id')

    # min_ind_cols = []
    # max_ind_cols = []
    # ch_min_ind_cols = []
    # ch_max_ind_cols = []
    # for ind in industry_columns:
    #     min_ind_cols.append('min_{}'.format(ind))
    #     max_ind_cols.append('max_{}'.format(ind))
    #     if ind in min_max_exist:
    #         ch_min_ind_cols.append('min_{}'.format(ind))
    #         ch_max_ind_cols.append('max_{}'.format(ind))
    #     else:
    #         ch_min_ind_cols.append(ind)
    #         ch_max_ind_cols.append(ind)

    # for i in range(len(min_ind_cols)):
    #     gdf_edges[min_ind_cols[i]] = 0
    #     gdf_edges[max_ind_cols[i]] = 0

    # # print (gdf_edges)
    # for iter_, path in save_paths_df.iterrows():
    #     min_path = ast.literal_eval(path['min_edge_path']) 
    #     max_path = ast.literal_eval(path['max_edge_path'])

    #     # gdf_edges.loc[gdf_edges['edge_id'].isin(min_path), min_ind_cols] += path[ch_min_ind_cols].values
    #     # gdf_edges.loc[gdf_edges['edge_id'].isin(max_path), max_ind_cols] += path[ch_max_ind_cols].values
    #     # print (min_path)
    #     gdf_edges.loc[min_path, min_ind_cols] += path[ch_min_ind_cols].values
    #     gdf_edges.loc[max_path, max_ind_cols] += path[ch_max_ind_cols].values

    #     print ('Done with path',iter_)

    #     if iter_ > 1000:
    #         break

    # tqdm.pandas()
    # for ind in industry_columns:
    #     gdf_edges['swap'] = gdf_edges.progress_apply(lambda x: swap_min_max(x,'min_{}'.format(ind),'max_{}'.format(ind)), axis = 1)
    #     gdf_edges[['min_{}'.format(ind),'max_{}'.format(ind)]] = gdf_edges['swap'].progress_apply(pd.Series)
    #     gdf_edges.drop('swap', axis=1, inplace=True)

    # gdf_edges = gdf_edges.reset_index()

    if save_shapes == True:
        gdf_edges.to_file(shape_output_path,encoding='utf-8')

    if save_csv == True:
        gdf_edges.drop('geometry', axis=1, inplace=True)
        gdf_edges.to_csv(csv_output_path,index=False,encoding='utf-8')


    del gdf_edges, save_paths_df

def identify_all_failure_paths(network_df_in,edge_failure_set,flow_dataframe,path_criteria):
    """Identify all paths that contain an edge

    Parameters
    ---------
    network_df_in - Pandas DataFrame of network
    edge_failure_set - List of string edge ID's
    flow_dataframe - Pandas DataFrame of list of edge paths
    path_criteria - String name of column of edge paths in flow dataframe

    Outputs
    -------
    network_df - Pandas DataFrame of network
        With removed edges
    edge_path_index - List of integer indexes
        Of locations of paths in flow dataframe
    """

    edge_path_index = []
    network_df = copy.deepcopy(network_df_in)
    for edge in edge_failure_set:
        network_df = network_df[network_df.edge_id != edge]
        edge_path_index += flow_dataframe.loc[flow_dataframe[path_criteria].str.contains(
            "'{}'".format(edge))].index.tolist()

    edge_path_index = list(set(edge_path_index))
    return network_df, edge_path_index

def igraph_scenario_edge_failures_changing_tonnages(network_df_in, edge_failure_set,
    flow_dataframe, vehicle_weight, path_criteria, tons_criteria, cost_criteria, time_criteria):
    """Estimate network impacts of each failures
    When the tariff costs of each path depends on the changing tonnages

    Parameters
    ---------
    network_df_in - Pandas DataFrame of network
    edge_failure_set - List of string edge ID's
    flow_dataframe - Pandas DataFrame of list of edge paths
    vehicle_weight - Float weight of vehcile weight
    path_criteria - String name of column of edge paths in flow dataframe
    tons_criteria - String name of column of path tons in flow dataframe
    cost_criteria - String name of column of path costs in flow dataframe
    time_criteria - String name of column of path travel time in flow dataframe


    Returns
    -------
    edge_failure_dictionary : list[dict]
        With attributes
        edge_id - String name or list of failed edges
        origin - String node ID of Origin of disrupted OD flow
        destination - String node ID of Destination of disrupted OD flow
        no_access - Boolean 1 (no reroutng) or 0 (rerouting)
        new_cost - Float value of estimated cost of OD journey after disruption
        new_distance - Float value of estimated distance of OD journey after disruption
        new_path - List of string edge ID's of estimated new route of OD journey after disruption
        new_time - Float value of estimated time of OD journey after disruption
    """
    edge_fail_dictionary = []

    network_df,edge_path_index = identify_all_failure_paths(network_df_in,edge_failure_set,flow_dataframe,path_criteria)

    if edge_path_index:
        if len(edge_failure_set) == 1:
            edge_failure_set = edge_failure_set[0]

        network_graph = ig.Graph.TupleList(network_df.itertuples(
            index=False), edge_attrs=list(network_df.columns)[2:])

        for e in edge_path_index:
            origin = flow_dataframe.iloc[e]['origin_id']
            destination = flow_dataframe.iloc[e]['destination_id']
            origin_node = [x for x in network_graph.vs if x['name'] == origin]
            destination_node = [x for x in network_graph.vs if x['name'] == destination]

            if not origin_node or not destination_node:
                # no alternative path exists
                edge_fail_dictionary.append({'edge_id': edge_failure_set, 'origin_id': origin, 'destination_id': destination,
                                             'new_path':[],'new_distance': 0, 'new_time': 0, 'new_cost': 0, 'no_access': 1})

            else:
                tons = flow_dataframe.iloc[e][tons_criteria]
                vh_nums = math.ceil(1.0*tons/vehicle_weight)
                network_graph = add_igraph_generalised_costs(
                    network_graph, vh_nums, tons)
                new_route = network_graph.get_shortest_paths(
                    origin, destination, weights=cost_criteria, output='epath')[0]
                if not new_route:
                    # no alternative path exists
                    edge_fail_dictionary.append({'edge_id': edge_failure_set, 'origin_id': origin, 'destination_id': destination,
                                                 'new_path':[],'new_distance': 0, 'new_time': 0, 'new_cost': 0, 'no_access': 1})

                else:
                    new_dist = 0
                    new_time = 0
                    new_gcost = 0
                    new_path = []
                    for n in new_route:
                        new_dist += network_graph.es[n]['length']
                        new_time += network_graph.es[n][time_criteria]
                        new_gcost += network_graph.es[n][cost_criteria]
                        new_path.append(network_graph.es[n]['edge_id'])

                    edge_fail_dictionary.append({'edge_id': edge_failure_set, 'origin_id': origin, 'destination_id': destination,
                                                 'new_path':new_path,'new_distance': new_dist, 'new_time': new_time, 'new_cost': new_gcost, 'no_access': 0})

    return edge_fail_dictionary


def igraph_scenario_edge_failures(network_df_in, edge_failure_set,
    flow_dataframe, vehicle_weight, path_criteria,
    tons_criteria, cost_criteria, time_criteria,transport_mode):
    """Estimate network impacts of each failures
    When the tariff costs of each path are fixed by vehicle weight

    Parameters
    ---------
    network_df_in - Pandas DataFrame of network
    edge_failure_set - List of string edge ID's
    flow_dataframe - Pandas DataFrame of list of edge paths
    vehicle_weight - Float weight of vehcile weight
    path_criteria - String name of column of edge paths in flow dataframe
    tons_criteria - String name of column of path tons in flow dataframe
    cost_criteria - String name of column of path costs in flow dataframe
    time_criteria - String name of column of path travel time in flow dataframe


    Returns
    -------
    edge_failure_dictionary : list[dict]
        With attributes
        edge_id - String name or list of failed edges
        origin - String node ID of Origin of disrupted OD flow
        destination - String node ID of Destination of disrupted OD flow
        no_access - Boolean 1 (no reroutng) or 0 (rerouting)
        new_cost - Float value of estimated cost of OD journey after disruption
        new_distance - Float value of estimated distance of OD journey after disruption
        new_path - List of string edge ID's of estimated new route of OD journey after disruption
        new_time - Float value of estimated time of OD journey after disruption
    """
    edge_fail_dictionary = []
    network_df,edge_path_index = identify_all_failure_paths(network_df_in,edge_failure_set,flow_dataframe,path_criteria)

    if edge_path_index:
        if len(edge_failure_set) == 1:
            edge_failure_set = edge_failure_set[0]

        network_graph = ig.Graph.TupleList(network_df.itertuples(
            index=False), edge_attrs=list(network_df.columns)[2:])
        if transport_mode != 'rail':
            network_graph = add_igraph_generalised_costs(
                network_graph, 1.0/vehicle_weight, 1)

        nodes_name = np.asarray([x['name'] for x in network_graph.vs])
        select_flows = flow_dataframe[flow_dataframe.index.isin(edge_path_index)]

        no_access = select_flows[(~select_flows['origin_id'].isin(nodes_name)) | (
            ~select_flows['destination_id'].isin(nodes_name))]
        if len(no_access.index) > 0:
            for iter_, value in no_access.iterrows():
                edge_fail_dictionary.append({'edge_id': edge_failure_set, 'origin_id': value['origin_id'], 'destination_id': value['destination_id'],
                                             'new_path':[],'new_distance': 0, 'new_time': 0, 'new_cost': 0, 'no_access': 1})

        po_access = select_flows[(select_flows['origin_id'].isin(nodes_name)) & (
            select_flows['destination_id'].isin(nodes_name))]
        if len(po_access.index) > 0:
            po_access = po_access.set_index('origin_id')
            origins = list(set(po_access.index.values.tolist()))
            for origin in origins:
                destinations = po_access.loc[[origin], 'destination_id'].values.tolist()
                tons = po_access.loc[[origin], tons_criteria].values.tolist()
                paths = network_graph.get_shortest_paths(
                    origin, destinations, weights=cost_criteria, output="epath")
                for p in range(len(paths)):
                    if len(paths[p]) > 0:
                        new_dist = 0
                        new_time = 0
                        new_gcost = 0
                        new_path = []
                        for n in paths[p]:
                            new_dist += network_graph.es[n]['length']
                            new_time += network_graph.es[n][time_criteria]
                            new_gcost += network_graph.es[n][cost_criteria]
                            new_path.append(network_graph.es[n]['edge_id'])
                        edge_fail_dictionary.append({'edge_id': edge_failure_set, 'origin_id': origin, 'destination_id': destinations[p],
                                                     'new_path':new_path,'new_distance': new_dist, 'new_time': new_time,
                                                     'new_cost': tons[p]*new_gcost, 'no_access': 0})
                    else:
                        edge_fail_dictionary.append({'edge_id': edge_failure_set, 'origin_id': origin, 'destination_id': destinations[p],
                                                     'new_path':[],'new_distance': 0, 'new_time': 0, 'new_cost': 0, 'no_access': 1})

    return edge_fail_dictionary

def rearrange_minmax_values(edge_failure_dataframe):
    """Write results to Shapefiles

    Parameters
    ---------
    edge_failure_dataframe : pandas.DataFrame
        with min-max columns

    Returns
    -------
    edge_failure_dataframe : pandas.DataFrame
        With columns where min < max
    """
    failure_columns = edge_failure_dataframe.columns.values.tolist()
    failure_columns = [f for f in failure_columns if f != ('edge_id','no_access')]

    industry_columns = list(set([f.split('min_')[1] for f in failure_columns if 'min' in f]))

    for ind in industry_columns:
        edge_failure_dataframe['swap'] = edge_failure_dataframe.apply(lambda x: swap_min_max(
            x, 'min_{}'.format(ind), 'max_{}'.format(ind)), axis=1)
        edge_failure_dataframe[['min_{}'.format(ind), 'max_{}'.format(ind)]
                  ] = edge_failure_dataframe['swap'].apply(pd.Series)
        edge_failure_dataframe.drop('swap', axis=1, inplace=True)

    return edge_failure_dataframe

def network_failure_assembly_shapefiles(edge_failure_dataframe, gdf_edges, save_edges=True, shape_output_path=''):
    """Write results to Shapefiles


    Outputs gdf_edges - a Shapefile with results of edge failure dataframe

    Parameters
    ---------
    edge_failure_dataframe
        Pandas DataFrame of edge failure results
    gdf_edges
        GeoDataFrame of network edge set with edge ID's and geometry
    save_edges : bool
        Boolean condition to tell code to save created edge shapefile
    shape_output_path : str
        Path where the output shapefile will be stored

    """
    failure_columns = edge_failure_dataframe.columns.values.tolist()
    failure_columns = [f for f in failure_columns if f != 'edge_id']

    for fc in failure_columns:
        gdf_edges[fc] = 0

    for iter_, row in edge_failure_dataframe.iterrows():
        # print (row[1:])
        gdf_edges.loc[gdf_edges['edge_id'] == row['edge_id'],
                      failure_columns] = row[failure_columns].values


    industry_columns = list(set([f.split('min_')[1] for f in failure_columns if 'min' in f]))

    for ind in industry_columns:
        gdf_edges['swap'] = gdf_edges.apply(lambda x: swap_min_max(
            x, 'min_{}'.format(ind), 'max_{}'.format(ind)), axis=1)
        gdf_edges[['min_{}'.format(ind), 'max_{}'.format(ind)]
                  ] = gdf_edges['swap'].apply(pd.Series)
        gdf_edges.drop('swap', axis=1, inplace=True)

    if save_edges == True:
        gdf_edges.to_file(shape_output_path)

    del gdf_edges, edge_failure_dataframe

def edge_failure_sampling(failure_scenarios,edge_column):
    """Criteria for selecting failure samples

    Parameters
    ---------
    failure_scenarios - Pandas DataFrame of failure scenarios
    edge_column - String name of column to select failed edge ID's

    Returns
    -------
    edge_failure_samples - List of lists of failed edge sets
    """
    edge_failure_samples = list(set(failure_scenarios[edge_column].values.tolist()))

    return edge_failure_samples

def merge_failure_results(flow_df_select,failure_df,tons_col,dist_col,time_col,cost_col):
    """Merge failure results with flow results

    Parameters
    ---------
    flow_df_select : pandas.DataFrame
        edge flow values
    failure_df : pandas.DataFrame
        edge failure values
    tons_col : str
        name of column of tonnages in flow dataframe
    dist_col : str
        name of column of distance in flow dataframe
    time_col : str
        name of column of time in flow dataframe
    cost_col : str
        name of column of cost in flow dataframe
    vehicle_col : str
        name of column of vehicle counts in flow dataframe
    changing_tonnages : bool

    Returns
    -------
    flow_df_select : pandas.DataFrame
        Of edge flow and failure values merged
    """
    flow_df_select = pd.merge(flow_df_select, failure_df, on=[
                              'origin_id', 'destination_id'], how='left').fillna(0)
    flow_df_select = flow_df_select[(flow_df_select[tons_col] > 0) & (flow_df_select['edge_id'] != 0)]

    flow_df_select['dist_diff'] = (1 - flow_df_select['no_access'])*(flow_df_select['new_distance'] - flow_df_select[dist_col])
    flow_df_select['time_diff'] = (1 - flow_df_select['no_access'])*(flow_df_select['new_time'] - flow_df_select[time_col])
    flow_df_select['tr_loss'] = (1 - flow_df_select['no_access']) * (flow_df_select['new_cost'] - flow_df_select[cost_col])
    
    return flow_df_select
