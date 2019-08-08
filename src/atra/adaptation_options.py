# -*- coding: utf-8 -*-
"""Estimate costs and benefits, either under fixed parameters or under a sensitivity analysis,
varying the cost components.
"""
import os
import sys
import pandas as pd
import numpy as np
import math
from SALib.sample import morris
from tqdm import tqdm

from dask import dataframe as dd
from dask.multiprocessing import get
from multiprocessing import cpu_count
from atra.utils import *

nCores = cpu_count()


def calculate_discounting_arrays(discount_rate=12, growth_rate=2.7,
                                start_year=2016,end_year=2050,
                                min_period=4,max_period=8):
    """Set discount rates for yearly and period maintenance costs

    Parameters
    ----------
    discount_rate
        yearly discount rate
    growth_rate
        yearly growth rate

    Returns
    -------
    discount_rate_norm
        discount rates to be used for the costs
    discount_rate_growth
        discount rates to be used for the losses
    min_main_dr
        discount rates for 4-year periodic maintenance
    max_main_dr
        discount rates for 8-year periodic maintenance

    """
    discount_rate_norm = []
    discount_rate_growth = []

    for year in range(start_year,end_year):
        discount_rate_norm.append(
            1.0/math.pow(1.0 + 1.0*discount_rate/100.0, year - start_year))

        discount_rate_growth.append(
            1.0*math.pow(1.0 + 1.0*growth_rate/100.0, year -
                         start_year)/math.pow(1.0 + 1.0*discount_rate/100.0, year - start_year))

    min_maintain_discount_years = np.arange(start_year, end_year,min_period)
    maintain_discount_ratio_list = []
    for year in min_maintain_discount_years[1:]:
        maintain_discount_ratio = 1.0 / math.pow(1.0 + 1.0*discount_rate/100.0, year - start_year)
        maintain_discount_ratio_list.append(maintain_discount_ratio)

    max_main_dr = np.array(maintain_discount_ratio_list)

    maintain_discount_ratio_list = []
    max_maintain_discount_years = np.arange(start_year, end_year,max_period)
    for year in max_maintain_discount_years[1:]:
        maintain_discount_ratio = 1.0 / math.pow(1.0 + 1.0*discount_rate/100.0, year - start_year)
        maintain_discount_ratio_list.append(maintain_discount_ratio)

    min_main_dr = np.array(maintain_discount_ratio_list)

    return np.array(discount_rate_norm), np.array(discount_rate_growth), min_main_dr, max_main_dr


def sum_tuples(l):
    return list(sum(x) for x in zip(*l))


def average_tuples(l):
    return list(np.mean(x) for x in zip(*l))


def max_tuples(l):
    return list(np.max(x) for x in zip(*l))


