"""Road network risks and adaptation maps
"""
import os
import sys
from collections import OrderedDict

import ast
import numpy as np
import geopandas as gpd
import pandas as pd
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from atra.utils import *


def main():
    config = load_config()
    data_path = config['paths']['data']
    calc_path = config['paths']['calc']
    output_path = config['paths']['output']

    # Supply input data and parameters
    modes = ['road', 'rail','bridge']
    mode_files = ['road_edges','rail_edges','bridges']
    modes_id_cols = ['edge_id','edge_id','bridge_id']

    hazard_cols = ['climate_scenario','year']

    # Give the paths to the input data files
    network_data_csv = os.path.join(data_path, 'network')

    risk_csv_dir = os.path.join(output_path, 'risk_results')
    if os.path.exists(risk_csv_dir) == False:
        os.mkdir(risk_csv_dir)

    # load cost file
    print ('* Get adaptation costs')
    adapt = pd.read_excel(os.path.join(data_path,'adaptation_costs','ROCKS - Database - ARNG (Version 2.3) Feb2018.xls'),
            sheet_name = 'Resultados Consolidados',
            skiprows=6,
            nrows=9,
            usecols = [2,4,5],
            encoding='utf-8-sig').fillna('No value')

    adapt.columns = ['option','cost_perkm','climate_uplift_perkm']
    adapt = adapt[~adapt.option.isin(['Subtotal','No value'])]
    cost_rehab = adapt.loc[adapt['option']=='Reconstruction','cost_perkm'].values[0] + \
                    adapt.loc[adapt['option']=='Reconstruction','climate_uplift_perkm'].values[0]

    del adapt

    # Process national scale results
    for m in range(len(modes)):
        risk_cols = ['min_eael_per_day','max_eael_per_day']
        output_cols = ['hazard_type','climate_scenario','year',
                    'min_flood_depth','max_flood_depth',
                    'min_exposure_length','min_exposure_percent',
                    'max_exposure_length','max_exposure_percent',
                    'min_eael_per_day','max_eael_per_day']
        # Load mode network DataFrame
        print('* Creating {} network risk results'.format(modes[m]))
        fail_results = pd.read_csv(os.path.join(output_path, 
                                'failure_results',
                                'minmax_combined_scenarios',
                                'single_edge_failures_minmax_{}_100_percent_disrupt.csv'.format(modes[m])))

        risk_results = pd.read_csv(os.path.join(output_path, 
                                                'risk_results',
                                                '{}_hazard_intersections_risk_weights.csv'.format(modes[m])))
        risk_results = pd.merge(risk_results,
                                fail_results[[modes_id_cols[m],'min_econ_impact','max_econ_impact']],
                                how='left', 
                                on=[modes_id_cols[m]]).fillna(0)
        del fail_results
        
        risk_results['min_eael_per_day'] = risk_results['risk_wt']*risk_results['min_econ_impact']
        risk_results['max_eael_per_day'] = risk_results['risk_wt']*risk_results['max_econ_impact']
        print('* Merging with {} network DataFrame'.format(modes[m]))
        if modes[m] in ('road','bridge'):
            risk_cols += ['ead']
            output_cols = [modes_id_cols[m]] + output_cols + ['ead'] 
            width_file = pd.read_csv(os.path.join(network_data_csv,
                                              '{}.csv'.format(mode_files[m])), encoding='utf-8-sig')
    
            risk_results = pd.merge(risk_results,
                                    width_file[[modes_id_cols[m],'width']],
                                    how='left', 
                                    on=[modes_id_cols[m]])
            del width_file
            if modes[m] == 'road':
                risk_results['ead'] = 1.0e3*cost_rehab*risk_results['dam_wt']*risk_results['width']/7.3
            else:
                risk_results['ead'] = 1.0e6*cost_rehab*risk_results['risk_wt']*risk_results['width']/7.3

        
        risk_results[output_cols].to_csv(os.path.join(risk_csv_dir,
                            '{}_hazard_and_climate_risks.csv'.format(modes[m])), index=False)

        print('* Creating {} network risk results for climate outlooks'.format(modes[m]))
        min_height = risk_results.groupby([modes_id_cols[m]] + hazard_cols)['min_flood_depth'].min().reset_index()
        max_height = risk_results.groupby([modes_id_cols[m]] + hazard_cols)['max_flood_depth'].max().reset_index()
        heights = pd.merge(min_height,max_height,how='left',on=[modes_id_cols[m]]+hazard_cols).fillna(0)
        del min_height,max_height
        
        min_exposures = risk_results.groupby([modes_id_cols[m]] + hazard_cols)['min_exposure_length',
                                                            'min_exposure_percent'].min().reset_index()
        max_exposures = risk_results.groupby([modes_id_cols[m]] + hazard_cols)['max_exposure_length',
                                                            'max_exposure_percent'].max().reset_index()
        exposures = pd.merge(min_exposures,max_exposures,how='left',on=[modes_id_cols[m]]+hazard_cols).fillna(0)
        del min_exposures,max_exposures
        
        height_exposures = pd.merge(heights,exposures,how='left',on=[modes_id_cols[m]]+hazard_cols).fillna(0)
        del heights, exposures
        
        # all_edge_fail_scenarios = risk_results[hazard_cols + [modes_id_cols[m]] + risk_cols]
        all_edge_fail_scenarios = risk_results.groupby([modes_id_cols[m]] + hazard_cols)[risk_cols].sum().reset_index()

        pd.merge(height_exposures,
                all_edge_fail_scenarios,
                how='left',
                on=[modes_id_cols[m]]+hazard_cols).fillna(0).to_csv(os.path.join(risk_csv_dir,
                            '{}_combined_climate_risks.csv'.format(modes[m])), index=False)

        del risk_results, height_exposures, all_edge_fail_scenarios        

if __name__ == '__main__':
    main()
