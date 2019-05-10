"""Collect network hazard scenarios
"""
import os
import sys

import pandas as pd
from oia.utils import *
from oia.transport_flow_and_failure_functions import *


def main():
    """Process results

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

    """
    config = load_config()
    data_path = config['paths']['data']
    calc_path = config['paths']['calc']
    output_path = config['paths']['output']

    # Supply input data and parameters
    modes = ['road', 'rail','bridge']
    # modes = ['bridge']
    start_year = 2016

    # Give the paths to the input data files
    network_data_excel = os.path.join(data_path, 'network')
    fail_scenarios_data = os.path.join(output_path, 'hazard_scenarios')

    # Process national scale results
    for m in range(len(modes)):
        # Load mode network DataFrame
        print('* Loading {} network DataFrame'.format(modes[m]))
        if modes[m] == 'rail':
            index_cols = ['edge_id', 'hazard_type', 'model',
                          'climate_scenario', 'year', 'edge_length']
            sel_cols = ['edge_id', 'length']
            cols = ['climate_scenario', 'edge_id', 'hazard_type', 'max_depth', 'min_depth','model', 'probability', 'year', 'length']
            length_thr = 500.0
            G_df = pd.read_csv(os.path.join(network_data_excel,
                                          'rail_edges.csv'), encoding='utf-8-sig')
            edge_id = 'edge_id'
        elif modes[m] == 'road':
            index_cols = ['edge_id', 'hazard_type', 'model', 
                            'climate_scenario', 'year', 
                            'road_type','road_name','surface',
                            'road_cond', 'width', 'edge_length']
            sel_cols = ['edge_id','road_type',
                        'road_name','surface',
                        'road_cond','width', 'length']
            cols = ['climate_scenario', 'edge_id', 
                    'hazard_type', 'max_depth', 
                    'min_depth','model', 'probability', 
                    'year', 'length']
            length_thr = 500.0
            G_df = pd.read_csv(os.path.join(network_data_excel,
                                          'road_edges.csv'), encoding='utf-8-sig')
            edge_id = 'edge_id'
        else:
            length_thr = 5.0
            index_cols = ['bridge_id', 'hazard_type', 'model',
                          'climate_scenario', 'year', 
                          'structure_type','pavement_material_asc', 
                          'pavement_material_desc','substructure_material',
                          'superstructure_material','road_name',
                          'width', 'edge_length']
            sel_cols = ['bridge_id','structure_type','pavement_material_asc', 
                        'pavement_material_desc','substructure_material',
                        'superstructure_material','road_name','width', 'length']
            cols = ['climate_scenario', 'bridge_id', 'hazard_type', 'max_depth', 'min_depth','model', 'probability', 'year', 'length']
            G_df = pd.read_csv(os.path.join(network_data_excel,
                                          'bridges.csv'), encoding='utf-8_sig')
            G_df.rename(columns = {'ruta':'road_name'},inplace=True)
            G_df['width'] = G_df['right_lane_width'] + G_df['left_lane_width'] + G_df['pavement_width_asc'] + G_df['pavement_width_desc']
            edge_id = 'bridge_id'


        G_df = G_df[sel_cols]
        # Load failure scenarios
        print('* Loading {} failure scenarios'.format(modes[m]))
        hazard_scenarios = pd.read_excel(os.path.join(
            fail_scenarios_data, 'national_scale_hazard_intersections.xlsx'),
            sheet_name=modes[m])
        if modes[m] == 'bridge_id':
            hazard_scenarios = hazard_scenarios.sort_values(by=['min_depth'],ascending=False)
            hazard_scenarios.drop_duplicates(
                subset=['bridge_id','department_id','hazard_type','climate_scenario','probability'],
                keep='first',inplace=True)
        else:
            hazard_scenarios = hazard_scenarios.drop_duplicates(
                subset=cols, keep='first')

        all_edge_fail_scenarios = combine_hazards_and_network_attributes_and_impacts(
            hazard_scenarios, G_df,edge_id)

        print('* Creating {} hazard-network scenarios'.format(modes[m]))
        scenarios_df = create_hazard_scenarios_for_adaptation(
            all_edge_fail_scenarios, index_cols, length_thr)
        scenarios_df.rename(
            columns={'road_length': '{}_length'.format(modes[m])}, inplace=True)

        df_path = os.path.join(output_path, 'network_stats',
                               'national_{}_hazard_intersections_risks.csv'.format(modes[m]))
        scenarios_df.to_csv(df_path, index=False)
        del scenarios_df


if __name__ == "__main__":
    main()
