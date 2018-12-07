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

3. Shapefile of administrative boundaries of Vietnam with attributes:
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
    modes = ['road','rail']
    out_modes = ['national_roads', 'national_rail', 'air_ports', 'inland_ports', 'sea_ports']
    national_results = 'Yes'

    # Give the paths to the input data files
    hazard_path = os.path.join(output_path, 'hazard_scenarios')


    # Specify the output files and paths to be created
    output_dir = os.path.join(output_path, 'network_stats')
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)

    # Process national scale results
    if national_results == 'Yes':
        print ('* Processing national scale results')
        data_excel = os.path.join(
            output_dir,'national_scale_hazard_intersection_summary_stats.xlsx')
        nat_excel_writer = pd.ExcelWriter(data_excel)
        for m in range(len(modes)):
            national_data = pd.read_csv(
                os.path.join(
                    data_path,
                    'network',
                    '{}_edges.csv'.format(modes[m])
                    ),encoding='utf-8'
                )
            hazard_data = pd.read_csv(os.path.join(
                hazard_path,
                'national_{}_hazard_intersections_risks.csv'.format(modes[m])))
            data_df = hazard_data_summary(hazard_data,national_data)
            data_df.to_excel(nat_excel_writer, modes[m], index=False)
            nat_excel_writer.save()
            del data_df




if __name__ == "__main__":
    main()
