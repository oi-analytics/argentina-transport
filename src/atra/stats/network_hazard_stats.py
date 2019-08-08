"""Summarise per-hazard total intersections (for the whole system)

Purpose
-------

Collect network-hazard intersection attributes
    - Combine with boundary Polygons to collect network-boundary intersection attributes
    - Write final results to an Excel sheet

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters

2. Shapefiles of network-hazard intersections results with attributes:
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
from atra.utils import *
from atra.transport_flow_and_failure_functions import *

def hazard_data_summary(hazard_network_dataframe,network_dataframe):
    df = pd.merge(network_dataframe,hazard_network_dataframe,how='left',on=['edge_id']).fillna(0)
    df['min_exposure_length'] = 0.001*df['min_exposure_length']
    df['max_exposure_length'] = 0.001*df['max_exposure_length']
    hazard_totals = df.groupby(['hazard_type','model','climate_scenario','year'])['min_exposure_length','max_exposure_length'].sum().reset_index()

    hazard_totals_min = hazard_totals.groupby(['hazard_type','climate_scenario','year'])['min_exposure_length'].min().reset_index()
    hazard_totals_min['Percentage (min)'] = hazard_totals_min['min_exposure_length']/df['length'].sum()

    hazard_totals_max = hazard_totals.groupby(['hazard_type','climate_scenario','year'])['max_exposure_length'].max().reset_index()
    hazard_totals_max['Percentage (max)'] = hazard_totals_max['max_exposure_length']/df['length'].sum()

    hazards = pd.merge(hazard_totals_min,hazard_totals_max,how='left',on=['hazard_type','climate_scenario','year'])

    hazards.rename(columns={'hazard_type':'Hazard Type','climate_scenario':'Climate Scenario','year':'Year'},inplace=True)

    return hazards


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
        - Hazard datasets description Excel file
        - String name of sheet in hazard datasets description Excel file

    4. Specify the output files and paths to be created
    """
    data_path, calc_path, output_path = load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    modes = ['road','rail','bridge','port','air']
    boundary_cols = ['department_id','department_name','province_id','province_name']
    hazard_cols = ['climate_scenario','hazard_type','model','probability','year']

    flood_types = ['fluvial flooding','pluvial flooding']
    climate_scenarios = ['Baseline','Future_Med','Future_High'] 

    # Give the paths to the input data files
    hazard_path = os.path.join(output_path, 'hazard_scenarios')

    # Give the paths to the input data files
    national_file = os.path.join(output_path,
            'network_stats',
            'national_scale_boundary_stats.xlsx')

    national_hazard_file = os.path.join(output_path,
            'hazard_scenarios')

    # Specify the output files and paths to be created
    output_dir = os.path.join(output_path, 'network_stats')
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)


    data_excel = os.path.join(
            output_dir,'national_scale_hazard_intersections_summary.xlsx')
    nat_excel_writer = pd.ExcelWriter(data_excel)

    data_excel = os.path.join(
            output_dir,'national_scale_hazard_intersections_boundary_summary.xlsx')
    bd_excel_writer = pd.ExcelWriter(data_excel)
    '''Flood stats
    '''
    for m in range(len(modes)):
        flood_df = pd.read_csv(os.path.join(national_hazard_file,
                            '{}_hazard_intersections.csv'.format(modes[m])),
                            encoding='utf-8-sig')
        
        network_stats = pd.read_excel(national_file,sheet_name=modes[m],encoding='utf-8-sig')
        if modes[m] in ['road','rail']:
            edges = pd.read_csv(os.path.join(data_path,'network','{}_edges.csv'.format(modes[m])),encoding='utf-8-sig')
            if modes[m] == 'road':
                edges = edges[(edges['road_type'] == 'national') | (edges['road_type'] == 'province') | (edges['road_type'] == 'rural')]
            else:
                flow_df = pd.read_csv(os.path.join(output_path,'flow_mapping_combined','weighted_flows_rail_100_percent.csv'))
                edges = pd.merge(edges,flow_df,how='left',on=['edge_id'])
                edges = edges[edges['max_total_tons'] > 0]
                del flow_df

            flood_df = flood_df[flood_df['edge_id'].isin(edges['edge_id'].values.tolist())]
            network_stats = network_stats[network_stats['edge_id'].isin(edges['edge_id'].values.tolist())]

            network_stats = network_stats.groupby(boundary_cols)['length'].sum().reset_index()
            network_stats.rename(columns={'length':'total_length_m'},inplace=True)
            hazard_stats = flood_df.groupby(boundary_cols+hazard_cols)['length'].sum().reset_index()
            hazard_stats.rename(columns={'length':'exposure_length_m'},inplace=True)
            hazard_stats = pd.merge(hazard_stats,network_stats,how='left', on=boundary_cols).fillna(0)
            hazard_stats['percentage'] = 100.0*hazard_stats['exposure_length_m']/hazard_stats['total_length_m']
            hazard_stats.to_excel(bd_excel_writer, modes[m], index=False,encoding='utf-8-sig')
            bd_excel_writer.save()

            total_length = edges['length'].values.sum()

            flood_df = flood_df[['hazard_type','climate_scenario','probability','length']].groupby(['hazard_type','climate_scenario','probability'])['length'].sum().reset_index()
            flood_df['length'] = 0.001*flood_df['length']
            flood_df.rename(columns={'length':'exposure_length_km'},inplace=True)
            flood_df['return period'] = 1/flood_df['probability']

            return_periods = list(set(flood_df['return period'].values.tolist()))
            f_df = pd.DataFrame(return_periods,columns=['return period'])
            flood_df['percentage_exposure'] = 1.0*flood_df['exposure_length_km']/total_length
            # flood_df.to_csv(os.path.join(output_path,'network_stats','{}_flood_exposure.csv'.format(modes[m])))
            for ft in flood_types:
                for cs in climate_scenarios:
                    f_s = flood_df[(flood_df['hazard_type'] == ft) & (flood_df['climate_scenario'] == cs)][['return period','exposure_length_km']]
                    f_df = pd.merge(f_df,f_s,how='left',on=['return period']).fillna(0)
                    f_df.rename(columns={'exposure_length_km':'{}_{}'.format(ft,cs)},inplace=True)

            del edges, network_stats, hazard_stats
        else:
            if modes[m] == 'port':
                flood_df = flood_df.sort_values(by=['min_depth'],ascending=False)
                flood_df.drop_duplicates(subset=['node_id','hazard_type','climate_scenario','probability'],keep='first',inplace=True)
                nodes = gpd.read_file(os.path.join(data_path,'network','port_nodes.shp'),encoding='utf-8')
                nodes = nodes[~nodes['name'].isin([0,'0','none'])]
                node_id = 'node_id'
            elif modes[m] == 'air':
                flood_df = flood_df.sort_values(by=['min_depth'],ascending=False)
                flood_df.drop_duplicates(subset=['node_id','hazard_type','climate_scenario','probability'],keep='first',inplace=True)
                nodes = gpd.read_file(os.path.join(data_path,'network','air_nodes.shp'),encoding='utf-8')
                flow_df = pd.read_csv(os.path.join(output_path,'network_stats','air_ranked_flows.csv'),encoding='utf-8-sig')
                nodes = pd.merge(nodes,flow_df,how='left',on=['node_id']).fillna(0)
                nodes = nodes[nodes['passengers_2016'] > 0]
                node_id = 'node_id'
                del flow_df
            elif modes[m] == 'bridge':
                flood_df = flood_df.sort_values(by=['min_depth'],ascending=False)
                flood_df.drop_duplicates(subset=['bridge_id','department_id','hazard_type','climate_scenario','probability'],keep='first',inplace=True)
                nodes = gpd.read_file(os.path.join(data_path,'network','bridges.shp'),encoding='utf-8')
                node_id = 'bridge_id'

            flood_df = flood_df[flood_df[node_id].isin(nodes[node_id].values.tolist())]
            network_stats = network_stats[network_stats[node_id].isin(nodes[node_id].values.tolist())]

            network_stats = network_stats.groupby(boundary_cols).size().reset_index(name='total_counts')
            hazard_stats = flood_df.groupby(boundary_cols+hazard_cols).size().reset_index(name='counts')
            hazard_stats = pd.merge(hazard_stats,network_stats,how='left', on=boundary_cols).fillna(0)
            hazard_stats['percentage'] = 100.0*hazard_stats['counts']/hazard_stats['total_counts']
            hazard_stats.to_excel(bd_excel_writer, modes[m], index=False,encoding='utf-8-sig')
            bd_excel_writer.save()


            total_nodes = len(nodes.index)
            flood_df = flood_df[['hazard_type','climate_scenario','probability']].groupby(['hazard_type','climate_scenario','probability']).size().reset_index(name='counts')
            flood_df['return period'] = 1/flood_df['probability']
            flood_df['percentage_exposure'] = 1.0*flood_df['counts']/total_nodes
            # flood_df.to_csv(os.path.join(output_path,'network_stats','{}_flood_exposure.csv'.format(modes[m])))
            return_periods = list(set(flood_df['return period'].values.tolist()))
            f_df = pd.DataFrame(return_periods,columns=['return period'])
            for ft in flood_types:
                for cs in climate_scenarios:
                    f_s = flood_df[(flood_df['hazard_type'] == ft) & (flood_df['climate_scenario'] == cs)][['return period','counts']]
                    f_df = pd.merge(f_df,f_s,how='left',on=['return period']).fillna(0)
                    f_df.rename(columns={'counts':'{}_{}'.format(ft,cs)},inplace=True)
            del nodes, network_stats, hazard_stats

        f_df.to_excel(nat_excel_writer, modes[m], index=False,encoding='utf-8-sig')
        nat_excel_writer.save()
        print ('* Done with mode:',modes[m])

    # # Process national scale results
    # if national_results == 'Yes':
    #     print ('* Processing national scale results')
    #     data_excel = os.path.join(
    #         output_dir,'national_scale_hazard_intersection_summary_stats.xlsx')
    #     nat_excel_writer = pd.ExcelWriter(data_excel)
    #     for m in range(len(modes)):
    #         national_data = pd.read_csv(
    #             os.path.join(
    #                 data_path,
    #                 'network',
    #                 '{}_edges.csv'.format(modes[m])
    #                 ),encoding='utf-8'
    #             )
    #         hazard_data = pd.read_csv(os.path.join(
    #             hazard_path,
    #             'national_{}_hazard_intersections_risks.csv'.format(modes[m])))
    #         data_df = hazard_data_summary(hazard_data,national_data)
    #         data_df.to_excel(nat_excel_writer, modes[m], index=False)
    #         nat_excel_writer.save()
    #         del data_df




if __name__ == "__main__":
    main()