def calc_costs(x, cst_2L_asphalt, cst_2L_concrete, cst_4L_concrete,
               cst_rehab,cst_routine,cst_periodic, discount_rates,
               discount_growth_rates, min_main_dr, max_main_dr, duration_max=10,
               min_exp=True, min_loss=True,mode='road',length_duration_weights=1):
    """Estimate the total cost and benefits for a road segment. This function is used within a
    pandas apply

    Parameters
    ----------
    x
        a row from the road segment dataframe that we are considering
    param_values
        numpy array with a set of parameter combinations
    mnt_dis_cost
        adaptation costs for a district road in the mountains
    mnt_nat_cost
        adaptation costs for a national road in the mountains
    cst_dis_cost
        adaptation costs for a district road on flat terrain
    cst_nat_cost
        adaptation costs for a national road on flat terrain
    pavement
        set of paving combinations. This corresponds with the cost table and the param_values
    mnt_main_cost
        maintenance costs for roads in the mountains
    cst_main_cost
        maintenance costs for roads on flat terrain
    discount_rates
        discount rates to be used for the costs
    discount_growth_rates
        discount rates to be used for the losses
    rehab_costs
        rehabilitation costs after a disaster
    min_main_dr
        discount rates for 4-year periodic maintenance
    max_main_dr
        discount rates for 8-year periodic maintenance
    min_exp : bool, optional
        Specify whether we want to use the minimum or maximum exposure length. The default value is set to **True**
    national : bool, optional
        Specify whether we are looking at national roads. The default value is set to **False**
    min_loss : bool, optional
        Specify whether we want to use the minimum or maximum economic losses.  The default value is set to **True**

    Returns
    -------
    uncer_output : list
        outcomes for the initial adaptation costs of this road segment
    tot_uncer_output : list
        outcomes for the total adaptation costs of this road segment
    rel_share : list
        relative share of each factor in the initial adaptation cost of this road segment
    tot_rel_share : list
        relative share of each factor in the total adaptation cost of this road segment
    bc_ratio : list
        benefit cost ratios for this road segment

    """
    if x.width == 0:
        x.width = 7.3

    # # Set which exposure length to use
    # if min_exp == True:
    #     exp_length = x.min_exposure_length
    # else:
    #     exp_length = x.max_exposure_length

    exp_length = x.max_exposure_length

    # Set which loss to use
    if min_loss == True:
        loss = x.min_eael_per_day
        if length_duration_weights == 1:
            duration = duration_max
        else:
            duration = duration_max*x.min_duration_wt
    else:
        loss = x.max_eael_per_day
        if length_duration_weights == 1:
            duration = duration_max
        else:
            duration = duration_max*x.max_duration_wt


    # if mode == 'road':
    #     cst_rehab = 1.0e3*(cst_rehab*x.width)/7.3
    #     damages = sum(discount_rates*x.dam_wt*cst_rehab)
    # elif mode == 'bridge':
    #     cst_rehab = 1.0e6*(cst_rehab*x.width)/7.3
    #     damages = sum(discount_rates*x.risk_wt*cst_rehab)

    # Estimate benefit
    damages = sum(discount_rates*x.ead)
    economic_losses = sum(loss*discount_growth_rates*duration)
    benefit = damages+economic_losses


    # Estimate cost of options
    if mode == 'bridge':
        options = 'Upgrading bridge'
        ini_adap_costs = cst_4L_concrete
        routine_costs = (cst_routine*x.width)/7.3
        periodic_costs = (cst_periodic*x.width)/7.3

    elif x.width <= 0.5*7.3:
        if 'Hormigon' in  str(x.surface.split(',')):
            options = 'Upgrading to Concrete 1L'
            ini_adap_costs = (cst_2L_concrete*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3
        else:
            options = 'Upgrading to Bituminous 1L'
            ini_adap_costs = (cst_2L_asphalt*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3

    elif 0.5*7.3 < x.width <= 7.3:
        if 'Hormigon' in  str(x.surface.split(',')):
            options = 'Upgrading to Concrete 2L'
            ini_adap_costs = (cst_2L_concrete*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3
        else:
            options = 'Upgrading to Bituminous 2L'
            ini_adap_costs = (cst_2L_asphalt*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3

    elif 7.3 < x.width <= 1.5*7.3:
        if 'Hormigon' in  str(x.surface.split(',')):
            options = 'Upgrading to Concrete 3L'
            ini_adap_costs = (cst_4L_concrete*x.width)/14.6
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3
        else:
            options = 'Upgrading to Bituminous 3L'
            ini_adap_costs = (cst_2L_asphalt*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3

    elif 1.5*7.3 < x.width <= 14.6:
        if 'Hormigon' in  str(x.surface.split(',')):
            options = 'Upgrading to Concrete 4L'
            ini_adap_costs = (cst_4L_concrete*x.width)/14.6
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3
        else:
            options = 'Upgrading to Bituminous 4L'
            ini_adap_costs = (cst_2L_asphalt*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3

    else:
        if 'Hormigon' in  str(x.surface.split(',')):
            options = 'Upgrading to Concrete > 4L'
            ini_adap_costs = (cst_4L_concrete*x.width)/14.6
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3
        else:
            options = 'Upgrading to Bituminous > 4L'
            ini_adap_costs = (cst_2L_asphalt*x.width)/7.3
            routine_costs = (cst_routine*x.width)/7.3
            periodic_costs = (cst_periodic*x.width)/7.3

    if mode == 'bridge':
        ini_adap_costs = 1.0e6*np.array(ini_adap_costs)
        tot_adap_costs = ini_adap_costs + 1.0e3*exp_length*(sum(discount_rates)*np.array(routine_costs) + sum(min_main_dr)*np.array(periodic_costs))
    else:
        ini_adap_costs = 1.0e3*exp_length*np.array(ini_adap_costs)
        tot_adap_costs = ini_adap_costs + 1.0e3*exp_length*(sum(discount_rates)*np.array(routine_costs) + sum(min_main_dr)*np.array(periodic_costs))

    # Calculate the benefit cost ratio and NPV difference
    bc_ratios = benefit/tot_adap_costs
    bc_diffs = benefit-tot_adap_costs

    return options,damages,economic_losses,benefit,ini_adap_costs,tot_adap_costs,bc_ratios,bc_diffs


def run_adaptation_calculation(file_id, data_path, output_path,results_type, duration_max=10,
                               discount_rate=10,growth_rate=2.9,start_year=2016,end_year=2050,
                                min_period=4,max_period=8,read_from_file=False):

    tqdm.pandas()
    print('* {} started!'.format(file_id))

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

    cost_2L_asphalt = adapt.loc[adapt['option']=='Upgrading to Bituminous 2L','cost_perkm'].values[0] + \
                     adapt.loc[adapt['option']=='Upgrading to Bituminous 2L','climate_uplift_perkm'].values[0]
    cost_2L_concrete = adapt.loc[adapt['option']=='Upgrading to Concrete 2L','cost_perkm'].values[0] + \
                        adapt.loc[adapt['option']=='Upgrading to Concrete 2L','climate_uplift_perkm'].values[0]
    cost_4L_concrete = adapt.loc[adapt['option']=='Upgrading to Concrete 4L','cost_perkm'].values[0] + \
                        adapt.loc[adapt['option']=='Upgrading to Concrete 4L','climate_uplift_perkm'].values[0]
    cost_rehab = adapt.loc[adapt['option']=='Reconstruction','cost_perkm'].values[0] + \
                    adapt.loc[adapt['option']=='Reconstruction','climate_uplift_perkm'].values[0]
    cost_routine = adapt.loc[adapt['option']=='CREMA: Rehabilitation and Routine Maintenance','cost_perkm'].values[0] + \
                    adapt.loc[adapt['option']=='CREMA: Rehabilitation and Routine Maintenance','climate_uplift_perkm'].values[0]
    cost_periodic = adapt.loc[adapt['option']=='Asphalt Mix Resurfacing / Surface Treatment Resurfacing','cost_perkm'].values[0] + \
                    adapt.loc[adapt['option']=='Asphalt Mix Resurfacing / Surface Treatment Resurfacing','climate_uplift_perkm'].values[0]

    print ('* Get discount ratios')
    dr_norm, dr_growth, min_main_dr, max_main_dr = calculate_discounting_arrays(
        discount_rate, growth_rate, start_year,end_year,min_period,max_period)
    # print(sum(dr_norm), sum(dr_growth), sum(min_main_dr), sum(max_main_dr))

    print ('* Analysis for {} {} days disruption and {} growth'.format(file_id,duration_max,round(growth_rate,1)))

    # if results_type == 'combined':
    #     roads_risks = pd.read_csv(os.path.join(output_path, 'risk_results',
    #                                          '{}_combined_climate_risks.csv'.format(file_id)))
    # else:
    #     roads_risks = pd.read_csv(os.path.join(output_path, 'risk_results',
    #                                          '{}_hazard_and_climate_risks.csv'.format(file_id)))
    
    roads_risks = pd.read_csv(os.path.join(output_path, 'risk_results',
                                             '{}_{}_risks.csv'.format(file_id,results_type)))
    # load networks
    if file_id == 'road':
        roads = pd.read_csv(os.path.join(data_path, 'network',
                                         'road_edges.csv'.format(file_id)))[['edge_id',
                                                                            'road_name',
                                                                            'road_type',
                                                                            'surface',
                                                                            'road_cond',
                                                                            'length',
                                                                            'width']]
    elif file_id == 'bridge':
        roads = pd.read_csv(os.path.join(data_path, 'network',
                                         'bridges.csv'.format(file_id)))[['bridge_id',
                                                                            'structure_type',
                                                                            'pavement_material_asc',
                                                                            'pavement_material_desc',
                                                                            'substructure_material',
                                                                            'superstructure_material',
                                                                            'ruta',
                                                                            'length',
                                                                            'width']]
        roads.rename(columns={'ruta':'road_name'},inplace=True)
    else:
        print ('Error: Mode should be road or bridge')

    roads = roads.merge(roads_risks)
    # roads = roads.merge(loss_roads)
    # roads = roads[roads['max_econ_impact'] > 0]

    roads = roads[(roads['max_eael_per_day'] + roads['ead']) > 0]
    tqdm.pandas()

    roads['min_options'],roads['min_tot_damages'],roads['min_tot_econ_losses'],roads['min_benefit'], \
        roads['min_ini_adap_cost'], roads['min_tot_adap_cost'], \
        roads['min_bc_ratio'], roads['min_bc_diff'] = zip(*roads.progress_apply(
            lambda x: calc_costs(x, cost_2L_asphalt, cost_2L_concrete, cost_4L_concrete,
               cost_rehab,cost_routine,cost_periodic, dr_norm,
               dr_growth, min_main_dr, max_main_dr, duration_max=duration_max,
               min_exp=False, min_loss=True,mode=file_id,length_duration_weights=1), axis=1))

    roads['max_options'],roads['max_tot_damages'],roads['max_tot_econ_losses'],roads['max_benefit'], \
        roads['max_ini_adap_cost'], roads['max_tot_adap_cost'], \
        roads['max_bc_ratio'], roads['max_bc_diff'] = zip(*roads.progress_apply(
            lambda x: calc_costs(x, cost_2L_asphalt, cost_2L_concrete, cost_4L_concrete,
               cost_rehab,cost_routine,cost_periodic, dr_norm,
               dr_growth, min_main_dr, max_main_dr, duration_max=duration_max,
               min_exp=False, min_loss=False,mode=file_id,length_duration_weights=1), axis=1))

    if read_from_file:
        filename = 'output_adaptation_{}_{}_days_max_{}_growth_disruption.csv'.format(
            file_id, duration_max,str(round(growth_rate,1)).replace('.','p').replace('-','minus'))
        roads.to_csv(os.path.join(output_path, 
                                'adaptation_results',
                                results_type, 
                                filename),index=False,encoding='utf-8-sig')
    else:
        filename = 'output_adaptation_{}_{}_days_max_{}_growth_disruption_fixed_parameters.csv'.format(
            file_id, duration_max,str(round(growth_rate,1)).replace('.','p').replace('-','minus'))
        roads.to_csv(os.path.join(output_path, 
                                'adaptation_results',
                                results_type, 
                                filename),index=False,encoding='utf-8-sig')
