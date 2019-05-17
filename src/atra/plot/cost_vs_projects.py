"""Plot adaptation cost ranges (national results)
"""
import sys
import os
import ast
import matplotlib as mpl
import matplotlib.patches as mpatches
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

def main():
    config = load_config()
    duration = 30
    modes = ['road','bridge']
    modes_id = ['edge_id','bridge_id']
    for m in range(len(modes)):
        adapt_file_path = os.path.join(config['paths']['output'], 'adaptation_results',
                                   'output_adaptation_{}_{}_days_max_disruption_fixed_parameters.csv'.format(modes[m],duration))
        adapt_scenarios = pd.read_csv(adapt_file_path)
        adapt_bcr = adapt_scenarios[[modes_id[m],'max_ini_adap_cost','max_tot_adap_cost','max_benefit','max_bc_ratio']]
        adapt_bcr_max = adapt_bcr.sort_values(['max_bc_ratio'], ascending=False)
        adapt_bcr_max.drop_duplicates(subset=[modes_id[m]],keep='first',inplace=True)
        adapt_bcr_sum = adapt_bcr_max[adapt_bcr_max['max_bc_ratio']>=1][['max_ini_adap_cost','max_tot_adap_cost']].cumsum()
        plot_values(adapt_bcr_sum['max_ini_adap_cost'],
                    1000000,
                    'Initial investment (million USD)',
                    'Numbers of assets',
                    '{} - Numbers of assets with max. BCR > 1 vs Initial Investment'.format(modes[m].title()),
                    'k',
                    os.path.join(config['paths']['figures'],'{}-initial-costs-vs-bcr-{}-days.png'.format(modes[m],duration)))


        plot_values(adapt_bcr_sum['max_tot_adap_cost'],
                    1000000,
                    'Total investment (million USD)',
                    'Numbers of assets',
                    '{} - Numbers of assets with max. BCR > 1 vs Total Investment'.format(modes[m].title()),
                    'k',
                    os.path.join(config['paths']['figures'],'{}-total-costs-vs-bcr-{}-days.png'.format(modes[m],duration)))



if __name__ == '__main__':
    main()
