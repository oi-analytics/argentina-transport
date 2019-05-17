# -*- coding: utf-8 -*-
"""
Run the MRIA Model for a given set of disruptions.
"""

import os
import numpy as np
import pandas as pd
from model import MRIA_IO as MRIA
from table import io_basic
from tqdm import tqdm

def get_rel_disruption(x,df_od):
    x.value = 1 - float(x.value/df_od.loc[(df_od.destination_province == x.destination_province) & (df_od.sector == x.sector)].value)
    return x

def estimate_losses(input_file):
    """
    Estimate the economic losses for a given set of failure scenarios

    Parameters
        - input_file - String name of input file to failure scenarios

    Outputs
        - .csv file with total losses per failure scenario
        
    """

    print('{} started!'.format(input_file))


    data_path = os.path.join('..','Data')
    output_path = os.path.join('..','results')
    
    """Specify disruption"""
    output_dir = os.path.join(output_path,
                              'economic_failure_results',
                              'od_regions_losses'
                              )

    """ Specify file path """
    filepath = os.path.join(data_path, 'economic_IO_tables','output', 'IO_ARGENTINA.xlsx')
    
    regions = ['Ciudad de Buenos Aires', 'Buenos Aires', 'Catamarca', 'Cordoba',
           'Corrientes', 'Chaco', 'Chubut', 'Entre Rios', 'Formosa', 'Jujuy',
           'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquen', 'Rio Negro',
           'Salta', 'San Juan', 'San Luis', 'Santa Cruz', 'Santa Fe',
           'Santiago del Estero', 'Tucuman', 'Tierra del Fuego']
    
    regions = [x.replace(' ','_') for x in regions]
    
    """Create data input"""
    DATA = io_basic('Argentina', filepath,regions)
    DATA.prep_data()

    """Run model and create some output"""
    output = pd.DataFrame()

    """Specify disruption"""
    output_dir = os.path.join(
        output_path,
        'economic_failure_results',
        os.path.basename(os.path.splitext(input_file)[0])
    )

    """Create output folders"""
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)

    """prepare mapper functions"""
    reg_mapper = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','sh_cou_06_16.xls'),
                          sheet_name='reg_mapper',header=None)
    reg_mapper = dict(zip(reg_mapper[0], reg_mapper[1]))

    failure_scens = pd.read_csv(input_file) #,encoding='iso-8859-1'
    failure_scens.origin_province = failure_scens.origin_province.apply(lambda x : reg_mapper[x])
    failure_scens.destination_province = failure_scens.destination_province.apply(lambda x : reg_mapper[x])
    
    if 'road' in input_file:
        failure_scens.columns = ['event_id', 'origin_province', 'destination_province',
               'A','C', 'D', 'B']
    else:
        failure_scens.columns = ['event_id', 'origin_province', 'destination_province','A','G','C','D','I']
    

    od_matrix_total = pd.DataFrame(pd.read_excel(os.path.join(data_path,'OD_data','province_ods.xlsx'),
                              sheet_name='total',index_col=[0,1],usecols =[0,1,2,3,4,5,6,7])).unstack(1).fillna(0)/365
    od_matrix_total.columns.set_levels(['A','G','C','D','B','I'],level=0,inplace=True)
    od_matrix_total.index = od_matrix_total.index.map(reg_mapper)
    od_matrix_total = od_matrix_total.stack(0)
    od_matrix_total.columns = od_matrix_total.columns.map(reg_mapper)
    od_matrix_total = od_matrix_total.swaplevel(i=-2, j=-1, axis=0)
    
    df_od = pd.DataFrame(od_matrix_total.stack().reset_index()).groupby(['level_0','destination_province']).sum().reset_index()
    df_failures = failure_scens.groupby(['event_id','destination_province']).sum().stack().reset_index()
    
    df_failures.columns = ['edge_id','destination_province','sector','value']
    df_od.columns = ['sector','destination_province','value']
    
    df_failures = df_failures.apply(lambda x : get_rel_disruption(x,df_od),axis=1)
    df_failures = df_failures.groupby(['edge_id','destination_province','sector']).sum().unstack(1)
    df_failures[df_failures <= 0.8] = 0.8

    """Run model for the first time and create some output"""
    output = pd.DataFrame()
    
    disr_dict_fd = {}
    disr_dict_sup = {}
    
    """Create model"""
    MRIA_RUN = MRIA(DATA.name, DATA.regions, DATA.sectors, list_fd_cats=['FinDem'])
    
    """Define sets and alias"""
    # CREATE SETS
    MRIA_RUN.create_sets()
    
    # CREATE ALIAS
    MRIA_RUN.create_alias()
    
    """ Define tables and parameters"""
    MRIA_RUN.baseline_data(DATA, disr_dict_sup, disr_dict_fd)
    MRIA_RUN.impact_data(DATA, disr_dict_sup, disr_dict_fd)
    
    MRIA_RUN.run_impactmodel()
    
    """Get base line values"""
    output['x_in'] = pd.Series(MRIA_RUN.X.get_values())
    output.index.names = ['region', 'sector']

    """Run model and create some output"""
    disr_dict_fd = {}
    collect_outputs = {}
    
    sum_disr = 0
    prov_impact = pd.DataFrame()
    
    for event,edge in tqdm(df_failures.groupby(level=0,axis=0),total=len(df_failures.groupby(level=0,axis=0).sum())):
        try:
            edge.index = edge.index.droplevel(0)
            edge.columns = edge.columns.droplevel(0)
    
            disr = edge.dropna(axis=1)
    
            if (1-disr.min().min()) < 0.05:
                continue
            elif abs(sum_disr - disr.sum().sum()) < 0.001:
                collect_outputs[event] = prov_impact
                total_losses_sum = (prov_impact['total_losses'].sum().sum())
                print('{} results in {} Million USD daily losses'.format(event,total_losses_sum))
                continue
    
            disr_dict_sup = {(k,r): v for r, kv in disr.iterrows() for k,v in kv.to_dict().items() if v < 1}
            sum_disr = disr.sum().sum()
    
            """Create model"""
            MRIA_RUN = MRIA(DATA.name, DATA.regions, DATA.sectors, list_fd_cats=['FinDem'])
    
            """Define sets and alias"""
            # CREATE SETS
            MRIA_RUN.create_sets()
    
            # CREATE ALIAS
            MRIA_RUN.create_alias()
    
            """ Define tables and parameters"""
            MRIA_RUN.baseline_data(DATA, disr_dict_sup, disr_dict_fd)
            MRIA_RUN.impact_data(DATA, disr_dict_sup, disr_dict_fd)
    
            """Get direct losses """
            disrupt = pd.DataFrame.from_dict(disr_dict_sup, orient='index')
            disrupt.reset_index(inplace=True)
            disrupt[['region', 'sector']] = disrupt['index'].apply(pd.Series)
            disrupt.drop('index', axis=1, inplace=True)
            disrupt = 1 - disrupt.groupby(['region', 'sector']).sum()
            disrupt.columns = ['shock']
    
            output['dir_losses'] = (disrupt['shock']*output['x_in']).fillna(0)*-1
    
            status = MRIA_RUN.run_impactmodel()
            if status.key != 'ok':
                continue
            output['x_out'] = pd.Series(MRIA_RUN.X.get_values())
            output['total_losses'] = (output['x_out'] - output['x_in'])
            output['ind_losses'] = (output['total_losses'] - output['dir_losses'])
    
            output.to_csv(os.path.join(output_dir, '{}.csv'.format(event)))
    
            prov_impact = output.groupby(level=0, axis=0).sum()[['dir_losses','total_losses','ind_losses']]/365
            collect_outputs[event] = prov_impact
    
            total_losses_sum = (output['total_losses'].sum().sum()/365)
            print('{} results in {} Million USD daily losses'.format(event,total_losses_sum))

        except Exception as e:
            print('Failed to finish {} because of {}!'.format(event, e))

    """Create output folders"""
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)
    
    pd.concat(collect_outputs).to_csv(os.path.join(
        output_path,
        'economic_failure_results',
        'od_regions_losses',
        '{}_od_regions.csv'.format(os.path.basename(os.path.splitext(input_file)[0]))))
    
    get_sums = {}
    for event in collect_outputs:
        get_sums[event] = collect_outputs[event]['total_losses'].sum()
    
    sums = pd.DataFrame.from_dict(get_sums, orient='index')
    sums.columns = ['total_losses']
    
    """Specify disruption"""
    output_dir = os.path.join(
        output_path,
        'economic_failure_results',
        'summarized'
    )
    
    """Create output folders"""
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)
    
    sums.to_csv(os.path.join(
        output_path,
        'economic_failure_results',
        'summarized',
        '{}_summarized.csv'.format(os.path.basename(os.path.splitext(input_file)[0]))))

    return pd.concat(collect_outputs), sums

