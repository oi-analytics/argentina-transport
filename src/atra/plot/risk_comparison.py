"""Road network risks and adaptation maps
"""
import os
import sys
from collections import defaultdict
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

def plot_many_ranges(input_dfs, division_factor,x_label, y_label,plot_title,plot_color,plot_labels,plot_file_path):
    fig, ax = plt.subplots(figsize=(8, 4))

    length = []
    for i in range(len(input_dfs)):
        input_data = input_dfs[i]

        vals_min_max = []
        for a, b in input_data.itertuples(index=False):
            if a < b:
                min_, max_ = a, b
            else:
                min_, max_ = b, a
            vals_min_max.append((min_, max_))

        # vals_min_max.sort(key=lambda el: el[1])

        vals_min_max = list(zip(*vals_min_max))

        percentlies = 100.0*np.arange(0,len(vals_min_max[0]))/len(vals_min_max[0])
        length.append(len(vals_min_max[0]))
        ax.plot(percentlies,
            1.0*np.array(vals_min_max[0])/division_factor,
            linewidth=0.5,
            color=plot_color[i]
        )
        ax.plot(percentlies,
            1.0*np.array(vals_min_max[1])/division_factor,
            linewidth=0.5,
            color=plot_color[i]
        )
        ax.fill_between(percentlies,
            1.0*np.array(vals_min_max[0])/division_factor,
            1.0*np.array(vals_min_max[1])/division_factor,
            alpha=0.5,
            edgecolor=None,
            facecolor=plot_color[i],
            label = plot_labels[i]
        )

    length = max(length)
    if 'BCR' in y_label:
        ax.plot(np.arange(0,100),
            np.array([1]*100),
            linewidth=0.5,
            color='red',
            label = 'BCR = 1'
        )
        # ax.set_xscale('log')
        ax.set_yscale('log')

    # ax.tick_params(axis='x', rotation=45)
    ax.legend(loc='upper left')
    plt.xlabel(x_label, fontweight='bold')
    plt.ylabel(y_label, fontweight='bold')
    plt.title(plot_title)

    plt.tight_layout()
    plt.savefig(plot_file_path, dpi=500)
    plt.close()

def main():
    config = load_config()
    output_path = config['paths']['output']
    durations = [10,20,30]
    value_thr =100000
    change_colors = ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#969696','#fee08b','#fdae61','#f46d43','#d73027']
    change_labels = ['< -100','-100 to -50','-50 to -10','-10 to 0','0','0 to 10','10 to 50','50 to 100',' > 100']
    change_ranges = [(-1e10,-100),(-100,-50),(-50,-10),(-10,0),(0,1e-7),(1e-7,10),(10,50),(50,100),(100,1e10)]

    modes = ['road','bridge']
    duration_colors = ['#f03b20','#6baed6','#3182bd','#08519c']
    duration_labels = ['EAD'] + ['EAEL for max. {} days disruption events'.format(d) for d in durations]

    for m in range(len(modes)):
        # change_df = change_df[change_df['future'] != -1]
        risk_df = pd.read_csv(os.path.join(output_path,
            'risk_results',
            '{}_combined_climate_risks.csv'.format(modes[m])
            )
        )
        risk_df = risk_df[risk_df['climate_scenario'] == 'Baseline']
        risk_df = risk_df[(risk_df['max_eael_per_day'] + risk_df['ead']) > value_thr]
        risk_df['zeroes'] = [0]*len(risk_df.index)
        # risk_ranges = [risk_df['zeroes'].values.tolist(),risk_df['ead'].values.tolist()]
        risk_cols = ['zeroes','ead']
        fig, ax = plt.subplots(figsize=(8, 4))
        for d in range(len(durations)):
            risk_df['max_risk_{}_days'.format(durations[d])] = durations[d]*risk_df['max_eael_per_day'] + risk_df['ead']
            risk_cols.append('max_risk_{}_days'.format(durations[d]))
            # risk_ranges.append(risk_df['max_risk_{}_days'.format(durations[d])].values.tolist())
            # if d == 0:
            #     risk_ranges.append(risk_df[['ead','max_risk_{}_days'.format(durations[d])]])
            # else:
            #     risk_ranges.append(risk_df[['max_risk_{}_days'.format(durations[d]),'max_risk_{}_days'.format(durations[d-1])]])

        risk_df = risk_df[risk_cols].sort_values(['max_risk_{}_days'.format(durations[-1])], ascending=True)
        risk_ranges = []
        for c in range(len(risk_cols)-1):
            risk_ranges.append(risk_df[[risk_cols[c],risk_cols[c+1]]])

        plot_many_ranges(risk_ranges, 
                        1e6,
                        'Percentile rank (%)', 
                        'EAD and EAEL (million US$)',
                        '{} - EAD and EAEL ranges for Total Risks > {:,} US$'.format(modes[m].title(),value_thr),
                        duration_colors,
                        duration_labels,
                        os.path.join(config['paths']['figures'],
                                '{}-changing-risks-with-days.png'.format(modes[m])))

    


if __name__ == '__main__':
    main()
