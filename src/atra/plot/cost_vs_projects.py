"""Plot adaptation cost ranges (national results)
"""
import sys
import os
import ast
import matplotlib as mpl
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from atra.utils import *

mpl.style.use('ggplot')
mpl.rcParams['font.size'] = 10.
mpl.rcParams['font.family'] = 'tahoma'
mpl.rcParams['axes.labelsize'] = 10.
mpl.rcParams['xtick.labelsize'] = 9.
mpl.rcParams['ytick.labelsize'] = 9.

def plot_values(input_data, division_factor,x_label, y_label,plot_title,plot_color,plot_file_path):
    fig, ax = plt.subplots(figsize=(8, 4))
    numbers = 1 + np.arange(0,len(input_data))
    # print (numbers)
    ax.plot(
        1.0*input_data/division_factor,
        numbers,
        linewidth=0.5,
        marker='o',
        markersize=1.0,
        color=plot_color
    )
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def plot_many_values(input_dfs, division_factor,x_label, y_label,plot_title,plot_colors,plot_labels,plot_file_path):
    fig, ax = plt.subplots(figsize=(8, 4))
    for i in range(len(input_dfs)):
        input_data = input_dfs[i]
        numbers = 1 + np.arange(0,len(input_data))
        # print (numbers)
        ax.plot(
            1.0*input_data/division_factor,
            numbers,
            linewidth=0.5,
            marker='o',
            markersize=1.0,
            color=plot_colors[i],
            label=plot_labels[i] 
        )
    ax.legend(loc='upper left')
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)
    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def plot_many_values_benefits(input_dfs, division_factor,x_label, y_label,plot_title,plot_colors,plot_labels,plot_file_path):
    fig, ax = plt.subplots(figsize=(8, 4))
    # Legend
    legend_handles = []
    for i in range(len(input_dfs)):
        input_data = input_dfs[i]
        numbers = 1 + np.arange(0,len(input_data.index))
        x_data = []
        y_data = []
        for a, b in input_data.itertuples(index=False):
            x_data.append(a)
            y_data.append(b)
        
        # print (numbers)
        # ax.plot(
        #     1.0*np.array(x_data)/division_factor,
        #     1.0*np.array(y_data)/division_factor,
        #     linewidth=0.5,
        #     marker='o',
        #     markersize=1.0,
        #     color=plot_colors[i],
        #     label=plot_labels[i] 
        # )
        ax.plot(
            1.0*np.array(x_data)/division_factor,
            1.0*np.array(y_data)/division_factor,
            linewidth=1.5,
            color=plot_colors[i],
            label=plot_labels[i] 
        )
        # legend_handles.append(mpatches.Patch(color=plot_colors[i], label=plot_labels[i]))
        # legend_handles.append(Line2D([0], [0], 
        #                     marker='o', 
        #                     color=plot_colors[i], 
        #                     label=plot_labels[i],
        #                     markerfacecolor=plot_colors[i],
        #                     markersize=6))
        legend_handles.append(Line2D([0], [0],  
                            color=plot_colors[i], 
                            label=plot_labels[i],
                            ))
        for n in range(len(numbers)):
            if numbers[n]%10 == 0:
                ax.scatter(
                1.0*x_data[n]/division_factor,
                1.0*y_data[n]/division_factor,
                marker='o',
                s=20,
                color='#a50f15',
                )

    # legend_handles.append(mpatches.Patch(color='#a50f15', label='Numbers of investments in increments of 10'))
    legend_handles.append(Line2D([0], [0], 
                        marker='o', 
                        color='w', 
                        label='Numbers of investments in increments of 10',
                        markerfacecolor='#a50f15',
                        markersize=10))

    ax.legend(handles=legend_handles,loc='best',fontsize=8)
    # ax.legend(
    #     handles=legend_handles,
    #     title='Percentage change in BCR',
    #     loc=(0.55,0.2),
    #     fancybox=True,
    #     framealpha=1.0
    # )
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)
    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def main():
    config = load_config()
    durations = [10,20,30]
    duration_colors = ['#9ecae1','#3182bd','#08519c']
    duration_labels = ['Max. {} days disruptions'.format(d) for d in durations]
    growth_rate = '2p8'
    modes = ['road','bridge']
    modes_id = ['edge_id','bridge_id']
    # for m in range(len(modes)):
    #     for duration in durations:
    #         adapt_file_path = os.path.join(config['paths']['output'], 'adaptation_results','combined_climate',
    #                             'output_adaptation_{}_{}_days_max_{}_growth_disruption_fixed_parameters.csv'.format(modes[m],
    #                                 duration,growth_rate))
    #         adapt_scenarios = pd.read_csv(adapt_file_path)
    #         adapt_bcr = adapt_scenarios[[modes_id[m],'max_ini_adap_cost','max_tot_adap_cost','max_benefit','max_bc_ratio']]
    #         adapt_bcr_max = adapt_bcr.sort_values(['max_bc_ratio'], ascending=False)
    #         adapt_bcr_max.drop_duplicates(subset=[modes_id[m]],keep='first',inplace=True)
    #         adapt_bcr_sum = adapt_bcr_max[adapt_bcr_max['max_bc_ratio']>=1][['max_ini_adap_cost','max_tot_adap_cost']].cumsum()
    #         plot_values(adapt_bcr_sum['max_ini_adap_cost'],
    #                     1000000,
    #                     'Initial investment (million USD)',
    #                     'Numbers of assets',
    #                     '{} - Numbers of assets with max. BCR > 1 vs Initial Investment'.format(modes[m].title()),
    #                     'k',
    #                     os.path.join(config['paths']['figures'],
    #                         '{}-initial-costs-vs-bcr-{}-days-{}-growth.png'.format(modes[m],duration,growth_rate)))


    #         plot_values(adapt_bcr_sum['max_tot_adap_cost'],
    #                     1000000,
    #                     'Total investment (million USD)',
    #                     'Numbers of assets',
    #                     '{} - Numbers of assets with max. BCR > 1 vs Total Investment'.format(modes[m].title()),
    #                     'k',
    #                     os.path.join(config['paths']['figures'],
    #                         '{}-total-costs-vs-bcr-{}-days-{}-growth.png'.format(modes[m],duration,growth_rate)))

    # for m in range(len(modes)):
    #     intial_investment_dfs = []
    #     total_investment_dfs = []
    #     for duration in durations:
    #         adapt_file_path = os.path.join(config['paths']['output'], 'adaptation_results','combined_climate',
    #                             'output_adaptation_{}_{}_days_max_{}_growth_disruption_fixed_parameters.csv'.format(modes[m],
    #                                 duration,growth_rate))
    #         adapt_scenarios = pd.read_csv(adapt_file_path)
    #         adapt_bcr = adapt_scenarios[[modes_id[m],'max_ini_adap_cost','max_tot_adap_cost','max_benefit','max_bc_ratio']]
    #         adapt_bcr_max = adapt_bcr.sort_values(['max_bc_ratio'], ascending=False)
    #         adapt_bcr_max.drop_duplicates(subset=[modes_id[m]],keep='first',inplace=True)
    #         adapt_bcr_sum = adapt_bcr_max[adapt_bcr_max['max_bc_ratio']>=1][['max_ini_adap_cost','max_tot_adap_cost']].cumsum()
    #         intial_investment_dfs.append(adapt_bcr_sum['max_ini_adap_cost'])
    #         total_investment_dfs.append(adapt_bcr_sum['max_tot_adap_cost'])
        
    #     plot_many_values(intial_investment_dfs,
    #                 1000000,
    #                 'Initial investment (million USD)',
    #                 'Numbers of assets',
    #                 '{} - Numbers of assets with max. BCR > 1 vs Initial Investment'.format(modes[m].title()),
    #                 duration_colors,
    #                 duration_labels,
    #                 os.path.join(config['paths']['figures'],
    #                     '{}-initial-costs-vs-bcr-{}-growth.png'.format(modes[m],growth_rate)))


    #     plot_many_values(total_investment_dfs,
    #                 1000000,
    #                 'Total investment (million USD)',
    #                 'Numbers of assets',
    #                 '{} - Numbers of assets with max. BCR > 1 vs Total Investment'.format(modes[m].title()),
    #                 duration_colors,
    #                 duration_labels,
    #                 os.path.join(config['paths']['figures'],
    #                     '{}-total-costs-vs-bcr-{}-growth.png'.format(modes[m],growth_rate)))


    for m in range(len(modes)):
        intial_investment_dfs = []
        total_investment_dfs = []
        max_investments = []
        for duration in durations:
            adapt_file_path = os.path.join(config['paths']['output'], 'adaptation_results','combined_climate',
                                'output_adaptation_{}_{}_days_max_{}_growth_disruption_fixed_parameters.csv'.format(modes[m],
                                    duration,growth_rate))
            adapt_scenarios = pd.read_csv(adapt_file_path)
            adapt_bcr = adapt_scenarios[[modes_id[m],'max_ini_adap_cost','max_tot_adap_cost','max_benefit','max_bc_ratio']]
            adapt_bcr_max = adapt_bcr.sort_values(['max_bc_ratio'], ascending=False)
            adapt_bcr_max.drop_duplicates(subset=[modes_id[m]],keep='first',inplace=True)
            adapt_bcr_sum = adapt_bcr_max[adapt_bcr_max['max_bc_ratio']>=1][['max_ini_adap_cost',
                                                                            'max_tot_adap_cost',
                                                                            'max_benefit']].cumsum()
            intial_investment_dfs.append(adapt_bcr_sum[['max_ini_adap_cost','max_benefit']])
            total_investment_dfs.append(adapt_bcr_sum[['max_tot_adap_cost','max_benefit']])
            max_investments.append((duration,
                                    adapt_bcr_sum['max_ini_adap_cost'].max(),
                                    adapt_bcr_sum['max_tot_adap_cost'].max(),
                                    adapt_bcr_sum['max_benefit'].max()))
        
        pd.DataFrame(max_investments,
                    columns=['days',
                            'Initial Investment',
                            'Total Investment','Benefits']).to_csv(os.path.join(config['paths']['output'],
                            'network_stats',
                            '{}_max_disruption_durations_benefits_investments_{}_growth.csv'.format(modes[m],growth_rate)
                            ), index=False)
        plot_many_values_benefits(intial_investment_dfs,
                    1000000,
                    'Initial investment budget (million USD)',
                    'Cumulative benefits (million USD)',
                    '{} - Benefits of assets with max. BCR > 1 vs Initial Investment'.format(modes[m].title()),
                    duration_colors,
                    duration_labels,
                    os.path.join(config['paths']['figures'],
                        '{}-initial-costs-vs-benefits-{}-growth.png'.format(modes[m],growth_rate)))


        plot_many_values_benefits(total_investment_dfs,
                    1000000,
                    'Total investment budget (million USD)',
                    'Cumulative benefits (million USD)',
                    '{} - Benefits of assets with max. BCR > 1 vs Total Investment'.format(modes[m].title()),
                    duration_colors,
                    duration_labels,
                    os.path.join(config['paths']['figures'],
                        '{}-total-costs-vs-benefits-{}-growth.png'.format(modes[m],growth_rate)))

if __name__ == '__main__':
    main()
