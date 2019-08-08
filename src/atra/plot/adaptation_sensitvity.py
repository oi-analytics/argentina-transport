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

def adaptation_sentivity_plot(input_dataframe,x_col,y_col,z_col,x_label,y_label,plot_title,plot_path,mode):
    fig, ax = plt.subplots(figsize=(8, 4))

    hdfpivot = input_dataframe[[x_col,y_col,z_col]].pivot(x_col,y_col)
    X = hdfpivot.columns.levels[1].values
    Y = hdfpivot.index.values
    Z = hdfpivot.values
    Xi,Yi = np.meshgrid(X, Y)
    plt.contourf(Yi, Xi,Z,10,alpha=0.7, cmap=cm.PuBu)
    plt.colorbar()
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_path, dpi=500)
    plt.close()

def main():
    config = load_config()
    output_path = config['paths']['output']
    duration_list = np.arange(10,110,10)
    growth_rates = np.arange(-2,4,0.2)
    modes = ['road','bridge']
    modes_id = ['edge_id','bridge_id']
    for m in range(len(modes)):
        adapt_senstivity = []
        for dur in duration_list:
            for growth in growth_rates:
                filename = 'output_adaptation_{}_{}_days_max_{}_growth_disruption_fixed_parameters.csv'.format(
                            modes[m], dur,str(round(growth,1)).replace('.','p').replace('-','minus'))

                adapt = pd.read_csv(os.path.join(output_path, 
                                                'adaptation_results', 
                                                'combined_climate',
                                                filename),encoding='utf-8-sig')
                if modes[m] == 'road':
                    adapt_bcr = adapt[[modes_id[m],'max_exposure_length','min_bc_ratio','max_bc_ratio']]
                    adapt_bcr_min = adapt_bcr.groupby([modes_id[m]])['max_exposure_length','min_bc_ratio'].min().reset_index()
                    adapt_bcr_max = adapt_bcr.groupby([modes_id[m]])['max_exposure_length','max_bc_ratio'].max().reset_index()
                    tot_max = len(adapt_bcr_max[adapt_bcr_max['max_bc_ratio'] > 1].index)
                    tot_max_length = 0.001*adapt_bcr_max[adapt_bcr_max['max_bc_ratio'] > 1]['max_exposure_length'].sum()
                    tot_max_perc = 100*len(adapt_bcr_max[adapt_bcr_max['max_bc_ratio'] > 1].index)/len(adapt_bcr_max.index)
                    tot_robust = len(adapt_bcr_min[adapt_bcr_min['min_bc_ratio'] > 1].index)
                    tot_robust_length = 0.001*adapt_bcr_min[adapt_bcr_min['min_bc_ratio'] > 1]['max_exposure_length'].sum()
                    tot_robust_perc = 100*len(adapt_bcr_min[adapt_bcr_min['min_bc_ratio'] > 1].index)/len(adapt_bcr_min.index)

                    adapt_senstivity.append((dur,round(growth,1),
                                            tot_max,tot_max_length,tot_max_perc,
                                            tot_robust,tot_robust_length,tot_robust_perc))
                else:
                    adapt_bcr = adapt[[modes_id[m],'min_bc_ratio','max_bc_ratio']]
                    adapt_bcr_min = adapt_bcr.groupby(modes_id[m])['min_bc_ratio'].min().reset_index()
                    adapt_bcr_max = adapt_bcr.groupby(modes_id[m])['max_bc_ratio'].max().reset_index()
                    tot_max = len(adapt_bcr_max[adapt_bcr_max['max_bc_ratio'] > 1].index)
                    tot_max_perc = 100*len(adapt_bcr_max[adapt_bcr_max['max_bc_ratio'] > 1].index)/len(adapt_bcr_max.index)
                    tot_robust = len(adapt_bcr_min[adapt_bcr_min['min_bc_ratio'] > 1].index)
                    tot_robust_perc = 100*len(adapt_bcr_min[adapt_bcr_min['min_bc_ratio'] > 1].index)/len(adapt_bcr_min.index)

                    adapt_senstivity.append((dur,round(growth,1),
                                            tot_max,tot_max_perc,
                                            tot_robust,tot_robust_perc))

                print ('* Done {} {} days disruption and {} growth'.format(modes[m],dur,round(growth,1)))

        
        if modes[m] == 'road':
            adapt_senstivity = pd.DataFrame(adapt_senstivity,
                                            columns=['duration',
                                                    'growth',
                                                    'max_robust','max_robust_length',
                                                    'max_robust_percent',
                                                    'tot_robust','tot_robust_length','tot_robust_percent'])
            adapt_senstivity.to_csv(os.path.join(output_path,'network_stats','{}_adaptation_sensitvities_lengths.csv'.format(modes[m])),index=False)
            adaptation_sentivity_plot(adapt_senstivity,'duration','growth',
                                'max_robust_length','Maximum duration of disruption (days)',
                                'Annual GDP growth (%)',
                                '{} - Kilometers of roads for which Max. BCR > 1'.format(modes[m].title()),
                                os.path.join(config['paths']['figures'],
                                        '{}-adapt-senstivity-max-robust-length.png'.format(modes[m])),
                                modes[m])

            adaptation_sentivity_plot(adapt_senstivity,'duration','growth',
                                'tot_robust_length','Maximum duration of disruption (days)',
                                'Annual GDP growth (%)',
                                '{} - Kilometers of roads for which Min.- Max. BCR > 1'.format(modes[m].title()),
                                os.path.join(config['paths']['figures'],
                                        '{}-adapt-senstivity-tot-robust-length.png'.format(modes[m])),
                                modes[m])

            adaptation_sentivity_plot(adapt_senstivity,'duration','growth',
                                'max_robust','Maximum duration of disruption (days)',
                                'Annual GDP growth (%)',
                                '{} - Numbers of roads for which Max. BCR > 1'.format(modes[m].title()),
                                os.path.join(config['paths']['figures'],
                                        '{}-adapt-senstivity-max-robust-numbers.png'.format(modes[m])),
                                modes[m])

            adaptation_sentivity_plot(adapt_senstivity,'duration','growth',
                                'tot_robust','Maximum duration of disruption (days)',
                                'Annual GDP growth (%)',
                                '{} - Numbers of roads for which Min.- Max. BCR > 1'.format(modes[m].title()),
                                os.path.join(config['paths']['figures'],
                                        '{}-adapt-senstivity-tot-robust-numbers.png'.format(modes[m])),
                                modes[m])
        else:
            adapt_senstivity = pd.DataFrame(adapt_senstivity,
                                            columns=['duration',
                                                    'growth',
                                                    'max_robust',
                                                    'max_robust_percent',
                                                    'tot_robust',
                                                    'tot_robust_percent'])
            adapt_senstivity.to_csv(os.path.join(output_path,
                                            'network_stats',
                                            '{}_adaptation_sensitvities.csv'.format(modes[m])),index=False)
            adaptation_sentivity_plot(adapt_senstivity,'duration','growth',
                                'max_robust','Maximum duration of disruption (days)',
                                'Annual GDP growth (%)',
                                '{} - Numbers of assets with Max. BCR > 1'.format(modes[m].title()),
                                os.path.join(config['paths']['figures'],
                                        '{}-adapt-senstivity-max-robust-numbers.png'.format(modes[m])),
                                modes[m])

            adaptation_sentivity_plot(adapt_senstivity,'duration','growth',
                                'tot_robust','Maximum duration of disruption (days)',
                                'Annual GDP growth (%)',
                                '{} - Numbers of assets with Min.- Max. BCR > 1'.format(modes[m].title()),
                                os.path.join(config['paths']['figures'],
                                        '{}-adapt-senstivity-tot-robust-numbers.png'.format(modes[m])),
                                modes[m])




if __name__ == '__main__':
    main()
