"""Summarise hazard data

Get OD data and process it
"""
import ast
import itertools
import math
import operator
import os
import subprocess
import sys

import geopandas as gpd
import igraph as ig
import numpy as np
import pandas as pd
from scipy.spatial import Voronoi
from shapely.geometry import Point, Polygon
from atra.utils import *


def nodes_flows_from_edges(edge_flow_file,nodes_name_file,nodes_name_column,flow_columns):
    from_node_flow = edge_flow_file.groupby(['from_node'])[flow_columns].sum().reset_index()
    from_node_flow.rename(columns={'from_node':'node_id'},inplace=True)
    to_node_flow = edge_flow_file.groupby(['to_node'])[flow_columns].sum().reset_index()
    to_node_flow.rename(columns={'to_node':'node_id'},inplace=True)

    nodes_flows = pd.concat([from_node_flow,to_node_flow],axis=0,sort='False',ignore_index=True).fillna(0)
    del from_node_flow, to_node_flow
    nodes_flows = nodes_flows.groupby(['node_id'])[flow_columns].sum().reset_index()
    nodes_name_file = pd.merge(nodes_name_file,nodes_flows,how='left',on=['node_id']).fillna(0)
    nodes_name_file = nodes_name_file[~nodes_name_file[nodes_name_column].isin([0,'0','none'])]

    return nodes_name_file





def main():
    data_path, calc_path, output_path, figure_path = load_config()['paths']['data'], load_config(
    )['paths']['calc'], load_config()['paths']['output'], load_config()['paths']['figures']

    # Get the modal shares
    modes = ['road', 'rail', 'port','air']
    modes_col = ['','nombre','name','name']

    for m in range(len(modes)):
        '''Find flow sensitvities and rank flows
        '''
        if modes[m] != 'air':
            mode_data_path = os.path.join(output_path, 'flow_mapping_paths','flow_paths_{}_100_percent_assignment.csv'.format(modes[m]))

            flow = pd.read_csv(mode_data_path)
            flow = flow[['min_edge_path','max_edge_path']]
            diff = 0
            for iter_,row in flow.iterrows():
                if row[0] != row[1]:
                    diff += 1

            print ('Percentage of changing paths in {} OD flows {}'.format(modes[m],100.0*diff/len(flow.index)))

            del flow

            flow_file_path = os.path.join(output_path, 'flow_mapping_combined',
                                           'weighted_flows_{}_100_percent.csv'.format(modes[m]))

            flow_file = pd.read_csv(flow_file_path)

            mode_file_path = os.path.join(data_path, 'network',
                                       '{}_edges.shp'.format(modes[m]))

            mode_file = gpd.read_file(mode_file_path,encoding='utf-8')
            mode_file.drop('geometry',axis=1,inplace=True)
            mode_file = pd.merge(mode_file,flow_file,how='left', on=['edge_id']).fillna(0)
            mode_file = mode_file[mode_file['max_total_tons'] > 0]
            if modes[m] == 'road':

                write_file = mode_file[['edge_id','road_name','road_type','min_total_tons','max_total_tons']]
            else:
                node_file = gpd.read_file(os.path.join(data_path, 'network','{}_nodes.shp'.format(modes[m])),encoding='utf-8')
                node_file.drop('geometry',axis=1,inplace=True)
                write_file = nodes_flows_from_edges(mode_file,node_file,modes_col[m],['min_total_tons','max_total_tons'])

            write_file.sort_values(by=['max_total_tons'],ascending=False).to_csv(os.path.join(output_path,
                                                                                'network_stats',
                                                                                '{}_ranked_flows.csv'.format(modes[m])),
                                                                                encoding='utf-8-sig',
                                                                                index=False)

        else:
            flow_file_path = os.path.join(data_path, 'usage','air_passenger.csv')

            flow_file = pd.read_csv(flow_file_path)
            # flow_file['passengers'] = 1.0*flow_file['passengers']/365
            node_file = gpd.read_file(os.path.join(data_path, 'network','{}_nodes.shp'.format(modes[m])),encoding='utf-8')
            node_file.drop('geometry',axis=1,inplace=True)
            write_file = nodes_flows_from_edges(flow_file,node_file,modes_col[m],['passengers'])

            write_file.sort_values(by=['passengers'],ascending=False).to_csv(os.path.join(output_path,'network_stats',
                                                                                '{}_ranked_flows.csv'.format(modes[m])),
                                                                                encoding='utf-8-sig',
                                                                                index=False)






if __name__ == '__main__':
    main()
