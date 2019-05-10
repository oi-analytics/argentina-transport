"""Summarise length of edges/number of nodes within each boundary (commune, district, province)

Purpose
-------

Collect network attributes
    - Combine with boundary Polygons to collect network-boundary intersection attributes
    - Write final results to an Excel sheet

Input data requirements
-----------------------

1. Correct paths to all files and correct input parameters

2. Shapefiles of networks with attributes:
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
from tqdm import tqdm


def risk_results_reorganise(risk_dataframe,id_column):
    risk_columns = []
    flood_types = ['fluvial flooding', 'pluvial flooding']
    climate_scenarios = ['Future_Med','Future_High']
    all_ids = pd.DataFrame(list(set(risk_dataframe[id_column].values.tolist())),columns=[id_column])
    for ft in flood_types:
        ht = risk_dataframe[risk_dataframe['hazard_type'] == ft]
        current = list(set(list(zip(ht[id_column].values.tolist(),ht['current'].values.tolist()))))
        current = pd.DataFrame(current,columns=[id_column,'{} current'.format(ft)])
        risk_columns.append('{} current'.format(ft))
        all_ids = pd.merge(all_ids,current,how='left',on=[id_column]).fillna(0)
        for cs in climate_scenarios:
            ht = risk_dataframe[(risk_dataframe['hazard_type'] == ft) & (risk_dataframe['climate_scenario'] == cs)]
            future = list(set(list(zip(ht[id_column].values.tolist(),ht['future'].values.tolist(),ht['change'].values.tolist()))))
            future = pd.DataFrame(future,columns=[id_column,'{} {} future'.format(ft,cs),'{} {} change'.format(ft,cs)])
            risk_columns.append('{} {} future'.format(ft,cs))
            risk_columns.append('{} {} change'.format(ft,cs))

            all_ids = pd.merge(all_ids,future,how='left',on=[id_column]).fillna(0)

    return all_ids, risk_columns

def change_matrix(risk_dataframe,value_threshold,change_threshold):
    total_counts_df = risk_dataframe.groupby(['hazard_type','climate_scenario']).size().reset_index(name='total_counts')
    # print (total_counts_df)
    scenario_df = risk_dataframe[risk_dataframe['change'] >= change_threshold].groupby(['hazard_type','climate_scenario']).size().reset_index(name='change_counts')
    # print (change_df)
    total_counts_df = pd.merge(total_counts_df,scenario_df,how='left',on=['hazard_type','climate_scenario']).fillna(0)
    total_counts_df['percent'] = 100.0*total_counts_df['change_counts']/total_counts_df['total_counts']
    
    scenario_df = risk_dataframe[risk_dataframe['future'] >= value_threshold].groupby(['hazard_type','climate_scenario']).size().reset_index(name='future_counts')
    total_counts_df = pd.merge(total_counts_df,scenario_df,how='left',on=['hazard_type','climate_scenario']).fillna(0)
    total_counts_df['percent_future'] = 100.0*total_counts_df['future_counts']/total_counts_df['total_counts']

    scenario_df = risk_dataframe[risk_dataframe['current'] >= value_threshold].groupby(['hazard_type','climate_scenario']).size().reset_index(name='current_counts')
    total_counts_df = pd.merge(total_counts_df,scenario_df,how='left',on=['hazard_type','climate_scenario']).fillna(0)
    total_counts_df['percent_current'] = 100.0*total_counts_df['current_counts']/total_counts_df['total_counts']
    scenario_df = risk_dataframe[(risk_dataframe['future'] >= value_threshold) & (risk_dataframe['change'] >= change_threshold)].groupby(['hazard_type','climate_scenario']).size().reset_index(name='future_percent_counts')
    total_counts_df = pd.merge(total_counts_df,scenario_df,how='left',on=['hazard_type','climate_scenario']).fillna(0)

    print (total_counts_df)    


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
        - String name of sheet in hazard datasets description Excel file

    4. Specify the output files and paths to be created
    """
    tqdm.pandas()
    incoming_data_path,data_path, calc_path, output_path = load_config()['paths']['incoming_data'],load_config()['paths']['data'], load_config()[
        'paths']['calc'], load_config()['paths']['output']

    # Supply input data and parameters
    modes = ['road','rail','bridge']
    val_cols = ['min_total_tons','max_total_tons','min_tr_loss','max_tr_loss','min_econ_loss','max_econ_loss','min_econ_impact','max_econ_impact']

    od_output_excel = os.path.join(os.path.join(output_path,'network_stats','network_failures_ranked.xlsx'))
    failure_excel_writer = pd.ExcelWriter(od_output_excel)


    od_output_excel = os.path.join(os.path.join(output_path,'network_stats','network_risks_ranked.xlsx'))
    risk_excel_writer = pd.ExcelWriter(od_output_excel)

    od_output_excel = os.path.join(os.path.join(output_path,'network_stats','network_adaptations_ranked.xlsx'))
    adapt_excel_writer = pd.ExcelWriter(od_output_excel)
    

    for m in range(len(modes)):
        network_stats = pd.read_excel(os.path.join(output_path,
                                                        'network_stats',
                                                        'national_scale_boundary_stats.xlsx'),sheet_name=modes[m],encoding='utf-8-sig')
        if modes[m] in ['road','rail','bridge']:
            failure_results = pd.read_csv(os.path.join(output_path,
                                        'failure_results',
                                        'minmax_combined_scenarios',
                                        'single_edge_failures_minmax_{}_100_percent_disrupt.csv'.format(modes[m])),encoding='utf-8-sig')

            risk_results = pd.read_csv(os.path.join(output_path,
                                        'network_stats',
                                        'national_{}_eael_climate_change.csv'.format(modes[m])),encoding='utf-8-sig')

            risk_results = risk_results.sort_values(by=['future'],ascending=False)
            risk_results.drop('year',axis=1,inplace=True)
            risk_results[['current','future']] = 1.0*risk_results[['current','future']]/1000000

            failure_results = failure_results.sort_values(by=['max_econ_impact'],ascending=False)
            failure_results.drop('no_access',axis=1,inplace=True)
            failure_results[['min_total_tons','max_total_tons']] = 1.0*failure_results[['min_total_tons','max_total_tons']]/1000.0
            failure_results[['min_tr_loss','max_tr_loss','min_econ_loss','max_econ_loss','min_econ_impact','max_econ_impact']] = 1.0*failure_results[['min_tr_loss','max_tr_loss','min_econ_loss','max_econ_loss','min_econ_impact','max_econ_impact']]/1000000

            if modes[m] == 'bridge':
                edges = pd.read_csv(os.path.join(data_path,'network','bridges.csv'),encoding='utf-8-sig')
                edges = edges[['bridge_id','edge_id','structure_type']]
                roads = pd.read_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8-sig')
                roads = roads[['edge_id','road_name']]
                edges = pd.merge(edges,roads,how='left',on=['edge_id'])
                del roads
                edge_id = 'bridge_id'

                print ('* Changes for {}'.format(modes[m]))
                change_matrix(risk_results,0.1,100)

                risk_results = risk_results[risk_results['future'] > 0.1]
                risk_vals,risk_cols = risk_results_reorganise(risk_results,edge_id)
                risk_vals = pd.merge(risk_vals,edges,how='left',on=[edge_id])
                risk_vals = pd.merge(risk_vals,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                risk_vals.drop_duplicates(subset=['bridge_id'],keep='first',inplace=True)
                risk_vals['totals'] = risk_vals[[cols for cols in risk_cols if 'future' in cols]].sum(axis=1)
                risk_vals = risk_vals.sort_values(by='totals',ascending=False)
                risk_vals.drop(['bridge_id','edge_id','totals'],axis=1,inplace=True)
                risk_vals.set_index(['road_name','structure_type','province_name']+risk_cols+['department_name']).to_excel(risk_excel_writer,modes[m],encoding='utf-8-sig')

                failure_results = failure_results[failure_results['max_econ_impact'] > 0.5]
                failure_results = pd.merge(failure_results,edges,how='left',on=[edge_id])
                del edges
                failure_results = pd.merge(failure_results,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                failure_results.drop_duplicates(subset=['bridge_id'],keep='first',inplace=True)
                failure_results.drop(['bridge_id','edge_id'],axis=1,inplace=True)
                failure_results.set_index(['road_name','structure_type','province_name']+val_cols+['department_name']).to_excel(failure_excel_writer,modes[m],encoding='utf-8-sig')

                duration = [10,20,30]
                for dur in duration:
                    adapt_results = pd.read_csv(os.path.join(output_path, 'adaptation_results',
                                'output_adaptation_{}_{}_days_max_disruption_fixed_parameters.csv'.format(modes[m],dur)),encoding='utf-8-sig')
                    adapt_results = pd.merge(adapt_results,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                    adapt_results['min_eael'] = dur*adapt_results['risk_wt']*adapt_results['min_econ_impact']
                    adapt_results['max_eael'] = dur*adapt_results['risk_wt']*adapt_results['max_econ_impact']
                    adapt_results = adapt_results.sort_values(by='max_bc_ratio',ascending=False)
                    adapt_results.drop_duplicates(subset=[edge_id],keep='first',inplace=True)
                    adapt_results.to_csv(os.path.join(output_path,'network_stats','{}_adaptation_summary_{}_days_disruption.csv'.format(modes[m],dur)),encoding='utf-8-sig')
                    adapt_results = adapt_results.head(50)
                    adapt_results.set_index(['road_name','structure_type',
                                            'province_name','department_name','climate_scenario','max_exposure_length',
                                            'max_ini_adap_cost','max_tot_adap_cost',
                                            'min_benefit','max_benefit','min_bc_ratio',
                                            'max_bc_ratio']).to_excel(adapt_excel_writer,'{}_{}_days'.format(modes[m],dur),encoding='utf-8-sig')
                    adapt_excel_writer.save()
                    del adapt_results

            elif modes[m] == 'road':
                edges = pd.read_csv(os.path.join(data_path,'network','road_edges.csv'),encoding='utf-8-sig')
                edges = edges[['edge_id','road_name','road_type']]
                edge_id = 'edge_id'

                print ('* Changes for {}'.format(modes[m]))
                change_matrix(risk_results,0.1,100)

                risk_results = risk_results[risk_results['future'] > 0.1]
                risk_vals,risk_cols = risk_results_reorganise(risk_results,edge_id)
                risk_vals = pd.merge(risk_vals,edges,how='left',on=[edge_id])
                risk_vals = pd.merge(risk_vals,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                risk_vals['totals'] = risk_vals[[cols for cols in risk_cols if 'future' in cols]].sum(axis=1)
                risk_vals = risk_vals.sort_values(by='totals',ascending=False)
                risk_vals.drop([edge_id,'totals'],axis=1,inplace=True)
                risk_vals.set_index(['road_name','road_type','province_name']+risk_cols+['department_name']).to_excel(risk_excel_writer,modes[m],encoding='utf-8-sig')

                failure_results = failure_results[failure_results['max_econ_impact'] > 0.5]
                failure_results = pd.merge(failure_results,edges,how='left',on=[edge_id])
                del edges
                failure_results = pd.merge(failure_results,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                failure_results.drop(edge_id,axis=1,inplace=True)
                failure_results.set_index(['road_name','road_type','province_name']+val_cols+['department_name']).to_excel(failure_excel_writer,modes[m],encoding='utf-8-sig')

                duration = [10,20,30]
                for dur in duration:
                    adapt_results = pd.read_csv(os.path.join(output_path, 'adaptation_results',
                                'output_adaptation_{}_{}_days_max_disruption_fixed_parameters.csv'.format(modes[m],dur)),encoding='utf-8-sig')
                    adapt_results = pd.merge(adapt_results,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                    adapt_results['min_eael'] = dur*adapt_results['risk_wt']*adapt_results['min_econ_impact']
                    adapt_results['max_eael'] = dur*adapt_results['risk_wt']*adapt_results['max_econ_impact']
                    adapt_results = adapt_results.sort_values(by='max_bc_ratio',ascending=False)
                    adapt_results.drop_duplicates(subset=[edge_id],keep='first',inplace=True)
                    adapt_results.to_csv(os.path.join(output_path,'network_stats','{}_adaptation_summary_{}_days_disruption.csv'.format(modes[m],dur)),encoding='utf-8-sig')
                    adapt_results = adapt_results.head(50)
                    adapt_results.set_index(['road_name',
                                            'province_name','department_name','climate_scenario','max_exposure_length',
                                            'max_ini_adap_cost','max_tot_adap_cost',
                                            'min_benefit','max_benefit','min_bc_ratio',
                                            'max_bc_ratio']).to_excel(adapt_excel_writer,'{}_{}_days'.format(modes[m],dur),encoding='utf-8-sig')

                    adapt_excel_writer.save()
                    del adapt_results

            else:
                edges = pd.read_csv(os.path.join(data_path,'network','rail_edges.csv'),encoding='utf-8-sig')
                edges = edges[['edge_id','operador','linea']]
                edge_id = 'edge_id'

                print ('* Changes for {}'.format(modes[m]))
                change_matrix(risk_results,1.0,100)
                risk_results = risk_results[risk_results['future'] > 1.0]
                risk_vals,risk_cols = risk_results_reorganise(risk_results,edge_id)
                risk_vals = pd.merge(risk_vals,edges,how='left',on=[edge_id])
                # del edges
                risk_vals = pd.merge(risk_vals,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                risk_vals['totals'] = risk_vals[[cols for cols in risk_cols if 'future' in cols]].sum(axis=1)
                risk_vals = risk_vals.sort_values(by='totals',ascending=False)
                risk_vals.drop([edge_id,'totals'],axis=1,inplace=True)
                risk_vals.set_index(['operador','linea','province_name']+risk_cols+['department_name']).to_excel(risk_excel_writer,modes[m],encoding='utf-8-sig')


                failure_results = failure_results[failure_results['max_econ_impact'] > 1.0]
                failure_results = pd.merge(failure_results,edges,how='left',on=[edge_id])
                del edges
                failure_results = pd.merge(failure_results,network_stats[[edge_id,'department_name','province_name']],how='left',on=[edge_id])
                failure_results.drop(edge_id,axis=1,inplace=True)
                risk_vals = risk_vals.sort_values(by=[cols for cols in risk_cols if 'future' in cols],ascending=False)
                failure_results.set_index(['operador','linea','province_name']+val_cols+['department_name']).to_excel(failure_excel_writer,modes[m],encoding='utf-8-sig')

            # failure_results.set_index([edge_id,'province_name']).to_excel(os.path.join(output_path,'network_stats','{}_failures_ranked.csv'.format(modes[m])),encoding='utf-8-sig')
            failure_excel_writer.save()
            risk_excel_writer.save()




if __name__ == "__main__":
    main()
