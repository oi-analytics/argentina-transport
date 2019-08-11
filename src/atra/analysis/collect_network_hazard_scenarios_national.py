"""Collect network hazard scenarios
"""
import os
import sys

import pandas as pd
from atra.utils import *
from atra.transport_flow_and_failure_functions import *


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
    mode_files = ['road_edges','rail_edges','bridges']
    modes_id_cols = ['edge_id','edge_id','bridge_id']
    mode_length_thr = [500,500,5]
    start_year = 2016

    idx_cols = ['hazard_type', 'model','climate_scenario', 'year', 'edge_length']
    cols = ['climate_scenario', 'hazard_type', 'max_depth', 'min_depth','model', 'probability', 'year', 'length']

    # Give the paths to the input data files
    network_data_csv = os.path.join(data_path, 'network')
    fail_scenarios_data = os.path.join(output_path, 'hazard_scenarios')

    risk_csv_dir = os.path.join(output_path, 'risk_results')
    if os.path.exists(risk_csv_dir) == False:
        os.mkdir(risk_csv_dir)

    # Process national scale results
    for m in range(len(modes)):
        # Load mode network DataFrame
        print('* Loading {} network DataFrame'.format(modes[m]))
        G_df = pd.read_csv(os.path.join(network_data_csv,
                                          '{}.csv'.format(mode_files[m])), encoding='utf-8-sig')
        index_cols = [modes_id_cols[m]] + idx_cols
        edge_id = modes_id_cols[m]
        length_thr = mode_length_thr[m]
        sel_cols = [modes_id_cols[m],'length']

        G_df = G_df[sel_cols]
        # Load failure scenarios
        print('* Loading {} failure scenarios'.format(modes[m]))
        # hazard_scenarios = pd.read_excel(os.path.join(
        #     fail_scenarios_data, 'national_scale_hazard_intersections.xlsx'),
        #     sheet_name=modes[m])
        hazard_scenarios = pd.read_csv(os.path.join(fail_scenarios_data,
                                        '{}_hazard_intersections.csv'.format(modes[m])))
        if modes[m] == 'bridge':
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

        df_path = os.path.join(risk_csv_dir,
                               '{}_hazard_intersections_risk_weights.csv'.format(modes[m]))
        scenarios_df.to_csv(df_path, index=False)
        del scenarios_df


if __name__ == "__main__":
    main()