if __name__ == '__main__':

    data_path = os.path.join('..','Data')
    output_path = os.path.join('..','results')
    
    """Specify disruption"""
    output_dir = os.path.join(output_path,
                              'economic_failure_results',
                              'od_regions_losses'
                              )
    multi_modal = False
    railway = True
    output_dir = os.path.join(
        output_path,
        'economic_failure_results')
    """Create output folders"""
    if os.path.exists(output_dir) == False:
        os.mkdir(output_dir)

    if (multi_modal == False) & (railway == False):
        get_all_input_files = [os.path.join(data_path,'isolated_od_scenarios','single_mode', x) 
            for x in os.listdir(os.path.join(data_path,'isolated_od_scenarios','single_mode')) if x.endswith(".csv")]
        get_all_input_files = [x for x in get_all_input_files if 'road' in x]
        get_all_input_files = [x for x in get_all_input_files if 'single_edge' in x]

    elif (multi_modal == False) & (railway == True):
        get_all_input_files = [os.path.join(data_path,'isolated_od_scenarios','single_mode', x) 
            for x in os.listdir(os.path.join(data_path,'isolated_od_scenarios','single_mode')) if x.endswith(".csv")]
        get_all_input_files = [x for x in get_all_input_files if 'rail' in x]
        get_all_input_files = [x for x in get_all_input_files if 'single_edge' in x]


    for gi in get_all_input_files:
        estimate_losses(gi)
